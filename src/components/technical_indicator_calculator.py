import pandas as pd
import pandas_ta as ta
import os

# Define input and output directories
INPUT_DATA_PATH = "data/stock_data/"
OUTPUT_DATA_PATH = "data/stock_data_with_indicators/"

def load_stock_data(file_path):
    """
    Reads a CSV stock data file into a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        pd.DataFrame: The loaded DataFrame, or None if an error occurs.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return None

def calculate_technical_indicators(df):
    """
    Calculates technical indicators and appends them to the DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame with stock data.

    Returns:
        pd.DataFrame: The DataFrame with added technical indicators.
    """
    if df is None:
        return None

    try:
        # Calculate SMAs
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)

        # Calculate EMAs
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)

        # Calculate RSI
        df.ta.rsi(length=14, append=True)

        # Calculate MACD
        df.ta.macd(append=True) # Uses default fast=12, slow=26, signal=9

        # pandas-ta might add suffixes like _12_26_9 for MACD columns.
        # Let's ensure column names are simple if possible or note them.
        # For now, we'll rely on pandas-ta's default naming.

    except Exception as e:
        print(f"Error calculating technical indicators: {e}")
        return df # Return original df if calculation fails for some reason
    return df

def save_data_with_indicators(df, file_path):
    """
    Saves the DataFrame (now including indicators) to a new CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        file_path (str): The path to save the CSV file.
    """
    if df is None:
        return

    try:
        df.to_csv(file_path, index=False)
        print(f"Successfully saved data with indicators to {file_path}")
    except Exception as e:
        print(f"Error saving data to {file_path}: {e}")

def process_all_stock_files(input_dir, output_dir):
    """
    Processes all stock CSV files in the input directory, calculates indicators,
    and saves them to the output directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} does not exist. Please run stock_data_fetcher.py first.")
        return

    for filename in os.listdir(input_dir):
        if filename.endswith("_data.csv"):
            print(f"\nProcessing {filename}...")
            input_file_path = os.path.join(input_dir, filename)

            stock_df = load_stock_data(input_file_path)
            if stock_df is None:
                continue

            # Ensure 'Close' column exists as it's commonly used by indicators
            if 'Close' not in stock_df.columns:
                if 'close' in stock_df.columns: # yfinance might use lowercase 'close'
                    stock_df.rename(columns={'close': 'Close'}, inplace=True)
                else:
                    print(f"'Close' column not found in {filename}. Skipping indicator calculation.")
                    # Optionally, try to infer or skip, but for now, we require 'Close'
                    # For yfinance, 'Close' is the standard column name for closing price.
                    # If it's named differently (e.g. 'adj close'), that needs to be handled.
                    # For now, let's assume 'Close' or 'close' is present.
                    # Some indicators might need Open, High, Low, Close (OHLC)
                    # pandas-ta can often infer these if column names are standard.
                    # Let's check for 'Date' and set it as index if not already, as it's good practice for time series data
                    if 'Date' in stock_df.columns:
                        stock_df['Date'] = pd.to_datetime(stock_df['Date'])
                        stock_df.set_index('Date', inplace=True)
                    elif 'Datetime' in stock_df.columns: # yfinance sometimes uses Datetime
                         stock_df['Datetime'] = pd.to_datetime(stock_df['Datetime'])
                         stock_df.set_index('Datetime', inplace=True)


            stock_df_with_indicators = calculate_technical_indicators(stock_df.copy()) # Use .copy() to avoid SettingWithCopyWarning

            if stock_df_with_indicators is not None:
                output_filename = filename.replace("_data.csv", "_data_with_indicators.csv")
                output_file_path = os.path.join(output_dir, output_filename)
                save_data_with_indicators(stock_df_with_indicators, output_file_path)
        else:
            print(f"Skipping non-data file: {filename}")


if __name__ == "__main__":
    print("Starting technical indicator calculation process...")
    process_all_stock_files(INPUT_DATA_PATH, OUTPUT_DATA_PATH)
    print("\nTechnical indicator calculation process finished.")
