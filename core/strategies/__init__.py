"""
Trading Strategies Module

Available strategies:
- SqueezeHunterStrategy: Short squeeze detection and trading
- PairsTradingStrategy: Statistical arbitrage through cointegrated pairs
"""

from core.strategies.pairs_trading import (
    CointegrationTest,
    PairSignal,
    PairStatus,
    PairsTradingStrategy,
    SpreadStatistics,
    TradingPair,
)
from core.strategies.squeeze_hunter import (
    Catalyst,
    ShortInterestData,
    SqueezeHunterStrategy,
    SqueezeOpportunity,
)

__all__ = [
    # Squeeze Hunter
    "SqueezeHunterStrategy",
    "SqueezeOpportunity",
    "ShortInterestData",
    "Catalyst",
    # Pairs Trading
    "PairsTradingStrategy",
    "TradingPair",
    "PairSignal",
    "PairStatus",
    "CointegrationTest",
    "SpreadStatistics",
]
