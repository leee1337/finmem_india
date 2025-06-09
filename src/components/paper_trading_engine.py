import json
import os
from datetime import datetime, timezone

# --- Configuration ---
INITIAL_CAPITAL = 100000.0
PORTFOLIO_DIR = "data/portfolio/"
PORTFOLIO_FILE = os.path.join(PORTFOLIO_DIR, "portfolio_state.json")

# --- Portfolio State Variables ---
# These will be loaded from file or initialized by load_portfolio_state()
cash = 0.0
holdings = {}  # e.g., {'RELIANCE.NS': {'quantity': 10, 'avg_price': 2500.0}}
transaction_log = []

# --- Utility Functions ---
def _ensure_portfolio_dir_exists():
    """Ensures the portfolio directory exists."""
    if not os.path.exists(PORTFOLIO_DIR):
        os.makedirs(PORTFOLIO_DIR)
        print(f"Created portfolio directory: {PORTFOLIO_DIR}")

# --- Save/Load Portfolio State ---
def save_portfolio_state():
    """Saves current cash, holdings, and transaction_log to PORTFOLIO_FILE."""
    _ensure_portfolio_dir_exists()
    state = {
        'cash': cash,
        'holdings': holdings,
        'transaction_log': transaction_log,
        'last_saved': datetime.now(timezone.utc).isoformat()
    }
    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        # print(f"Portfolio state saved to {PORTFOLIO_FILE}")
    except IOError as e:
        print(f"Error saving portfolio state: {e}")

def load_portfolio_state():
    """Loads portfolio state from PORTFOLIO_FILE or initializes it."""
    global cash, holdings, transaction_log
    _ensure_portfolio_dir_exists()

    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                cash = state.get('cash', INITIAL_CAPITAL)
                holdings = state.get('holdings', {})
                transaction_log = state.get('transaction_log', [])
            print(f"Portfolio state loaded from {PORTFOLIO_FILE}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading portfolio state from {PORTFOLIO_FILE}: {e}. Initializing fresh state.")
            _initialize_fresh_state()
    else:
        print(f"Portfolio file not found ({PORTFOLIO_FILE}). Initializing fresh state.")
        _initialize_fresh_state()

def _initialize_fresh_state():
    """Initializes portfolio to default state."""
    global cash, holdings, transaction_log
    cash = INITIAL_CAPITAL
    holdings = {}
    transaction_log = []
    print("Initialized with fresh portfolio state.")
    save_portfolio_state() # Save the initial fresh state

# --- Execute Order ---
def execute_order(stock_symbol: str, action: str, quantity: int, current_price: float):
    """
    Executes a buy or sell order and updates portfolio state.
    """
    global cash, holdings, transaction_log
    timestamp = datetime.now(timezone.utc).isoformat()

    if not isinstance(stock_symbol, str) or not stock_symbol:
        print("Error: Stock symbol must be a non-empty string.")
        return False
    if action.upper() not in ["BUY", "SELL"]:
        print(f"Error: Invalid action '{action}'. Must be 'BUY' or 'SELL'.")
        return False
    if not isinstance(quantity, int) or quantity <= 0:
        print("Error: Quantity must be a positive integer.")
        return False
    if not isinstance(current_price, (float, int)) or current_price <= 0:
        print("Error: Current price must be a positive number.")
        return False

    action = action.upper() # Standardize action

    if action == "BUY":
        cost = quantity * current_price
        if cash >= cost:
            cash -= cost
            if stock_symbol in holdings:
                current_qty = holdings[stock_symbol]['quantity']
                current_avg_price = holdings[stock_symbol]['avg_price']
                new_total_value = (current_qty * current_avg_price) + cost
                new_quantity = current_qty + quantity
                holdings[stock_symbol]['quantity'] = new_quantity
                holdings[stock_symbol]['avg_price'] = new_total_value / new_quantity
            else:
                holdings[stock_symbol] = {'quantity': quantity, 'avg_price': current_price}

            log_entry = {'timestamp': timestamp, 'stock': stock_symbol, 'action': 'BUY',
                         'price': current_price, 'quantity': quantity, 'cost': cost, 'status': 'SUCCESS'}
            transaction_log.append(log_entry)
            print(f"BUY order successful: {quantity} {stock_symbol} @ {current_price:.2f}")
            save_portfolio_state()
            return True
        else:
            log_entry = {'timestamp': timestamp, 'stock': stock_symbol, 'action': 'BUY',
                         'price': current_price, 'quantity': quantity, 'status': 'FAILED',
                         'reason': 'Insufficient cash'}
            transaction_log.append(log_entry)
            print(f"BUY order failed: Insufficient cash for {quantity} {stock_symbol} @ {current_price:.2f}")
            return False

    elif action == "SELL":
        if stock_symbol in holdings and holdings[stock_symbol]['quantity'] >= quantity:
            proceeds = quantity * current_price
            avg_buy_price = holdings[stock_symbol]['avg_price']
            pnl_for_this_sale = (current_price - avg_buy_price) * quantity

            cash += proceeds
            holdings[stock_symbol]['quantity'] -= quantity

            if holdings[stock_symbol]['quantity'] == 0:
                del holdings[stock_symbol]

            log_entry = {'timestamp': timestamp, 'stock': stock_symbol, 'action': 'SELL',
                         'price': current_price, 'quantity': quantity, 'proceeds': proceeds,
                         'pnl': pnl_for_this_sale, 'status': 'SUCCESS'}
            transaction_log.append(log_entry)
            print(f"SELL order successful: {quantity} {stock_symbol} @ {current_price:.2f}. P&L: {pnl_for_this_sale:.2f}")
            save_portfolio_state()
            return True
        else:
            reason = "Stock not held" if stock_symbol not in holdings else "Insufficient quantity"
            log_entry = {'timestamp': timestamp, 'stock': stock_symbol, 'action': 'SELL',
                         'price': current_price, 'quantity': quantity, 'status': 'FAILED',
                         'reason': reason}
            transaction_log.append(log_entry)
            print(f"SELL order failed: {reason} for {quantity} {stock_symbol}")
            return False
    return False # Should not reach here

# --- Portfolio Valuation Functions ---
def get_current_holdings_value(current_market_prices: dict):
    """Calculates the total current market value of all holdings."""
    total_value = 0.0
    for stock, data in holdings.items():
        if stock in current_market_prices:
            total_value += data['quantity'] * current_market_prices[stock]
        else:
            # If market price for a holding isn't available, use its average buy price (conservative)
            # Or print a warning, or skip. For now, using avg_price as fallback.
            print(f"Warning: Market price for {stock} not provided. Using average buy price for valuation.")
            total_value += data['quantity'] * data['avg_price']
    return total_value

def get_total_portfolio_value(current_market_prices: dict):
    """Calculates total portfolio value (cash + current value of holdings)."""
    return cash + get_current_holdings_value(current_market_prices)

# --- Getter Functions ---
def get_cash():
    return cash

def get_holdings():
    return holdings.copy() # Return a copy to prevent direct modification

def get_transaction_log():
    return transaction_log[:] # Return a copy

# --- Main Execution Block (Demonstration) ---
if __name__ == "__main__":
    print("--- Paper Trading Engine Demonstration ---")
    load_portfolio_state()

    def print_portfolio_status(market_prices=None):
        print(f"\nPortfolio Status:")
        print(f"  Cash: {get_cash():.2f}")
        current_h = get_holdings()
        if current_h:
            print(f"  Holdings:")
            for stock, data in current_h.items():
                print(f"    {stock}: Quantity={data['quantity']}, Avg Price={data['avg_price']:.2f}")
        else:
            print("  Holdings: None")
        if market_prices:
            print(f"  Holdings Market Value: {get_current_holdings_value(market_prices):.2f}")
            print(f"  Total Portfolio Value: {get_total_portfolio_value(market_prices):.2f}")

    print_portfolio_status()

    print("\n--- Executing Sample Trades ---")
    # Sample BUY orders
    execute_order("RELIANCE.NS", "BUY", 10, 2850.00)
    execute_order("TCS.NS", "BUY", 5, 3800.50)
    execute_order("INFY.NS", "BUY", 15, 1520.75)

    sample_market_prices = {"RELIANCE.NS": 2880.00, "TCS.NS": 3810.00, "INFY.NS": 1500.00}
    print_portfolio_status(sample_market_prices)

    # Sample SELL orders
    execute_order("RELIANCE.NS", "SELL", 3, 2880.00) # Sell some RELIANCE
    execute_order("HDFCBANK.NS", "SELL", 2, 1500.00) # Try to sell stock not held
    execute_order("TCS.NS", "SELL", 10, 3850.00) # Try to sell more than held

    print_portfolio_status(sample_market_prices)

    # Insufficient funds scenario
    print("\n--- Testing Insufficient Funds ---")
    # Assuming remaining cash is less than 100 * 3000 = 300000
    execute_order("RELIANCE.NS", "BUY", 100, 3000.00)

    print_portfolio_status(sample_market_prices)

    print("\n--- Final Transaction Log ---")
    log = get_transaction_log()
    if log:
        for entry in log:
            print(entry)
    else:
        print("Transaction log is empty.")

    # Final save (though execute_order saves on success)
    # save_portfolio_state() # Not strictly necessary here if all successful trades saved.
    print("\n--- Paper Trading Engine Demonstration Finished ---")
