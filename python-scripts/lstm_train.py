import pandas as pd
import snowflake.connector
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import numpy as np

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
print(df.head())

df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
df.set_index('TIMESTAMP_UTC', inplace=True)
df.sort_index(inplace=True)

scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(df[['CURRENT_PRICE']])

# Create sequences for LSTM
sequence_length = 60  # Use the past 60 minutes to predict the next value
X, y = [], []
for i in range(sequence_length, len(scaled_data)):
    X.append(scaled_data[i-sequence_length:i, 0])
    y.append(scaled_data[i, 0])

X, y = np.array(X), np.array(y)
X = np.reshape(X, (X.shape[0], X.shape[1], 1))  # Reshape for LSTM input

# Build LSTM model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=False))
model.add(Dropout(0.2))
model.add(Dense(units=25))
model.add(Dense(units=1))

model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
model.fit(X, y, batch_size=32, epochs=10)

# Predict and evaluate
predicted_prices = model.predict(X)
predicted_prices = scaler.inverse_transform(predicted_prices)

# Add predictions to the DataFrame for visualization
df['Predicted_Price'] = np.nan
df.iloc[sequence_length:, df.columns.get_loc('Predicted_Price')] = predicted_prices.flatten()

print(df[['CURRENT_PRICE', 'Predicted_Price']].tail())

df.to_csv('lstm_output.csv', index=False)