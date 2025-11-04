"""
Tax optimization module for DeepStack trading system.

Provides tax-aware trading features including:
- Wash sale tracking and prevention
- Tax loss harvesting
- Capital gains optimization
"""

from .wash_sale_tracker import (
    LossSale,
    WashSaleTracker,
    WashSaleViolation,
)

__all__ = [
    "WashSaleTracker",
    "LossSale",
    "WashSaleViolation",
]
