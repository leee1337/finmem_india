import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Define news sources
NEWS_SOURCES = [
    {'name': 'Reuters_BusinessNews', 'url': 'https://www.reuters.com/news/archive/businessNews', # Reuters archive page
     'headline_selector': 'h3 > a', # Generic selector, likely needs refinement
     'link_prefix': 'https://www.reuters.com'} # For relative links, if any
]

# Output directory for news data
NEWS_DATA_OUTPUT_PATH = "data/news_data/"

# Standard headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_html(url):
    """
    Fetches HTML content from a given URL.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HTML from {url}: {e}")
        return None

def parse_news_headlines(html_content, source_config):
    """
    Parses news headlines and links from HTML content using BeautifulSoup.
    """
    if not html_content:
        return []

    news_items = []
    soup = BeautifulSoup(html_content, 'lxml') # Specify lxml parser

    # This is the part that needs careful inspection and adjustment per website
    # The selector 'h2 > a' is a common pattern but likely too generic.
    # We might need to find a specific class or ID that wraps news items.

    # Example: If headlines are in <a> tags within <h2> elements with a specific class
    # headline_elements = soup.select('.specific_news_class h2 a')
    # For now, using the placeholder:

    # headline_elements = soup.select(source_config['headline_selector'])

    # for element in headline_elements:
        # headline_text = element.get_text(strip=True)
    # Instead of parsing, returning a dummy item for testing file operations
    if source_config['name'] == 'Reuters_BusinessNews': # Ensure it's for the configured source
        news_items.append({
            'source': source_config['name'],
            'headline': 'Dummy Headline - Scraping Blocked',
            'link': source_config['url'], # Use the source URL as a dummy link
            'scraped_at': datetime.now().isoformat()
        })
        print(f"Returning dummy news item for {source_config['name']} due to scraping restrictions.")
        return news_items

    # Original loop - kept for structure, but won't be reached with current dummy logic for Reuters
    headline_elements = soup.select(source_config['headline_selector'])
    for element in headline_elements:
        headline_text = element.get_text(strip=True)
        link = element.get('href')

        if not link:
            continue # Skip if no link

        # Ensure link is absolute
        if source_config.get('link_prefix') and not link.startswith('http'):
            link = source_config['link_prefix'] + link

        # Basic check if link is a valid URL (can be improved)
        if not link.startswith('http'):
            print(f"Skipping potentially invalid link for '{headline_text}': {link}")
            continue

        # Date parsing would be highly site-specific and require more complex selectors.
        # For now, we'll skip date_published.
        news_items.append({
            'source': source_config['name'],
            'headline': headline_text,
            'link': link,
            'scraped_at': datetime.now().isoformat() # Add a timestamp for when it was scraped
            # 'date_published': 'YYYY-MM-DD' # Placeholder for future
        })

    # print(f"Found {len(news_items)} headlines from {source_config['name']}") # Original print
    return news_items

def save_news_data(news_items, output_path, filename_prefix):
    """
    Saves extracted news items to a JSON file.
    """
    if not news_items:
        print("No news items to save.")
        return

    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created news data directory: {output_path}")

    timestamp = datetime.now().strftime("%Y%m%d")
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
    Iterates through news sources, fetches, parses, and saves news.
    """
    print("Starting news scraping process...")
    for source_config in NEWS_SOURCES:
        print(f"\nScraping {source_config['name']} from {source_config['url']}...")
        html_content = fetch_html(source_config['url'])
        news_items = [] # Initialize news_items
        if html_content:
            news_items = parse_news_headlines(html_content, source_config)
        else:
            print(f"Failed to fetch HTML for {source_config['name']}. Generating dummy data for test.")
            # Generate dummy data if fetching fails, to test saving
            if source_config['name'] == 'Reuters_BusinessNews': # Or a more generic condition
                news_items.append({
                    'source': source_config['name'],
                    'headline': 'Dummy Headline - Fetching Failed',
                    'link': source_config['url'],
                    'scraped_at': datetime.now().isoformat()
                })

        if news_items: # Check if there are any news items (real or dummy)
            save_news_data(news_items, NEWS_DATA_OUTPUT_PATH, source_config['name'])
        else:
            # This condition will be met if fetching succeeded but parsing found nothing,
            # OR if fetching failed and no dummy data was generated.
            print(f"No headlines parsed or generated for {source_config['name']}.")
    print("\nNews scraping process finished.")

if __name__ == "__main__":
    scrape_all_sources()
