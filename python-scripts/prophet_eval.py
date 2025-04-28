import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np


merged = pd.read_csv('merged_output.csv')["ds"]
merged['ds'] = pd.to_datetime(merged['ds'])
merged = merged[merged['ds'].dt.date == pd.to_datetime('2025-04-24').date()]
print(merged.head())


y_true = merged['y']
y_pred = merged['yhat']

# 3. Calculate metrics
rmse = np.sqrt(mean_squared_error(y_true, y_pred))
mae = mean_absolute_error(y_true, y_pred)
r2 = r2_score(y_true, y_pred)

# 4. Print results
print(f"RMSE: {rmse:.2f}")
print(f"MAE: {mae:.2f}")
print(f"R²: {r2:.2f}")