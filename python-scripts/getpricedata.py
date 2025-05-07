import sys
import requests
from datetime import datetime
import pytz

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
        "ivl": ms_since_midnight # edit for testing and to find start and end of day, 0 and 57600000 respectively
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and 'response' in data and data['response']:
            trade = data['response'][0]
            price = trade[9]
            print(f"Ticker: {ticker.upper()}")
            print(params) # debugging for params
            print(f"Price: {price}")
        else:
            print(f"No trade data available for {ticker.upper()} at the current time.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_price_at_time.py <TICKER>")
    else:
        ticker_symbol = sys.argv[1]
        get_current_stock_price(ticker_symbol)