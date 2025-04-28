import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import numpy as np
import pickle
import os

#train, pickled model, model_eval.py, predixt, 10 models


df = pd.read_csv("HistoricalData/AAPL_ohlc_data.csv")
df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'])
df.set_index('DATE_TIME', inplace=True)
df.sort_index(inplace=True)

scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(df[['CLOSE_PRICE']])
sequence_length = 60
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

print(f"Train: {len(X_train)}, Validation: {len(X_val)}, Test: {len(X_test)}")


# train_size = int(len(X) * 0.8)
# X_train, X_test = X[:train_size], X[train_size:]
# y_train, y_test = y[:train_size], y[train_size:]

# print(f"Training samples: {len(X_train)}, Testing samples: {len(X_test)}")

model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=False))
model.add(Dropout(0.2))
model.add(Dense(units=25))
model.add(Dense(units=1))

model.compile(optimizer='adam', loss='mean_squared_error')
model.fit(X_train, y_train, batch_size=32, epochs=10, validation_data=(X_val, y_val))

model_file = "models/lstm_model.pkl"
with open(model_file, "wb") as file:
    pickle.dump(model, file)

print(f"Model saved to {model_file}")


# model = Sequential()
# model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
# model.add(Dropout(0.2))
# model.add(LSTM(units=50, return_sequences=False))
# model.add(Dropout(0.2))
# model.add(Dense(units=25))
# model.add(Dense(units=1))

# model.compile(optimizer='adam', loss='mean_squared_error')

# model.fit(X, y, batch_size=32, epochs=10)

# model_file = "models/lstm_model.pkl"
# with open(model_file, "wb") as file:
#     pickle.dump(model, file)

# print (f"Model saved to {model_file}")
