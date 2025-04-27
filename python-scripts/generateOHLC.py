import requests
import csv
import io
import os
from datetime import datetime

def fetch_and_process_ohlc_data(ticker):
    url = "http://127.0.0.1:25510/v2/hist/stock/ohlc"
    params = {
        "root": ticker,
        "start_date": 20250414,
        "end_date": 20250425,
        "ivl": 60000,  # 1 minute intervals
        "rth": True,   # Regular trading hours
        "use_csv": True,
        "pretty_time": True
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # Read the CSV data from the response
    csv_data = response.text
    csv_reader = csv.reader(io.StringIO(csv_data))
    
    # Skip the header
    headers = next(csv_reader)
    
    # Ensure the directory exists
    os.makedirs("HistoricalData", exist_ok=True)
    
    # Open a new CSV file to write the cleaned data
    file_path = os.path.join("HistoricalData", f"{ticker}_ohlc_data.csv")
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the new header
        writer.writerow(["STOCK_SYMBOL", "DATE_TIME", "OPEN_PRICE", "CLOSE_PRICE"])
        
        # Process and write each row
        for row in csv_reader:
            ms_of_day, open_price, high_price, low_price, close_price, volume, count, date = row
            # Combine date and time into a cleaner format
            datetime_str = f"{date} {ms_of_day}"
            datetime_obj = datetime.strptime(datetime_str, "%Y%m%d %H:%M:%S.%f")
            formatted_datetime = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([ticker, formatted_datetime, open_price, close_price])

    print(f"Data for {ticker} has been written to {file_path}")

if __name__ == "__main__":
    stocks = ["MSFT", "AAPL", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "IBM", "NFLX"]
    for stock in stocks:
        fetch_and_process_ohlc_data(stock)