import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import glob # For finding files matching a pattern

# --- Configuration ---
NEWS_DATA_PATH = "data/news_data/" # As used by news_scraper.py

# --- Global Variables for Vector Store ---
vectorizer = TfidfVectorizer(stop_words='english')
news_embeddings = None # TF-IDF matrix
all_news_items = [] # List of actual news item dictionaries

# --- Helper Function to Load News Data ---
def load_news_from_directory(news_data_path=NEWS_DATA_PATH):
    """
    Scans the news_data_path for JSON files, loads all news items from them.
    """
    loaded_items = []
    if not os.path.exists(news_data_path):
        print(f"Warning: News data directory not found: {news_data_path}")
        return loaded_items

    json_files = glob.glob(os.path.join(news_data_path, "*.json"))
    if not json_files:
        print(f"No JSON files found in {news_data_path}")
        return loaded_items

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list): # Expecting a list of news items
                    loaded_items.extend(data)
                else:
                    print(f"Warning: Expected a list of items in {file_path}, but found {type(data)}. Skipping.")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing {file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {file_path}: {e}")

    print(f"Loaded {len(loaded_items)} news items from {len(json_files)} file(s) in {news_data_path}.")
    return loaded_items

# --- Build/Update Vector Store ---
def build_or_update_vector_store(force_reload=False):
    """
    Builds or updates the TF-IDF vector store from news items.
    """
    global news_embeddings, all_news_items, vectorizer

    # Check if store needs building/updating
    if news_embeddings is not None and not force_reload and all_news_items:
        print("Vector store already exists. Skipping build/update unless force_reload is True.")
        return

    print("Building/updating vector store...")
    current_news_items = load_news_from_directory()

    if not current_news_items:
        print("No news items found to build the vector store.")
        all_news_items = [] # Ensure it's empty
        news_embeddings = None # Ensure it's None
        return

    # Filter for items with a 'headline'
    corpus = [item['headline'] for item in current_news_items if 'headline' in item and isinstance(item['headline'], str)]

    if not corpus:
        print("No valid headlines found in news items to build corpus for vector store.")
        all_news_items = current_news_items # Store them anyway, but embeddings will be None
        news_embeddings = None
        return

    # Update global list of all items (only those that will be in the corpus)
    # We need to align all_news_items with the corpus that news_embeddings will represent
    all_news_items = [item for item in current_news_items if 'headline' in item and isinstance(item['headline'], str)]

    try:
        news_embeddings = vectorizer.fit_transform(corpus)
        print(f"Vector store built/updated. Shape of embeddings: {news_embeddings.shape}")
        print(f"Number of items in all_news_items for retrieval: {len(all_news_items)}")
    except Exception as e:
        print(f"Error during TF-IDF fitting or transformation: {e}")
        news_embeddings = None
        all_news_items = []


# --- Similarity Search Function ---
def find_similar_news(query_text, top_n=5):
    """
    Finds news articles similar to the query_text using TF-IDF cosine similarity.
    """
    global news_embeddings, all_news_items, vectorizer

    build_or_update_vector_store() # Ensure store is up-to-date (but won't rebuild if not forced and exists)

    if news_embeddings is None or not all_news_items:
        print("Cannot perform search: Vector store is empty or not built.")
        return []

    if not isinstance(query_text, str) or not query_text.strip():
        print("Query text must be a non-empty string.")
        return []

    try:
        query_embedding = vectorizer.transform([query_text])
    except Exception as e:
        print(f"Error transforming query text: {e}")
        return []

    # Calculate cosine similarities
    # news_embeddings is (n_samples, n_features), query_embedding is (1, n_features)
    similarities = cosine_similarity(query_embedding, news_embeddings)

    # similarities is a 2D array [[]], get the first row
    if similarities.shape[0] == 0:
        print("Could not compute similarities.")
        return []

    similarity_scores = similarities[0]

    # Get top_n indices
    # Sort by similarity score in descending order and get indices
    # Ensure we don't request more items than available
    num_available_items = len(similarity_scores)
    actual_top_n = min(top_n, num_available_items)

    # Get indices of top N scores. If all scores are 0, argsort might behave unexpectedly for "top"
    # We only want items with similarity > 0
    # Filter out zero similarity scores before sorting if needed, or handle it by checking score

    sorted_indices = similarity_scores.argsort()[::-1] # Sort descending, get indices

    results = []
    for i in range(actual_top_n):
        idx = sorted_indices[i]
        score = similarity_scores[idx]
        # Optionally, set a threshold for minimum similarity
        # if score < 0.01: # Example threshold to avoid completely unrelated items
        #     break
        if idx < len(all_news_items): # Boundary check
             results.append({'item': all_news_items[idx], 'score': score})
        else:
            print(f"Warning: Index {idx} out of bounds for all_news_items (len: {len(all_news_items)}).")


    print(f"Found {len(results)} similar news items for query: '{query_text}'")
    return results

# --- Main Execution Block (Demonstration) ---
if __name__ == "__main__":
    print("--- RAG Retriever Demonstration ---")

    # 1. Build the vector store (force reload for demonstration)
    # In a real app, force_reload might be False unless new data is known to be available.
    build_or_update_vector_store(force_reload=True)

    # 2. Check if news items were loaded and embeddings built
    if news_embeddings is not None and all_news_items:
        print(f"\nSuccessfully built vector store with {news_embeddings.shape[0]} items.")

        # 3. Formulate a sample query
        # Try a query that might match the dummy data if that's what news_scraper produced
        sample_queries = ["market news", "dummy headline", "Reuters update"]

        for query in sample_queries:
            print(f"\n--- Searching for: '{query}' ---")
            similar_articles = find_similar_news(query_text=query, top_n=3)

            if similar_articles:
                print(f"Top {len(similar_articles)} articles found for '{query}':")
                for article_info in similar_articles:
                    print(f"  Score: {article_info['score']:.4f} - Headline: {article_info['item']['headline']}")
                    if 'link' in article_info['item']:
                        print(f"    Link: {article_info['item']['link']}")
                    if 'source' in article_info['item']:
                         print(f"    Source: {article_info['item']['source']}")
            else:
                print(f"No similar articles found for '{query}'.")
    else:
        print("\nCould not build vector store. This might be because no news data files were found,")
        print("or the files were empty/malformed, or contained no valid headlines.")
        print("Please ensure 'news_scraper.py' has run and produced data in 'data/news_data/'.")
        # Example of dummy data structure that load_news_from_directory expects:
        # [{"source": "...", "headline": "...", "link": "...", "scraped_at": "..."}]

    print("\n--- RAG Retriever Demonstration Finished ---")
