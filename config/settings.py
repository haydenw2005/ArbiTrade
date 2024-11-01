from dotenv import load_dotenv
import os

load_dotenv()

# API Configuration
KALSHI_API_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"  # Base URL without /trade-api/v2
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY")
PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kalshi-key-1.key")