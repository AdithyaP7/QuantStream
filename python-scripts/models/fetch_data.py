# fetch data connected to snowlfkae. isolate model training and pickle the model for eval
# save model results to csv so it can be visualized independently

#workflow for lstm^, can be altered to work for prophet


import pandas as pd
import snowflake.connector

conn = snowflake.connector.connect(
    user='quantstream',
    password='Quantstream123',
    account='wrbnhoo-xib79361',
    warehouse='COMPUTE_WH',
    database='STOCK_DB',
    schema='STOCK_SCHEMA'
)

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
df.to_csv("fetched_data.csv", index=False)