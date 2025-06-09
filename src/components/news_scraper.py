import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Import Nifty 50 symbols
from config.nifty50_stocks import NIFTY_50_SYMBOLS

# Output directory for news data
NEWS_DATA_OUTPUT_PATH = "data/news_data/"

# Standard headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Configuration for Moneycontrol
MONEYCONTROL_CONFIG = {
    'name': 'Moneycontrol',
    'base_url': 'https://www.moneycontrol.com/news/business/companies/',  # General companies news page
    # Placeholder selectors - THESE WILL LIKELY NEED MANUAL ADJUSTMENT by inspecting Moneycontrol's HTML structure
    'news_item_container_selector': 'li.clearfix', # Example: Common list item selector
    'headline_selector_relative': 'h2 > a', # Selector for headline relative to the container
    'link_selector_relative': 'h2 > a', # Selector for link relative to the container (often same as headline)
    'date_selector_relative': 'span.meta_info', # Selector for date relative to the container
    'link_prefix': 'https://www.moneycontrol.com' # If links are relative
}

def fetch_html(url):
    """
    Fetches HTML content from a given URL.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15) # Increased timeout
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML from {url}: {e}")
        return None

def parse_moneycontrol_headlines(html_content, stock_symbol_context, config):
    """
    Parses news headlines, links, and dates from Moneycontrol HTML content.
    stock_symbol_context: Used to tag news items, e.g., "NIFTY50_GENERAL" if from a general page.
    config: The Moneycontrol configuration dictionary.
    """
    if not html_content:
        return []
    news_items = []
    soup = BeautifulSoup(html_content, 'lxml')

    # --- THIS SECTION USES PLACEHOLDER SELECTORS AND NEEDS REAL SELECTORS FROM SITE INSPECTION ---
    articles = soup.select(config.get('news_item_container_selector', 'div.news_item')) # Default to a generic div if not specified

    print(f"    Found {len(articles)} potential article containers using selector: '{config.get('news_item_container_selector')}'")

    for article_idx, article in enumerate(articles):
        try:
            headline_tag = article.select_one(config.get('headline_selector_relative', 'h3 > a'))
            headline_text = headline_tag.get_text(strip=True) if headline_tag else None

            link_tag = article.select_one(config.get('link_selector_relative', 'h3 > a')) # Often same as headline
            link = link_tag.get('href') if link_tag else None

            if not headline_text or not link:
                # print(f"      Skipping article {article_idx+1}: Missing headline or link.")
                continue

            if config.get('link_prefix') and not link.startswith('http'):
                link = config['link_prefix'] + link

            date_text = None
            date_tag = article.select_one(config.get('date_selector_relative', 'span.date')) # Generic date class guess
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                # TODO: Implement robust date parsing to convert 'Mar 23, 2024' or '2 hours ago' to 'YYYY-MM-DD'
                # For now, storing the raw text.

            # print(f"      Headline: {headline_text}, Link: {link}, Date: {date_text}")

            news_items.append({
                'source': config['name'],
                'stock_symbol': stock_symbol_context, # e.g., "NIFTY50_GENERAL"
                'headline': headline_text,
                'link': link,
                'published_at_raw': date_text, # Raw date string from site
                'scraped_at': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"    Error parsing an article for {stock_symbol_context} on Moneycontrol (article index {article_idx+1}): {e}")
    # --- END OF GUESS SECTION ---

    if not news_items and articles: # If containers were found but no items parsed
        print(f"    WARNING: Found {len(articles)} article containers, but no news items were successfully parsed with current selectors for {stock_symbol_context}.")
        print(f"    Consider refining selectors: headline_selector_relative, link_selector_relative, date_selector_relative within the container.")

    if not articles: # If no containers were found
         print(f"    No article containers found using selector '{config.get('news_item_container_selector')}' for {stock_symbol_context} on Moneycontrol.")
         # Add a dummy item to indicate an attempt was made but nothing specific found by selectors
         news_items.append({
            'source': config['name'],
            'stock_symbol': stock_symbol_context,
            'headline': f'Dummy: No articles found/parsed for {stock_symbol_context} with current selectors.',
            'link': config['base_url'],
            'published_at_raw': None,
            'scraped_at': datetime.now().isoformat()
        })

    print(f"    Parsed {len(news_items)} headlines for {stock_symbol_context} from Moneycontrol.")
    return news_items

def scrape_moneycontrol_nifty50():
    """
    Scrapes news from a general Moneycontrol news page relevant to Nifty 50 / business.
    """
    all_nifty50_news = []

    print(f"Fetching general news from Moneycontrol ({MONEYCONTROL_CONFIG['name']})...")
    url_to_scrape = MONEYCONTROL_CONFIG['base_url']
    html_content = fetch_html(url_to_scrape)

    if html_content:
        # Use "NIFTY50_GENERAL" as context since we are scraping a general page.
        # RAG will be responsible for matching these to specific stocks if possible.
        news_items = parse_moneycontrol_headlines(html_content, "NIFTY50_GENERAL", MONEYCONTROL_CONFIG)
        all_nifty50_news.extend(news_items)
        print(f"Fetched and parsed general Moneycontrol page. Total items: {len(all_nifty50_news)}")
    else:
        print(f"Failed to fetch general news from Moneycontrol. Adding a dummy failure item.")
        all_nifty50_news.append({
            'source': MONEYCONTROL_CONFIG['name'],
            'stock_symbol': 'NIFTY50_GENERAL',
            'headline': 'Dummy: Failed to fetch Moneycontrol general news page',
            'link': url_to_scrape,
            'published_at_raw': None,
            'scraped_at': datetime.now().isoformat()
        })

    if all_nifty50_news:
        save_news_data(all_nifty50_news, NEWS_DATA_OUTPUT_PATH, "moneycontrol_nifty50_general_feed")
    else:
        print("No news items (including dummies for failure) were generated from Moneycontrol general feed.")
    return all_nifty50_news

def save_news_data(news_items, output_path, filename_prefix):
    """
    Saves extracted news items to a JSON file. A timestamp is appended to the filename.
    """
    if not news_items:
        print("No news items to save.")
        return

    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created news data directory: {output_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Added H M S for more unique filenames
    filename = f"{filename_prefix}_{timestamp}.json"
    file_path = os.path.join(output_path, filename)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(news_items, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved news data to {file_path}")
    except IOError as e:
        print(f"Error saving news data to {file_path}: {e}")

def scrape_all_sources():
    """
    Main function to trigger scraping for all configured primary sources.
    Currently focused on Moneycontrol for Nifty 50 general news.
    """
    print("\n--- Starting News Scraping Process (Moneycontrol Focus) ---")
    # For now, directly calls the Moneycontrol specific scraper.
    # Could be extended to loop through a list of scraper functions if more sources are added.
    scrape_moneycontrol_nifty50()
    print("--- News Scraping Process Finished ---\n")

if __name__ == "__main__":
    print("--- News Scraper Main Execution ---")
    # Ensure data directory exists for the output
    if not os.path.exists(NEWS_DATA_OUTPUT_PATH):
        os.makedirs(NEWS_DATA_OUTPUT_PATH)
        print(f"Created news data directory: {NEWS_DATA_OUTPUT_PATH}")

    scrape_all_sources()
    print("--- News Scraper Main Execution Finished ---")
