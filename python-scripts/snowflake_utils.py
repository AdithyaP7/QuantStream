import snowflake.connector
import pandas as pd

def get_snowflake_connection():
    conn = snowflake.connector.connect(
        user='QUANTSTREAM',
        password='Quantstream123',
        account='wrbnhoo-xib79361',  
        warehouse='COMPUTE_WH',
        database='STOCK_DB',
        schema='STOCK_SCHEMA',
        role='ACCOUNTADMIN'  # Optional but recommended
    )
    return conn

def query_snowflake(sql_query):
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        df = cursor.fetch_pandas_all()  # You get a nice Pandas dataframe
    finally:
        cursor.close()
        conn.close()
    return df
