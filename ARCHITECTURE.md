# ArbiTrade Architecture

## Project Info (DO NOT EDIT!)

** Arbitrade is personal project, intended for personal use. It is a terminal that allows for the analysis and research of prediction markets through Kalshi. It is intended for personal use, and will not be released for others. This means that the emphasis is on functionality, not user experience. I am using streamlit, because it allows for quick development of data driven applications. **

## Project Overview:

ArbiTrade is a prediction market analysis platform that combines real-time market data from Kalshi with news analysis and AI-powered research to identify trading opportunities. The system features a Streamlit-based dashboard for visualization and interaction.

## Key Components:

1. Data Collection

   - KalshiScraper: Interfaces with Kalshi API to fetch market and event data
   - NewsService: Retrieves relevant news articles using NewsAPI
   - Authentication: RSA-based signing for secure API interactions

2. Analysis Tools

   - MarginExaminer: Core analysis engine using OpenAI GPT-4 for market analysis
   - ArbitrageCalculator: Identifies arbitrage opportunities (in development)
   - Research Context: AI-powered analysis of news and market sentiment

3. Visualization

   - Market Dashboard: Streamlit-based UI with multiple tabs
   - Events Tab: Main interface for viewing and analyzing events
   - Markets Tab: Dedicated market analysis view
   - Logs Tab: Debug and system logging display
   - Research Sidebar: Contextual market research panel

4. Research Tools
   - News Analysis: AI-powered news relevance scoring
   - Market Analysis: Probability estimation and confidence scoring
   - Sentiment Analysis: Market sentiment evaluation
   - OpenAI Integration: GPT-4 powered market analysis

## Data Flow:

1. Market Data Pipeline

   - Kalshi API → KalshiScraper → Dashboard Display
   - User Selection → MarginExaminer → Analysis Results
   - Authentication Flow: API Key + Private Key → RSA Signing → Authenticated Requests

2. Research Pipeline

   - User Query → NewsService → News Articles
   - Articles → AI Analysis → Research Context
   - Research Context + Market Data → Final Analysis
   - GPT-4 → Probability Estimates + Confidence Scores

3. Visualization Pipeline
   - Event Selection → Grid Display → Research Panel
   - Analysis Results → Summary Grid → Detailed Views
   - Debug Logs → Real-time Updates → Log Display

## Dependencies:

1. Core Dependencies

   - Python 3.12+
   - Streamlit: Web interface
   - OpenAI: GPT-4 API for analysis
   - Pandas: Data manipulation
   - Cryptography: API authentication
   - Pydantic: Data validation
   - aiohttp: Async HTTP requests

2. External APIs
   - Kalshi API: Market data
   - NewsAPI: News aggregation
   - OpenAI API: Analysis and research

## Design Patterns:

1. Service Pattern

   - NewsService: News article retrieval and processing
   - KalshiClient: Market data access
   - MarginExaminer: Analysis orchestration

2. Repository Pattern

   - KalshiScraper: Data collection abstraction
   - Centralized data access patterns

3. Factory Pattern

   - Analysis components creation
   - Standardized result generation

4. Observer Pattern

   - Real-time dashboard updates
   - Event-driven architecture
   - Session state management

5. Validation Pattern
   - Pydantic models for data validation
   - Structured API responses
   - Type hints throughout codebase

## Key Interactions:

1. User Interactions

   - Event selection and filtering
   - Analysis initiation
   - Research panel toggling
   - Log viewing and clearing
   - Market data pagination
   - Category filtering

2. System Interactions
   - Asynchronous API calls
   - Concurrent analysis processing
   - Real-time data updates
   - Authentication handling
   - Session state management
   - Debug logging
