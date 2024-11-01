import requests
import json
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from src.utils.auth import get_auth_headers
from src.utils.logger import log_debug

class KalshiClient:
    def __init__(self, host: str, key_id: str, private_key: rsa.RSAPrivateKey):
        self.elections_host = "https://api.elections.kalshi.com"
        self.trading_host = "https://trading-api.kalshi.com"
        self.key_id = key_id
        self.private_key = private_key

    def _make_request(self, method: str, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None, requires_auth: bool = True) -> Dict:
        """Make a request to the Kalshi API"""
        # Ensure path starts with /trade-api/v2
        if not path.startswith('/trade-api/v2'):
            path = f'/trade-api/v2{path}'

        # Choose the correct host
        if 'events' in path:
            base_url = self.elections_host
            requires_auth = False
        else:
            base_url = self.trading_host

        # Build URL with query params
        url = f"{base_url}{path}"
        if params:
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                query_string = '&'.join(f'{key}={value}' for key, value in sorted(params.items()))
                url = f"{url}?{query_string}"


        headers = get_auth_headers(method, path, self.private_key, self.key_id)
        log_debug(f"Debug - URL: {url} - Method: {method} - Path: {path} - Params: {params} - Headers: {headers}")

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            return response.json()
        else:
            log_debug(f"Debug - Failed Response: {response.text}")
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

    def get_markets(self, status: str = "open") -> Dict:
        """Get markets from Kalshi API"""
        params = {
            'limit': 100,
            'status': status,
            'cursor': None,
            'event_ticker': None,
            'series_ticker': None,
            'max_close_ts': None,
            'min_close_ts': None,
            'tickers': None
        }
        return self._make_request('GET', '/markets', params=params, requires_auth=True)

    def get_events(self, 
                  limit: int = 100, 
                  status: str = "open", 
                  series_ticker: str = None,
                  with_nested_markets: bool = True,
                  cursor: str = None) -> Dict:
        """Get events from Kalshi API"""
        params = {
            'limit': limit,
            'status': status,
            'series_ticker': series_ticker,
            'with_nested_markets': with_nested_markets,
            'cursor': cursor
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self._make_request('GET', '/events', params=params, requires_auth=False)

    def get_event(self, event_ticker: str) -> Dict:
        """Get specific event details"""
        return self._make_request('GET', f'/trade-api/v2/events/{event_ticker}')

    def get_market(self, market_ticker: str) -> Dict:
        """Get specific market details"""
        return self._make_request('GET', f'/trade-api/v2/markets/{market_ticker}')

    def get_event_details(self, event_ticker: str, with_nested_markets: bool = True) -> Dict:
        """Get detailed information about a specific event."""
        params = {
            'with_nested_markets': with_nested_markets
        }
        return self._make_request('GET', f'/events/{event_ticker}', params=params, requires_auth=False)