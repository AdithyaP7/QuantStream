import pandas as pd
import snowflake.connector # type: ignore

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
    AND DAYOFWEEK(RECORD_CONTENT:timestamp_utc::TIMESTAMP_NTZ) BETWEEN 2 AND 6  -- Monday to Friday
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

from prophet import Prophet
model = Prophet()
model.fit(df_prophet)


future = model.make_future_dataframe(periods=60, freq = 'min')
forecast = model.predict(future)

from prophet.plot import plot_plotly, plot_components_plotly
from plotly.subplots import make_subplots
import plotly.graph_objects as go
fig1 = plot_plotly(model, forecast)
fig2 = plot_components_plotly(model, forecast)

combined_fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=("Forecast", "Components"),
    vertical_spacing=0.2
)

for trace in fig1.data:
    combined_fig.add_trace(trace, row=1, col=1)

for trace in fig2.data:
    combined_fig.add_trace(trace, row=2, col=1)

combined_fig.update_layout(height=1000, title_text="Stock Forecast and Components")
combined_fig.show()


