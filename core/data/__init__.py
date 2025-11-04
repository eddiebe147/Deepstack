"""
Data management module for DeepStack Trading System

Handles market data, price feeds, historical data, and data persistence.
"""

from .data_storage import DataStorage
from .market_data import MarketDataManager
from .price_feed import PriceFeed

__all__ = ["MarketDataManager", "PriceFeed", "DataStorage"]
