from typing import List, Optional
import aiohttp
from datetime import datetime, timedelta
import json
from src.research_tools.margin_schemas import NewsArticle
from src.utils.logger import log_debug
from config.settings import NEWS_API_KEY
from src.research_tools.vector_store import VectorStore

class NewsService:
    def __init__(self):
        self.api_key = NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2"
        self.session = None
        self.vector_store = VectorStore()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_relevant_articles(self, query: str, days_back: int = 30) -> List[NewsArticle]:
        """Get relevant news articles from both API and vector store"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Get new articles from API
            api_articles = await self._fetch_from_api(query, days_back)
            # Store new articles in vector store
            if len(api_articles) > 0:
                await self.vector_store.insert_articles(api_articles, query)
            
            # Search for similar articles in vector store
            stored_articles = await self.vector_store.search_similar_articles(query)
            
            # Combine and deduplicate articles
            all_articles = api_articles + stored_articles
            # Debug print all articles
            unique_articles = self._deduplicate_articles(all_articles)
            
            # Sort by relevance score and return
            unique_articles.sort(key=lambda x: x.relevance_score, reverse=True)
            return unique_articles

        except Exception as e:
            log_debug(f"Error fetching all news articles: {str(e)}")
            return []

    async def _fetch_from_api(self, query: str, days_back: int) -> List[NewsArticle]:
        """Fetch articles from NewsAPI"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Clean and parse the query
            terms = query.replace('"', '').split()  # Remove any existing quotes
            
            # # Handle multi-word phrases
            phrases = []
            current_phrase = []
            
            for term in terms:
                if term.lower() in ['and', 'or', 'not']:
                    if current_phrase:
                        phrases.append(' '.join(current_phrase))
                        current_phrase = []
                    continue
                current_phrase.append(term)
            
            if current_phrase:
                phrases.append(' '.join(current_phrase))
            
            # Build the optimized query
            if len(phrases) == 1:
                # Single phrase query
                cleaned_query = f'"{phrases[0]}"'
            else:
                # Multi-phrase query
                main_phrase = f'"{phrases[0]}"'  # Quote the main phrase
                other_phrases = []
                
                # Group remaining phrases
                for i in range(1, len(phrases), 2):
                    if i + 1 < len(phrases):
                        other_phrases.append(f'("{phrases[i]}" OR "{phrases[i+1]}")')
                    else:
                        other_phrases.append(f'"{phrases[i]}"')
                
                cleaned_query = f"{main_phrase}"
                if other_phrases:
                    cleaned_query += f" AND {' AND '.join(other_phrases)}"
            
            log_debug(f"Original query: {query}")
            log_debug(f"Optimized query: {cleaned_query}")
            
            cleaned_query = query

            # Calculate date range
            from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            to_date = datetime.now().strftime('%Y-%m-%d')
            
            # Construct parameters
            params = {
                'q': cleaned_query,
                'from': from_date,
                'to': to_date,
                'sortBy': 'relevancy',
                'language': 'en',
                'apiKey': self.api_key,
                'pageSize': 25,
                'searchIn': 'title,description,content'
            }
            
            #TODO Add headlines to query
            #TODO fix the nested retry logic, improve query

            # Try everything endpoint
            async with self.session.get(f"{self.base_url}/everything", params=params) as response:
                log_debug(f"NewsAPI response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    log_debug(f"API Response: {data}")
                    
                    if data.get('totalResults', 0) == 0:
                        # Try with just the main phrase
                        simple_query = f'"{phrases[0]}"'
                        log_debug(f"Trying simpler query: {simple_query}")
                        params['q'] = simple_query
                        
                        async with self.session.get(f"{self.base_url}/everything", params=params) as simple_response:
                            if simple_response.status == 200:
                                data = await simple_response.json()
                                log_debug(f"Simple query response: {data}")
                                
                                # If still no results, try without quotes
                                if data.get('totalResults', 0) == 0:
                                    final_query = phrases[0]
                                    log_debug(f"Trying final query without quotes: {final_query}")
                                    params['q'] = final_query
                                    
                                    async with self.session.get(f"{self.base_url}/everything", params=params) as final_response:
                                        if final_response.status == 200:
                                            data = await final_response.json()
                                            log_debug(f"Final query response: {data}")
                elif (response.status == 429):
                    log_debug(f"Error fetching from news api: {response.status} - RATE LIMIT EXCEEDED")
                    return []
                else:
                    log_debug(f"Unknown error fetching from news api: {response.status}")
                    return []
            
                articles = []
                for article in data.get('articles', []):
                    try:
                        if not article.get('title') or not article.get('url'):
                            continue

                        # Calculate relevance score based on phrase matches
                        title_text = article['title'].lower()
                        desc_text = article.get('description', '').lower()
                        
                        # Score based on phrase matches
                        score = 0
                        for phrase in phrases:
                            phrase_lower = phrase.lower()
                            if phrase_lower in title_text:
                                score += 2  # Higher weight for title matches
                            if phrase_lower in desc_text:
                                score += 1
                        
                        # Normalize score
                        relevance_score = min(score / (len(phrases) * 3), 1.0)
                        relevance_score = max(relevance_score, 0.5)  # Minimum score of 0.5

                        articles.append(NewsArticle(
                            title=article['title'],
                            description=article.get('description', ''),
                            url=article['url'],
                            source_name=article['source'].get('name', 'Unknown Source'),
                            published_at=datetime.fromisoformat(
                                article['publishedAt'].replace('Z', '+00:00')
                            ),
                            relevance_score=relevance_score
                        ))
                        
                        log_debug(f"Article successfully parsed: {article['title']}")
                    except Exception as e:
                        log_debug(f"Error parsing article: {str(e)}")
                        continue
                
                # Sort by relevance score and return top results
                articles.sort(key=lambda x: x.relevance_score, reverse=True)
                log_debug(f"Returning {len(articles)} processed articles")
                return articles
                
        except Exception as e:
            log_debug(f"Error processing fetched news api articles: {str(e)}")
            return []

    def _deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
                
        return unique_articles