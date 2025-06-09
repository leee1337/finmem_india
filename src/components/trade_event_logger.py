import json
import os
from datetime import datetime, timezone
import uuid # For unique event IDs

LOG_DIR = "data/logs/"
EVENT_LOG_FILE = os.path.join(LOG_DIR, "trade_events.jsonl")

def _ensure_log_dir_exists():
    """Ensures the log directory exists."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        print(f"Created log directory: {LOG_DIR}")

def log_event(event_data: dict):
    """
    Logs a structured event to a JSON Lines file.
    The event_data dictionary should conform to the defined schema.
    """
    _ensure_log_dir_exists()

    # Enrich with common information
    event_data['event_id'] = str(uuid.uuid4())
    event_data['log_timestamp'] = datetime.now(timezone.utc).isoformat()

    try:
        with open(EVENT_LOG_FILE, 'a', encoding='utf-8') as f:
            # Write the event as a single line of JSON
            f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
        # print(f"Logged event (ID: {event_data['event_id']}, Type: {event_data.get('event_type')})") # Optional: too verbose for many events
    except IOError as e:
        print(f"Error logging event: {e}")
    except TypeError as e:
        print(f"Error serializing event data to JSON: {e}. Event Data: {event_data}")


# --- Example Usage and Schema Definition (Conceptual) ---
# The actual calls to log_event will be made from main_trader.py
# This section serves as documentation for the expected event_data structure.

CONCEPTUAL_EVENT_SCHEMA = {
    # --- Automatically added by log_event ---
    # "event_id": "string (uuid)",
    # "log_timestamp": "string (ISO datetime UTC)",

    # --- To be provided by caller (main_trader.py) ---
    "event_type": "string (e.g., 'decision_analysis', 'trade_execution')",
    "stock_symbol": "string",

    # --- Fields for 'decision_analysis' type events ---
    "decision_input_current_price": "float (optional, if event_type is decision_analysis)",
    "decision_input_technical_indicators": "dict (optional, snapshot of indicators used)",
    "decision_input_news_context": "list (optional, news headlines/summaries considered by RAG)",
    "decision_input_stm_extracts": "list (optional, snapshot of STM used)",
    "decision_input_ltm_extracts": "list (optional, snapshot of LTM used)",
    "decision_input_portfolio_cash": "float (optional)",
    "decision_input_portfolio_holdings_stock": "dict (optional, quantity and avg_price for the current stock)",

    "gemini_raw_response": "string (optional, full response from Gemini)",
    "gemini_decision": "string (BUY/SELL/HOLD)",
    "gemini_reasoning": "string (full text)",
    "gemini_confidence": "string (High/Medium/Low)",
    "gemini_position_size_shares": "int (optional)",
    "gemini_position_size_percent": "float (optional)",
    "calculated_trade_quantity": "int (optional, if BUY/SELL decision)",

    # --- Fields for 'trade_execution' type events ---
    "trade_action": "string (BUY/SELL, optional, if event_type is trade_execution)",
    "trade_quantity_attempted": "int (optional)",
    "trade_price_attempted": "float (optional)", # This would be the current_price at time of decision

    "trade_status": "string (SUCCESS/FAILED, optional)",
    "trade_quantity_executed": "int (optional, if successful)",
    "trade_price_executed": "float (optional, actual execution price if different, for now same as attempted)",
    "trade_pnl": "float (optional, for SELLs)", # Calculated by paper_trading_engine
    "trade_failure_reason": "string (optional, if trade failed)",

    "portfolio_cash_after_trade": "float (optional)",
    "portfolio_holdings_stock_after_trade": "dict (optional, for the current stock)"
}

if __name__ == '__main__':
    print("--- Trade Event Logger Demonstration ---")
    _ensure_log_dir_exists() # Ensure dir exists for demo

    # Example 1: Decision Analysis Event
    analysis_event = {
        "event_type": "decision_analysis",
        "stock_symbol": "RELIANCE.NS",
        "decision_input_current_price": 2900.50,
        "decision_input_technical_indicators": {"SMA20": 2850.0, "RSI14": 60.1},
        "decision_input_news_context": [{"headline": "Reliance AGM soon", "link": "news.com/1"}],
        "decision_input_stm_extracts": [{"type": "price_alert", "content": "Price crossed 2880"}],
        "decision_input_ltm_extracts": [{"category": "past_performance", "summary": "Good results last quarter"}],
        "decision_input_portfolio_cash": 100000.0,
        "decision_input_portfolio_holdings_stock": {"quantity": 0, "avg_price": 0},
        "gemini_raw_response": "DECISION: BUY\nREASONING: Good setup.\nCONFIDENCE: High\nPOSITION_SIZE: 10\nPOSITION_SIZE_PERCENT: N/A",
        "gemini_decision": "BUY",
        "gemini_reasoning": "Good setup.",
        "gemini_confidence": "High",
        "gemini_position_size_shares": 10,
        "calculated_trade_quantity": 10
    }
    log_event(analysis_event)
    print(f"Logged sample 'decision_analysis' event to {EVENT_LOG_FILE}")

    # Example 2: Successful Trade Execution Event
    execution_event_success = {
        "event_type": "trade_execution",
        "stock_symbol": "RELIANCE.NS",
        "trade_action": "BUY",
        "trade_quantity_attempted": 10,
        "trade_price_attempted": 2900.50,
        "trade_status": "SUCCESS",
        "trade_quantity_executed": 10,
        "trade_price_executed": 2900.50,
        "portfolio_cash_after_trade": 70995.0, # 100000 - (10 * 2900.50)
        "portfolio_holdings_stock_after_trade": {"quantity": 10, "avg_price": 2900.50}
    }
    log_event(execution_event_success)
    print(f"Logged sample successful 'trade_execution' event to {EVENT_LOG_FILE}")

    # Example 3: Failed Trade Execution Event
    execution_event_fail = {
        "event_type": "trade_execution",
        "stock_symbol": "TCS.NS",
        "trade_action": "BUY",
        "trade_quantity_attempted": 100, # Attempting to buy too many
        "trade_price_attempted": 3800.00,
        "trade_status": "FAILED",
        "trade_failure_reason": "Insufficient cash",
        "portfolio_cash_after_trade": 70995.0, # Unchanged from previous state
        "portfolio_holdings_stock_after_trade": {"quantity": 0, "avg_price": 0} # Assuming no prior TCS holdings
    }
    log_event(execution_event_fail)
    print(f"Logged sample failed 'trade_execution' event to {EVENT_LOG_FILE}")

    print("\n--- Trade Event Logger Demonstration Finished ---")
    print(f"Check the log file at: {EVENT_LOG_FILE}")
