from flask import Flask, jsonify, render_template
from snowflake_utils import query_snowflake
from prophet import Prophet
import pandas as pd

app = Flask(__name__)

STOCKS = ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'IBM', 'NFLX']

def build_stock_query(symbol):
    return f"""
        SELECT
            RECORD_CONTENT:stock_symbol::STRING AS stock_symbol,
            RECORD_CONTENT:timestamp_utc::TIMESTAMP_NTZ AS timestamp_utc,
            RECORD_CONTENT:open_price::FLOAT AS open_price,
            RECORD_CONTENT:close_price::FLOAT AS close_price,
            RECORD_CONTENT:current_price::FLOAT AS current_price
        FROM
            STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
        WHERE
            RECORD_CONTENT:stock_symbol::STRING = '{symbol}'
            AND DAYOFWEEK(RECORD_CONTENT:timestamp_utc::TIMESTAMP_NTZ) BETWEEN 2 AND 6
        ORDER BY
            timestamp_utc
    """


@app.context_processor
def inject_stocks():
    return dict(stocks=STOCKS)


@app.route('/')
def home():
    # 🛠 Query ALL latest rows in one shot
    sql = f"""
        WITH latest_per_stock AS (
            SELECT 
                RECORD_CONTENT:stock_symbol::STRING AS stock_symbol,
                RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
                RECORD_CONTENT:close_price::FLOAT AS close_price,
                ROW_NUMBER() OVER (PARTITION BY RECORD_CONTENT:stock_symbol::STRING ORDER BY RECORD_CONTENT:timestamp_utc::TIMESTAMP DESC) AS rn
            FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
            WHERE RECORD_CONTENT:stock_symbol::STRING IN ({','.join(f"'{s}'" for s in STOCKS)})
        )
        SELECT stock_symbol, timestamp_utc, close_price
        FROM latest_per_stock
        WHERE rn = 1
    """

    df = query_snowflake(sql)

    # 🧹 Normalize column names
    df.columns = df.columns.str.lower()

    latest_data = {}

    # 🗺 Map stock -> (price, timestamp)
    for stock in STOCKS:
        stock_row = df[df['stock_symbol'] == stock]

        if not stock_row.empty:
            latest_price = stock_row.iloc[0]['close_price']
            latest_time = pd.to_datetime(stock_row.iloc[0]['timestamp_utc']).strftime('%Y-%m-%d %H:%M')
            latest_data[stock] = {'price': latest_price, 'timestamp': latest_time}
        else:
            latest_data[stock] = {'price': None, 'timestamp': None}

    return render_template('home.html', stocks=STOCKS, latest_data=latest_data, title="Stock Forecast Dashboard")

def run_lstm_forecast(df, future_steps=50):
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from tensorflow.keras.callbacks import EarlyStopping

    # 1. Preprocessing
    df = df.copy()
    df.columns = df.columns.str.lower()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    df = df.dropna()
    df = df.sort_values('timestamp_utc')
    series = df['close_price'].values.reshape(-1, 1)

    # 2. Create log-returns
    log_ret = np.log(series[1:] / series[:-1]).flatten()
    series = log_ret.reshape(-1, 1)

    # 🚨 Clean any NaNs, infs, -infs
    series = series[np.isfinite(series)]
    series = series.reshape(-1, 1)

    # ──────────────────── 3. Scaling ─────────────────────────────
    scaler = StandardScaler()
    series_s = scaler.fit_transform(series)

    # 4. Build sliding windows
    WINDOW = 20

    def make_dataset(arr, window):
        X, y = [], []
        for i in range(len(arr) - window):
            X.append(arr[i : i + window, 0])
            y.append(arr[i + window, 0])
        return np.array(X), np.array(y)

    X, y = make_dataset(series_s, WINDOW)
    if len(X) == 0:
        raise ValueError("Not enough data points for LSTM training.")

    X = X.reshape(-1, WINDOW, 1)

    # 5. Model
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(WINDOW, 1)),
        LSTM(25),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse")

    # 6. Fit
    es = EarlyStopping("loss", patience=5, restore_best_weights=True)
    model.fit(X, y, epochs=20, batch_size=32, callbacks=[es], verbose=0)

    # 7. Forecast
    history_s = list(series_s[-WINDOW:, 0])
    future_s = []

    for _ in range(future_steps):
        x = np.array(history_s[-WINDOW:]).reshape(1, WINDOW, 1)
        nxt = model.predict(x, verbose=0)[0, 0]
        future_s.append(nxt)
        history_s.append(nxt)

    # 8. Inverse scale
    future_r = scaler.inverse_transform(np.array(future_s).reshape(-1, 1)).flatten()

    # 9. Return to price
    last_price = df['close_price'].iloc[-1]
    prices = [last_price]
    for r in future_r:
        prices.append(prices[-1] * np.exp(r))
    prices = np.array(prices[1:])

    # 10. Build future timestamps
    freq = pd.infer_freq(df['timestamp_utc'])
    if freq is None or freq not in ['H', '1H']:
        freq = 'H'  # fallback to hourly

    future_idx = pd.date_range(df['timestamp_utc'].iloc[-1] + pd.Timedelta(hours=1), periods=future_steps, freq=freq)

    forecast_df = pd.DataFrame({
        'ds': future_idx,             # keep same Prophet naming
        'yhat': prices,               # predicted price
        'yhat_lower': prices * 0.98,   # dummy lower bound (2% range)
        'yhat_upper': prices * 1.02    # dummy upper bound (2% range)
    })
    return forecast_df


def run_prophet_forecast(df):
    df.columns = df.columns.str.lower()
    prophet_df = df.rename(columns={'timestamp_utc': 'ds', 'close_price': 'y'})
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'], errors='coerce')
    prophet_df['ds'] = prophet_df['ds'].dt.tz_localize(None)
    prophet_df = prophet_df.dropna(subset=['ds', 'y'])

    model = Prophet(daily_seasonality=True)
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=24*7, freq='H')
    forecast = model.predict(future)

    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

@app.route('/api/stock/<symbol>')
def api_stock(symbol):
    sql = build_stock_query(symbol)
    df = query_snowflake(sql)
    return jsonify(df.to_dict(orient="records"))

@app.route('/api/forecast/<symbol>')
def api_forecast(symbol):
    sql = build_stock_query(symbol)
    df = query_snowflake(sql)
    forecast_df = run_prophet_forecast(df)
    return jsonify(forecast_df.to_dict(orient="records"))

@app.route('/stock/<symbol>')
def stock(symbol):
    sql = build_stock_query(symbol)
    df = query_snowflake(sql)
    df.columns = df.columns.str.lower()

    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    df['timestamp_utc'] = df['timestamp_utc'].dt.strftime('%Y-%m-%d %H:%M')
    labels = df['timestamp_utc'].tolist()
    prices = df['close_price'].tolist()
    return render_template('stock.html', symbol=symbol, labels=labels, prices=prices, stocks=STOCKS, title=f"{symbol} Stock History")

# def train_lstm_forecast(df, future_steps=50):
#     import numpy as np
#     import pandas as pd
#     import matplotlib.pyplot as plt
#     from sklearn.preprocessing import StandardScaler
#     from sklearn.metrics import mean_squared_error, r2_score
#     import tensorflow as tf
#     from tensorflow.keras.models import Sequential
#     from tensorflow.keras.layers import LSTM, Dense
#     from tensorflow.keras.callbacks import EarlyStopping

#     # ──────────────────── 1. Preprocessing ──────────────────────
#     df = df.copy()
#     df.columns = df.columns.str.lower()
#     df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
#     df = df.dropna()
#     df = df.sort_values('timestamp_utc')
#     series = df['close_price'].values.reshape(-1, 1)

#     # ──────────────────── 2. Compute log-returns ─────────────────
#     log_ret = np.log(series[1:] / series[:-1]).flatten()
#     series = log_ret.reshape(-1, 1)

#     # ──────────────────── 3. Scaling ─────────────────────────────
#     scaler = StandardScaler()
#     series_s = scaler.fit_transform(series)

#     # ──────────────────── 4. Build sliding windows ───────────────
#     WINDOW = 20

#     def make_dataset(arr, window):
#         X, y = [], []
#         for i in range(len(arr) - window):
#             X.append(arr[i : i + window, 0])
#             y.append(arr[i + window, 0])
#         return np.array(X), np.array(y)

#     X, y = make_dataset(series_s, WINDOW)
#     if len(X) == 0:
#         raise ValueError("Not enough data points for LSTM training.")

#     X = X.reshape(-1, WINDOW, 1)

#     # ──────────────────── 5. Model ───────────────────────────────
#     model = Sequential([
#         LSTM(50, return_sequences=True, input_shape=(WINDOW, 1)),
#         LSTM(25),
#         Dense(1)
#     ])
#     model.compile(optimizer="adam", loss="mse")

#     # ──────────────────── 6. Train ───────────────────────────────
#     es = EarlyStopping("loss", patience=5, restore_best_weights=True)
#     model.fit(X, y, epochs=20, batch_size=32, callbacks=[es], verbose=0)

#     # ──────────────────── 7. Evaluation on known data ────────────
#     pred_s = model.predict(X).flatten()

#     # Inverse scale
#     def inv_scaled(a):
#         return scaler.inverse_transform(a.reshape(-1, 1)).flatten()

#     y_true_r = inv_scaled(y)
#     y_pred_r = inv_scaled(pred_s)

#     # Reconstruct price paths
#     def returns_to_price(start_price, returns):
#         prices = [start_price]
#         for r in returns:
#             prices.append(prices[-1] * np.exp(r))
#         return np.array(prices[1:])

#     anchor_price = df['close_price'].iloc[WINDOW - 1]

#     y_true_p = returns_to_price(anchor_price, y_true_r)
#     y_pred_p = returns_to_price(anchor_price, y_pred_r)

#     # Metrics
#     rmse = mean_squared_error(y_true_p, y_pred_p, squared=False)
#     r2 = r2_score(y_true_p, y_pred_p)

#     print(f"\n=== LSTM Evaluation (train_lstm_forecast) ===")
#     print(f"RMSE: {rmse:.4f}")
#     print(f"R²: {r2:.4f}")
#     print("=============================================\n")

#     # ──────────────────── 8. Future Forecast ────────────────────
#     history_s = list(series_s[-WINDOW:, 0])
#     future_s = []

#     for _ in range(future_steps):
#         x = np.array(history_s[-WINDOW:]).reshape(1, WINDOW, 1)
#         nxt = model.predict(x, verbose=0)[0, 0]
#         future_s.append(nxt)
#         history_s.append(nxt)

#     future_r = inv_scaled(np.array(future_s))
#     last_price = df['close_price'].iloc[-1]
#     future_p = returns_to_price(last_price, future_r)

#     # Build future timeline
#     freq = pd.infer_freq(df['timestamp_utc'])
#     if freq is None or freq not in ['H', '1H']:
#         freq = 'H'

#     future_idx = pd.date_range(df['timestamp_utc'].iloc[-1] + pd.Timedelta(hours=1), periods=future_steps, freq=freq)

#     # ──────────────────── 9. Plot real vs predicted vs forecast ─
#     idx_real = df['timestamp_utc'].iloc[WINDOW:].reset_index(drop=True)

#     plt.figure(figsize=(14,6))


#     # ──────────────────── 10. Return forecast dataframe ─────────
#     forecast_df = pd.DataFrame({'timestamp_utc': future_idx, 'predicted_price': future_p})
#     return forecast_df

def train_lstm_forecast(df, future_steps=50):
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from tensorflow.keras.callbacks import EarlyStopping

    # 1. Preprocessing
    df = df.copy()
    df.columns = df.columns.str.lower()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    df = df.dropna()
    df = df.sort_values('timestamp_utc')
    series = df['close_price'].values.reshape(-1, 1)

    # 2. Create log-returns
    log_ret = np.log(series[1:] / series[:-1])
    log_ret = log_ret.flatten()
    series = log_ret.reshape(-1, 1)

    # 3. Scale
    scaler = StandardScaler()
    series_s = scaler.fit_transform(series)

    # 4. Build sliding windows
    WINDOW = 20

    def make_dataset(arr, window):
        X, y = [], []
        for i in range(len(arr) - window):
            X.append(arr[i : i + window, 0])
            y.append(arr[i + window, 0])
        return np.array(X), np.array(y)

    X, y = make_dataset(series_s, WINDOW)
    if len(X) == 0:
        raise ValueError("Not enough data points for LSTM training.")

    X = X.reshape(-1, WINDOW, 1)

    # 5. Model
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(WINDOW, 1)),
        LSTM(25),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse")

    # 6. Fit
    es = EarlyStopping("loss", patience=5, restore_best_weights=True)
    model.fit(X, y, epochs=20, batch_size=32, callbacks=[es], verbose=0)

    # 7. Forecast
    history_s = list(series_s[-WINDOW:, 0])
    future_s = []

    for _ in range(future_steps):
        x = np.array(history_s[-WINDOW:]).reshape(1, WINDOW, 1)
        nxt = model.predict(x, verbose=0)[0, 0]
        future_s.append(nxt)
        history_s.append(nxt)

    # 8. Inverse scale
    future_r = scaler.inverse_transform(np.array(future_s).reshape(-1, 1)).flatten()

    # 9. Return to price
    last_price = df['close_price'].iloc[-1]
    prices = [last_price]
    for r in future_r:
        prices.append(prices[-1] * np.exp(r))
    prices = np.array(prices[1:])

    freq = pd.infer_freq(df['timestamp_utc'])
    if freq is None or freq not in ['H', '1H']:
        freq = 'H'  # fallback to hourly

    future_idx = pd.date_range(df['timestamp_utc'].iloc[-1] + pd.Timedelta(hours=1), periods=future_steps, freq=freq)

    forecast_df = pd.DataFrame({'timestamp_utc': future_idx, 'predicted_price': prices})

    historical_df = df[['timestamp_utc', 'close_price']].copy()

    return forecast_df, historical_df


@app.route('/forecast/<symbol>')
def forecast(symbol):
    sql = f"""
        SELECT 
            RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
            RECORD_CONTENT:close_price::FLOAT AS close_price
        FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR_SYNTHETIC
        WHERE RECORD_CONTENT:stock_symbol::STRING = '{symbol}'
        ORDER BY timestamp_utc
    """

    df = query_snowflake(sql)

    try:
        forecast_df, historical_df = train_lstm_forecast(df, future_steps=50)

        forecast_labels = forecast_df["timestamp_utc"].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
        forecast_prices = forecast_df["predicted_price"].tolist()

        historical_labels = historical_df['timestamp_utc'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
        historical_prices = historical_df['close_price'].tolist()

        combined = list(zip(reversed(forecast_labels+historical_labels), reversed(forecast_prices+historical_prices)))

        return render_template('forecast.html',
            symbol=symbol,
            f_labels=forecast_labels,
            f_prices=forecast_prices,
            h_labels=historical_labels,
            h_prices=historical_prices,
            combined=combined,
            stocks=STOCKS,
            title=f"{symbol} Forecast"
        )
    except Exception as e:
        return f"Error generating forecast for {symbol}: {str(e)}", 500
    # df.columns = df.columns.str.lower()
    # df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    # df = df.dropna()

    # prophet_df = df.rename(columns={'timestamp_utc': 'ds', 'close_price': 'y'})
    # prophet_df['ds'] = prophet_df['ds'].dt.tz_localize(None)

    # model = Prophet(daily_seasonality=True)
    # model.fit(prophet_df)

    # future = model.make_future_dataframe(periods=24*7, freq='H')
    # forecast = model.predict(future)

    # future_forecast = forecast[forecast['ds'] > prophet_df['ds'].max()]

    # labels = future_forecast['ds'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    # prices = future_forecast['yhat'].tolist()

    # combined = list(zip(reversed(labels), reversed(prices)))

    # return render_template('forecast.html',
    #     symbol=symbol,
    #     labels=labels,
    #     prices=prices,
    #     combined=combined,
    #     stocks=STOCKS,
    #     title=f"{symbol} Forecast"
    # )



@app.route('/dashboard/<symbol>')
def dashboard(symbol):
    sql = build_stock_query(symbol)
    df = query_snowflake(sql)

    df.columns = df.columns.str.lower()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    df['timestamp_utc'] = df['timestamp_utc'].dt.tz_localize(None)
    df = df.dropna()

    forecast_df = run_prophet_forecast(df)

    historical = df[['timestamp_utc', 'current_price']].rename(columns={'timestamp_utc': 'ds', 'current_price': 'y'})
    forecast = forecast_df[['ds', 'yhat']]

    combined = pd.concat([
        historical.set_index('ds'),
        forecast.set_index('ds')
    ])

    combined = combined[~combined.index.duplicated(keep='first')]
    combined = combined.sort_index()

    labels = combined.index.strftime('%Y-%m-%d %H:%M').tolist()
    values = combined['y'].fillna(combined['yhat']).tolist()

    return render_template('dashboard.html', symbol=symbol, labels=labels, values=values, stocks=STOCKS, title=f"{symbol} Dashboard")

@app.route('/api/latest_prices')
def latest_prices():
    latest_data = {}

    for stock in STOCKS:
        sql = f"""
            SELECT 
                RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
                RECORD_CONTENT:close_price::FLOAT AS close_price
            FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
            WHERE RECORD_CONTENT:stock_symbol::STRING = '{stock}'
            ORDER BY timestamp_utc DESC
            LIMIT 1
        """
        df = query_snowflake(sql)

        df.columns = df.columns.str.lower()

        if not df.empty and 'close_price' in df.columns:
            latest_price = df.iloc[0]['close_price']
            latest_time = pd.to_datetime(df.iloc[0]['timestamp_utc']).strftime('%Y-%m-%d %H:%M')
            latest_data[stock] = {'price': latest_price, 'timestamp': latest_time}
        else:
            latest_data[stock] = {'price': None, 'timestamp': None}

    return jsonify(latest_data)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
