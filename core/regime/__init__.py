"""
Market Regime Detection Module

Provides multi-factor market regime detection and allocation adjustment.
"""

from core.regime.regime_allocator import (
    AllocationConfig,
    RegimeBasedAllocator,
)
from core.regime.regime_detector import (
    MarketRegime,
    RegimeDetection,
    RegimeDetector,
    RegimeFactors,
)
from core.regime.regime_transition import (
    RegimeTransition,
    RegimeTransitionManager,
)

__all__ = [
    "MarketRegime",
    "RegimeFactors",
    "RegimeDetection",
    "RegimeDetector",
    "AllocationConfig",
    "RegimeBasedAllocator",
    "RegimeTransition",
    "RegimeTransitionManager",
]
