import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt


df = pd.read_csv("lstm_output.csv")

mse = mean_squared_error(df["CURRENT_PRICE"][60:], df["Predicted_Price"][60:])
print(f"Mean Squared Error: {mse}")
rmse = np.sqrt(mse)
print(f"Root Mean Squared Error: {rmse}")
mae = mean_absolute_error(df['CURRENT_PRICE'][60:], df['Predicted_Price'][60:])
print(f"Mean Absolute Error: {mae}")
r2 = r2_score(df['CURRENT_PRICE'][60:], df['Predicted_Price'][60:])
print(f"R-squared: {r2}")


# Plotting the results
plt.figure(figsize=(14, 7))         
plt.plot(df['CURRENT_PRICE'], label='Actual Price', color='blue')
plt.plot(df['Predicted_Price'], label='Predicted Price', color='orange')
plt.title('LSTM Model Predictions vs Actual Prices')
plt.xlabel('Time')
plt.ylabel('Price')
plt.legend()
plt.show()