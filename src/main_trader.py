import os
import json
import pandas as pd
from datetime import datetime

# Import components
from components import stock_data_fetcher
from components import technical_indicator_calculator
from components import news_scraper
from config.nifty50_stocks import NIFTY_50_SYMBOLS
from components import memory_manager
from components import rag_retriever
from components import gemini_client
from components import paper_trading_engine
from components import trade_event_logger
from components import data_manager

# Configuration
# Load the list of Nifty 50 stocks to be processed from the configuration file.
STOCKS_TO_PROCESS = NIFTY_50_SYMBOLS
STOCK_DATA_WITH_INDICATORS_PATH = "data/stock_data_with_indicators/"
# FIXED_TRADE_QUANTITY = 1 # Fixed quantity for trades for now - Replaced by dynamic sizing

def format_for_gemini(data_object, max_items=None):
    """Helper to format various data types for Gemini prompts, with truncation."""
    if isinstance(data_object, pd.DataFrame):
        return data_object.to_string()
    if isinstance(data_object, list):
        if max_items and len(data_object) > max_items:
            data_object = data_object[:max_items]
            return json.dumps([str(item) for item in data_object] + ["... (truncated)"], indent=2)
        return json.dumps([str(item) for item in data_object], indent=2) # Convert items to str if not serializable
    if isinstance(data_object, dict):
        # Convert dict values to strings to ensure serializability for complex dicts
        return json.dumps({k: str(v) for k, v in data_object.items()}, indent=2)
    return str(data_object)

def main_trading_logic():
    print("--- Starting Main Trading Logic ---")

    # 1. Initial Setup
    print("\n--- Phase 1: Initial Setup ---")
    memory_manager.load_memory()
    paper_trading_engine.load_portfolio_state()

    gemini_api_key_available = gemini_client.API_KEY_LOADED and gemini_client.MODEL_INITIALIZED
    if not gemini_api_key_available:
        print("\nWARNING: Gemini API key not available or model not initialized.")
        print("Trading decisions will be defaulted to HOLD or use dummy logic.")

    print(f"Initial portfolio: Cash: {paper_trading_engine.get_cash():.2f}, Holdings: {paper_trading_engine.get_holdings()}")

    # Store latest prices encountered for final portfolio valuation
    latest_market_prices = {}

    # --- Ensure News Data and RAG are Up-to-Date (Global - Once per run) ---
    print("\n--- Phase 1.5: Ensuring News Data and RAG readiness ---")
    # Define desired news recency in hours, e.g., 12 or 24 hours
    # This value could also come from a global config file later.
    data_manager.ensure_news_data_available(news_recency_hours=12)
    print("--- News Data and RAG readiness check complete ---")

    # 2. Main Loop per Stock
    print("\n--- Phase 2: Processing Stocks ---")
    for stock_symbol in STOCKS_TO_PROCESS:
        print(f"\n===== Processing {stock_symbol} =====")

        # --- Ensure Stock-Specific Data is Available and Up-to-Date ---
        # Define desired data/indicator recency in days.
        # These values could also come from a global config file.
        data_manager.ensure_stock_data_available(
            stock_symbol,
            data_recency_days=1,  # How old raw data can be
            indicator_recency_days=1 # How old indicator files can be
        )
        # Now, the data file at data_file_path should exist and be recent.

        # a. Load Stock Data and Indicators (This section remains, but now it's more certain files exist)
        print(f"\n  --- a. Loading data for {stock_symbol} ---")
        data_file_path = os.path.join(STOCK_DATA_WITH_INDICATORS_PATH, f"{stock_symbol}_data_with_indicators.csv")
        if not os.path.exists(data_file_path):
            print(f"    Data file not found for {stock_symbol} at {data_file_path}. Skipping stock.")
            memory_manager.add_to_stm(item_type="error", content=f"Data file missing for {stock_symbol}", stock_symbol=stock_symbol)
            continue

        try:
            stock_df = pd.read_csv(data_file_path)
            if stock_df.empty:
                print(f"    Data file for {stock_symbol} is empty. Skipping stock.")
                memory_manager.add_to_stm(item_type="error", content=f"Data file empty for {stock_symbol}", stock_symbol=stock_symbol)
                continue

            # Ensure 'Date' or 'Datetime' column is parsed as datetime
            if 'Date' in stock_df.columns:
                stock_df['Date'] = pd.to_datetime(stock_df['Date'])
                stock_df.sort_values(by='Date', inplace=True)
            elif 'Datetime' in stock_df.columns: # yfinance often uses 'Datetime'
                stock_df['Datetime'] = pd.to_datetime(stock_df['Datetime'])
                stock_df.sort_values(by='Datetime', inplace=True)

            latest_data = stock_df.iloc[-1]
            current_price = latest_data['Close']
            latest_market_prices[stock_symbol] = current_price # Store for final valuation

            # Extract relevant indicators (example columns from pandas-ta)
            indicator_cols = ['SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'RSI_14', 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']
            technical_indicators_dict = {}
            for col in indicator_cols:
                if col in latest_data and pd.notna(latest_data[col]):
                    technical_indicators_dict[col] = latest_data[col]

            formatted_indicators = format_for_gemini(technical_indicators_dict)
            stock_data_summary = format_for_gemini(stock_df.tail(5)) # Last 5 days OHLCV

            print(f"    Latest Close Price for {stock_symbol}: {current_price:.2f}")
            # print(f"    Latest Indicators: {formatted_indicators}")

        except Exception as e:
            print(f"    Error loading or processing data for {stock_symbol}: {e}")
            memory_manager.add_to_stm(item_type="error", content=f"Data processing error for {stock_symbol}: {str(e)}", stock_symbol=stock_symbol)
            continue

        # b. Gather Intelligence
        print(f"\n  --- b. Gathering intelligence for {stock_symbol} ---")
        # news_scraper.scrape_all_sources() # This was commented out, news is now handled by data_manager globally.
        # print("    News scraping attempted/completed (might be dummy data).")

        # rag_retriever.build_or_update_vector_store(force_reload=True) # REMOVED: This is now handled by data_manager.ensure_news_data_available() before the loop.
        # print("    RAG vector store built/updated.")

        news_query = f"What is the latest news for {stock_symbol}? Also general market sentiment or news for Nifty 50 index."
        relevant_news_results = rag_retriever.find_similar_news(query_text=news_query, top_n=3)
        relevant_news_headlines = [news['item']['headline'] for news in relevant_news_results if 'item' in news and 'headline' in news['item']]
        formatted_news = format_for_gemini(relevant_news_headlines, max_items=3)
        # print(f"    Relevant News: {formatted_news}")

        stm_extracts_list = memory_manager.get_recent_stm_items(count=5)
        formatted_stm = format_for_gemini(stm_extracts_list, max_items=5)
        # print(f"    STM Extracts: {formatted_stm}")

        # More targeted LTM keywords
        ltm_keywords = [stock_symbol.split('.')[0]]
        # Add general terms if stock specific is too narrow
        if not memory_manager.retrieve_from_ltm(keywords=ltm_keywords):
             ltm_keywords.extend(['market', 'trend', 'analysis', 'Nifty50'])

        ltm_extracts_list = memory_manager.retrieve_from_ltm(keywords=ltm_keywords)
        formatted_ltm = format_for_gemini(ltm_extracts_list, max_items=3) # Truncate LTM for prompt
        # print(f"    LTM Extracts (Keywords: {ltm_keywords}): {formatted_ltm}")

        # c. Get Trading Decision
        print(f"\n  --- c. Getting trading decision for {stock_symbol} ---")
        raw_response = "Gemini API not called or key unavailable" # Initialize raw_response
        current_holdings_dict = paper_trading_engine.get_holdings()
        portfolio_cash = paper_trading_engine.get_cash()
        portfolio_status_dict = {
            'cash': portfolio_cash,
            'holdings': current_holdings_dict.get(stock_symbol, {'quantity': 0, 'avg_price': 0}) # Specific to current stock
        }
        # More general portfolio status if needed by Gemini for broader context
        # portfolio_status_dict['all_holdings'] = current_holdings_dict
        formatted_portfolio_status = format_for_gemini(portfolio_status_dict)

        if gemini_api_key_available:
            print(f"    Querying Gemini for {stock_symbol}...")
            raw_response = gemini_client.get_trading_decision_from_gemini(
                stock_symbol=stock_symbol,
                current_price=current_price,
                stock_data_summary=stock_data_summary,
                technical_indicators=technical_indicators_dict, # Pass as dict
                relevant_news_headlines=relevant_news_headlines, # Pass as list
                stm_extracts=stm_extracts_list, # Pass as list
                ltm_extracts=ltm_extracts_list, # Pass as list
                current_portfolio_status=portfolio_status_dict # Pass as dict
            )
            # print(f"    Gemini Raw Response for {stock_symbol}: {raw_response}")
            parsed_decision = gemini_client.parse_gemini_response(raw_response)
        else:
            print(f"    Gemini API key not available. Defaulting to HOLD for {stock_symbol}.")
            parsed_decision = {'decision': 'HOLD', 'reasoning': 'Gemini API key not available. Defaulting to HOLD.', 'confidence': 'N/A'}

        print(f"    Decision for {stock_symbol}: {parsed_decision.get('decision')} (Confidence: {parsed_decision.get('confidence')})")
        print(f"    Reasoning: {parsed_decision.get('reasoning')}")

        # --- Determine Trade Quantity (Moved before decision logging) ---
        # This section calculates trade_quantity based on parsed_decision
        trade_quantity = 0
        if parsed_decision.get('decision') in ["BUY", "SELL"]:
            position_size = parsed_decision.get('position_size')
            position_size_percent = parsed_decision.get('position_size_percent')
            if position_size is not None and position_size > 0:
                trade_quantity = position_size
                # print(f"    Using specific share quantity from Gemini: {trade_quantity}") # Will be logged in event
            elif position_size_percent is not None and position_size_percent > 0:
                if current_price > 0:
                    cash_to_allocate = portfolio_cash * (position_size_percent / 100.0)
                    calculated_quantity = int(cash_to_allocate / current_price)
                    trade_quantity = calculated_quantity
                    # print(f"    Using percentage of cash from Gemini: {position_size_percent}%") # Will be logged
                    # print(f"    Allocating {cash_to_allocate:.2f} for trade, calculated quantity: {trade_quantity}") # Will be logged
                # else: # Warning for current_price <= 0 is already printed below if trade_quantity ends up 0
                    # print(f"    Warning: Current price is {current_price}. Cannot calculate quantity from percentage.")
            # else: # Warning for no valid size is already printed below if trade_quantity ends up 0
                # print(f"    Warning: Position size not specified or invalid. Defaulting quantity to 0.")

        # --- Log Decision Analysis Event ---
        decision_event_data = {
            "event_type": "decision_analysis",
            "stock_symbol": stock_symbol,
            "decision_input_current_price": current_price,
            "decision_input_technical_indicators": technical_indicators_dict,
            "decision_input_news_context": relevant_news_headlines,
            "decision_input_stm_extracts": stm_extracts_list,
            "decision_input_ltm_extracts": ltm_extracts_list,
            "decision_input_portfolio_cash": portfolio_cash,
            "decision_input_portfolio_holdings_stock": current_holdings_dict.get(stock_symbol, {'quantity': 0, 'avg_price': 0}),
            "gemini_raw_response": raw_response,
            "gemini_decision": parsed_decision.get('decision'),
            "gemini_reasoning": parsed_decision.get('reasoning'),
            "gemini_confidence": parsed_decision.get('confidence'),
            "gemini_position_size_shares": parsed_decision.get('position_size'),
            "gemini_position_size_percent": parsed_decision.get('position_size_percent'),
            "calculated_trade_quantity": trade_quantity
        }
        trade_event_logger.log_event(decision_event_data)

        # d. Execute Trade
        print(f"\n  --- d. Executing trade for {stock_symbol} ---")
        trade_executed_info = None
        # --- Determine Trade Quantity Dynamically --- # This comment block is now slightly redundant as logic is above
        # The trade_quantity is determined based on Gemini's recommendation:
        # 1. Specific number of shares (position_size). # Redundant comment
        # 2. Percentage of available cash (position_size_percent). # Redundant comment
        # If neither is provided or valid, quantity defaults to 0. # Redundant comment
        # trade_quantity calculation is now above the decision_analysis event logging.
        # The print statements for how quantity was derived were removed as this detail is now in the decision_analysis log.

        # Original print statements for quantity derivation (now part of decision_analysis log or implicit):
        # if parsed_decision.get('decision') in ["BUY", "SELL"]:
        #     if position_size is not None and position_size > 0: # position_size is defined above
        #         print(f"    Using specific share quantity from Gemini: {trade_quantity}")
        #     elif position_size_percent is not None and position_size_percent > 0: # position_size_percent is defined above
        #         if current_price > 0:
        #             print(f"    Using percentage of cash from Gemini: {position_size_percent}%")
        #             print(f"    Cash available: {portfolio_cash:.2f}, Current price: {current_price:.2f}")
        #             print(f"    Allocating {cash_to_allocate:.2f} for trade, calculated quantity: {trade_quantity}") # cash_to_allocate defined above
        #         else:
        #             print(f"    Warning: Current price is {current_price}. Cannot calculate quantity from percentage. Defaulting quantity to 0.")
        #     else:
        #         print(f"    Warning: Position size not specified or invalid in Gemini response. Defaulting quantity to 0.")

            if trade_quantity > 0:
                trade_success = paper_trading_engine.execute_order(
                    stock_symbol,
                    parsed_decision['decision'],
                    trade_quantity, # Use dynamic quantity
                    current_price
                )
                print(f"    Trade Execution Status for {stock_symbol} ({parsed_decision['decision']} {trade_quantity} @ {current_price:.2f}): {'SUCCESS' if trade_success else 'FAILED'}")
                trade_executed_info = {
                    'status': 'SUCCESS' if trade_success else 'FAILED',
                    'action': parsed_decision['decision'],
                    'quantity': trade_quantity, # Use dynamic quantity
                    'price': current_price,
                    'reason_if_failed': paper_trading_engine.transaction_log[-1].get('reason') if not trade_success and paper_trading_engine.transaction_log else None
                }
                # --- Log Trade Execution Event ---
                execution_event_data = {
                    "event_type": "trade_execution",
                    "stock_symbol": stock_symbol,
                    "decision_gemini_decision": parsed_decision.get('decision'),
                    "decision_calculated_trade_quantity": trade_quantity,
                    "trade_action": trade_executed_info['action'],
                    "trade_quantity_attempted": trade_quantity,
                    "trade_price_attempted": current_price,
                    "trade_status": trade_executed_info['status'],
                    "trade_quantity_executed": trade_executed_info['quantity'] if trade_executed_info['status'] == 'SUCCESS' else 0,
                    "trade_price_executed": trade_executed_info['price'] if trade_executed_info['status'] == 'SUCCESS' else None,
                    "trade_pnl": paper_trading_engine.transaction_log[-1].get('pnl') if trade_executed_info['status'] == 'SUCCESS' and trade_executed_info['action'] == 'SELL' and paper_trading_engine.transaction_log else None,
                    "trade_failure_reason": trade_executed_info.get('reason_if_failed'),
                    "portfolio_cash_after_trade": paper_trading_engine.get_cash(),
                    "portfolio_holdings_stock_after_trade": paper_trading_engine.get_holdings().get(stock_symbol, {'quantity': 0, 'avg_price': 0})
                }
                trade_event_logger.log_event(execution_event_data)
            else:
                print(f"    Trade quantity is 0. No trade executed for {stock_symbol}.")
        else: # HOLD or error in decision
            print(f"    No trade action (HOLD or error) for {stock_symbol}.")

        # e. Update Memory
        print(f"\n  --- e. Updating memory for {stock_symbol} ---")
        # STM logging for trade_decision and trade_execution removed as this is now in trade_event_logger.
        # memory_manager.add_to_stm(item_type='trade_decision', stock_symbol=stock_symbol,
        #                           content=f"Decision: {parsed_decision.get('decision')}, Reasoning: {parsed_decision.get('reasoning')}, Confidence: {parsed_decision.get('confidence')}")
        # if trade_executed_info:
        #     memory_manager.add_to_stm(item_type='trade_execution', stock_symbol=stock_symbol,
        #                               content=f"Action: {trade_executed_info['action']}, Qty: {trade_executed_info['quantity']}, Price: {trade_executed_info['price']:.2f}, Status: {trade_executed_info['status']}" + (f", Reason: {trade_executed_info['reason_if_failed']}" if not trade_executed_info['status'] and trade_executed_info['reason_if_failed'] else ""))

        # Consider adding significant news or analysis results to LTM periodically or based on rules
        # This LTM logging remains as it's for curated insights, not a direct event log.
        if parsed_decision.get('confidence') == 'High' and relevant_news_headlines:
             memory_manager.add_to_ltm(category="trade_catalyst_news", summary=f"High confidence {parsed_decision.get('decision')} for {stock_symbol} based on news: {relevant_news_headlines[0]} and analysis: {parsed_decision.get('reasoning')}", stock_symbol=stock_symbol)


    # 3. Final Reporting and Saving
    print("\n--- Phase 3: Final Reporting and Saving ---")
    print(f"\nFinal Portfolio Status:")
    print(f"  Cash: {paper_trading_engine.get_cash():.2f}")
    final_holdings = paper_trading_engine.get_holdings()
    if final_holdings:
        print(f"  Holdings:")
        for stock, data in final_holdings.items():
            print(f"    {stock}: Quantity={data['quantity']}, Avg Price={data['avg_price']:.2f}")
    else:
        print("  Holdings: None")

    if latest_market_prices: # Use prices from the loop if available
        print(f"  Holdings Market Value (based on last known prices): {paper_trading_engine.get_current_holdings_value(latest_market_prices):.2f}")
        print(f"  Total Portfolio Value: {paper_trading_engine.get_total_portfolio_value(latest_market_prices):.2f}")
    else:
        print("  Portfolio value could not be calculated as no market prices were processed.")

    memory_manager.save_memory()
    print("Memory saved.")
    # paper_trading_engine.save_portfolio_state() # Already saved by execute_order on success
    print("Portfolio state should be saved by individual successful trades.")

    print("\n--- Main Trading Logic Finished ---")


if __name__ == "__main__":
    # This is where you might run pre-requisite data fetching if needed for a full run,
    # but for now, assume data is already present from previous component runs.

    # Example: Ensure news data directory exists for RAG to not fail completely on load
    if not os.path.exists(news_scraper.NEWS_DATA_OUTPUT_PATH):
        os.makedirs(news_scraper.NEWS_DATA_OUTPUT_PATH)
        print(f"Created empty news data directory for RAG: {news_scraper.NEWS_DATA_OUTPUT_PATH}")
        # Optionally, create a dummy news file if news_scraper hasn't run
        # This ensures rag_retriever.load_news_from_directory() doesn't fail if directory is empty
        # and news_scraper.scrape_all_sources() is not called before RAG in main_trading_logic
        # However, scrape_all_sources *is* called in the loop now.

    main_trading_logic()
