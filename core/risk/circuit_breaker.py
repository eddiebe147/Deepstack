"""
Circuit Breaker System - Production-ready trading halt protection for DeepStack

Protects against catastrophic losses by automatically halting trading when
risk thresholds are breached. Implements multiple breaker types with fail-safe
logic and mandatory confirmation for resets.

Circuit Breaker Types:
    1. Daily Loss Limit - Halt if daily loss exceeds threshold (e.g., -3%)
    2. Max Drawdown - Halt if portfolio down X% from peak (e.g., -10%)
    3. Consecutive Losses - Halt after N losing trades in a row (e.g., 5)
    4. Volatility Spike - Halt during extreme market conditions (VIX > threshold)

Critical Design Principles:
    - FAIL-SAFE: If uncertain, trip the breaker (err on side of caution)
    - NO BYPASS: Only reset with proper confirmation code
    - EXTENSIVE LOGGING: All trips/resets logged with reason
    - IMMEDIATE HALT: Trading stops instantly when tripped
    - COMPREHENSIVE: Multiple breaker types for different risk scenarios

Example:
    >>> breaker = CircuitBreaker(
    ...     daily_loss_limit=0.03,
    ...     max_drawdown_limit=0.10,
    ...     consecutive_loss_limit=5,
    ...     volatility_threshold=40.0
    ... )
    >>> status = breaker.check_breakers(
    ...     current_portfolio_value=97000,
    ...     start_of_day_value=100000
    ... )
    >>> if not status["trading_allowed"]:
    ...     print(f"Trading halted: {status['reasons']}")
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BreakerType(Enum):
    """Supported circuit breaker types."""

    DAILY_LOSS = "daily_loss"
    MAX_DRAWDOWN = "max_drawdown"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    VOLATILITY_SPIKE = "volatility_spike"
    MANUAL = "manual"  # Manually triggered halt


class BreakerState(Enum):
    """Circuit breaker states."""

    ARMED = "armed"  # Active, monitoring
    TRIPPED = "tripped"  # Halted trading
    RESET = "reset"  # Temporarily disabled (cooling down)


class CircuitBreaker:
    """
    Production-ready circuit breaker system for trading protection.

    Monitors multiple risk factors and automatically halts trading when
    thresholds are breached. Provides comprehensive logging and fail-safe
    protection against catastrophic losses.

    Example:
        >>> breaker = CircuitBreaker(
        ...     initial_portfolio_value=100000,
        ...     daily_loss_limit=0.03,
        ...     max_drawdown_limit=0.10
        ... )
        >>> # Check breakers before each trade
        >>> status = breaker.check_breakers(
        ...     current_portfolio_value=97000,
        ...     start_of_day_value=100000
        ... )
        >>> if status["trading_allowed"]:
        ...     # Execute trade
        ...     pass
    """

    def __init__(
        self,
        initial_portfolio_value: float,
        daily_loss_limit: float = 0.03,
        max_drawdown_limit: float = 0.10,
        consecutive_loss_limit: int = 5,
        volatility_threshold: float = 40.0,
        auto_reset_hours: int = 24,
        enable_alerts: bool = True,
    ):
        """
        Initialize circuit breaker system.

        Args:
            initial_portfolio_value: Starting portfolio value in dollars
            daily_loss_limit: Max daily loss % before halt (default 0.03 = 3%)
            max_drawdown_limit: Max drawdown % from peak before halt (default 0.10 = 10%)
            consecutive_loss_limit: Max consecutive losing trades before halt (default 5)
            volatility_threshold: VIX level to trigger volatility halt (default 40.0)
            auto_reset_hours: Hours before auto-reset (for certain breakers, default 24)
            enable_alerts: Enable alert logging (default True)

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if initial_portfolio_value <= 0:
            raise ValueError(
                f"Initial portfolio value must be positive, got {initial_portfolio_value}"
            )

        if not 0 < daily_loss_limit <= 1.0:
            raise ValueError(
                f"daily_loss_limit must be between 0 and 1, got {daily_loss_limit}"
            )

        if not 0 < max_drawdown_limit <= 1.0:
            raise ValueError(
                f"max_drawdown_limit must be between 0 and 1, got {max_drawdown_limit}"
            )

        if consecutive_loss_limit < 1:
            raise ValueError(
                f"consecutive_loss_limit must be >= 1, got {consecutive_loss_limit}"
            )

        if volatility_threshold <= 0:
            raise ValueError(
                f"volatility_threshold must be positive, got {volatility_threshold}"
            )

        if auto_reset_hours < 0:
            raise ValueError(
                f"auto_reset_hours must be non-negative, got {auto_reset_hours}"
            )

        # Core configuration
        self.initial_portfolio_value = initial_portfolio_value
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown_limit = max_drawdown_limit
        self.consecutive_loss_limit = consecutive_loss_limit
        self.volatility_threshold = volatility_threshold
        self.auto_reset_hours = auto_reset_hours
        self.enable_alerts = enable_alerts

        # State tracking
        self.peak_portfolio_value = initial_portfolio_value
        self.start_of_day_value: Optional[float] = None
        self.current_day: Optional[datetime] = None
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_trades = 0

        # Breaker states
        self.breaker_states: Dict[str, BreakerState] = {
            BreakerType.DAILY_LOSS.value: BreakerState.ARMED,
            BreakerType.MAX_DRAWDOWN.value: BreakerState.ARMED,
            BreakerType.CONSECUTIVE_LOSSES.value: BreakerState.ARMED,
            BreakerType.VOLATILITY_SPIKE.value: BreakerState.ARMED,
            BreakerType.MANUAL.value: BreakerState.ARMED,
        }

        # Trip tracking
        self.trip_times: Dict[str, Optional[datetime]] = {
            breaker.value: None for breaker in BreakerType
        }
        self.trip_reasons: Dict[str, Optional[str]] = {
            breaker.value: None for breaker in BreakerType
        }

        # Trade history for consecutive loss tracking
        self.recent_trades: List[Dict[str, Any]] = []

        # Confirmation codes for reset (security)
        self.active_confirmation_codes: Dict[str, str] = {}

        logger.info(
            f"CircuitBreaker initialized: daily_loss={daily_loss_limit:.1%}, "
            f"max_drawdown={max_drawdown_limit:.1%}, "
            f"consecutive_losses={consecutive_loss_limit}, VIX={volatility_threshold}"
        )

    def check_breakers(
        self,
        current_portfolio_value: float,
        start_of_day_value: Optional[float] = None,
        recent_trades: Optional[List[Dict]] = None,
        current_vix: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check all circuit breakers and return trading status.

        This is the PRIMARY method - call before EVERY trade to ensure
        trading is allowed. If ANY breaker is tripped, trading is halted.

        Args:
            current_portfolio_value: Current portfolio value
            start_of_day_value: Portfolio value at start of day (for daily loss calc)
            recent_trades: List of recent trade dicts with 'profit' or 'pnl' keys
            current_vix: Current VIX level (for volatility check)

        Returns:
            Dict with breaker status:
                {
                    "trading_allowed": bool,           # Can we trade?
                    "breakers_tripped": List[str],     # Which breakers are tripped
                    "reasons": List[str],              # Why each breaker tripped
                    "current_daily_loss_pct": float,   # Current daily loss %
                    "current_drawdown_pct": float,     # Current drawdown %
                    "consecutive_losses": int,         # Current losing streak
                    "current_vix": float or None,      # Current VIX level
                    "warnings": List[str],             # Near-threshold warnings
                }

        Raises:
            ValueError: If inputs are invalid (FAIL-SAFE: also trips breaker)
        """
        try:
            # Validate input
            if current_portfolio_value <= 0:
                raise ValueError(
                    f"Current portfolio value must be positive, got {current_portfolio_value}"
                )

            # Update peak portfolio value if we hit new high
            if current_portfolio_value > self.peak_portfolio_value:
                old_peak = self.peak_portfolio_value
                self.peak_portfolio_value = current_portfolio_value
                logger.info(
                    f"New portfolio peak: ${self.peak_portfolio_value:,.2f} "
                    f"(previous: ${old_peak:,.2f})"
                )

            # Update start of day if provided or new day
            self._update_start_of_day(start_of_day_value, current_portfolio_value)

            # Update trade history
            if recent_trades is not None:
                self._update_trade_history(recent_trades)

            # Check each breaker type
            breakers_tripped = []
            reasons = []
            warnings = []

            # 1. Daily Loss Breaker
            daily_result = self._check_daily_loss_breaker(current_portfolio_value)
            if daily_result["tripped"]:
                breakers_tripped.append(BreakerType.DAILY_LOSS.value)
                reasons.append(daily_result["reason"])
            if daily_result["warning"]:
                warnings.append(daily_result["warning"])

            # 2. Max Drawdown Breaker
            drawdown_result = self._check_max_drawdown_breaker(current_portfolio_value)
            if drawdown_result["tripped"]:
                breakers_tripped.append(BreakerType.MAX_DRAWDOWN.value)
                reasons.append(drawdown_result["reason"])
            if drawdown_result["warning"]:
                warnings.append(drawdown_result["warning"])

            # 3. Consecutive Losses Breaker
            consecutive_result = self._check_consecutive_losses_breaker()
            if consecutive_result["tripped"]:
                breakers_tripped.append(BreakerType.CONSECUTIVE_LOSSES.value)
                reasons.append(consecutive_result["reason"])
            if consecutive_result["warning"]:
                warnings.append(consecutive_result["warning"])

            # 4. Volatility Spike Breaker
            volatility_result = self._check_volatility_breaker(current_vix)
            if volatility_result["tripped"]:
                breakers_tripped.append(BreakerType.VOLATILITY_SPIKE.value)
                reasons.append(volatility_result["reason"])
            if volatility_result["warning"]:
                warnings.append(volatility_result["warning"])

            # 5. Manual Breaker (if manually tripped)
            if self.breaker_states[BreakerType.MANUAL.value] == BreakerState.TRIPPED:
                breakers_tripped.append(BreakerType.MANUAL.value)
                reasons.append(
                    self.trip_reasons.get(
                        BreakerType.MANUAL.value, "Manual halt triggered"
                    )
                )

            # Check for auto-reset eligibility
            self._check_auto_reset()

            # Determine if trading allowed
            trading_allowed = len(breakers_tripped) == 0

            # Alert if trading halted
            if not trading_allowed and self.enable_alerts:
                self._alert_trading_halted(breakers_tripped, reasons)

            return {
                "trading_allowed": trading_allowed,
                "breakers_tripped": breakers_tripped,
                "reasons": reasons,
                "current_daily_loss_pct": daily_result["current_loss_pct"],
                "current_drawdown_pct": drawdown_result["current_drawdown_pct"],
                "consecutive_losses": self.consecutive_losses,
                "current_vix": current_vix,
                "warnings": warnings,
            }

        except Exception as e:
            # FAIL-SAFE: If check fails, assume breaker is tripped
            logger.error(
                f"Circuit breaker check failed: {e}. Halting trading (FAIL-SAFE)"
            )
            return {
                "trading_allowed": False,
                "breakers_tripped": ["system_error"],
                "reasons": [f"Breaker check failed: {str(e)} (FAIL-SAFE halt)"],
                "current_daily_loss_pct": 0.0,
                "current_drawdown_pct": 0.0,
                "consecutive_losses": self.consecutive_losses,
                "current_vix": current_vix,
                "warnings": ["System error triggered fail-safe halt"],
            }

    def trip_breaker(
        self,
        breaker_type: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Manually trip a circuit breaker and halt trading.

        Use this for manual intervention or when external systems detect
        issues requiring immediate halt.

        Args:
            breaker_type: Type of breaker to trip (e.g., "manual", "daily_loss")
            reason: Detailed reason for tripping breaker

        Returns:
            Dict with trip details:
                {
                    "breaker_type": str,
                    "tripped": bool,
                    "trip_time": datetime,
                    "reason": str,
                    "confirmation_code": str,  # Needed to reset
                }

        Raises:
            ValueError: If breaker type is invalid
        """
        # Validate breaker type
        valid_types = [bt.value for bt in BreakerType]
        if breaker_type not in valid_types:
            raise ValueError(
                f"Invalid breaker_type: {breaker_type}. Must be one of {valid_types}"
            )

        # Trip the breaker
        self.breaker_states[breaker_type] = BreakerState.TRIPPED
        trip_time = datetime.now()
        self.trip_times[breaker_type] = trip_time
        self.trip_reasons[breaker_type] = reason

        # Generate confirmation code for reset
        confirmation_code = self._generate_confirmation_code(breaker_type)
        self.active_confirmation_codes[breaker_type] = confirmation_code

        # Log the trip
        logger.warning(
            f"CIRCUIT BREAKER TRIPPED: {breaker_type.upper()} - {reason} "
            f"(tripped at {trip_time.isoformat()})"
        )

        if self.enable_alerts:
            self._alert_breaker_tripped(breaker_type, reason, trip_time)

        return {
            "breaker_type": breaker_type,
            "tripped": True,
            "trip_time": trip_time,
            "reason": reason,
            "confirmation_code": confirmation_code,
        }

    def reset_breaker(
        self,
        breaker_type: str,
        confirmation_code: str,
        reset_reason: str = "Manual reset",
    ) -> Dict[str, Any]:
        """
        Reset a tripped circuit breaker with mandatory confirmation.

        This is the ONLY way to resume trading after a breaker trips.
        Requires the exact confirmation code generated during trip.

        Args:
            breaker_type: Type of breaker to reset
            confirmation_code: Confirmation code from trip_breaker()
            reset_reason: Reason for reset (for audit trail)

        Returns:
            Dict with reset details:
                {
                    "breaker_type": str,
                    "reset_successful": bool,
                    "reset_time": datetime,
                    "trip_duration": timedelta,
                    "reason": str,
                }

        Raises:
            ValueError: If breaker type invalid or not tripped
            PermissionError: If confirmation code is wrong
        """
        # Validate breaker type
        valid_types = [bt.value for bt in BreakerType]
        if breaker_type not in valid_types:
            raise ValueError(
                f"Invalid breaker_type: {breaker_type}. Must be one of {valid_types}"
            )

        # Check if breaker is tripped
        if self.breaker_states[breaker_type] != BreakerState.TRIPPED:
            raise ValueError(
                f"Breaker {breaker_type} is not tripped (state: {self.breaker_states[breaker_type].value})"
            )

        # Validate confirmation code
        expected_code = self.active_confirmation_codes.get(breaker_type)
        if expected_code is None:
            raise PermissionError(f"No confirmation code found for {breaker_type}")

        if confirmation_code != expected_code:
            logger.error(f"INVALID CONFIRMATION CODE for {breaker_type} reset attempt")
            raise PermissionError(
                f"Invalid confirmation code for {breaker_type}. Reset denied."
            )

        # Calculate trip duration
        trip_time = self.trip_times[breaker_type]
        reset_time = datetime.now()
        trip_duration = reset_time - trip_time if trip_time else timedelta(0)

        # Reset the breaker
        self.breaker_states[breaker_type] = BreakerState.ARMED
        self.trip_times[breaker_type] = None
        self.trip_reasons[breaker_type] = None
        del self.active_confirmation_codes[breaker_type]

        # Reset consecutive losses if that breaker was reset
        if breaker_type == BreakerType.CONSECUTIVE_LOSSES.value:
            old_losses = self.consecutive_losses
            self.consecutive_losses = 0
            logger.info(f"Reset consecutive losses from {old_losses} to 0")

        # Log the reset
        logger.info(
            f"CIRCUIT BREAKER RESET: {breaker_type.upper()} - {reset_reason} "
            f"(trip duration: {trip_duration})"
        )

        if self.enable_alerts:
            self._alert_breaker_reset(breaker_type, reset_reason, trip_duration)

        return {
            "breaker_type": breaker_type,
            "reset_successful": True,
            "reset_time": reset_time,
            "trip_duration": trip_duration,
            "reason": reset_reason,
        }

    def record_trade(
        self,
        profit_or_loss: float,
        trade_details: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a trade result for consecutive loss tracking.

        Args:
            profit_or_loss: Trade P&L (positive = profit, negative = loss)
            trade_details: Optional dict with additional trade details
        """
        is_win = profit_or_loss > 0

        if is_win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0  # Reset loss streak
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0  # Reset win streak

        self.total_trades += 1

        trade_record = {
            "timestamp": datetime.now(),
            "pnl": profit_or_loss,
            "is_win": is_win,
            "trade_number": self.total_trades,
        }

        if trade_details:
            trade_record.update(trade_details)

        self.recent_trades.append(trade_record)

        # Keep only last 100 trades
        if len(self.recent_trades) > 100:
            self.recent_trades = self.recent_trades[-100:]

        logger.debug(
            f"Trade recorded: {'WIN' if is_win else 'LOSS'} ${profit_or_loss:,.2f}, "
            f"consecutive_losses={self.consecutive_losses}"
        )

    def update_peak_portfolio_value(self, portfolio_value: float):
        """
        Manually update peak portfolio value (for drawdown calculation).

        Args:
            portfolio_value: New portfolio value to consider for peak

        Raises:
            ValueError: If portfolio value is invalid
        """
        if portfolio_value <= 0:
            raise ValueError(f"Portfolio value must be positive, got {portfolio_value}")

        if portfolio_value > self.peak_portfolio_value:
            old_peak = self.peak_portfolio_value
            self.peak_portfolio_value = portfolio_value
            logger.info(
                f"Peak portfolio value updated: ${old_peak:,.2f} -> ${portfolio_value:,.2f}"
            )

    def get_breaker_status(self) -> Dict[str, Any]:
        """
        Get current status of all circuit breakers.

        Returns:
            Dict with breaker status:
                {
                    "daily_loss": {...},
                    "max_drawdown": {...},
                    "consecutive_losses": {...},
                    "volatility_spike": {...},
                    "manual": {...},
                    "any_tripped": bool,
                    "trading_allowed": bool,
                }
        """
        status = {}

        for breaker_type in BreakerType:
            bt = breaker_type.value
            status[bt] = {
                "state": self.breaker_states[bt].value,
                "tripped": self.breaker_states[bt] == BreakerState.TRIPPED,
                "trip_time": self.trip_times[bt],
                "trip_reason": self.trip_reasons[bt],
                "has_confirmation_code": bt in self.active_confirmation_codes,
            }

        any_tripped = any(b["tripped"] for b in status.values())

        status["any_tripped"] = any_tripped
        status["trading_allowed"] = not any_tripped

        return status

    # Private helper methods

    def _check_daily_loss_breaker(
        self, current_portfolio_value: float
    ) -> Dict[str, Any]:
        """Check if daily loss limit breaker should trip."""
        # Skip if already tripped
        if self.breaker_states[BreakerType.DAILY_LOSS.value] == BreakerState.TRIPPED:
            return {
                "tripped": True,
                "reason": "Daily loss breaker already tripped",
                "current_loss_pct": 0.0,
                "warning": None,
            }

        # Need start of day value to calculate
        if self.start_of_day_value is None:
            return {
                "tripped": False,
                "reason": "",
                "current_loss_pct": 0.0,
                "warning": None,
            }

        # Calculate daily loss
        daily_pnl = current_portfolio_value - self.start_of_day_value
        daily_loss_pct = abs(daily_pnl / self.start_of_day_value)

        # Check if breaker should trip
        if daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit:
            reason = (
                f"Daily loss limit breached: {daily_loss_pct:.2%} loss "
                f"(limit: {self.daily_loss_limit:.2%}). "
                f"Portfolio: ${self.start_of_day_value:,.2f} -> ${current_portfolio_value:,.2f}"
            )
            self.trip_breaker(BreakerType.DAILY_LOSS.value, reason)
            return {
                "tripped": True,
                "reason": reason,
                "current_loss_pct": daily_loss_pct,
                "warning": None,
            }

        # Check for warning threshold (80% of limit)
        warning = None
        if daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit * 0.8:
            warning = (
                f"Approaching daily loss limit: {daily_loss_pct:.2%} "
                f"(limit: {self.daily_loss_limit:.2%})"
            )

        return {
            "tripped": False,
            "reason": "",
            "current_loss_pct": daily_loss_pct if daily_pnl < 0 else 0.0,
            "warning": warning,
        }

    def _check_max_drawdown_breaker(
        self, current_portfolio_value: float
    ) -> Dict[str, Any]:
        """Check if max drawdown breaker should trip."""
        # Skip if already tripped
        if self.breaker_states[BreakerType.MAX_DRAWDOWN.value] == BreakerState.TRIPPED:
            return {
                "tripped": True,
                "reason": "Max drawdown breaker already tripped",
                "current_drawdown_pct": 0.0,
                "warning": None,
            }

        # Calculate drawdown from peak
        drawdown = self.peak_portfolio_value - current_portfolio_value
        drawdown_pct = drawdown / self.peak_portfolio_value

        # Check if breaker should trip
        if drawdown_pct >= self.max_drawdown_limit:
            reason = (
                f"Max drawdown limit breached: {drawdown_pct:.2%} drawdown "
                f"(limit: {self.max_drawdown_limit:.2%}). "
                f"Peak: ${self.peak_portfolio_value:,.2f}, Current: ${current_portfolio_value:,.2f}"
            )
            self.trip_breaker(BreakerType.MAX_DRAWDOWN.value, reason)
            return {
                "tripped": True,
                "reason": reason,
                "current_drawdown_pct": drawdown_pct,
                "warning": None,
            }

        # Check for warning threshold (80% of limit)
        warning = None
        if drawdown_pct >= self.max_drawdown_limit * 0.8:
            warning = (
                f"Approaching max drawdown limit: {drawdown_pct:.2%} "
                f"(limit: {self.max_drawdown_limit:.2%})"
            )

        return {
            "tripped": False,
            "reason": "",
            "current_drawdown_pct": drawdown_pct,
            "warning": warning,
        }

    def _check_consecutive_losses_breaker(self) -> Dict[str, Any]:
        """Check if consecutive losses breaker should trip."""
        # Skip if already tripped
        if (
            self.breaker_states[BreakerType.CONSECUTIVE_LOSSES.value]
            == BreakerState.TRIPPED
        ):
            return {
                "tripped": True,
                "reason": "Consecutive losses breaker already tripped",
                "warning": None,
            }

        # Check if breaker should trip
        if self.consecutive_losses >= self.consecutive_loss_limit:
            reason = (
                f"Consecutive loss limit breached: {self.consecutive_losses} losses "
                f"(limit: {self.consecutive_loss_limit}). Strategy may be broken."
            )
            self.trip_breaker(BreakerType.CONSECUTIVE_LOSSES.value, reason)
            return {"tripped": True, "reason": reason, "warning": None}

        # Check for warning threshold (80% of limit)
        warning = None
        if self.consecutive_losses >= int(self.consecutive_loss_limit * 0.8):
            warning = (
                f"Approaching consecutive loss limit: {self.consecutive_losses} "
                f"(limit: {self.consecutive_loss_limit})"
            )

        return {"tripped": False, "reason": "", "warning": warning}

    def _check_volatility_breaker(self, current_vix: Optional[float]) -> Dict[str, Any]:
        """Check if volatility spike breaker should trip."""
        # Skip if already tripped
        if (
            self.breaker_states[BreakerType.VOLATILITY_SPIKE.value]
            == BreakerState.TRIPPED
        ):
            return {
                "tripped": True,
                "reason": "Volatility breaker already tripped",
                "warning": None,
            }

        # Skip if VIX not provided
        if current_vix is None:
            return {"tripped": False, "reason": "", "warning": None}

        # Validate VIX
        if current_vix < 0:
            logger.warning(f"Invalid VIX value: {current_vix}")
            return {"tripped": False, "reason": "", "warning": None}

        # Check if breaker should trip
        if current_vix >= self.volatility_threshold:
            reason = (
                f"Volatility spike detected: VIX={current_vix:.2f} "
                f"(threshold: {self.volatility_threshold:.2f}). Market conditions too volatile."
            )
            self.trip_breaker(BreakerType.VOLATILITY_SPIKE.value, reason)
            return {"tripped": True, "reason": reason, "warning": None}

        # Check for warning threshold (90% of limit)
        warning = None
        if current_vix >= self.volatility_threshold * 0.9:
            warning = (
                f"VIX approaching threshold: {current_vix:.2f} "
                f"(threshold: {self.volatility_threshold:.2f})"
            )

        return {"tripped": False, "reason": "", "warning": warning}

    def _check_auto_reset(self):
        """Check if any breakers are eligible for auto-reset."""
        if self.auto_reset_hours <= 0:
            return  # Auto-reset disabled

        now = datetime.now()
        reset_threshold = timedelta(hours=self.auto_reset_hours)

        # Only certain breakers can auto-reset
        auto_reset_eligible = [
            BreakerType.DAILY_LOSS.value,
            BreakerType.VOLATILITY_SPIKE.value,
        ]

        for breaker_type in auto_reset_eligible:
            if self.breaker_states[breaker_type] == BreakerState.TRIPPED:
                trip_time = self.trip_times[breaker_type]
                if trip_time and (now - trip_time) >= reset_threshold:
                    # Generate confirmation code for audit trail
                    code = self._generate_confirmation_code(breaker_type)
                    self.active_confirmation_codes[breaker_type] = code

                    # Auto-reset
                    try:
                        self.reset_breaker(
                            breaker_type,
                            code,
                            f"Auto-reset after {self.auto_reset_hours}h",
                        )
                        logger.info(
                            f"Auto-reset successful: {breaker_type} after {self.auto_reset_hours}h"
                        )
                    except Exception as e:
                        logger.error(f"Auto-reset failed for {breaker_type}: {e}")

    def _update_start_of_day(
        self, start_of_day_value: Optional[float], current_portfolio_value: float
    ):
        """Update start of day value for daily loss calculation."""
        now = datetime.now()

        # If new day, reset start of day value
        if self.current_day is None or now.date() > self.current_day.date():
            old_day = self.current_day
            self.current_day = now
            self.start_of_day_value = (
                start_of_day_value
                if start_of_day_value is not None
                else current_portfolio_value
            )
            logger.info(
                f"New trading day: {now.date().isoformat()}, "
                f"start value: ${self.start_of_day_value:,.2f} "
                f"(previous day: {old_day.date().isoformat() if old_day else 'N/A'})"
            )

            # Auto-reset daily loss breaker on new day
            if (
                self.breaker_states[BreakerType.DAILY_LOSS.value]
                == BreakerState.TRIPPED
            ):
                code = self._generate_confirmation_code(BreakerType.DAILY_LOSS.value)
                self.active_confirmation_codes[BreakerType.DAILY_LOSS.value] = code
                try:
                    self.reset_breaker(
                        BreakerType.DAILY_LOSS.value,
                        code,
                        "Auto-reset on new trading day",
                    )
                except Exception as e:
                    logger.error(f"Failed to auto-reset daily loss breaker: {e}")

        # If start of day provided, update it
        elif start_of_day_value is not None:
            self.start_of_day_value = start_of_day_value

    def _update_trade_history(self, recent_trades: List[Dict]):
        """Update trade history from external source."""
        if not recent_trades:
            return

        # Merge with existing trades (avoid duplicates)
        for trade in recent_trades:
            # Extract P&L from trade dict
            pnl = trade.get("pnl") or trade.get("profit") or trade.get("profit_loss")
            if pnl is not None:
                self.record_trade(pnl, trade)

    def _generate_confirmation_code(self, breaker_type: str) -> str:
        """Generate secure confirmation code for breaker reset."""
        # Create unique code using timestamp, breaker type, and random salt
        timestamp = datetime.now().isoformat()
        random_salt = secrets.token_hex(8)
        code_input = f"{breaker_type}:{timestamp}:{random_salt}"

        # Hash it for security
        code_hash = hashlib.sha256(code_input.encode()).hexdigest()

        # Return first 16 chars (sufficient for uniqueness)
        return code_hash[:16].upper()

    def _alert_trading_halted(self, breakers: List[str], reasons: List[str]):
        """Alert that trading has been halted."""
        logger.warning(
            f"{'='*60}\n"
            f"TRADING HALTED - CIRCUIT BREAKER(S) TRIPPED\n"
            f"{'='*60}\n"
            f"Breakers: {', '.join(breakers)}\n"
            f"Reasons:\n" + "\n".join(f"  - {r}" for r in reasons) + "\n"
            f"{'='*60}"
        )

    def _alert_breaker_tripped(
        self, breaker_type: str, reason: str, trip_time: datetime
    ):
        """Alert that a specific breaker tripped."""
        logger.warning(
            f"\n{'*'*60}\n"
            f"CIRCUIT BREAKER TRIPPED: {breaker_type.upper()}\n"
            f"Time: {trip_time.isoformat()}\n"
            f"Reason: {reason}\n"
            f"{'*'*60}\n"
        )

    def _alert_breaker_reset(self, breaker_type: str, reason: str, duration: timedelta):
        """Alert that a breaker was reset."""
        logger.info(
            f"\n{'+'*60}\n"
            f"CIRCUIT BREAKER RESET: {breaker_type.upper()}\n"
            f"Reason: {reason}\n"
            f"Trip Duration: {duration}\n"
            f"{'+'*60}\n"
        )
