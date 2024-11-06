from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Pydantic Models for Validation
class NewsArticle(BaseModel):
    """Pydantic model for news articles"""
    title: str
    description: Optional[str]
    url: str
    source_name: str
    published_at: datetime
    relevance_score: float = Field(..., ge=0, le=1)

class ResearchContext(BaseModel):
    """Pydantic model for research context"""
    articles: List[NewsArticle] = Field(default_factory=list)
    summary: str
    key_points: List[str]
    market_sentiment: float = Field(..., ge=-1, le=1)  # -1 very negative, +1 very positive

class AIAnalysisResponse(BaseModel):
    """Pydantic model for AI response structure"""
    estimated_probability: float = Field(..., ge=0, le=1)
    confidence_score: float = Field(..., ge=0, le=1)
    reasoning: str
    sources: List[str]
    recommendation: str
    research_context: ResearchContext

    @validator('recommendation')
    def validate_recommendation(cls, v):
        valid_recommendations = {'BID YES', 'BID NO', 'DISREGARD'}
        if v.upper() not in valid_recommendations:
            raise ValueError(f'Recommendation must be one of {valid_recommendations}')
        return v.upper()

# Dataclass for Analysis Results
@dataclass
class MarginAnalysis:
    market_ticker: str
    current_yes_ask: float
    estimated_probability: float
    confidence_score: float
    reasoning: str
    sources: List[str]
    recommendation: str
    research_context: ResearchContext

# OpenAI Function Schemas
MARKET_ANALYSIS_SCHEMA = {
    "name": "analyze_prediction_market",
    "description": "Analyze a prediction market and provide structured output",
    "parameters": {
        "type": "object",
        "properties": {
            "estimated_probability": {
                "type": "number",
                "description": "Estimated probability of the event occurring (0-1)",
                "minimum": 0,
                "maximum": 1
            },
            "confidence_score": {
                "type": "number",
                "description": "Confidence in the analysis (0-1)",
                "minimum": 0,
                "maximum": 1
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed explanation of the analysis incorporating news and research"
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of sources used in analysis"
            },
            "recommendation": {
                "type": "string",
                "enum": ["BID YES", "BID NO", "DISREGARD"],
                "description": "Trading recommendation based on analysis"
            },
            "research_context": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Summary of relevant news and research"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points from the research"
                    },
                    "market_sentiment": {
                        "type": "number",
                        "description": "Overall market sentiment from -1 (very negative) to +1 (very positive)",
                        "minimum": -1,
                        "maximum": 1
                    }
                },
                "required": ["summary", "key_points", "market_sentiment"]
            }
        },
        "required": ["estimated_probability", "confidence_score", "reasoning", 
                    "sources", "recommendation", "research_context"]
    }
}

# Prompts
SYSTEM_PROMPT = """You are an expert financial and social analyst specializing in prediction markets.
You analyze markets by combining market data with latest news and research.
Provide detailed analysis with clear reasoning, citing specific news sources and data points.
Be objective and focus on how new information affects the probability of the event occurring."""

def generate_market_analysis_prompt(market_data: Dict[str, Any], news_articles: List[NewsArticle]) -> str:
    """Generate the analysis prompt including news context"""
    news_context = "\n\n".join([
        f"Source: {article.source_name}\n"
        f"Title: {article.title}\n"
        f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Description: {article.description or 'No description available'}\n"
        f"URL: {article.url}"
        for article in news_articles
    ])
    
    return f"""
    Analyze this prediction market using the provided market data and latest news:
    
    MARKET INFORMATION:
    Title: {market_data.get('title', 'Unknown Title')}
    Current YES Ask Price: ${market_data.get('yes_ask', 0)/100:.2f}
    Rules: {market_data.get('rules_primary', 'No rules available')}
    
    LATEST NEWS AND RESEARCH:
    {news_context}
    
    Based on this information, provide:
    1. Estimated probability (0-1)
    2. Confidence score (0-1)
    3. Detailed reasoning incorporating the news and research
    4. Key points from the research
    5. Overall market sentiment (-1 to +1)
    6. Trading recommendation (BID YES/BID NO/DISREGARD)
    """

# Research Models (if you add web research later)
class ResearchSource(BaseModel):
    """Pydantic model for research sources"""
    url: str
    title: str
    relevance_score: float = Field(..., ge=0, le=1)
    timestamp: datetime
    summary: str 