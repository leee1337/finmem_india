import os
import time
from datetime import datetime, timedelta

# Assuming these components can be imported and their functions called
from components import stock_data_fetcher
from components import technical_indicator_calculator
from components import news_scraper # Will be enhanced later
from components import rag_retriever

STOCK_DATA_PATH = "data/stock_data/"
STOCK_DATA_WITH_INDICATORS_PATH = "data/stock_data_with_indicators/"
NEWS_DATA_PATH = "data/news_data/" # For news recency check later

def file_is_older_than(filepath, days):
    """Checks if a file's modification date is older than a specified number of days."""
    if not os.path.exists(filepath):
        return True # File doesn't exist, so it's "older" / needs creation

    file_mod_time = os.path.getmtime(filepath)
    # Convert to datetime object
    file_mod_datetime = datetime.fromtimestamp(file_mod_time)

    # Calculate the age
    age = datetime.now() - file_mod_datetime

    return age > timedelta(days=days)

def ensure_stock_data_available(stock_symbol: str, data_recency_days: int = 1, indicator_recency_days: int = 1):
    """
    Ensures that historical data and data with technical indicators are available and recent enough for a given stock.
    If data is missing or too old, it triggers fetching and/or calculation.
    data_recency_days: How old raw data can be before re-fetching.
    indicator_recency_days: How old indicator data can be before re-calculating.
    """
    print(f"--- DataManager: Checking data for {stock_symbol} ---")

    raw_data_filename = f"{stock_symbol}_data.csv"
    raw_data_filepath = os.path.join(STOCK_DATA_PATH, raw_data_filename)

    indicator_filename = f"{stock_symbol}_data_with_indicators.csv"
    indicator_filepath = os.path.join(STOCK_DATA_WITH_INDICATORS_PATH, indicator_filename)

    data_fetched_this_run = False

    # 1. Check raw stock data
    if file_is_older_than(raw_data_filepath, data_recency_days):
        print(f"    Raw data for {stock_symbol} is missing or older than {data_recency_days} days. Fetching...")
        # stock_data_fetcher.fetch_and_save_stock_data expects a list of tickers
        stock_data_fetcher.fetch_and_save_stock_data([stock_symbol], stock_data_fetcher.DATA_STORAGE_PATH)
        data_fetched_this_run = True
    else:
        print(f"    Raw data for {stock_symbol} is up-to-date.")

    # 2. Check stock data with indicators
    # If raw data was just fetched, or if indicator file is missing/old, recalculate.
    if data_fetched_this_run or file_is_older_than(indicator_filepath, indicator_recency_days):
        if data_fetched_this_run:
            print(f"    Raw data for {stock_symbol} was just updated. Recalculating indicators...")
        else:
            print(f"    Indicator data for {stock_symbol} is missing or older than {indicator_recency_days} days. Recalculating...")

        # technical_indicator_calculator.process_all_stock_files processes everything in the input_dir.
        # This is suboptimal if only one stock needs updating but follows current plan.
        # A future refinement could be a function in technical_indicator_calculator
        # to process a single stock file.
        technical_indicator_calculator.process_all_stock_files(
            technical_indicator_calculator.INPUT_DATA_PATH,
            technical_indicator_calculator.OUTPUT_DATA_PATH
        )
        # Verify the specific file was created after processing all
        if not os.path.exists(indicator_filepath):
             print(f"    WARNING: Indicator file for {stock_symbol} still not found after attempting calculation.")
        else:
             print(f"    Indicator data for {stock_symbol} should now be up-to-date.")
    else:
        print(f"    Indicator data for {stock_symbol} is up-to-date.")
    print(f"--- DataManager: Data check for {stock_symbol} complete ---")


def ensure_news_data_available(news_recency_hours: int = 24):
    """
    Ensures that news data is available and recent enough.
    If news is too old, it triggers scraping and RAG update.
    (Placeholder for now, will be enhanced in Phase 2)
    """
    print(f"--- DataManager: Checking news data ---")
    # Placeholder logic: Assume for now news needs to be "fetched" daily.
    # In a real scenario, we'd check modification times of files in NEWS_DATA_PATH
    # or a timestamp in a control file.

    print(f"    Triggering news scraping (current implementation is dummy/basic)...")
    news_scraper.scrape_all_sources() # This uses the existing basic scraper

    print(f"    Triggering RAG vector store update...")
    # This should be called *after* all news for all relevant sources/stocks is scraped.
    rag_retriever.build_or_update_vector_store(force_reload=True)

    print(f"--- DataManager: News data check and update complete ---")

if __name__ == '__main__':
    print("--- DataManager Demonstration ---")
    # Example: Ensure data for a few stocks (assuming NIFTY_50_SYMBOLS is available for testing)
    # You would typically run stock_data_fetcher.py and technical_indicator_calculator.py first
    # to populate data for a full test. This demo will try to fetch if missing.

    # To run this demo effectively, ensure config.nifty50_stocks is accessible
    # For simplicity, using a few known stock symbols that might exist from previous runs
    # or will be fetched.
    sample_stocks_for_demo = ["RELIANCE.NS", "TCS.NS"]
    # In a real main_trader context, these would be from NIFTY_50_SYMBOLS

    # Create dummy data directories if they don't exist, so fetcher doesn't fail on dir creation
    if not os.path.exists(STOCK_DATA_PATH):
        os.makedirs(STOCK_DATA_PATH)
    if not os.path.exists(STOCK_DATA_WITH_INDICATORS_PATH):
        os.makedirs(STOCK_DATA_WITH_INDICATORS_PATH)
    if not os.path.exists(NEWS_DATA_PATH):
        os.makedirs(NEWS_DATA_PATH)

    print("\n--- Testing ensure_stock_data_available ---")
    for stock_sym in sample_stocks_for_demo:
        ensure_stock_data_available(stock_sym, data_recency_days=1, indicator_recency_days=1)
        time.sleep(1) # Small delay to make print outputs sequential and readable

    print("\n--- Testing ensure_news_data_available ---")
    ensure_news_data_available(news_recency_hours=6)

    print("\n--- DataManager Demonstration Finished ---")
