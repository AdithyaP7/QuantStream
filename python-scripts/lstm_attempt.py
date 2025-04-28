## DECENT PREDICTION BAD RMSE

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping

# reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# ───────────────────────── 1. Load data ────────────────────────────────────────
PATH = "HistoricalData/AAPL_ohlc_data.csv"          # <-- change if needed
df = (
    pd.read_csv(PATH, parse_dates=["DATE_TIME"])
      .sort_values("DATE_TIME")
      .set_index("DATE_TIME")
)

# ───────────────────────── 2. Compute log-returns ──────────────────────────────
df["log_ret"] = np.log(df["CLOSE_PRICE"]).diff()      # r_t = log(P_t) – log(P_{t-1})
df = df.dropna()                                      # first row has NaN return

series = df["log_ret"].values.reshape(-1, 1)

# ───────────────────────── 3. Scaling ──────────────────────────────────────────
scaler = StandardScaler()
series_s = scaler.fit_transform(series)

# ───────────────────────── 4. Build sliding windows ────────────────────────────
WINDOW = 20      # 20 past returns → predict next return

def make_dataset(arr, window):
    X, y = [], []
    for i in range(len(arr) - window):
        X.append(arr[i : i + window, 0])
        y.append(arr[i + window, 0])
    return np.array(X), np.array(y)

X, y = make_dataset(series_s, WINDOW)
X = X.reshape(-1, WINDOW, 1)          # (samples, timesteps, features)

# ───────────────────────── 5. Train / test split ───────────────────────────────
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"Train samples: {len(X_train)} | Test samples: {len(X_test)}")

# ───────────────────────── 6. Model builder ────────────────────────────────────
def build_model():
    m = Sequential(
        [
            LSTM(50, return_sequences=True, input_shape=(WINDOW, 1)),
            LSTM(25),
            Dense(1),
        ]
    )
    m.compile(optimizer="adam", loss="mse")
    return m

# ───────────────────────── 7. Fit on training only ─────────────────────────────
model = build_model()
es = EarlyStopping("val_loss", patience=10, restore_best_weights=True)

print("\n=== Fit on training split ===")
model.fit(
    X_train,
    y_train,
    validation_split=0.2,
    epochs=100,
    batch_size=32,
    callbacks=[es],
    verbose=1,
)

# ───────────────────────── 8. Evaluate level MSE ───────────────────────────────
def inv_scaled(a):                      # helper: scaled → log-return
    return scaler.inverse_transform(a.reshape(-1, 1)).flatten()

# predictions (still in scaled return space)
train_pred_s = model.predict(X_train).flatten()
test_pred_s  = model.predict(X_test).flatten()

# inverse-scale to real log-returns
train_pred_r = inv_scaled(train_pred_s)
test_pred_r  = inv_scaled(test_pred_s)
y_train_r    = inv_scaled(y_train)
y_test_r     = inv_scaled(y_test)

# convert returns to price for MSE (optional but intuitive):
def returns_to_price(start_price, returns):
    prices = [start_price]
    for r in returns:
        prices.append(prices[-1] * np.exp(r))
    return np.array(prices[1:])

# anchor each segment at its own “last known” price
anchor_train = df["CLOSE_PRICE"].iloc[WINDOW - 1]
anchor_test  = df["CLOSE_PRICE"].iloc[WINDOW + len(train_pred_r) - 1]

train_pred_p = returns_to_price(anchor_train, train_pred_r)
y_train_p    = returns_to_price(anchor_train, y_train_r)
test_pred_p  = returns_to_price(anchor_test, test_pred_r)
y_test_p     = returns_to_price(anchor_test, y_test_r)

print(f"\nTrain MSE (price level): {mean_squared_error(y_train_p, train_pred_p):.4f}")
print(f" Test MSE (price level): {mean_squared_error(y_test_p,  test_pred_p):.4f}")

# ───────────────────────── 9. Plot train / test results ────────────────────────
plt.figure(figsize=(13, 5))
# indices
idx_train = df.index[WINDOW : WINDOW + len(train_pred_p)]
idx_test  = df.index[WINDOW + len(train_pred_p) : WINDOW + len(train_pred_p) + len(test_pred_p)]

plt.plot(idx_train, y_train_p, label="Train actual", alpha=0.4)
plt.plot(idx_test, y_test_p, label="Test actual", color="black", linewidth=2)
plt.plot(idx_test, test_pred_p, label="Test pred", color="red", linestyle="--", linewidth=2)

plt.title("LSTM on log-returns: Train vs Test")
plt.xlabel("Date")
plt.ylabel("Close Price")
plt.legend()
plt.tight_layout()
plt.show()

# ───────────────────────── 10. Retrain on full series ──────────────────────────
print("\n=== Retrain on full data for forecasting ===")
model_full = build_model()
es_full = EarlyStopping("loss", patience=10, restore_best_weights=True)
model_full.fit(X, y, epochs=100, batch_size=32, callbacks=[es_full], verbose=1)
print("Full-data fit complete.")

# ───────────────────────── 11. Multi-step forecast (recursive) ─────────────────
FUTURE_STEPS = 50                         # change as needed

history_s = list(series_s[-WINDOW:, 0])    # last WINDOW scaled returns
future_s  = []

for _ in range(FUTURE_STEPS):
    x = np.array(history_s[-WINDOW:]).reshape(1, WINDOW, 1)
    nxt = model_full.predict(x, verbose=0)[0, 0]
    future_s.append(nxt)
    history_s.append(nxt)

# inverse-scale to real log-returns
future_r = inv_scaled(np.array(future_s))

# convert to price path
last_price = df["CLOSE_PRICE"].iloc[-1]
future_p = returns_to_price(last_price, future_r)

# build timeline with the same frequency as original data
freq = pd.infer_freq(df.index) or (df.index[1] - df.index[0])
future_idx = pd.date_range(df.index[-1] + freq, periods=FUTURE_STEPS, freq=freq)

# ───────────────────────── 12. Plot forecast ───────────────────────────────────
plt.figure(figsize=(13, 5))
# show last part of actual data for context
lookback_days = 300
plt.plot(df.index[-lookback_days:], df["CLOSE_PRICE"].iloc[-lookback_days:], color="grey", alpha=0.5)

# future
plt.plot(future_idx, future_p, color="green", linestyle=":", label=f"Forecast {FUTURE_STEPS} steps")

plt.title("LSTM forecast on log-returns (no price collapse!)")
plt.xlabel("Date")
plt.ylabel("Close Price")
plt.legend()
plt.tight_layout()
plt.show()

# ───────────────────────── 13. Print numeric forecast (optional) ───────────────
forecast_series = pd.Series(future_p, index=future_idx, name="Pred_Close")
print("\nNext few predicted closes:")
print(forecast_series.head())
