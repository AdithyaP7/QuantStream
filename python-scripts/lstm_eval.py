import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


df = pd.read_csv("lstm_output.csv")

mse = mean_squared_error(df["CLOSE_PRICE"][60:], df["PREDICTED_PRICE"][60:])
print(f"Mean Squared Error: {mse}")
rmse = np.sqrt(mse)
print(f"Root Mean Squared Error: {rmse}")
mae = mean_absolute_error(df['CLOSE_PRICE'][60:], df['PREDICTED_PRICE'][60:])
print(f"Mean Absolute Error: {mae}")
r2 = r2_score(df['CLOSE_PRICE'][60:], df['PREDICTED_PRICE'][60:])
print(f"R-squared: {r2}")