from typing import List, Dict, Any
import openai
import asyncio
import json
from src.data_collectors.kalshi_scraper import KalshiScraper
from src.utils.logger import log_debug
from config.settings import OPENAI_API_KEY, MAX_CONCURRENT_ANALYSES, CONFIDENCE_THRESHOLD
from src.research_tools.margin_schemas import (
    AIAnalysisResponse,
    MarginAnalysis,
    MARKET_ANALYSIS_SCHEMA,
    SYSTEM_PROMPT,
    generate_market_analysis_prompt,
    NewsArticle,
    ResearchContext
)
from src.research_tools.news_service import NewsService

class MarginExaminer:
    def __init__(self):        
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in environment variables")
        log_debug(f"Initializing MarginExaminer with API key: {OPENAI_API_KEY[:8]}...")
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.kalshi_scraper = KalshiScraper()
        self.news_service = NewsService()
        self.max_concurrent = MAX_CONCURRENT_ANALYSES
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        
    async def analyze_market(self, market_data: Dict[str, Any]) -> MarginAnalysis:
        """Analyze a single market using AI and web research."""
        
        log_debug(f"Starting market analysis for {market_data.get('ticker', 'unknown market')}")
        
        try:
            # Create a coroutine for the OpenAI query construction
            async def construct_search_query():
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert at constructing search queries for news articles. "
                                    "Your task is to generate three broad keywords that will yield relevant articles. "
                                    "Avoid exact phrases or highly specific terms. Each keyword should be distinct and broad, "
                                    "forming a flexible search query string."
                                )
                            },
                            {
                                "role": "user",
                                "content": f"""
                                Create a search query for news articles about the topic. Do not make it specific to the market, but to current climate and events:
                                
                                Title: {market_data.get('title', '')}
                                Category: {market_data.get('category', '')}
                                Rules: {market_data.get('rules_primary', '')}
                                """
                            }
                        ],
                        functions=[
                            {
                                "name": "construct_search_query",
                                "description": "Construct an optimal search query for news articles",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "search_query": {
                                            "type": "string",
                                            "description": "A flexible search query string with three broad keywords"
                                        },
                                    },
                                    "required": ["search_query", "reasoning"]
                                }
                            }
                        ],
                        function_call={"name": "construct_search_query"}
                    )
                )
            # Create a coroutine for the news analysis
            async def analyze_news(articles: List[NewsArticle]):
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Analyze these news articles for relevance to the prediction market."},
                            {"role": "user", "content": f"Market: {market_data.get('title')}\nArticles:\n" + 
                             ("\n".join([f"- {a.title} ({a.source_name}): {a.description}" for a in articles]) 
                              if articles else "No relevant articles found.")}
                        ],
                        functions=[{
                            "name": "analyze_news",
                            "description": "Analyze news articles and provide research context",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "summary": {
                                        "type": "string",
                                        "description": "Summary of relevant news findings"
                                    },
                                    "key_points": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Key points from the research"
                                    },
                                    "market_sentiment": {
                                        "type": "number",
                                        "description": "Overall market sentiment (-1 to +1)",
                                        "minimum": -1,
                                        "maximum": 1
                                    }
                                },
                                "required": ["summary", "key_points", "market_sentiment"]
                            }
                        }],
                        function_call={"name": "analyze_news"}
                    )
                )

            # Create a coroutine for the final market analysis
            async def analyze_market_with_research(research_context: ResearchContext):
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": generate_market_analysis_prompt(market_data, research_context.articles)},
                            {"role": "assistant", "content": f"Research Summary:\n{research_context.summary}\n\n" +
                             f"Key Points:\n" + "\n".join([f"- {p}" for p in research_context.key_points])}
                        ],
                        functions=[MARKET_ANALYSIS_SCHEMA],
                        function_call={"name": "analyze_prediction_market"}
                    )
                )

            # Execute the pipeline
            query_response = await construct_search_query()
            query_data = json.loads(query_response.choices[0].message.function_call.arguments)
            search_query = query_data['search_query']
            log_debug(f"Generated search query: {search_query}")
            
            news_articles = await self.news_service.get_relevant_articles(search_query)
            log_debug(f"Found {len(news_articles)} relevant news articles")
            
            news_analysis_response = await analyze_news(news_articles)
            news_analysis = json.loads(news_analysis_response.choices[0].message.function_call.arguments)
            
            research_context = ResearchContext(
                articles=news_articles,
                summary=news_analysis['summary'],
                key_points=news_analysis['key_points'],
                market_sentiment=news_analysis['market_sentiment']
            )
            
            market_analysis_response = await analyze_market_with_research(research_context)
            analysis_dict = json.loads(market_analysis_response.choices[0].message.function_call.arguments)
            
            complete_analysis = {
                **analysis_dict,
                "research_context": {
                    "articles": [article.dict() for article in news_articles],
                    "summary": research_context.summary,
                    "key_points": research_context.key_points,
                    "market_sentiment": research_context.market_sentiment
                }
            }
            
            validated_response = AIAnalysisResponse(**complete_analysis)
            
            result = MarginAnalysis(
                market_ticker=market_data.get('ticker', 'unknown'),
                current_yes_ask=market_data.get('yes_ask', 0)/100,
                estimated_probability=validated_response.estimated_probability,
                confidence_score=validated_response.confidence_score,
                reasoning=validated_response.reasoning,
                sources=validated_response.sources,
                recommendation=validated_response.recommendation,
                research_context=validated_response.research_context
            )
            
            log_debug(f"Analysis complete for market {market_data.get('ticker')}")
            return result
            
        except Exception as e:
            log_debug(f"Error in analyze_market: {str(e)}")
            log_debug(f"Error type: {type(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def examine_events(self, event_tickers: List[str]) -> Dict[str, List[MarginAnalysis]]:
        """Examine multiple events and their markets."""
        results = {}
        
        log_debug(f"Starting examination of events: {event_tickers}")
        
        # Create semaphore to limit concurrent analyses
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def analyze_event(ticker):
            async with semaphore:
                log_debug(f"Fetching event details for {ticker}")
                event_response = self.kalshi_scraper.get_event_details(ticker)
                
                # Debug the response structure
                log_debug(f"Event response structure: {event_response.keys() if event_response else 'None'}")
                
                # Check if we have a valid response with an 'event' key
                if not event_response or 'event' not in event_response:
                    log_debug(f"No valid event data found for {ticker}")
                    return ticker, []
                
                # Extract the event data
                event_data = event_response['event']
                
                # Check if markets exist in the event data
                if 'markets' not in event_data:
                    log_debug(f"No markets found in event data for {ticker}")
                    return ticker, []
                
                log_debug(f"Found {len(event_data['markets'])} markets for event {ticker}")
                
                # Create tasks for parallel market analysis
                market_tasks = []
                for market in event_data['markets']:
                    market_tasks.append(self.analyze_market(market))
                
                # Execute all market analyses in parallel
                try:
                    market_analyses = await asyncio.gather(*market_tasks, return_exceptions=True)
                    # Filter out exceptions and log errors
                    market_analyses = [
                        analysis for analysis in market_analyses 
                        if not isinstance(analysis, Exception)
                    ]
                    
                    # Log any failed analyses
                    failed_count = len(market_tasks) - len(market_analyses)
                    if failed_count > 0:
                        log_debug(f"Failed to analyze {failed_count} markets for event {ticker}")
                    
                    log_debug(f"Successfully analyzed {len(market_analyses)} markets for event {ticker}")
                except Exception as e:
                    log_debug(f"Error during parallel market analysis for event {ticker}: {str(e)}")
                    market_analyses = []
                
                log_debug(f"Completed analysis for event {ticker}")
                return ticker, market_analyses
        
        # Create tasks for all events
        tasks = [analyze_event(ticker) for ticker in event_tickers]
        
        # Wait for all tasks to complete
        try:
            analyses = await asyncio.gather(*tasks)
            log_debug(f"All analyses completed successfully")
        except Exception as e:
            log_debug(f"Error during analyses: {str(e)}")
            raise
        
        # Convert results to dictionary
        for ticker, market_analyses in analyses:
            results[ticker] = market_analyses
            
        return results