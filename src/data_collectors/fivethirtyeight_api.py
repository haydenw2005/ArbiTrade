import requests
import pandas as pd
from config.settings import FIVETHIRTYEIGHT_API_BASE_URL

class FiveThirtyEightAPI:
    def __init__(self):
        self.base_url = FIVETHIRTYEIGHT_API_BASE_URL
    
    def get_election_forecasts(self):
        """
        Fetch election forecasts from FiveThirtyEight
        """
        try:
            # Note: You'll need to adjust this endpoint based on FiveThirtyEight's actual API structure
            response = requests.get(f"{self.base_url}/elections/forecasts")
            response.raise_for_status()
            
            forecast_data = response.json()
            return pd.DataFrame(forecast_data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching FiveThirtyEight forecasts: {e}")
            return pd.DataFrame() 