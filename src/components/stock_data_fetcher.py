import yfinance as yf
import pandas as pd
import os
from config.nifty50_stocks import NIFTY_50_SYMBOLS

# Nifty 50 stock tickers (subset)
NIFTY_50_TICKERS = NIFTY_50_SYMBOLS

# Data storage path
DATA_STORAGE_PATH = "data/stock_data/"

def fetch_and_save_stock_data(tickers, data_path):
    """
    Fetches historical stock data for the given tickers and saves it to CSV files.

    Args:
        tickers (list): A list of stock tickers.
        data_path (str): The path to the directory where CSV files will be stored.
    """
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    for ticker_symbol in tickers:
        try:
            print(f"Fetching data for {ticker_symbol}...")
            ticker_data = yf.Ticker(ticker_symbol)
            historical_data = ticker_data.history(period="5y")

            if historical_data.empty:
                print(f"No data found for {ticker_symbol}. Skipping.")
                continue

            file_name = f"{ticker_symbol}_data.csv"
            file_path = os.path.join(data_path, file_name)
            historical_data.to_csv(file_path)
            print(f"Saved data for {ticker_symbol} to {file_path}")

        except Exception as e:
            print(f"Error fetching data for {ticker_symbol}: {e}")

if __name__ == "__main__":
    fetch_and_save_stock_data(NIFTY_50_TICKERS, DATA_STORAGE_PATH)
