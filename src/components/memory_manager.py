import json
import os
from collections import deque
from datetime import datetime, timezone

# --- Configuration ---
MAX_STM_ITEMS = 100
MEMORY_DIR = "data/memory/"
STM_FILE = os.path.join(MEMORY_DIR, "stm_data.json")
LTM_FILE = os.path.join(MEMORY_DIR, "ltm_data.json")

# --- Memory Structures ---
stm_data = deque(maxlen=MAX_STM_ITEMS)
ltm_data = []

# --- STM Functions ---
def add_to_stm(item_type, content, stock_symbol=None, data=None):
    """
    Adds an item to the Short-Term Memory (STM).
    'item' could be a dictionary like
    {'type': 'news', 'content': news_headline, 'timestamp': datetime.now()} or
    {'type': 'price_update', 'stock': 'RELIANCE.NS', 'data': latest_ohlcv, 'timestamp': datetime.now()}
    """
    if not isinstance(item_type, str) or not content:
        print("Error: item_type (string) and content are required for STM.")
        return

    item = {
        'type': item_type,
        'content': content,
        'timestamp': datetime.now(timezone.utc).isoformat() # Store as ISO format string
    }
    if stock_symbol:
        item['stock'] = stock_symbol
    if data:
        item['data'] = data

    stm_data.append(item)
    print(f"Added to STM: {item['type']} - {item['content'][:50]}...")

def get_recent_stm_items(count=10):
    """Returns the last 'count' items from STM."""
    return list(stm_data)[-count:]

def get_stm_by_type(item_type, count=10):
    """Returns the last 'count' items of a specific 'item_type' from STM."""
    if not isinstance(item_type, str):
        print("Error: item_type must be a string.")
        return []

    filtered_items = [item for item in stm_data if item.get('type') == item_type]
    return filtered_items[-count:]

# --- LTM Functions ---
def add_to_ltm(category, summary, date_str=None, stock_symbol=None, related_stm_ids=None):
    """
    Adds an entry to Long-Term Memory (LTM).
    'entry' could be a dictionary like
    {'category': 'significant_event', 'stock': 'RELIANCE.NS',
     'summary': 'Positive earnings Q1 2023 led to 10% price increase', 'date': 'YYYY-MM-DD'}
    """
    if not isinstance(category, str) or not isinstance(summary, str):
        print("Error: category (string) and summary (string) are required for LTM.")
        return

    entry = {
        'id': f"ltm_{len(ltm_data) + 1}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}", # Unique ID
        'category': category,
        'summary': summary,
        'timestamp_added': datetime.now(timezone.utc).isoformat() # Store as ISO format string
    }
    if date_str: # Expected format 'YYYY-MM-DD'
        try:
            datetime.strptime(date_str, '%Y-%m-%d') # Validate date format
            entry['date'] = date_str
        except ValueError:
            print(f"Warning: Invalid date format for LTM entry '{summary}'. Use YYYY-MM-DD.")
            entry['date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d') # Default to today
    else:
        entry['date'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')


    if stock_symbol:
        entry['stock'] = stock_symbol
    if related_stm_ids and isinstance(related_stm_ids, list):
        entry['related_stm_ids'] = related_stm_ids

    ltm_data.append(entry)
    print(f"Added to LTM: {entry['category']} - {entry['summary'][:50]}...")


def retrieve_from_ltm(keywords: list):
    """
    Retrieves LTM entries containing all provided keywords (case-insensitive)
    in their 'summary', 'category', or 'stock' fields.
    """
    if not isinstance(keywords, list) or not all(isinstance(kw, str) for kw in keywords):
        print("Error: keywords must be a list of strings.")
        return []
    if not keywords:
        return [] # Return empty if no keywords provided

    results = []
    for entry in ltm_data:
        # Concatenate searchable fields into a single string for easier searching
        search_space = f"{entry.get('summary', '')} {entry.get('category', '')} {entry.get('stock', '')}".lower()

        match_all_keywords = True
        for kw in keywords:
            if kw.lower() not in search_space:
                match_all_keywords = False
                break

        if match_all_keywords:
            results.append(entry)

    print(f"LTM retrieval for keywords '{', '.join(keywords)}' found {len(results)} items.")
    return results

# --- Save/Load Functionality ---
def _ensure_memory_dir_exists():
    """Ensures the memory directory exists."""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
        print(f"Created memory directory: {MEMORY_DIR}")

def save_memory():
    """Saves STM and LTM data to JSON files."""
    _ensure_memory_dir_exists()

    try:
        with open(STM_FILE, 'w', encoding='utf-8') as f:
            # Datetime objects in STM items are already ISO strings
            json.dump(list(stm_data), f, ensure_ascii=False, indent=4)
        print(f"STM data saved to {STM_FILE}")
    except IOError as e:
        print(f"Error saving STM data: {e}")

    try:
        with open(LTM_FILE, 'w', encoding='utf-8') as f:
            # Datetime objects in LTM entries are already ISO strings or validated date strings
            json.dump(ltm_data, f, ensure_ascii=False, indent=4)
        print(f"LTM data saved to {LTM_FILE}")
    except IOError as e:
        print(f"Error saving LTM data: {e}")

def load_memory():
    """Loads STM and LTM data from JSON files."""
    global stm_data, ltm_data
    _ensure_memory_dir_exists() # Ensure directory exists even if files don't

    # Load STM
    if os.path.exists(STM_FILE):
        try:
            with open(STM_FILE, 'r', encoding='utf-8') as f:
                loaded_stm_list = json.load(f)
                # No complex object parsing needed as timestamps are ISO strings
                stm_data = deque(loaded_stm_list, maxlen=MAX_STM_ITEMS)
            print(f"STM data loaded from {STM_FILE}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading STM data from {STM_FILE}: {e}. Initializing empty STM.")
            stm_data = deque(maxlen=MAX_STM_ITEMS)
    else:
        print(f"STM file not found ({STM_FILE}). Initializing empty STM.")
        stm_data = deque(maxlen=MAX_STM_ITEMS)

    # Load LTM
    if os.path.exists(LTM_FILE):
        try:
            with open(LTM_FILE, 'r', encoding='utf-8') as f:
                loaded_ltm_list = json.load(f)
                # No complex object parsing needed as timestamps are ISO strings/dates are strings
                ltm_data = loaded_ltm_list
            print(f"LTM data loaded from {LTM_FILE}")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading LTM data from {LTM_FILE}: {e}. Initializing empty LTM.")
            ltm_data = []
    else:
        print(f"LTM file not found ({LTM_FILE}). Initializing empty LTM.")
        ltm_data = []

# --- Main Execution Block (Demonstration) ---
if __name__ == "__main__":
    print("--- Memory Manager Demonstration ---")

    # 1. Load existing memory (if any)
    load_memory()
    print(f"\nInitial STM items: {len(stm_data)}")
    print(f"Initial LTM items: {len(ltm_data)}")

    # 2. Add sample items to STM
    print("\n--- Adding to STM ---")
    add_to_stm(item_type="news", content="Market hits all-time high driven by tech stocks.")
    add_to_stm(item_type="price_update", content="Price increased", stock_symbol="TCS.NS", data={"open": 3800, "high": 3850, "low": 3790, "close": 3845})
    add_to_stm(item_type="analyst_rating", content="Upgraded to BUY", stock_symbol="RELIANCE.NS", data={"firm": "Global Brokers", "rating": "BUY", "target_price": 3200})
    add_to_stm(item_type="news", content="RBI keeps repo rate unchanged in latest policy meeting.")

    # 3. Demonstrate STM retrieval
    print("\n--- Retrieving from STM ---")
    recent_items = get_recent_stm_items(count=2)
    print(f"Last 2 STM items: {json.dumps(recent_items, indent=2)}")

    news_items = get_stm_by_type(item_type="news", count=5)
    print(f"Recent news STM items: {json.dumps(news_items, indent=2)}")

    # 4. Add sample items to LTM
    print("\n--- Adding to LTM ---")
    add_to_ltm(category="significant_event",
                 summary="Company X announced a 2:1 stock split, effective next month.",
                 date_str="2023-05-15",
                 stock_symbol="COMPANYX.NS")
    add_to_ltm(category="market_trend",
                 summary="Small-cap stocks saw significant rally in Q2 2023 after policy changes.",
                 date_str="2023-06-30")
    add_to_ltm(category="earnings_report",
                 summary="RELIANCE.NS Q1 2024: Net profit up 15% YoY, beat estimates. Revenue from retail grew 20%.",
                 date_str="2023-07-21",
                 stock_symbol="RELIANCE.NS")

    # 5. Demonstrate LTM retrieval
    print("\n--- Retrieving from LTM ---")
    reliance_events = retrieve_from_ltm(keywords=["reliance.ns", "profit"])
    print(f"LTM items for 'reliance.ns' and 'profit': {json.dumps(reliance_events, indent=2)}")

    split_events = retrieve_from_ltm(keywords=["split"])
    print(f"LTM items for 'split': {json.dumps(split_events, indent=2)}")

    # 6. Save memory
    print("\n--- Saving Memory ---")
    save_memory()

    # 7. Verify by reloading and checking counts (optional, for full demo)
    print("\n--- Verifying Save (by reloading) ---")
    # Clear current in-memory data to simulate fresh load
    stm_data.clear()
    ltm_data.clear()
    print("In-memory STM and LTM cleared.")

    load_memory()
    print(f"Reloaded STM items: {len(stm_data)}")
    print(f"Reloaded LTM items: {len(ltm_data)}")

    print("\n--- Memory Manager Demonstration Finished ---")
