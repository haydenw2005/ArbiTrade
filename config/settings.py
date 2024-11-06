from dotenv import load_dotenv
import os

load_dotenv()

# API Configuration
KALSHI_API_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY")
PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kalshi-key-1.key")

# Research Tools Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MAX_CONCURRENT_ANALYSES = int(os.getenv("MAX_CONCURRENT_ANALYSES", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))