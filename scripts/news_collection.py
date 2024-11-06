from pymilvus import MilvusClient
from datetime import datetime

# script for querying news articles from milvus

client = MilvusClient(uri="./milvus_news.db")  

# Define the collection name
collection_name = "news_articles"

# Check if the collection exists
if client.has_collection(collection_name):
    try:
        # Query the collection with proper field names
        results = client.query(
            collection_name=collection_name,
            limit=50
        )

        # Display results
        for article in results:
            print("\nArticle Details:")
            print(f"Title: {article.get('title')}")
            print(f"Description: {article.get('description')[:200]}...")  # Truncate long descriptions
            print(f"URL: {article.get('url')}")
            print(f"Source: {article.get('source_name')}")
            print(f"Published: {article.get('published_at')}")
            if article.get('query'):
                print(f"Original Query: {article.get('query')}")
            if article.get('relevance_score'):
                print(f"Relevance Score: {article.get('relevance_score'):.2f}")
            print("-" * 80)

    except Exception as e:
        print(f"Failed to query collection: {collection_name}")
        print("Error:", str(e))
else:
    print(f"Collection '{collection_name}' does not exist.")
