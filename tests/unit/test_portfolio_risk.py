"""
Unit tests for PortfolioRisk - Risk Management

Tests core risk management functionality including:
- Kelly Criterion position sizing
- Stop loss validation
- Portfolio heat checks
- Risk limit validation
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.risk.portfolio_risk import PortfolioRisk


class TestKellyCriterionSizing:
    """Test Kelly Criterion position sizing calculations."""

    @pytest.mark.asyncio
    async def test_kelly_sizing_positive_edge(self, mock_config):
        """Test Kelly sizing with positive edge (win rate > 50%)."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.calculate_kelly_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_price=92.0,  # 8% risk
            win_rate=0.60,  # 60% win rate
            avg_win=2.0,  # 2:1 win/loss ratio
        )

        # Should recommend a position
        assert result["position_size"] > 0
        assert result["position_pct"] > 0.0
        assert result["position_pct"] <= 0.05  # Max position limit
        assert result["kelly_fraction"] > 0.0

    @pytest.mark.asyncio
    async def test_kelly_sizing_negative_edge(self, mock_config):
        """Test Kelly sizing with negative edge (win rate < 50%)."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.calculate_kelly_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_price=92.0,
            win_rate=0.30,  # 30% win rate (negative edge)
            avg_win=1.5,  # 1.5:1 win/loss ratio
        )

        # Kelly should be 0 or very small with negative edge
        assert result["kelly_fraction"] <= 0.05
        assert result["position_size"] >= 0

    @pytest.mark.asyncio
    async def test_kelly_sizing_respects_max_fraction(self, mock_config):
        """Test that Kelly sizing respects max_kelly_fraction limit."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.calculate_kelly_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_price=90.0,
            win_rate=0.80,  # Very high win rate
            avg_win=3.0,  # 3:1 win/loss ratio
        )

        # Kelly fraction should be capped at max_kelly_fraction (0.30)
        assert result["kelly_fraction"] <= 0.30

    @pytest.mark.asyncio
    async def test_kelly_sizing_invalid_stop_price(self, mock_config):
        """Test Kelly sizing with invalid stop price (equal to entry)."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.calculate_kelly_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_price=100.0,  # Invalid: same as entry
            win_rate=0.60,
            avg_win=2.0,
        )

        # Should return 0 position size
        assert result["position_size"] == 0
        assert "Invalid" in result["reason"]


class TestStopLossValidation:
    """Test stop loss validation logic."""

    @pytest.mark.asyncio
    async def test_validate_stop_loss_buy_valid(self, mock_config):
        """Test valid stop loss for buy order."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.validate_stop_loss(
            symbol="TEST",
            entry_price=100.0,
            stop_price=92.0,  # 8% below entry
            action="BUY",
        )

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_stop_loss_buy_invalid_above_entry(self, mock_config):
        """Test invalid stop loss above entry for buy order."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.validate_stop_loss(
            symbol="TEST",
            entry_price=100.0,
            stop_price=105.0,  # Above entry (invalid for buy)
            action="BUY",
        )

        assert result["valid"] is False
        assert "below entry" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_stop_loss_buy_too_wide(self, mock_config):
        """Test stop loss that's too wide."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.validate_stop_loss(
            symbol="TEST",
            entry_price=100.0,
            stop_price=70.0,  # 30% below entry (too wide)
            action="BUY",
        )

        assert result["valid"] is False
        assert "exceeds maximum" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_stop_loss_buy_too_tight(self, mock_config):
        """Test stop loss that's too tight."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.validate_stop_loss(
            symbol="TEST",
            entry_price=100.0,
            stop_price=99.5,  # 0.5% below entry (too tight)
            action="BUY",
        )

        assert result["valid"] is False
        assert "below minimum" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_stop_loss_sell_valid(self, mock_config):
        """Test valid stop loss for sell order."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.validate_stop_loss(
            symbol="TEST",
            entry_price=100.0,
            stop_price=108.0,  # 8% above entry
            action="SELL",
        )

        assert result["valid"] is True


class TestPortfolioHeatCheck:
    """Test portfolio heat checking."""

    @pytest.mark.asyncio
    async def test_portfolio_heat_sell_always_approved(self, mock_config):
        """Test that sell orders are always approved (reduce heat)."""
        risk_manager = PortfolioRisk(mock_config)

        result = await risk_manager.check_portfolio_heat(
            symbol="TEST", quantity=100, action="SELL", price=100.0
        )

        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_portfolio_heat_buy_within_limits(self, mock_config):
        """Test buy order within portfolio heat limits."""
        risk_manager = PortfolioRisk(mock_config)

        # Mock current heat as low - need to use AsyncMock for async methods
        async def mock_current_heat():
            return 0.02  # Lower heat to stay within limits

        with patch.object(
            risk_manager, "_calculate_current_heat", side_effect=mock_current_heat
        ):
            result = await risk_manager.check_portfolio_heat(
                symbol="TEST",
                quantity=50,  # $5k position on $100k portfolio = 5% (max position)
                action="BUY",
                price=100.0,
            )

            # Should be approved (2% current + 5% new = 7% total < 15% limit)
            # and position is exactly at max_position_pct (5%)
            assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_portfolio_heat_exceeds_max(self, mock_config):
        """Test buy order that would exceed portfolio heat limit."""
        risk_manager = PortfolioRisk(mock_config)

        # Mock current heat as high - need to use AsyncMock for async methods
        async def mock_current_heat():
            return 0.10

        with patch.object(
            risk_manager, "_calculate_current_heat", side_effect=mock_current_heat
        ):
            result = await risk_manager.check_portfolio_heat(
                symbol="TEST",
                quantity=600,  # $60k position on $100k portfolio = 60%
                action="BUY",
                price=100.0,
            )

            # Should be rejected (10% current + 60% new = 70% > 15% limit)
            assert result["approved"] is False
            assert "exceed" in result["reason"].lower()
