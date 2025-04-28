import pandas as pd
import snowflake.connector
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly
from plotly.subplots import make_subplots
import plotly.graph_objects as go


conn = snowflake.connector.connect(
    user='quantstream',
    password='Quantstream123',
    account='wrbnhoo-xib79361',
    warehouse='COMPUTE_WH',
    database='STOCK_DB',
    schema='STOCK_SCHEMA'
)

# query = """
#         SELECT 
#             RECORD_CONTENT:stock_symbol::STRING AS stock_symbol,
#             RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
#             RECORD_CONTENT:open_price::FLOAT AS open_price,
#             RECORD_CONTENT:close_price::FLOAT AS close_price,
#             RECORD_CONTENT:current_price::FLOAT AS current_price
#         FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
#         WHERE RECORD_CONTENT:stock_symbol::STRING = 'AAPL'
#         ORDER BY timestamp_utc
#     """
query = """
SELECT
    RECORD_CONTENT:stock_symbol::STRING AS stock_symbol,
    RECORD_CONTENT:timestamp_utc::TIMESTAMP_NTZ AS timestamp_utc,
    RECORD_CONTENT:open_price::FLOAT AS open_price,
    RECORD_CONTENT:close_price::FLOAT AS close_price,
    RECORD_CONTENT:current_price::FLOAT AS current_price
FROM
    STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR_SYNTHETIC
WHERE
    RECORD_CONTENT:stock_symbol::STRING = 'NFLX'
    AND DAYOFWEEK(RECORD_CONTENT:timestamp_utc::TIMESTAMP_NTZ) BETWEEN 2 AND 6
ORDER BY
    timestamp_utc ASC

    """
      

df = pd.read_sql(query, conn)
conn.close()
print(df.head())

df_prophet = df[['TIMESTAMP_UTC', 'CURRENT_PRICE']]
df_prophet = df_prophet.rename(columns={'TIMESTAMP_UTC': 'ds', 'CURRENT_PRICE': 'y'})
# df_prophet = df_prophet[df_prophet['ds'].dt.dayofweek < 5]
print (df_prophet.head())
df_prophet['ds'] = pd.to_datetime(df_prophet['ds']).dt.tz_localize(None)

unique_days = df_prophet['ds'].dt.date.unique()

# Split
train_days = unique_days[:3:]
val_days = unique_days[3::]

train_df = df_prophet[df_prophet['ds'].dt.date.isin(train_days)]
val_df = df_prophet[df_prophet['ds'].dt.date.isin(val_days)]

print(f"Training on {len(train_df)} points from days: {train_days}")
print(f"Validating on {len(val_df)} points from days: {val_days}")

# print (df_prophet["ds"].unique())

# --- Train Prophet ---
model = Prophet()
model.fit(train_df)

# --- Forecast for validation period ---
# How many periods into the future?
future = model.make_future_dataframe(
    periods=60,
    freq='min'  # change to 'H' if your data is hourly!
)

forecast = model.predict(future)

last_train_date = train_df['ds'].max()
print (last_train_date)

# Filter forecast to only future dates
future_forecast = forecast[forecast['ds'] > (last_train_date)]
print (future_forecast.head())
fig = go.Figure()

# Line plot of prediction
fig.add_trace(go.Scatter(
    x=future_forecast['ds'], 
    y=future_forecast['yhat'], 
    mode='lines',
    name='Predicted'
))

# Confidence interval (yhat_lower, yhat_upper)
fig.add_trace(go.Scatter(
    x=future_forecast['ds'],
    y=future_forecast['yhat_upper'],
    mode='lines',
    line=dict(width=0),
    showlegend=False
))
fig.add_trace(go.Scatter(
    x=future_forecast['ds'],
    y=future_forecast['yhat_lower'],
    mode='lines',
    fill='tonexty',  # Fill between upper and lower
    line=dict(width=0),
    fillcolor='rgba(0,100,80,0.2)',
    showlegend=False
))

fig.update_layout(title='Forecasted Stock Price (Only Future)',
                  xaxis_title='Date',
                  yaxis_title='Price')

fig.show()
# from prophet import Prophet
# model = Prophet()
# model.fit(df_prophet)


# future = model.make_future_dataframe(periods=60, freq = 'min')
# forecast = model.predict(future)


# fig1 = plot_plotly(model, forecast)
# fig2 = plot_components_plotly(model, forecast)

# combined_fig = make_subplots(
#     rows=2, cols=1,
#     subplot_titles=("Forecast", "Components"),
#     vertical_spacing=0.2
# )

# for trace in fig1.data:
#     combined_fig.add_trace(trace, row=1, col=1)

# for trace in fig2.data:
#     combined_fig.add_trace(trace, row=2, col=1)

# combined_fig.update_layout(height=1000, title_text="Stock Forecast and Components")
# combined_fig.show()


future_forecast.to_csv('python-scripts/forecast_output.csv', index=False)
merged = pd.merge(
    df_prophet, 
    future_forecast[['ds', 'yhat']], 
    on='ds', 
    how='inner'
)
merged.to_csv('python-scripts/merged_output.csv', index=False)

# print (forecast["ds"].unique())
# print (df_prophet["ds"].unique())
# print (merged["ds"].unique())