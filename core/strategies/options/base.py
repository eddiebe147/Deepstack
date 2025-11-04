"""
Base classes and data models for options strategies.

Provides the foundation for all options trading strategies including
data models for option legs, positions, and Greeks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class OptionLeg:
    """
    Single option leg in a multi-leg strategy.

    Attributes:
        symbol: Underlying stock symbol (e.g., "AAPL")
        strike: Strike price of the option
        expiration: Expiration date
        option_type: "call" or "put"
        action: "buy" or "sell"
        quantity: Number of contracts
        premium: Premium per contract (in dollars)
    """

    symbol: str
    strike: float
    expiration: datetime
    option_type: str
    action: str
    quantity: int
    premium: float

    def __post_init__(self):
        """Validate option leg parameters."""
        if self.option_type not in ["call", "put"]:
            raise ValueError(
                f"option_type must be 'call' or 'put', got {self.option_type}"
            )

        if self.action not in ["buy", "sell"]:
            raise ValueError(f"action must be 'buy' or 'sell', got {self.action}")

        if self.strike <= 0:
            raise ValueError(f"strike must be positive, got {self.strike}")

        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")

        if self.premium < 0:
            raise ValueError(f"premium cannot be negative, got {self.premium}")

    def contract_multiplier(self) -> int:
        """
        Get the contract multiplier (shares per contract).
        Standard options represent 100 shares.
        """
        return 100

    def total_premium(self) -> float:
        """
        Calculate total premium for this leg.

        Returns:
            Total premium (premium * quantity * multiplier)
        """
        return self.premium * self.quantity * self.contract_multiplier()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "strike": self.strike,
            "expiration": self.expiration.isoformat(),
            "option_type": self.option_type,
            "action": self.action,
            "quantity": self.quantity,
            "premium": self.premium,
        }


@dataclass
class OptionsPosition:
    """
    Multi-leg options position representing a complete strategy.

    Attributes:
        strategy_name: Name of the strategy (e.g., "Iron Condor")
        legs: List of option legs in the position
        entry_date: When the position was entered
        entry_cost: Net debit (positive) or credit (negative) paid
        max_profit: Maximum possible profit
        max_loss: Maximum possible loss
        breakeven_points: List of breakeven prices
        profit_target_pct: Close at X% of max profit (optional)
        loss_limit_pct: Close at X% of max loss (optional)
    """

    strategy_name: str
    legs: List[OptionLeg]
    entry_date: datetime
    entry_cost: float
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    profit_target_pct: Optional[float] = None
    loss_limit_pct: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate position parameters."""
        if not self.legs:
            raise ValueError("Position must have at least one leg")

        # Ensure all legs have the same symbol
        symbols = {leg.symbol for leg in self.legs}
        if len(symbols) > 1:
            raise ValueError(f"All legs must have the same symbol, got {symbols}")

        # Ensure all legs have the same expiration
        expirations = {leg.expiration for leg in self.legs}
        if len(expirations) > 1:
            raise ValueError(
                f"All legs must have the same expiration, got {expirations}"
            )

    @property
    def symbol(self) -> str:
        """Get the underlying symbol."""
        return self.legs[0].symbol

    @property
    def expiration(self) -> datetime:
        """Get the expiration date."""
        return self.legs[0].expiration

    def days_to_expiration(self, current_date: Optional[datetime] = None) -> int:
        """
        Calculate days remaining until expiration.

        Args:
            current_date: Current date (defaults to now)

        Returns:
            Days to expiration (minimum 0)
        """
        if current_date is None:
            current_date = datetime.now()

        delta = self.expiration - current_date
        return max(0, delta.days)

    def is_credit_spread(self) -> bool:
        """
        Check if this is a credit spread (received money at entry).

        Returns:
            True if entry_cost is negative (credit received)
        """
        return self.entry_cost < 0

    def net_credit_received(self) -> float:
        """
        Get net credit received (0 if debit spread).

        Returns:
            Positive value if credit spread, 0 otherwise
        """
        return abs(self.entry_cost) if self.is_credit_spread() else 0.0

    def net_debit_paid(self) -> float:
        """
        Get net debit paid (0 if credit spread).

        Returns:
            Positive value if debit spread, 0 otherwise
        """
        return self.entry_cost if not self.is_credit_spread() else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "legs": [leg.to_dict() for leg in self.legs],
            "entry_date": self.entry_date.isoformat(),
            "expiration": self.expiration.isoformat(),
            "entry_cost": self.entry_cost,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "breakeven_points": self.breakeven_points,
            "profit_target_pct": self.profit_target_pct,
            "loss_limit_pct": self.loss_limit_pct,
            "metadata": self.metadata,
        }


@dataclass
class Greeks:
    """
    Greeks for an options position.

    Greeks measure the sensitivity of an option's price to various factors:
    - Delta: Price change per $1 move in underlying
    - Gamma: Delta change per $1 move in underlying
    - Theta: Price change per day (time decay)
    - Vega: Price change per 1% change in volatility

    Attributes:
        delta: Position delta (-1 to +1 per contract)
        gamma: Position gamma
        theta: Position theta (per day, usually negative)
        vega: Position vega (per 1% volatility change)
    """

    delta: float
    gamma: float
    theta: float
    vega: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation."""
        return {
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Greeks(delta={self.delta:.4f}, gamma={self.gamma:.4f}, "
            f"theta={self.theta:.4f}, vega={self.vega:.4f})"
        )


class OptionsStrategy(ABC):
    """
    Abstract base class for options trading strategies.

    All options strategies must implement:
    - create_position: Build the multi-leg position
    - calculate_pnl: Calculate current profit/loss
    - should_close: Determine if position should be closed
    """

    @abstractmethod
    def create_position(
        self, symbol: str, underlying_price: float, **kwargs
    ) -> OptionsPosition:
        """
        Create the options position for this strategy.

        Args:
            symbol: Underlying stock symbol
            underlying_price: Current price of underlying
            **kwargs: Strategy-specific parameters

        Returns:
            Complete OptionsPosition with all legs
        """

    @abstractmethod
    def calculate_pnl(
        self,
        position: OptionsPosition,
        current_price: float,
        days_to_expiration: int,
        volatility: float = 0.30,
    ) -> float:
        """
        Calculate current profit/loss for the position.

        Args:
            position: The options position
            current_price: Current price of underlying
            days_to_expiration: Days until expiration
            volatility: Implied volatility (default 30%)

        Returns:
            Current P&L (positive = profit, negative = loss)
        """

    @abstractmethod
    def should_close(
        self, position: OptionsPosition, current_pnl: float, days_to_expiration: int
    ) -> bool:
        """
        Determine if the position should be closed.

        Args:
            position: The options position
            current_pnl: Current profit/loss
            days_to_expiration: Days until expiration

        Returns:
            True if position should be closed
        """

    def get_close_reason(
        self, position: OptionsPosition, current_pnl: float, days_to_expiration: int
    ) -> Optional[str]:
        """
        Get the reason for closing (if should_close is True).

        Args:
            position: The options position
            current_pnl: Current profit/loss
            days_to_expiration: Days until expiration

        Returns:
            Reason string or None if should not close
        """
        if not self.should_close(position, current_pnl, days_to_expiration):
            return None

        # Check profit target
        if position.profit_target_pct is not None:
            profit_target = position.max_profit * position.profit_target_pct
            if current_pnl >= profit_target:
                pct_str = f"{position.profit_target_pct:.0%}"
                return f"Profit target reached ({pct_str} of max profit)"

        # Check loss limit
        if position.loss_limit_pct is not None:
            loss_limit = -abs(position.max_loss * position.loss_limit_pct)
            if current_pnl <= loss_limit:
                pct_str = f"{position.loss_limit_pct:.0%}"
                return f"Loss limit hit ({pct_str} of max loss)"

        # Check expiration
        if days_to_expiration <= 0:
            return "Expiration reached"

        return "Strategy exit condition met"
