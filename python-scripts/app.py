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
            STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR_SYNTHETIC
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

    df.columns = df.columns.str.lower()
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], errors='coerce')
    df = df.dropna()

    prophet_df = df.rename(columns={'timestamp_utc': 'ds', 'close_price': 'y'})
    prophet_df['ds'] = prophet_df['ds'].dt.tz_localize(None)

    model = Prophet(daily_seasonality=True)
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=24*7, freq='H')
    forecast = model.predict(future)

    future_forecast = forecast[forecast['ds'] > prophet_df['ds'].max()]

    labels = future_forecast['ds'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    prices = future_forecast['yhat'].tolist()

    combined = list(zip(reversed(labels), reversed(prices)))

    return render_template('forecast.html',
        symbol=symbol,
        labels=labels,
        prices=prices,
        combined=combined,
        stocks=STOCKS,
        title=f"{symbol} Forecast"
    )



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
