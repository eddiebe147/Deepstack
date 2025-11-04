"""
Pytest fixtures and configuration for DeepStack tests.

Provides reusable fixtures for testing strategy agents, risk management,
and other core components.
"""

import asyncio

# Add parent directory to path for imports
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config, RiskLimits, StrategiesConfig, StrategyConfig


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock(spec=Config)

    # Risk limits
    config.risk_limits = RiskLimits(
        max_position_pct=0.05,
        max_portfolio_heat=0.15,
        daily_stop=0.02,
        weekly_stop=0.05,
        max_drawdown=0.15,
        kelly_settings={
            "max_kelly_fraction": 0.30,
            "default_fraction": 0.25,
            "min_fraction": 0.10,
        },
        stop_loss={
            "never_move_down": True,
            "thesis_break_exit": True,
            "trailing_stops": True,
            "max_stop_pct": 0.25,
        },
    )

    # Strategy configurations
    config.strategies = StrategiesConfig(
        deep_value=StrategyConfig(
            enabled=True,
            allocation=0.40,
            criteria={
                "p_b_max": 1.0,
                "p_e_max": 10,
                "ev_ebitda_max": 7,
                "fcf_yield_min": 0.07,
                "debt_equity_max": 1.0,
                "current_ratio_min": 1.5,
                "roe_min": 0.15,
            },
        ),
        squeeze_hunter=StrategyConfig(
            enabled=True,
            allocation=0.30,
            criteria={
                "short_interest_min": 0.20,
                "days_to_cover_min": 3,
                "borrow_cost_min": 0.05,
            },
        ),
    )

    return config


@pytest.fixture
def sample_fundamentals():
    """Sample fundamental data for testing."""
    return {
        "symbol": "TEST",
        "pe_ratio": 12.5,
        "pb_ratio": 0.8,
        "roe": 0.18,
        "debt_equity": 0.3,
        "current_ratio": 1.5,
        "fcf_yield": 0.08,
        "dividend_yield": 0.02,
    }


@pytest.fixture
def sample_fundamentals_high_value():
    """Sample fundamental data representing a high-value stock."""
    return {
        "symbol": "VALUE",
        "pe_ratio": 8.0,
        "pb_ratio": 0.6,
        "roe": 0.22,
        "debt_equity": 0.2,
        "current_ratio": 2.0,
        "fcf_yield": 0.10,
        "dividend_yield": 0.03,
    }


@pytest.fixture
def sample_fundamentals_low_value():
    """Sample fundamental data representing a low-value stock."""
    return {
        "symbol": "OVERVALUED",
        "pe_ratio": 35.0,
        "pb_ratio": 3.5,
        "roe": 0.08,
        "debt_equity": 1.5,
        "current_ratio": 0.8,
        "fcf_yield": 0.02,
        "dividend_yield": 0.0,
    }


@pytest.fixture
def sample_squeeze_data():
    """Sample squeeze data for testing."""
    return {
        "symbol": "TEST",
        "short_interest_pct": 0.30,
        "days_to_cover": 7.0,
        "cost_to_borrow": 0.10,
        "float_available_pct": 0.15,
    }


@pytest.fixture
def sample_squeeze_data_high():
    """Sample squeeze data representing high squeeze potential."""
    return {
        "symbol": "SQUEEZE",
        "short_interest_pct": 0.50,
        "days_to_cover": 9.0,
        "cost_to_borrow": 0.18,
        "float_available_pct": 0.10,
    }


@pytest.fixture
def sample_squeeze_data_low():
    """Sample squeeze data representing low squeeze potential."""
    return {
        "symbol": "NOSQUEEZE",
        "short_interest_pct": 0.05,
        "days_to_cover": 1.5,
        "cost_to_borrow": 0.01,
        "float_available_pct": 0.40,
    }


@pytest.fixture
def sample_quote_data():
    """Sample quote data for testing."""
    return {
        "symbol": "TEST",
        "price": 150.0,
        "volume": 1000000,
        "market_cap": 50000000000,
        "sector": "Technology",
    }


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_portfolio_value():
    """Mock portfolio value for risk testing."""
    return 100000.0


@pytest.fixture
def mock_broker():
    """Mock broker for testing."""
    broker = AsyncMock()
    broker.get_account_summary.return_value = {
        "TotalCashValue": 50000.0,
        "NetLiquidation": 100000.0,
        "GrossPositionValue": 50000.0,
    }
    broker.get_positions.return_value = []
    broker.submit_order.return_value = {"orderId": "12345", "status": "Submitted"}
    return broker
