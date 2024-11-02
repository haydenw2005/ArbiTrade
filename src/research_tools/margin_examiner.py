from typing import List, Dict, Any
import openai
from dataclasses import dataclass
import asyncio
from src.data_collectors.kalshi_scraper import KalshiScraper
from src.utils.logger import log_debug
from config.settings import OPENAI_API_KEY, MAX_CONCURRENT_ANALYSES, CONFIDENCE_THRESHOLD

@dataclass
class MarginAnalysis:
    market_ticker: str
    current_yes_ask: float
    estimated_probability: float
    confidence_score: float
    reasoning: str
    sources: List[str]
    recommendation: str

class MarginExaminer:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in environment variables")
        log_debug(f"Initializing MarginExaminer with API key: {OPENAI_API_KEY[:8]}...")
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.kalshi_scraper = KalshiScraper()
        self.max_concurrent = MAX_CONCURRENT_ANALYSES
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        
    async def analyze_market(self, market_data: Dict[str, Any]) -> MarginAnalysis:
        """Analyze a single market using AI and web research."""
        
        log_debug(f"Starting market analysis for {market_data.get('ticker', 'unknown market')}")
        log_debug(f"Market data received: {market_data.keys()}")
        
        try:
            # Construct the prompt for the AI
            prompt = f"""
            Analyze this prediction market:
            Title: {market_data.get('title', 'Unknown Title')}
            Current YES Ask Price: ${market_data.get('yes_ask', 0)/100:.2f}
            Rules: {market_data.get('rules_primary', 'No rules available')}
            
            Please analyze the probability of this event occurring based on available data and research.
            Return your analysis in the following format:
            - Estimated probability: (0-1)
            - Confidence score: (0-1)
            - Reasoning: (detailed explanation)
            - Sources: (list of sources used)
            - Recommendation: (whether the current ask price represents an opportunity)
            """
            
            log_debug("Sending request to OpenAI API...")
            
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a financial analyst specializing in prediction markets."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                log_debug(f"Received response from OpenAI: {response.choices[0].message.content[:100]}...")
                
            except Exception as api_error:
                log_debug(f"OpenAI API Error: {str(api_error)}")
                raise
            
            analysis = self._parse_ai_response(response.choices[0].message.content)
            log_debug(f"Parsed analysis: {analysis}")
            
            result = MarginAnalysis(
                market_ticker=market_data.get('ticker', 'unknown'),
                current_yes_ask=market_data.get('yes_ask', 0)/100,
                estimated_probability=analysis['estimated_probability'],
                confidence_score=analysis['confidence_score'],
                reasoning=analysis['reasoning'],
                sources=analysis['sources'],
                recommendation=analysis['recommendation']
            )
            
            log_debug(f"Analysis complete for market {market_data.get('ticker')}")
            return result
            
        except Exception as e:
            log_debug(f"Error in analyze_market: {str(e)}")
            log_debug(f"Error type: {type(e)}")
            import traceback
            log_debug(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        log_debug(f"Parsing AI response: {response_text[:100]}...")
        
        lines = response_text.split('\n')
        analysis = {
            'estimated_probability': 0.5,
            'confidence_score': 0.8,
            'reasoning': '',
            'sources': [],
            'recommendation': 'HOLD'
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith('- Estimated probability:'):
                try:
                    prob_str = line.split(':')[1].strip().strip('()')
                    analysis['estimated_probability'] = float(prob_str)
                except Exception as e:
                    log_debug(f"Error parsing probability: {str(e)} from line: {line}")
            elif line.startswith('- Confidence score:'):
                try:
                    conf_str = line.split(':')[1].strip().strip('()')
                    analysis['confidence_score'] = float(conf_str)
                except Exception as e:
                    log_debug(f"Error parsing confidence: {str(e)} from line: {line}")
            elif line.startswith('- Reasoning:'):
                current_section = 'reasoning'
            elif line.startswith('- Sources:'):
                current_section = 'sources'
            elif line.startswith('- Recommendation:'):
                analysis['recommendation'] = line.split(':')[1].strip()
            elif current_section == 'reasoning' and line:
                analysis['reasoning'] += line + '\n'
            elif current_section == 'sources' and line.startswith('-'):
                analysis['sources'].append(line.strip('- '))
        
        log_debug(f"Parsed analysis result: {analysis}")
        return analysis
    
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
                    
                market_analyses = []
                for market in event_data['markets']:
                    try:
                        analysis = await self.analyze_market(market)
                        market_analyses.append(analysis)
                        log_debug(f"Successfully analyzed market {market.get('ticker', 'unknown')}")
                    except Exception as e:
                        log_debug(f"Error analyzing market {market.get('ticker', 'unknown')}: {str(e)}")
                        continue  # Skip failed market analyses
                    
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