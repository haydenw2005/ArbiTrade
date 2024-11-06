from typing import List, Optional
from pymilvus import MilvusClient
import numpy as np
from datetime import datetime
from src.research_tools.margin_schemas import NewsArticle
from src.utils.logger import log_debug
import openai
import asyncio
from config.settings import OPENAI_API_KEY
import json
import uuid
import re


class VectorStore:
    def __init__(self):
        # Use Milvus Lite with a local file
        self.client = MilvusClient(uri="./milvus_news.db")
        self.collection_name = "news_articles"
        self.embedding_dim = 1536  # OpenAI's text-embedding-3-small dimension
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists with the correct schema"""
        try:
            # Check if collection exists
            if not self.client.has_collection(self.collection_name):
                # Create collection with specified parameters and schema
                self.client.create_collection(
                    collection_name=self.collection_name,
                    dimension=self.embedding_dim,
                    primary_field_name="id",  # Specify id as primary field
                    id_type="int64",  # Specify id type
                    vector_field_name="embedding",
                    metric_type="L2",
                    consistency_level="Strong",
                    enable_dynamic_field=True  # Enable dynamic fields for other attributes
                )
                log_debug("Created news articles collection in Milvus")
            
            log_debug("Connected to existing collection")
            
        except Exception as e:
            log_debug(f"Error ensuring collection: {str(e)}")
            raise

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI's API (synchronous)"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            # Convert to numpy array to ensure proper format
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            log_debug(f"Error getting embedding: {str(e)}")
            raise

    async def get_embedding_async(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI's API (async wrapper)"""
        try:
            # Run the synchronous embedding creation in a thread pool
            return await asyncio.get_event_loop().run_in_executor(
                None, self.get_embedding, text
            )
        except Exception as e:
            log_debug(f"Error getting embedding async: {str(e)}")
            raise

    async def insert_articles(self, articles: List[NewsArticle], news_query):
        """Insert articles into vector store"""
        try:
            BATCH_SIZE = 100  

            # Initialize a batch for insertion
            batch_data = []

            # Loop through articles
            for article in articles:
                # Check if article already exists using expr string format
                existing = self.client.query(
                    collection_name=self.collection_name,
                    filter=f'url == "{article.url}"'  # Changed to string expression
                )
                if existing:
                    continue

                # Create embedding from title + description
                text = f"{article.title} {article.description} {news_query} "
                try:
                    embedding = await self.get_embedding_async(text)
                except Exception as e:
                    print(f"Failed to generate embedding for article {article.url}: {e}")
                    continue

                # Convert embedding to the correct format for Milvus
                embedding_list = embedding.astype(np.float32).tolist()

                # Prepare the article data with a unique UUID as ID
                article_data = {
                    "id": str(uuid.uuid4()),  # Use UUID for unique identification
                    "title": article.title,
                    "description": article.description,
                    "url": article.url,
                    "source_name": article.source_name,
                    "published_at": article.published_at.isoformat(),
                    "embedding": embedding_list
                }
                
                # Add article data to batch
                batch_data.append(article_data)

                # Insert in batches
                if len(batch_data) >= BATCH_SIZE:
                    try:
                        self.client.insert(
                            collection_name=self.collection_name,
                            data=batch_data  # Insert batch
                        )
                        log_debug(f"Inserted batch of {len(batch_data)} articles to vectore store...")
                        batch_data.clear()  # Clear batch after successful insertion
                    except Exception as e:
                        print(f"Failed to insert batch: {e}")
                        batch_data.clear()  # Clear batch to prevent re-attempt with faulty data

            # Insert any remaining data in batch_data after loop ends
            if batch_data:
                try:
                    self.client.insert(
                        collection_name=self.collection_name,
                        data=batch_data
                    )
                    log_debug(f"Inserted FINAL batch of {len(batch_data)} articles to vectore store...")
                    batch_data.clear()
                except Exception as e:
                    print(f"Failed to insert final batch: {e}")

            
            log_debug(f"Inserted {len(articles)} articles into vector store")
            
        except Exception as e:
            log_debug(f"Error inserting articles: {str(e)}")
            raise

    async def search_similar_articles(self, query: str, limit: int = 10) -> List[NewsArticle]:
        """Search for similar articles using vector similarity"""
        try:
            # Get query embedding
            query_embedding = await self.get_embedding_async(query)
            
            # Convert to list for search
            query_embedding_list = query_embedding.tolist()
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding_list],
                limit=limit,
                output_fields=["title", "description", "url", "source_name", "published_at"],
                # Set search parameters for better performance
                search_params={
                    'metric_type': 'L2', #Euclidian distance
                    'params': {
                        'nprobe': 10,
                        'level': 1,
                        'radius': 1.0,
                        'range_filter': 0.8
                    }           
                }
            )
            
            #convert to valid json
            results_json = json.dumps(results, indent=4)
            #log_debug(f"JSON compatible data: {results_json}")
            results_json = json.loads(results_json)
            
            articles = []
            if results_json and results_json[0]:  # Check if results exist and have data
                for hit in results_json[0]:
                    try:
                        entity = hit['entity']
                        distance = hit['distance']
                        
                        articles.append(NewsArticle(
                            title=entity['title'],
                            description=entity['description'],
                            url=entity['url'],
                            source_name=entity['source_name'],
                            published_at=datetime.fromisoformat(
                                entity['published_at']
                            ),
                            # Convert distance score to similarity score
                            relevance_score=1.0 - min(distance / 2.0, 1.0)  # Adjusted normalization
                        ))
                    except Exception as e:
                        log_debug(f"Error converting search result to NewsArticle: {str(e)}")
                        continue
            
            return articles
            
        except Exception as e:
            log_debug(f"Error searching articles: {str(e)}")
            return []