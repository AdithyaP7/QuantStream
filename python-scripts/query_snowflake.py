from snowflake_utils import query_snowflake

sql = """
SELECT RECORD_CONTENT:stock_symbol::STRING AS stock_symbol,
       RECORD_CONTENT:timestamp_utc::STRING AS timestamp_utc,
       RECORD_CONTENT:close_price::FLOAT AS close_price
FROM STOCK_DB.STOCK_SCHEMA.TEST_CONNECTOR
WHERE RECORD_CONTENT:stock_symbol::STRING = 'AAPL'
ORDER BY timestamp_utc
"""

df = query_snowflake(sql)
print(df.head())