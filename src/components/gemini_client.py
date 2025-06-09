import google.generativeai as genai
import os
import json # For formatting data in prompts
import re # For parsing
from dotenv import load_dotenv

# --- Initialize Gemini Client ---
API_KEY_LOADED = False
MODEL_INITIALIZED = False
model = None

try:
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_API_KEY_HERE":
        genai.configure(api_key=GEMINI_API_KEY)
        # Check available models, could use 'gemini-1.5-flash' or 'gemini-pro'
        # for model_info in genai.list_models():
        #     if 'generateContent' in model_info.supported_generation_methods:
        #         print(model_info.name) # e.g. models/gemini-1.5-flash-latest

        # Using gemini-1.5-flash as it's generally available and efficient
        model = genai.GenerativeModel('gemini-1.5-flash')
        API_KEY_LOADED = True
        MODEL_INITIALIZED = True
        print("Gemini API Key loaded and model initialized successfully (gemini-1.5-flash).")
    else:
        print("Error: GEMINI_API_KEY not found or is set to placeholder in .env file.")
        print("Please create a .env file in the project root (copy from .env.example) and add your valid API key.")
        API_KEY_LOADED = False # Explicitly set

except Exception as e:
    print(f"Error during Gemini client initialization: {e}")
    API_KEY_LOADED = False
    MODEL_INITIALIZED = False


# --- Data Formatting Helper Function ---
def _format_input_for_gemini(label, data_object):
    """
    Formats various Python objects into a string representation for the prompt.
    """
    if isinstance(data_object, (dict, list)):
        try:
            # Pretty print JSON for readability in the prompt
            return f"{label}:\n{json.dumps(data_object, indent=2)}\n"
        except TypeError: # Handle non-serializable objects if they sneak in
             return f"{label}:\n{str(data_object)}\n" # Fallback to string
    return f"{label}:\n{str(data_object)}\n"


# --- Get Trading Decision from Gemini ---
def get_trading_decision_from_gemini(stock_symbol, current_price, stock_data_summary,
                                     technical_indicators, relevant_news_headlines,
                                     stm_extracts, ltm_extracts, current_portfolio_status):
    """
    Constructs a prompt and queries the Gemini model for a trading decision.
    """
    if not MODEL_INITIALIZED:
        return "Error: Gemini model not initialized. Cannot get trading decision."

    prompt_parts = [
        "You are a financial analyst AI providing trading advice for the Indian stock market (Nifty 50).",
        "Your goal is to recommend a trading action (BUY, SELL, HOLD) and provide brief reasoning and a confidence level.",
        "Later, you will also be asked for position sizing if applicable.\n",

        _format_input_for_gemini("Stock Symbol", stock_symbol),
        _format_input_for_gemini("Current Market Price", current_price),
        _format_input_for_gemini("Recent Stock Data Summary (e.g., Last 5 days OHLCV)", stock_data_summary),
        _format_input_for_gemini("Calculated Technical Indicators", technical_indicators),
        _format_input_for_gemini("Relevant News Headlines (from RAG)", relevant_news_headlines),
        _format_input_for_gemini("Recent Short-Term Memory Extracts (e.g., recent trades, market sentiment)", stm_extracts),
        _format_input_for_gemini("Relevant Long-Term Memory Extracts (e.g., past performance, significant events)", ltm_extracts),
        _format_input_for_gemini("Current Portfolio Status", current_portfolio_status),

        f"Based on all the above information, what is your trading recommendation for {stock_symbol}?",
        "Please provide your response STRICTLY in the following format, with each part on a new line:",
        "DECISION: [BUY/SELL/HOLD]",
        "REASONING: [Your brief reasoning here, ideally within 2-3 sentences]",
        "CONFIDENCE: [High/Medium/Low]"
    ]
    prompt = "\n".join(prompt_parts)

    # print("\n--- Generated Prompt for Gemini ---")
    # print(prompt)
    # print("--- End of Prompt ---\n")

    try:
        response = model.generate_content(prompt)
        # print(f"Gemini Raw Response: {response}") # For debugging the full response object
        if response and response.candidates and hasattr(response.candidates[0].content, 'parts'):
            return response.candidates[0].content.parts[0].text
        elif response and hasattr(response, 'text'): # Older API versions might have response.text
            return response.text
        else:
            # Try to access parts if it's an iterable (like a list)
            if response and response.parts:
                 return response.parts[0].text
            print("Warning: Unexpected response structure from Gemini API.")
            print(f"Full response object: {response}")
            return "Error: Could not extract text from Gemini response. Structure was not as expected."

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return f"Error: Exception during API call - {str(e)}"

# --- Response Parsing Function ---
def parse_gemini_response(response_text):
    """
    Parses the Gemini response text to extract decision, reasoning, and confidence.
    """
    if not isinstance(response_text, str):
        return {'decision': 'ERROR', 'reasoning': 'Invalid response object received.', 'confidence': 'Unknown'}

    parsed_data = {
        'decision': 'Unknown',
        'reasoning': 'Not found',
        'confidence': 'Unknown'
    }

    # Using regex to find the key-value pairs, allowing for some flexibility
    decision_match = re.search(r"DECISION:\s*(BUY|SELL|HOLD)", response_text, re.IGNORECASE)
    if decision_match:
        parsed_data['decision'] = decision_match.group(1).upper()

    reasoning_match = re.search(r"REASONING:\s*(.+)", response_text, re.IGNORECASE)
    if reasoning_match:
        # Capture until the next potential keyword (CONFIDENCE:) or end of string
        reasoning_text = reasoning_match.group(1).strip()
        confidence_pos = re.search(r"\nCONFIDENCE:", reasoning_text, re.IGNORECASE)
        if confidence_pos:
            parsed_data['reasoning'] = reasoning_text[:confidence_pos.start()].strip()
        else:
            parsed_data['reasoning'] = reasoning_text

    confidence_match = re.search(r"CONFIDENCE:\s*(High|Medium|Low)", response_text, re.IGNORECASE)
    if confidence_match:
        parsed_data['confidence'] = confidence_match.group(1).capitalize()
        # Further refine reasoning if confidence was captured within it
        if parsed_data['reasoning'].endswith(confidence_match.group(0)):
             parsed_data['reasoning'] = parsed_data['reasoning'][:-len(confidence_match.group(0))].strip()


    if parsed_data['decision'] == 'Unknown' and "error" not in response_text.lower():
        parsed_data['reasoning'] = f"Could not parse. Raw response: {response_text}"

    return parsed_data

# --- Main Execution Block (Demonstration) ---
if __name__ == "__main__":
    print("\n--- Gemini Client Demonstration ---")

    if not API_KEY_LOADED or not MODEL_INITIALIZED:
        print("Cannot run Gemini Client demonstration because API key is not loaded or model failed to initialize.")
        print("Please ensure your .env file is correctly set up with a valid GEMINI_API_KEY.")
    else:
        print("Proceeding with demonstration as API key seems to be loaded and model initialized.")
        # Prepare sample data (as strings or simple dicts/lists for formatting)
        stock_symbol = "RELIANCE.NS"
        current_price = "2900.50"
        stock_data_summary = "Day1: O:2800 H:2850 L:2790 C:2840 V:1M\nDay2: O:2840 H:2860 L:2830 C:2855 V:1.2M"
        technical_indicators = {'SMA20': 2800, 'SMA50': 2750, 'RSI14': 60, 'MACD_line': 15.5, 'MACD_signal': 12.3}
        relevant_news_headlines = [
            "Reliance AGM announced for next month, focus on new energy.",
            "Global oil prices show slight increase.",
            "SEBI introduces new margin rules for derivatives."
        ]
        stm_extracts = [
            {'type': 'market_sentiment', 'content': 'Overall market is cautiously optimistic.', 'timestamp': '...'},
            {'type': 'trade_executed', 'stock': 'TCS.NS', 'action': 'BUY', 'quantity': 10, 'price': 3800, 'timestamp': '...'}
        ]
        ltm_extracts = [
            {'category': 'past_event', 'stock': 'RELIANCE.NS', 'summary': 'Historically, Reliance stock sees volatility around AGM dates.', 'date': '...'},
            {'category': 'company_strategy', 'stock': 'RELIANCE.NS', 'summary': 'Reliance investing heavily in green energy, long-term positive.', 'date': '...'}
        ]
        current_portfolio_status = {'cash': 50000, 'holdings': {'TCS.NS': {'quantity': 10, 'avg_price': 3800}, 'INFY.NS': {'quantity': 20, 'avg_price': 1500}}}

        print("\n--- Calling Gemini for Trading Decision ---")
        raw_response_text = get_trading_decision_from_gemini(
            stock_symbol, current_price, stock_data_summary,
            technical_indicators, relevant_news_headlines,
            stm_extracts, ltm_extracts, current_portfolio_status
        )

        print("\n--- Raw Response from Gemini ---")
        print(raw_response_text)

        print("\n--- Parsed Response ---")
        parsed_decision = parse_gemini_response(raw_response_text)
        print(json.dumps(parsed_decision, indent=2))

    print("\n--- Gemini Client Demonstration Finished ---")
