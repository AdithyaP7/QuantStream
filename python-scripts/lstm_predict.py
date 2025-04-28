import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

model_file = "models/lstm_model.pkl"
with open(model_file, "rb") as file:
    model = pickle.load(file)


df = pd.read_csv("HistoricalData/AAPL_ohlc_data.csv")
df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'])
df.set_index('DATE_TIME', inplace=True)
df.sort_index(inplace=True)
sequence_length = 60
adjusted_index = df.index[sequence_length:]

scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(df[['CLOSE_PRICE']])
X, y = [], []
for i in range(sequence_length, len(scaled_data)):
    X.append(scaled_data[i-sequence_length:i, 0])
    y.append(scaled_data[i, 0])
X, y = np.array(X), np.array(y)
X = np.reshape(X, (X.shape[0], X.shape[1], 1))

train_size = int(len(X) * 0.7)
val_size = int(len(X) * 0.15)

X_train = X[:train_size]
y_train = y[:train_size]

X_val = X[train_size:train_size + val_size]
y_val = y[train_size:train_size + val_size]

X_test = X[train_size + val_size:]
y_test = y[train_size + val_size:]

# Predict only on test set
predicted_prices = model.predict(X_test)
predicted_prices = scaler.inverse_transform(predicted_prices)

# Rebuild the time index for test set
test_dates = adjusted_index[train_size + val_size:]
# Now create DataFrame
test_df = pd.DataFrame({
    'CLOSE_PRICE': df['CLOSE_PRICE'].iloc[sequence_length + train_size + val_size:].values,
    'PREDICTED_PRICE': predicted_prices.flatten()
}, index=test_dates)

test_df.to_csv('lstm_output.csv', index=False)

### PREDICT FUTURE

future_steps = 1440  # minutes

last_sequence = scaled_data[-sequence_length:].reshape(1, sequence_length, 1)

future_predictions = []

for _ in range(future_steps):
    next_pred = model.predict(last_sequence)
    
    future_predictions.append(next_pred[0, 0])
    
    last_sequence = np.append(last_sequence[:,1:,:], [[next_pred[0]]], axis=1)

future_predictions = scaler.inverse_transform(np.array(future_predictions).reshape(-1, 1))

last_timestamp = test_df.index[-1]
future_timestamps = pd.date_range(start=last_timestamp + pd.Timedelta(minutes=1), periods=future_steps, freq='T')

future_df = pd.DataFrame({
    'CLOSE_PRICE': [np.nan]*future_steps,
    'PREDICTED_PRICE': future_predictions.flatten()
}, index=future_timestamps)

future_df.to_csv('future_output.csv')


