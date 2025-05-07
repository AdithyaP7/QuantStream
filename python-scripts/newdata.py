import os
import requests
import json
from dotenv import load_dotenv
from kafka import KafkaProducer
import time
from datetime import datetime
import pytz


KAFKA_TOPIC = "stock_data"
KAFKA_BROKER = "localhost:9091"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def get_ohlc_prices(ticker):
    url = f"http://127.0.0.1:25510/v2/snapshot/stock/ohlc?root={ticker.upper()}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data and 'response' in data and data['response']:
            ohlc_data = data['response'][0]
            open_price = ohlc_data[1]
            high_price = ohlc_data[2]
            low_price = ohlc_data[3]
            close_price = ohlc_data[4]
            volume = ohlc_data[5]
            return open_price, high_price, low_price, close_price, volume
        else:
            print(f"No OHLC data available for {ticker.upper()}.")
            return None, None, None, None, None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching OHLC prices: {e}")
        return None, None, None, None, None


def get_current_stock_price(ticker):
    eastern = pytz.timezone('America/New_York')
    now_et = datetime.now(eastern)
    midnight_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    ms_since_midnight = int((now_et - midnight_et).total_seconds() * 1000)

    date_str = now_et.strftime('%Y%m%d')

    url = "http://127.0.0.1:25510/v2/at_time/stock/trade"
    params = {
        "root": ticker.upper(),
        "start_date": date_str,
        "end_date": date_str,
        "ivl": ms_since_midnight
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and 'response' in data and data['response']:
            trade = data['response'][0]
            current_price = trade[9]  # Assuming index 9 is current price
            return {"current_price": current_price}
        else:
            return {"error": f"No trade data available for {ticker.upper()} at the current time."}
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching current price: {e}")
        return {"error": str(e)}


def send_to_kafka(symbols):
    timestamp_utc = datetime.now(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    for symbol in symbols:
        open_price, high_price, low_price, close_price, volume = get_ohlc_prices(symbol)
        if None not in (open_price, high_price, low_price, close_price, volume):
            current_price_data = get_current_stock_price(symbol)
            if 'error' not in current_price_data:
                current_price = current_price_data['current_price']
                stock_data = {
                    "stock_symbol": symbol.upper(),
                    "timestamp_utc": timestamp_utc,
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "close_price": close_price,
                    "volume": volume,
                    "current_price": current_price
                }
                # Send each record separately
                producer.send(KAFKA_TOPIC, value=stock_data)
                producer.flush()
                print(f"Sent to Kafka: {stock_data}")
            else:
                print(f"Failed to retrieve current price for {symbol}.")
        else:
            print(f"Failed to retrieve OHLC data for {symbol}.")

if __name__ == "__main__":
    try:
        while True:
            send_to_kafka(["MSFT", 'AAPL', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'IBM', 'NFLX'])
            time.sleep(30)
    except KeyboardInterrupt:
        print("Stopped producer.")
