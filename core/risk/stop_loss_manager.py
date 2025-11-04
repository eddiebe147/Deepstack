"""
Stop Loss Manager - Production-ready stop loss management for DeepStack

Ensures EVERY trade has automatic risk protection with multiple stop types.
Implements trailing stops, ATR-based stops, and fixed percentage stops with
strict never-downgrade rules.

Key Features:
    - 100% stop loss coverage (every order MUST have a stop)
    - Multiple stop types: fixed %, ATR-based, trailing
    - Never-downgrade rule (stops only move favorably)
    - Automatic profit locking with trailing stops
    - Emergency stop updates for market crashes
    - Integration with Kelly position sizer

Critical Rules:
    - EVERY order has a stop loss (100% coverage)
    - Stops NEVER downgrade (only move favorably)
    - Default 2% max risk per trade
    - Fail-safe: reject trade if stop can't be calculated
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StopType(Enum):
    """Supported stop loss types."""

    FIXED_PCT = "fixed_pct"  # Fixed percentage below entry
    ATR_BASED = "atr_based"  # Based on Average True Range (volatility)
    TRAILING = "trailing"  # Follows price up, locks profits


class PositionSide(Enum):
    """Position direction."""

    LONG = "long"
    SHORT = "short"


class StopLossManager:
    """
    Production-ready stop loss manager.

    Calculates and manages stop losses for all positions with multiple
    stop types and strict risk management rules.

    Example:
        >>> manager = StopLossManager(
        ...     account_balance=100000,
        ...     max_risk_per_trade=0.02
        ... )
        >>> stop = manager.calculate_stop_loss(
        ...     symbol="AAPL",
        ...     entry_price=150.0,
        ...     position_size=10000.0,
        ...     stop_type="fixed_pct",
        ...     stop_pct=0.02
        ... )
        >>> print(f"Stop price: ${stop['stop_price']:.2f}")
    """

    def __init__(
        self,
        account_balance: float,
        max_risk_per_trade: float = 0.02,
        default_stop_pct: float = 0.02,
        default_atr_multiplier: float = 2.0,
        default_trailing_pct: float = 0.05,
        min_stop_distance: float = 0.005,
        max_stop_distance: float = 0.10,
    ):
        """
        Initialize stop loss manager.

        Args:
            account_balance: Total account balance in dollars
            max_risk_per_trade: Maximum risk per trade as % of account (default 0.02 = 2%)
            default_stop_pct: Default fixed stop % (default 0.02 = 2%)
            default_atr_multiplier: Default ATR multiplier (default 2.0)
            default_trailing_pct: Default trailing stop % (default 0.05 = 5%)
            min_stop_distance: Minimum stop distance % (default 0.005 = 0.5%)
            max_stop_distance: Maximum stop distance % (default 0.10 = 10%)

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate account balance
        if account_balance <= 0:
            raise ValueError(f"Account balance must be positive, got {account_balance}")

        # Validate risk parameters
        if not 0 < max_risk_per_trade <= 0.10:
            raise ValueError(
                f"max_risk_per_trade must be between 0 and 0.10, got {max_risk_per_trade}"
            )

        if not 0 < default_stop_pct <= 1.0:
            raise ValueError(
                f"default_stop_pct must be between 0 and 1, got {default_stop_pct}"
            )

        if default_atr_multiplier <= 0:
            raise ValueError(
                f"default_atr_multiplier must be positive, got {default_atr_multiplier}"
            )

        if not 0 < default_trailing_pct <= 1.0:
            raise ValueError(
                f"default_trailing_pct must be between 0 and 1, got {default_trailing_pct}"
            )

        if not 0 < min_stop_distance < max_stop_distance <= 1.0:
            raise ValueError(
                f"Invalid stop distance range: min={min_stop_distance}, max={max_stop_distance}"
            )

        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.default_stop_pct = default_stop_pct
        self.default_atr_multiplier = default_atr_multiplier
        self.default_trailing_pct = default_trailing_pct
        self.min_stop_distance = min_stop_distance
        self.max_stop_distance = max_stop_distance

        # Track active stops for never-downgrade validation
        self.active_stops: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"StopLossManager initialized: balance=${account_balance:,.2f}, "
            f"max_risk={max_risk_per_trade:.1%}, default_stop={default_stop_pct:.1%}"
        )

    def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        position_size: float,
        position_side: str = "long",
        stop_type: str = "fixed_pct",
        stop_pct: Optional[float] = None,
        atr: Optional[float] = None,
        atr_multiplier: Optional[float] = None,
        custom_stop_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate stop loss price for a position.

        This method ENSURES 100% stop loss coverage. Every call returns a valid
        stop or raises an exception to prevent unprotected trades.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            entry_price: Entry price for the position
            position_size: Position size in dollars
            position_side: "long" or "short" (default "long")
            stop_type: "fixed_pct", "atr_based", or "trailing"
            stop_pct: Stop loss percentage (for fixed_pct stops)
            atr: Average True Range value (for atr_based stops)
            atr_multiplier: ATR multiplier (for atr_based stops)
            custom_stop_price: Custom stop price (overrides calculation)

        Returns:
            Dict with stop loss details:
                {
                    "stop_price": float,           # Actual stop price
                    "stop_type": str,              # Type of stop used
                    "risk_amount": float,          # Dollar risk
                    "risk_pct": float,             # % of position at risk
                    "account_risk_pct": float,     # % of account at risk
                    "stop_distance": float,        # Distance from entry (%)
                    "shares": int,                 # Number of shares (if applicable)
                    "rationale": str,              # Explanation
                    "warnings": list,              # Any warnings
                    "position_side": str,          # "long" or "short"
                }

        Raises:
            ValueError: If stop loss cannot be calculated (FAIL-SAFE)
        """
        # Validate inputs
        self._validate_stop_inputs(
            symbol, entry_price, position_size, position_side, stop_type
        )

        # Normalize position side
        side = PositionSide(position_side.lower())

        # Use custom stop if provided
        if custom_stop_price is not None:
            stop_price = custom_stop_price
            rationale = "Custom stop price provided"
            stop_type_used = "custom"
        else:
            # Calculate stop based on type
            if stop_type == StopType.FIXED_PCT.value:
                stop_price = self._calculate_fixed_pct_stop(
                    entry_price, side, stop_pct or self.default_stop_pct
                )
                rationale = f"Fixed {(stop_pct or self.default_stop_pct):.1%} stop"
                stop_type_used = StopType.FIXED_PCT.value

            elif stop_type == StopType.ATR_BASED.value:
                if atr is None or atr <= 0:
                    raise ValueError(
                        f"ATR value required for ATR-based stops, got {atr}"
                    )
                stop_price = self._calculate_atr_based_stop(
                    entry_price,
                    side,
                    atr,
                    atr_multiplier or self.default_atr_multiplier,
                )
                rationale = f"ATR-based stop ({(atr_multiplier or self.default_atr_multiplier):.1f}x ATR)"
                stop_type_used = StopType.ATR_BASED.value

            elif stop_type == StopType.TRAILING.value:
                # Trailing stops start at fixed % then trail
                stop_price = self._calculate_fixed_pct_stop(
                    entry_price, side, stop_pct or self.default_trailing_pct
                )
                rationale = f"Trailing stop initialized ({(stop_pct or self.default_trailing_pct):.1%} trail)"
                stop_type_used = StopType.TRAILING.value

            else:
                raise ValueError(f"Invalid stop_type: {stop_type}")

        # Validate stop distance
        self._validate_stop_distance(entry_price, stop_price, side)

        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(
            entry_price, stop_price, position_size, side
        )

        # Validate account risk
        if risk_metrics["account_risk_pct"] > self.max_risk_per_trade:
            raise ValueError(
                f"Stop loss exceeds max account risk: "
                f"{risk_metrics['account_risk_pct']:.2%} > {self.max_risk_per_trade:.2%}. "
                f"Reduce position size or tighten stop."
            )

        # Calculate shares
        shares = int(position_size / entry_price) if entry_price > 0 else 0

        warnings = []
        if risk_metrics["account_risk_pct"] > self.max_risk_per_trade * 0.8:
            warnings.append(
                f"High account risk: {risk_metrics['account_risk_pct']:.2%} "
                f"(near max {self.max_risk_per_trade:.2%})"
            )

        # Store stop for never-downgrade tracking
        self.active_stops[symbol] = {
            "stop_price": stop_price,
            "entry_price": entry_price,
            "position_side": side.value,
            "stop_type": stop_type_used,
            "highest_price": entry_price if side == PositionSide.LONG else entry_price,
            "lowest_price": entry_price if side == PositionSide.SHORT else entry_price,
        }

        return {
            "stop_price": stop_price,
            "stop_type": stop_type_used,
            "risk_amount": risk_metrics["risk_amount"],
            "risk_pct": risk_metrics["risk_pct"],
            "account_risk_pct": risk_metrics["account_risk_pct"],
            "stop_distance": risk_metrics["stop_distance"],
            "shares": shares,
            "rationale": rationale,
            "warnings": warnings,
            "position_side": side.value,
        }

    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        trailing_pct: Optional[float] = None,
        force_update: bool = False,
    ) -> Dict[str, Any]:
        """
        Update trailing stop based on new price.

        Trailing stops move UP with price (for longs) or DOWN (for shorts),
        but NEVER move against the position (never-downgrade rule).

        Args:
            symbol: Stock symbol
            current_price: Current market price
            trailing_pct: Trailing percentage (default: self.default_trailing_pct)
            force_update: Force update even if stop would downgrade (DANGEROUS)

        Returns:
            Dict with update details:
                {
                    "stop_price": float,        # New stop price
                    "old_stop_price": float,    # Previous stop price
                    "stop_moved": bool,         # Whether stop was updated
                    "highest_price": float,     # Highest price seen (for longs)
                    "lowest_price": float,      # Lowest price seen (for shorts)
                    "profit_locked": float,     # Profit locked in (if any)
                    "rationale": str,
                }

        Raises:
            ValueError: If symbol has no active stop or inputs invalid
        """
        if symbol not in self.active_stops:
            raise ValueError(f"No active stop for {symbol}")

        if current_price <= 0:
            raise ValueError(f"Current price must be positive, got {current_price}")

        stop_data = self.active_stops[symbol]
        side = PositionSide(stop_data["position_side"])
        old_stop = stop_data["stop_price"]
        entry_price = stop_data["entry_price"]
        trail_pct = trailing_pct or self.default_trailing_pct

        # Update highest/lowest price
        if side == PositionSide.LONG:
            highest = max(stop_data["highest_price"], current_price)
            stop_data["highest_price"] = highest

            # Calculate new trailing stop from highest price
            new_stop = highest * (1 - trail_pct)

            # Never-downgrade: stop can only move UP for longs
            if new_stop > old_stop or force_update:
                stop_data["stop_price"] = new_stop
                stop_moved = True
                rationale = f"Trailing stop raised to {new_stop:.2f} (trailing {trail_pct:.1%} from high ${highest:.2f})"
            else:
                new_stop = old_stop
                stop_moved = False
                rationale = "Trailing stop unchanged (never-downgrade rule)"

        else:  # SHORT
            lowest = min(stop_data["lowest_price"], current_price)
            stop_data["lowest_price"] = lowest

            # Calculate new trailing stop from lowest price
            new_stop = lowest * (1 + trail_pct)

            # Never-downgrade: stop can only move DOWN for shorts
            if new_stop < old_stop or force_update:
                stop_data["stop_price"] = new_stop
                stop_moved = True
                rationale = f"Trailing stop lowered to {new_stop:.2f} (trailing {trail_pct:.1%} from low ${lowest:.2f})"
            else:
                new_stop = old_stop
                stop_moved = False
                rationale = "Trailing stop unchanged (never-downgrade rule)"

        # Calculate profit locked
        if side == PositionSide.LONG:
            profit_locked = max(0, new_stop - entry_price)
        else:
            profit_locked = max(0, entry_price - new_stop)

        return {
            "stop_price": new_stop,
            "old_stop_price": old_stop,
            "stop_moved": stop_moved,
            "highest_price": stop_data.get("highest_price", current_price),
            "lowest_price": stop_data.get("lowest_price", current_price),
            "profit_locked": profit_locked,
            "rationale": rationale,
        }

    def validate_stop_never_downgrades(
        self,
        symbol: str,
        new_stop: float,
        position_side: Optional[str] = None,
    ) -> bool:
        """
        Validate that new stop doesn't downgrade (violate never-downgrade rule).

        For LONGS: new stop must be >= old stop (only move up)
        For SHORTS: new stop must be <= old stop (only move down)

        Args:
            symbol: Stock symbol
            new_stop: Proposed new stop price
            position_side: Position side (if symbol not in active_stops)

        Returns:
            bool: True if stop doesn't downgrade, False if it violates rule

        Raises:
            ValueError: If validation cannot be performed
        """
        if symbol not in self.active_stops:
            # No existing stop, so can't downgrade
            return True

        if new_stop <= 0:
            raise ValueError(f"Stop price must be positive, got {new_stop}")

        stop_data = self.active_stops[symbol]
        old_stop = stop_data["stop_price"]
        side = PositionSide(stop_data["position_side"])

        if side == PositionSide.LONG:
            # For longs, new stop must be >= old stop (move up or stay same)
            is_valid = new_stop >= old_stop
            if not is_valid:
                logger.warning(
                    f"NEVER-DOWNGRADE VIOLATION: {symbol} LONG stop would move down "
                    f"from ${old_stop:.2f} to ${new_stop:.2f}"
                )
        else:  # SHORT
            # For shorts, new stop must be <= old stop (move down or stay same)
            is_valid = new_stop <= old_stop
            if not is_valid:
                logger.warning(
                    f"NEVER-DOWNGRADE VIOLATION: {symbol} SHORT stop would move up "
                    f"from ${old_stop:.2f} to ${new_stop:.2f}"
                )

        return is_valid

    def emergency_stop_update(
        self,
        symbol: str,
        emergency_stop_price: float,
        reason: str = "Emergency stop update",
    ) -> Dict[str, Any]:
        """
        Emergency stop loss update (e.g., market crash, flash crash).

        This bypasses never-downgrade rule in extreme situations.
        USE WITH EXTREME CAUTION.

        Args:
            symbol: Stock symbol
            emergency_stop_price: New emergency stop price
            reason: Reason for emergency update

        Returns:
            Dict with update details:
                {
                    "stop_price": float,
                    "old_stop_price": float,
                    "violated_never_downgrade": bool,
                    "reason": str,
                    "warning": str,
                }

        Raises:
            ValueError: If symbol has no active stop
        """
        if symbol not in self.active_stops:
            raise ValueError(f"No active stop for {symbol}")

        if emergency_stop_price <= 0:
            raise ValueError(
                f"Emergency stop price must be positive, got {emergency_stop_price}"
            )

        stop_data = self.active_stops[symbol]
        old_stop = stop_data["stop_price"]

        # Check if violating never-downgrade
        violated_rule = not self.validate_stop_never_downgrades(
            symbol, emergency_stop_price
        )

        # Update stop regardless (emergency override)
        stop_data["stop_price"] = emergency_stop_price

        warning = ""
        if violated_rule:
            warning = "WARNING: Emergency stop violated never-downgrade rule!"
            logger.warning(
                f"EMERGENCY STOP UPDATE: {symbol} stop moved from ${old_stop:.2f} "
                f"to ${emergency_stop_price:.2f} - VIOLATED NEVER-DOWNGRADE RULE. "
                f"Reason: {reason}"
            )
        else:
            logger.info(
                f"Emergency stop update: {symbol} stop moved from ${old_stop:.2f} "
                f"to ${emergency_stop_price:.2f}. Reason: {reason}"
            )

        return {
            "stop_price": emergency_stop_price,
            "old_stop_price": old_stop,
            "violated_never_downgrade": violated_rule,
            "reason": reason,
            "warning": warning,
        }

    def get_active_stop(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get active stop for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with stop details or None if no active stop
        """
        return self.active_stops.get(symbol)

    def remove_stop(self, symbol: str) -> bool:
        """
        Remove active stop (e.g., position closed).

        Args:
            symbol: Stock symbol

        Returns:
            bool: True if stop was removed, False if no stop existed
        """
        if symbol in self.active_stops:
            del self.active_stops[symbol]
            logger.info(f"Stop removed for {symbol}")
            return True
        return False

    def get_all_stops(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active stops.

        Returns:
            Dict of {symbol: stop_data}
        """
        return self.active_stops.copy()

    def validate_100pct_coverage(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Validate that all positions have stops (100% coverage).

        Args:
            symbols: List of symbols with open positions

        Returns:
            Dict with coverage report:
                {
                    "total_positions": int,
                    "positions_with_stops": int,
                    "coverage_pct": float,
                    "missing_stops": list,
                    "has_100pct_coverage": bool,
                }
        """
        total = len(symbols)
        symbols_with_stops = [s for s in symbols if s in self.active_stops]
        missing_stops = [s for s in symbols if s not in self.active_stops]

        coverage = len(symbols_with_stops) / total if total > 0 else 1.0

        result = {
            "total_positions": total,
            "positions_with_stops": len(symbols_with_stops),
            "coverage_pct": coverage,
            "missing_stops": missing_stops,
            "has_100pct_coverage": coverage == 1.0,
        }

        if not result["has_100pct_coverage"]:
            logger.error(
                f"STOP COVERAGE VIOLATION: {len(missing_stops)} positions without stops: {missing_stops}"
            )

        return result

    def _calculate_fixed_pct_stop(
        self, entry_price: float, side: PositionSide, stop_pct: float
    ) -> float:
        """Calculate fixed percentage stop loss."""
        if side == PositionSide.LONG:
            return entry_price * (1 - stop_pct)
        else:  # SHORT
            return entry_price * (1 + stop_pct)

    def _calculate_atr_based_stop(
        self,
        entry_price: float,
        side: PositionSide,
        atr: float,
        atr_multiplier: float,
    ) -> float:
        """Calculate ATR-based stop loss."""
        stop_distance = atr * atr_multiplier

        if side == PositionSide.LONG:
            return entry_price - stop_distance
        else:  # SHORT
            return entry_price + stop_distance

    def _validate_stop_inputs(
        self,
        symbol: str,
        entry_price: float,
        position_size: float,
        position_side: str,
        stop_type: str,
    ):
        """Validate stop loss calculation inputs."""
        if not symbol:
            raise ValueError("Symbol cannot be empty")

        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")

        if position_size <= 0:
            raise ValueError(f"Position size must be positive, got {position_size}")

        try:
            PositionSide(position_side.lower())
        except ValueError:
            raise ValueError(
                f"Invalid position_side: {position_side}. Must be 'long' or 'short'"
            )

        valid_stop_types = [st.value for st in StopType]
        if stop_type not in valid_stop_types:
            raise ValueError(
                f"Invalid stop_type: {stop_type}. Must be one of {valid_stop_types}"
            )

    def _validate_stop_distance(
        self, entry_price: float, stop_price: float, side: PositionSide
    ):
        """Validate stop distance is within acceptable range."""
        if stop_price <= 0:
            raise ValueError(f"Stop price must be positive, got {stop_price}")

        if side == PositionSide.LONG:
            if stop_price >= entry_price:
                raise ValueError(
                    f"Stop price ({stop_price:.2f}) must be below entry ({entry_price:.2f}) for long positions"
                )
            stop_distance = (entry_price - stop_price) / entry_price
        else:  # SHORT
            if stop_price <= entry_price:
                raise ValueError(
                    f"Stop price ({stop_price:.2f}) must be above entry ({entry_price:.2f}) for short positions"
                )
            stop_distance = (stop_price - entry_price) / entry_price

        if stop_distance < self.min_stop_distance:
            raise ValueError(
                f"Stop too tight: {stop_distance:.2%} < min {self.min_stop_distance:.2%}"
            )

        if stop_distance > self.max_stop_distance:
            raise ValueError(
                f"Stop too wide: {stop_distance:.2%} > max {self.max_stop_distance:.2%}"
            )

    def _calculate_risk_metrics(
        self,
        entry_price: float,
        stop_price: float,
        position_size: float,
        side: PositionSide,
    ) -> Dict[str, float]:
        """Calculate risk metrics for a stop loss."""
        if side == PositionSide.LONG:
            price_risk = entry_price - stop_price
            stop_distance = price_risk / entry_price
        else:  # SHORT
            price_risk = stop_price - entry_price
            stop_distance = price_risk / entry_price

        shares = position_size / entry_price
        risk_amount = shares * price_risk
        risk_pct = risk_amount / position_size
        account_risk_pct = risk_amount / self.account_balance

        return {
            "risk_amount": risk_amount,
            "risk_pct": risk_pct,
            "account_risk_pct": account_risk_pct,
            "stop_distance": stop_distance,
        }

    def update_account_balance(self, new_balance: float):
        """
        Update account balance.

        Args:
            new_balance: New account balance

        Raises:
            ValueError: If new balance is invalid
        """
        if new_balance <= 0:
            raise ValueError(f"Account balance must be positive, got {new_balance}")

        old_balance = self.account_balance
        self.account_balance = new_balance
        logger.info(
            f"Account balance updated: ${old_balance:,.2f} -> ${new_balance:,.2f}"
        )
