import matplotlib.pyplot as plt
import pandas as pd

df_1 = pd.read_csv("lstm_output.csv")
df_2 = pd.read_csv('future_output.csv')

start_idx = int(len(df_1) * 0.85)
df_tail = df_1.iloc[start_idx:]

df_res = pd.concat([df_tail, df_2], ignore_index=True)

def plot_stock_predictions_from_csv(df, title="Stock Price Predictions (1-min intervals)"):
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df['CLOSE_PRICE'], label='Actual Close Price', marker='o')
    plt.plot(df.index, df['PREDICTED_PRICE'], label='Predicted Close Price', marker='x')
    plt.title(title)
    plt.xlabel('Minute Interval')
    plt.ylabel('Stock Price')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

plot_stock_predictions_from_csv(df_res)