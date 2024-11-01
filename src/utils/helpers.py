import pandas as pd
from datetime import datetime

def convert_probability_to_odds(probability: float) -> float:
    """Convert probability to decimal odds"""
    return 1 / probability if probability > 0 else float('inf')

def convert_odds_to_probability(odds: float) -> float:
    """Convert decimal odds to probability"""
    return 1 / odds if odds > 0 else 0

def calculate_edge(market_prob: float, model_prob: float) -> float:
    """Calculate the edge between market probability and model probability"""
    return (model_prob - market_prob) * 100  # Return as percentage 