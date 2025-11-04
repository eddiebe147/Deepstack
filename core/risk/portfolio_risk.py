"""
Portfolio Risk Management - Core risk management for DeepStack

Manages portfolio-wide risk limits, position sizing, and risk metrics.
Implements Kelly Criterion, stop loss management, and portfolio heat tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from ..config import Config

logger = logging.getLogger(__name__)


class RiskMetrics:
    """Risk metrics for a position or portfolio."""

    def __init__(self, symbol: str = None):
        self.symbol = symbol
        self.portfolio_value: float = 0.0
        self.position_value: float = 0.0
        self.position_pct: float = 0.0
        self.portfolio_heat: float = 0.0
        self.kelly_fraction: float = 0.0
        self.var_95: float = 0.0  # 95% Value at Risk
        self.max_drawdown: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.sortino_ratio: float = 0.0
        self.calmar_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "symbol": self.symbol,
            "portfolio_value": self.portfolio_value,
            "position_value": self.position_value,
            "position_pct": self.position_pct,
            "portfolio_heat": self.portfolio_heat,
            "kelly_fraction": self.kelly_fraction,
            "var_95": self.var_95,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
        }


class PortfolioRisk:
    """
    Portfolio risk manager for DeepStack trading system.

    Implements:
    - Position size limits
    - Portfolio heat tracking
    - Kelly Criterion sizing
    - Risk/reward validation
    - Stop loss management
    """

    def __init__(self, config: Config):
        """
        Initialize portfolio risk manager.

        Args:
            config: DeepStack configuration
        """
        self.config = config

        # Risk limits from config
        self.max_position_pct = config.risk_limits.max_position_pct
        self.max_portfolio_heat = config.risk_limits.max_portfolio_heat
        self.daily_stop = config.risk_limits.daily_stop
        self.weekly_stop = config.risk_limits.weekly_stop
        self.max_drawdown = config.risk_limits.max_drawdown

        # Kelly settings
        self.kelly_settings = config.risk_limits.kelly_settings

        # Historical data for risk calculations
        self.portfolio_history: List[Tuple[datetime, float]] = []
        self.position_history: Dict[str, List[Tuple[datetime, float]]] = {}

        logger.info("PortfolioRisk manager initialized")

    async def check_portfolio_heat(
        self, symbol: str, quantity: int, action: str, price: float
    ) -> Dict[str, Any]:
        """
        Check if adding/removing position exceeds portfolio heat limits.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            price: Current price

        Returns:
            Dict with 'approved' bool and 'reason' string
        """
        try:
            # Get current portfolio value
            portfolio_value = await self._get_portfolio_value()
            if portfolio_value <= 0:
                return {"approved": False, "reason": "Cannot determine portfolio value"}

            # Calculate position value change
            position_value = quantity * price
            position_pct = position_value / portfolio_value

            # For sells, we're reducing heat
            if action == "SELL":
                return {"approved": True, "reason": "Sell order reduces portfolio heat"}

            # For buys, check if this exceeds limits
            current_heat = await self._calculate_current_heat()
            new_heat = current_heat + position_pct

            if new_heat > self.max_portfolio_heat:
                return {
                    "approved": False,
                    "reason": f"Portfolio heat {new_heat:.1%} would exceed limit {self.max_portfolio_heat:.1%}",
                }

            # Check individual position limit
            if position_pct > self.max_position_pct:
                return {
                    "approved": False,
                    "reason": f"Position size {position_pct:.1%} exceeds limit {self.max_position_pct:.1%}",
                }

            return {
                "approved": True,
                "reason": f"Portfolio heat check passed (current: {current_heat:.1%}, new: {new_heat:.1%})",
            }

        except Exception as e:
            logger.error(f"Error checking portfolio heat: {e}")
            return {
                "approved": False,
                "reason": f"Error checking portfolio heat: {str(e)}",
            }

    async def calculate_kelly_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        win_rate: float = 0.5,
        avg_win: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size using Kelly Criterion.

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            stop_price: Stop loss price
            win_rate: Historical win rate (0-1)
            avg_win: Average win/loss ratio

        Returns:
            Dict with position sizing recommendations
        """
        try:
            portfolio_value = await self._get_portfolio_value()
            if portfolio_value <= 0:
                return {
                    "position_size": 0,
                    "position_pct": 0.0,
                    "reason": "Cannot determine portfolio value",
                }

            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_price)

            if risk_per_share <= 0:
                return {
                    "position_size": 0,
                    "position_pct": 0.0,
                    "reason": "Invalid stop loss price",
                }

            # Kelly formula: f = (bp - q) / b
            # where:
            #   f = fraction of portfolio to risk
            #   b = odds (avg_win)
            #   p = win probability (win_rate)
            #   q = loss probability (1 - p)

            b = avg_win  # Odds (win/loss ratio)
            p = win_rate  # Win probability
            q = 1 - p  # Loss probability

            kelly_f = (b * p - q) / b

            # Apply conservative multiplier
            max_kelly_fraction = self.kelly_settings["max_kelly_fraction"]
            kelly_f = min(kelly_f, max_kelly_fraction)

            # Ensure positive Kelly
            kelly_f = max(kelly_f, 0)

            # Calculate position size
            risk_amount = portfolio_value * kelly_f
            position_size = int(risk_amount / risk_per_share)

            # Apply position size limits
            max_position_value = portfolio_value * self.max_position_pct
            max_shares_by_value = int(max_position_value / entry_price)

            position_size = min(position_size, max_shares_by_value)

            # Calculate position percentage
            position_value = position_size * entry_price
            position_pct = position_value / portfolio_value

            return {
                "position_size": position_size,
                "position_pct": position_pct,
                "position_value": position_value,
                "kelly_fraction": kelly_f,
                "risk_amount": risk_amount,
                "reason": f"Kelly sizing: {kelly_f:.1%} of portfolio, {position_pct:.1%} position",
            }

        except Exception as e:
            logger.error(f"Error calculating Kelly position size: {e}")
            return {
                "position_size": 0,
                "position_pct": 0.0,
                "reason": f"Error calculating Kelly size: {str(e)}",
            }

    async def validate_stop_loss(
        self, symbol: str, entry_price: float, stop_price: float, action: str
    ) -> Dict[str, Any]:
        """
        Validate stop loss placement.

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            stop_price: Stop loss price
            action: 'BUY' or 'SELL'

        Returns:
            Dict with validation result
        """
        try:
            # Check stop distance
            stop_distance_pct = abs(stop_price - entry_price) / entry_price

            # For buys, stop should be below entry
            if action == "BUY":
                if stop_price >= entry_price:
                    return {
                        "valid": False,
                        "reason": "Stop loss must be below entry price for buy orders",
                    }

                # Check if stop is too tight or too wide
                max_stop_pct = self.config.risk_limits.stop_loss.get(
                    "max_stop_pct", 0.25
                )

                if stop_distance_pct > max_stop_pct:
                    return {
                        "valid": False,
                        "reason": f"Stop loss {stop_distance_pct:.1%} exceeds maximum {max_stop_pct:.1%}",
                    }

            # For sells, stop should be above entry
            elif action == "SELL":
                if stop_price <= entry_price:
                    return {
                        "valid": False,
                        "reason": "Stop loss must be above entry price for sell orders",
                    }

                # Check if stop is too tight or too wide
                max_stop_pct = self.config.risk_limits.stop_loss.get(
                    "max_stop_pct", 0.25
                )

                if stop_distance_pct > max_stop_pct:
                    return {
                        "valid": False,
                        "reason": f"Stop loss {stop_distance_pct:.1%} exceeds maximum {max_stop_pct:.1%}",
                    }

            # Check minimum stop distance (avoid market noise)
            min_stop_pct = 0.01  # 1% minimum
            if stop_distance_pct < min_stop_pct:
                return {
                    "valid": False,
                    "reason": f"Stop loss {stop_distance_pct:.1%} below minimum {min_stop_pct:.1%}",
                }

            return {
                "valid": True,
                "reason": f"Stop loss {stop_distance_pct:.1%} within acceptable range",
            }

        except Exception as e:
            logger.error(f"Error validating stop loss: {e}")
            return {"valid": False, "reason": f"Error validating stop loss: {str(e)}"}

    async def calculate_portfolio_metrics(self) -> RiskMetrics:
        """
        Calculate comprehensive portfolio risk metrics.

        Returns:
            RiskMetrics object with current portfolio risk data
        """
        try:
            portfolio_value = await self._get_portfolio_value()
            if portfolio_value <= 0:
                return RiskMetrics()

            # Calculate portfolio heat
            portfolio_heat = await self._calculate_current_heat()

            # Calculate Sharpe ratio (simplified)
            sharpe_ratio = await self._calculate_sharpe_ratio()

            # Calculate maximum drawdown
            max_drawdown = await self._calculate_max_drawdown()

            # Calculate VaR (simplified)
            var_95 = portfolio_value * 0.05  # 5% daily VaR assumption

            metrics = RiskMetrics()
            metrics.portfolio_value = portfolio_value
            metrics.portfolio_heat = portfolio_heat
            metrics.sharpe_ratio = sharpe_ratio
            metrics.max_drawdown = max_drawdown
            metrics.var_95 = var_95

            return metrics

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return RiskMetrics()

    async def check_daily_loss_limit(self) -> Dict[str, Any]:
        """
        Check if daily loss limit has been exceeded.

        Returns:
            Dict with loss limit status
        """
        try:
            # Get current portfolio value and day's P&L
            portfolio_value = await self._get_portfolio_value()
            day_pnl = await self._get_day_pnl()

            if portfolio_value <= 0:
                return {
                    "within_limit": True,
                    "reason": "Cannot determine portfolio value",
                }

            # Calculate loss percentage
            loss_pct = abs(day_pnl) / portfolio_value

            if day_pnl >= 0:  # Profit or no loss
                return {
                    "within_limit": True,
                    "current_loss_pct": 0.0,
                    "limit_pct": self.daily_stop,
                    "reason": f"Current P&L: ${day_pnl:+.2f} (profit)",
                }

            # Check if loss exceeds limit
            if loss_pct > self.daily_stop:
                return {
                    "within_limit": False,
                    "current_loss_pct": loss_pct,
                    "limit_pct": self.daily_stop,
                    "reason": f"Daily loss {loss_pct:.1%} exceeds limit {self.daily_stop:.1%}",
                }

            return {
                "within_limit": True,
                "current_loss_pct": loss_pct,
                "limit_pct": self.daily_stop,
                "reason": f"Daily loss {loss_pct:.1%} within limit {self.daily_stop:.1%}",
            }

        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return {
                "within_limit": True,
                "reason": f"Error checking daily loss limit: {str(e)}",
            }

    async def check_weekly_loss_limit(self) -> Dict[str, Any]:
        """
        Check if weekly loss limit has been exceeded.

        Returns:
            Dict with loss limit status
        """
        try:
            # Get current portfolio value and week's P&L
            portfolio_value = await self._get_portfolio_value()
            week_pnl = await self._get_week_pnl()

            if portfolio_value <= 0:
                return {
                    "within_limit": True,
                    "reason": "Cannot determine portfolio value",
                }

            # Calculate loss percentage
            loss_pct = abs(week_pnl) / portfolio_value

            if week_pnl >= 0:  # Profit or no loss
                return {
                    "within_limit": True,
                    "current_loss_pct": 0.0,
                    "limit_pct": self.weekly_stop,
                    "reason": f"Current P&L: ${week_pnl:+.2f} (profit)",
                }

            # Check if loss exceeds limit
            if loss_pct > self.weekly_stop:
                return {
                    "within_limit": False,
                    "current_loss_pct": loss_pct,
                    "limit_pct": self.weekly_stop,
                    "reason": f"Weekly loss {loss_pct:.1%} exceeds limit {self.weekly_stop:.1%}",
                }

            return {
                "within_limit": True,
                "current_loss_pct": loss_pct,
                "limit_pct": self.weekly_stop,
                "reason": f"Weekly loss {loss_pct:.1%} within limit {self.weekly_stop:.1%}",
            }

        except Exception as e:
            logger.error(f"Error checking weekly loss limit: {e}")
            return {
                "within_limit": True,
                "reason": f"Error checking weekly loss limit: {str(e)}",
            }

    # Helper Methods

    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        # This would integrate with the broker/portfolio manager
        # For now, return a default value
        return 100000.0

    async def _calculate_current_heat(self) -> float:
        """Calculate current portfolio heat (total risk)."""
        # This would calculate based on current positions and their risk
        # For now, return 0
        return 0.0

    async def _get_day_pnl(self) -> float:
        """Get day's P&L."""
        # This would get from broker/portfolio manager
        return 0.0

    async def _get_week_pnl(self) -> float:
        """Get week's P&L."""
        # This would get from broker/portfolio manager
        return 0.0

    async def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio."""
        # Simplified calculation
        # In production, this would use historical returns
        return 1.0

    async def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        # This would use historical portfolio values
        return 0.0
