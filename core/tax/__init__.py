"""
Tax optimization module for DeepStack trading system.

Provides tax-aware trading features including:
- Wash sale tracking and prevention
- Tax loss harvesting (3-5% annual alpha)
- Capital gains optimization
"""

from .tax_loss_harvester import (
    HarvestOpportunity,
    HarvestPlan,
    HarvestResult,
    TaxLossHarvester,
    YearEndPlan,
)
from .wash_sale_tracker import (
    LossSale,
    WashSaleTracker,
    WashSaleViolation,
)

__all__ = [
    # Wash Sale Tracking
    "WashSaleTracker",
    "LossSale",
    "WashSaleViolation",
    # Tax-Loss Harvesting
    "TaxLossHarvester",
    "HarvestOpportunity",
    "HarvestPlan",
    "HarvestResult",
    "YearEndPlan",
]
