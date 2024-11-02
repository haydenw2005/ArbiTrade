import os
import sys
import pandas as pd
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import KALSHI_API_BASE_URL, KALSHI_API_KEY, PRIVATE_KEY_PATH
from src.utils.kalshi_client import KalshiClient
from src.utils.logger import log_debug

class KalshiScraper:
    def __init__(self):
        # Initialize client with private key path
        self.client = KalshiClient(
            host=KALSHI_API_BASE_URL,
            key_id=KALSHI_API_KEY,
            private_key=PRIVATE_KEY_PATH
        )
    
    def get_events(self, 
                  limit: int = 100, 
                  status: str = "open", 
                  series_ticker: str = None,
                  with_nested_markets: bool = True,
                  cursor: str = None) -> pd.DataFrame:
        """Fetch events from Kalshi API"""
        try:
            events_data = self.client.get_events(
                limit=limit,
                status=status,
                series_ticker=series_ticker,
                with_nested_markets=with_nested_markets,
                cursor=cursor
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(events_data.get('events', []))
            if df.empty:
                log_debug("No events data received")
                return df
            
            # Store cursor in DataFrame attributes if available
            if 'cursor' in events_data:
                df.attrs['cursor'] = events_data['cursor']
            
            # Process markets data if available
            if 'markets' in df.columns:
                #Extract market data
                df['yes_bid'] = df['markets'].apply(
                    lambda x: x[0].get('yes_bid', None) if x and len(x) > 0 else None
                )
                df['no_bid'] = df['markets'].apply(
                    lambda x: x[0].get('no_bid', None) if x and len(x) > 0 else None
                )
                df['last_price'] = df['markets'].apply(
                    lambda x: x[0].get('last_price', None) if x and len(x) > 0 else None
                )
                
                # Add volume and liquidity metrics
                df['volume'] = df['markets'].apply(
                    lambda x: sum(m.get('volume', 0) for m in x) if x else 0
                )
                df['market_value'] = df['volume'] * 1  # Assuming $1 per contract
                df['liquidity'] = df['markets'].apply(
                    lambda x: sum(
                        (m.get('yes_bid', 0) * m.get('volume', 0) + 
                         m.get('no_bid', 0) * m.get('volume', 0)) 
                        for m in x if x
                    )
                )
                
                # Store numeric values for sorting
                df['volume_sort'] = df['volume']
                df['market_value_sort'] = df['market_value']
                df['liquidity_sort'] = df['liquidity']
                df['implied_prob_sort'] = df['last_price'].apply(
                    lambda x: float(x) if pd.notnull(x) else 0.0
                )
                
                # Format display values, dont *100, alreayd formmated
                df['implied_prob'] = df['last_price'].apply(
                    lambda x: f"{x:.1f}%" if pd.notnull(x) else None
                )
                df['betting_line'] = df.apply(
                    lambda row: f"Yes: ${row['yes_bid']:.2f} / No: ${row['no_bid']:.2f}" 
                    if pd.notnull(row['yes_bid']) and pd.notnull(row['no_bid']) 
                    else None,
                    axis=1
                )
                df['market_value'] = df['market_value'].apply(
                    lambda x: f"${x:,.0f}" if pd.notnull(x) else None
                )
                df['liquidity'] = df['liquidity'].apply(
                    lambda x: f"${x:,.0f}" if pd.notnull(x) else None
                )
                df['volume'] = df['volume'].apply(
                    lambda x: f"{x:,.0f}" if pd.notnull(x) else None
                )
            
            # Select final columns
            columns = [
                'event_ticker', 'title', 'category', 
                #'betting_line', 'implied_prob',
                'market_value', 'volume', 'liquidity',
                #'yes_bid', 'no_bid', 'last_price'
            ]
            columns = [col for col in columns if col in df.columns]
            
            return df[columns].copy()
            
        except Exception as e:
            log_debug(f"Error fetching Kalshi events: {e}")
            return pd.DataFrame()
    
    def get_markets(self, limit: int = 100) -> pd.DataFrame:
        """Fetch markets from Kalshi"""
        try:
            markets_data = self.client.get_markets(status="open")
            
            df = pd.DataFrame(markets_data.get('markets', []))
            if df.empty:
                log_debug("No markets data received")
                return df
            
            # Select relevant columns
            columns = [
                'ticker', 'title', 'last_price', 
                'yes_bid', 'yes_ask', 'volume', 'status'
            ]
            available_cols = [col for col in columns if col in df.columns]
            
            filtered_df = df[available_cols].copy()
            
            # Add market metrics
            if 'volume' in filtered_df.columns:
                filtered_df['market_value'] = filtered_df['volume'] * 1  # $1 per contract
                filtered_df['liquidity'] = filtered_df.apply(
                    lambda row: (row.get('yes_bid', 0) + row.get('no_bid', 0)) * row['volume']
                    if pd.notnull(row.get('volume')) else None,
                    axis=1
                )
                
                # Format monetary values
                filtered_df['market_value'] = filtered_df['market_value'].apply(
                    lambda x: f"${x:,.0f}" if pd.notnull(x) else None
                )
                filtered_df['liquidity'] = filtered_df['liquidity'].apply(
                    lambda x: f"${x:,.0f}" if pd.notnull(x) else None
                )
                filtered_df['volume'] = filtered_df['volume'].apply(
                    lambda x: f"{x:,.0f}" if pd.notnull(x) else None
                )
            
            # Add betting information
            if 'last_price' in filtered_df.columns:
                filtered_df['implied_prob'] = filtered_df['last_price'].apply(
                    lambda x: f"{x*100:.1f}%" if pd.notnull(x) else None
                )
            
            if 'yes_bid' in filtered_df.columns and 'yes_ask' in filtered_df.columns:
                filtered_df['betting_line'] = filtered_df.apply(
                    lambda row: f"Bid: ${row['yes_bid']:.2f} / Ask: ${row['yes_ask']:.2f}"
                    if pd.notnull(row['yes_bid']) and pd.notnull(row['yes_ask'])
                    else None,
                    axis=1
                )
            
            # Limit rows if needed
            if len(filtered_df) > limit:
                filtered_df = filtered_df.head(limit)
                
            return filtered_df
            
        except Exception as e:
            log_debug(f"Error fetching Kalshi markets: {e}")
            return pd.DataFrame()
    
    def get_event_details(self, event_ticker: str) -> dict:
        """
        Fetch detailed information about a specific event by its ticker.
        
        Args:
            event_ticker (str): The ticker symbol of the event
            
        Returns:
            dict: Detailed event information including markets and other metadata
        """
        try:
            log_debug(f"Fetching details for event: {event_ticker}")
            response = self.client.get_event(event_ticker)
            
            if not response:
                log_debug(f"No data received for event: {event_ticker}")
                return {}
                
            log_debug(f"Successfully retrieved details for event: {event_ticker}")
            return response
            
        except Exception as e:
            log_debug(f"Error fetching event details for {event_ticker}: {e}")
            return {}
        
        
        
        