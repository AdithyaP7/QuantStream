import requests
import csv
import io
import os
from datetime import datetime
import json

def fetch_and_process_ohlc_data(ticker):
    url = "http://127.0.0.1:25510/v2/hist/stock/ohlc"
    params = {
        "root": ticker,
        "start_date": 20250421,
        "end_date": 20250421,
        "ivl": 30000,  # 30 second intervals
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
    
    # Prepare a list to hold JSON objects
    json_objects = []
    
    # Process each row and format as JSON
    for row in csv_reader:
        ms_of_day, open_price, high_price, low_price, close_price, volume, count, date = row
        # Combine date and time into a cleaner format
        datetime_str = f"{date} {ms_of_day}"
        datetime_obj = datetime.strptime(datetime_str, "%Y%m%d %H:%M:%S.%f")
        timestamp_utc = datetime_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Create a JSON object
        json_obj = {
            "close_price": float(close_price),
            "current_price": float(close_price),  # Assuming current price is the same as close price
            "high_price": float(high_price),
            "low_price": float(low_price),
            "open_price": float(open_price),
            "stock_symbol": ticker,
            "timestamp_utc": timestamp_utc,
            "volume": int(volume)
        }
        
        # Add the JSON object to the list
        json_objects.append(json_obj)
    
    return json_objects

if __name__ == "__main__":
    stocks = ["MSFT", "AAPL", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD", "IBM", "NFLX"]
    all_json_objects = []
    
    for stock in stocks:
        all_json_objects.extend(fetch_and_process_ohlc_data(stock))
    
    # Sort all JSON objects by timestamp
    all_json_objects.sort(key=lambda x: x["timestamp_utc"])
    
    # Write all JSON objects to a single file in the current directory
    file_path = "all_stocks_ohlc_data.csv"
    with open(file_path, mode='w', newline='') as file:
        for json_obj in all_json_objects:
            json_line = json.dumps(json_obj)
            file.write(json_line + '\n')

    print(f"All stock data has been written to {file_path}")