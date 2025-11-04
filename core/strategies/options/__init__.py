"""
Options trading strategies module.

Provides advanced options strategies including:
- Iron Condor (neutral strategy)
- Bull Call Spread (bullish strategy)
- Bear Put Spread (bearish strategy)

With full Greeks calculation and P&L modeling.
"""

from .base import (
    Greeks,
    OptionLeg,
    OptionsPosition,
    OptionsStrategy,
)
from .greeks import (
    calculate_black_scholes_greeks,
    calculate_position_greeks,
)
from .iron_condor import IronCondorStrategy
from .pnl_modeling import model_pnl_scenarios
from .vertical_spreads import BearPutSpread, BullCallSpread

__all__ = [
    "OptionLeg",
    "OptionsPosition",
    "Greeks",
    "OptionsStrategy",
    "IronCondorStrategy",
    "BullCallSpread",
    "BearPutSpread",
    "calculate_black_scholes_greeks",
    "calculate_position_greeks",
    "model_pnl_scenarios",
]
