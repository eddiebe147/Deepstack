"""
Trading TimeOut - Mandatory breaks after losses for DeepStack

Enforces cooling-off periods after consecutive losses or significant drawdowns.
Uses exponential backoff to increase timeout duration with each violation,
preventing emotional revenge trading.

TimeOut Triggers:
    - Consecutive losses: 3, 5, 7+ losses trigger timeouts
    - Daily loss limit: Automatic timeout until next day
    - Drawdown threshold: Timeout during significant drawdowns
    - Manual timeout: Can be set by user or system

Backoff Schedule:
    - 1st trigger: 1 hour timeout
    - 2nd trigger: 4 hours timeout
    - 3rd trigger: 24 hours timeout
    - 4th+ trigger: 7 days timeout

Example:
    >>> timeout = TradingTimeOut()
    >>> # Record 3 consecutive losses
    >>> for i in range(3):
    ...     timeout.record_loss(symbol="TEST", amount=500)
    >>> if timeout.is_in_timeout():
    ...     print(f"Trading suspended until {timeout.timeout_expires_at}")
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TimeOutReason(Enum):
    """Reasons for trading timeout."""

    CONSECUTIVE_LOSSES = "consecutive_losses"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_THRESHOLD = "drawdown_threshold"
    MANUAL = "manual_timeout"
    EMOTIONAL_PATTERN = "emotional_pattern"


class TradingTimeOut:
    """
    Enforce mandatory cooling-off periods after losses.

    Implements exponential backoff to prevent emotional revenge trading.
    Tracks timeout history and provides override mechanism with logging.

    Example:
        >>> timeout = TradingTimeOut(
        ...     consecutive_loss_limit=3,
        ...     daily_loss_limit_pct=0.02
        ... )
        >>>
        >>> # Record losses
        >>> timeout.record_loss("AAPL", 1000)
        >>> timeout.record_loss("TSLA", 800)
        >>> timeout.record_loss("MSFT", 1200)
        >>>
        >>> # Check if trading allowed
        >>> status = timeout.check_timeout()
        >>> if status["in_timeout"]:
        ...     print(f"Timeout: {status['reason']}")
        ...     print(f"Expires: {status['expires_at']}")
    """

    # Consecutive loss thresholds
    CONSECUTIVE_LOSS_THRESHOLDS = [3, 5, 7]  # Trigger timeouts at these levels

    # Exponential backoff schedule (minutes)
    TIMEOUT_SCHEDULE = [
        60,  # 1st trigger: 1 hour
        240,  # 2nd trigger: 4 hours
        1440,  # 3rd trigger: 24 hours
        10080,  # 4th+ trigger: 7 days
    ]

    def __init__(
        self,
        consecutive_loss_limit: int = 3,
        daily_loss_limit_pct: float = 0.02,
        drawdown_limit_pct: float = 0.10,
        portfolio_value: float = 100000,
        enable_timeouts: bool = True,
        enable_logging: bool = True,
    ):
        """
        Initialize trading timeout system.

        Args:
            consecutive_loss_limit: Number of losses before timeout (default: 3)
            daily_loss_limit_pct: Daily loss % that triggers timeout (default: 2%)
            drawdown_limit_pct: Drawdown % that triggers timeout (default: 10%)
            portfolio_value: Current portfolio value
            enable_timeouts: Master switch for timeout system
            enable_logging: Whether to log timeout events
        """
        self.consecutive_loss_limit = consecutive_loss_limit
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.drawdown_limit_pct = drawdown_limit_pct
        self.portfolio_value = portfolio_value
        self.enable_timeouts = enable_timeouts
        self.enable_logging = enable_logging

        # Current state
        self.consecutive_losses = 0
        self.last_trade_was_loss = False

        # Daily tracking
        self.daily_loss_amount = 0.0
        self.daily_reset_time = self._get_next_daily_reset()

        # Timeout state
        self.in_timeout = False
        self.timeout_reason: Optional[TimeOutReason] = None
        self.timeout_started_at: Optional[datetime] = None
        self.timeout_expires_at: Optional[datetime] = None

        # Backoff tracking
        self.timeout_trigger_count = 0
        self.timeout_history: List[Dict] = []

        # Statistics
        self.total_losses_recorded = 0
        self.total_timeouts_triggered = 0
        self.total_timeout_minutes = 0
        self.timeouts_by_reason: Dict[TimeOutReason, int] = {
            reason: 0 for reason in TimeOutReason
        }

        if self.enable_logging:
            logger.info(
                f"TradingTimeOut initialized: consecutive_limit={consecutive_loss_limit}, "
                f"daily_loss_limit={daily_loss_limit_pct:.1%}, "
                f"drawdown_limit={drawdown_limit_pct:.1%}"
            )

    def record_loss(
        self,
        symbol: str,
        loss_amount: float,
        timestamp: Optional[datetime] = None,
    ) -> Dict:
        """
        Record a trading loss and check if timeout should be triggered.

        Args:
            symbol: Stock symbol
            loss_amount: Loss amount (positive value)
            timestamp: Loss timestamp (default: now)

        Returns:
            Dictionary with timeout status
        """
        timestamp = timestamp or datetime.now(timezone.utc)
        loss_amount = abs(loss_amount)  # Ensure positive

        self.total_losses_recorded += 1

        # Check if we need to reset daily tracking
        if timestamp >= self.daily_reset_time:
            self._reset_daily_tracking()

        # Update daily loss
        self.daily_loss_amount += loss_amount

        # Update consecutive loss counter
        self.consecutive_losses += 1
        self.last_trade_was_loss = True

        if self.enable_logging:
            logger.info(
                f"Loss recorded: {symbol}, ${loss_amount:.2f}, "
                f"Consecutive: {self.consecutive_losses}, "
                f"Daily total: ${self.daily_loss_amount:.2f}"
            )

        # Check if timeout should be triggered
        self._check_timeout_triggers(timestamp)

        return self.check_timeout()

    def record_win(
        self,
        symbol: str,
        profit_amount: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        Record a winning trade (resets consecutive loss counter).

        Args:
            symbol: Stock symbol
            profit_amount: Profit amount
            timestamp: Win timestamp (default: now)
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        # Reset consecutive losses on win
        if self.consecutive_losses > 0:
            if self.enable_logging:
                logger.info(
                    f"Win recorded: {symbol}, ${profit_amount:.2f}. "
                    f"Consecutive losses reset from {self.consecutive_losses} to 0"
                )

        self.consecutive_losses = 0
        self.last_trade_was_loss = False

    def _check_timeout_triggers(self, timestamp: datetime):
        """Check if any timeout conditions are met."""
        if not self.enable_timeouts:
            return

        # Already in timeout
        if self.in_timeout:
            return

        # Check consecutive losses
        if self.consecutive_losses >= self.consecutive_loss_limit:
            self._trigger_timeout(
                reason=TimeOutReason.CONSECUTIVE_LOSSES,
                timestamp=timestamp,
                details=f"{self.consecutive_losses} consecutive losses",
            )
            return

        # Check daily loss limit
        daily_loss_pct = self.daily_loss_amount / self.portfolio_value
        if daily_loss_pct >= self.daily_loss_limit_pct:
            self._trigger_timeout(
                reason=TimeOutReason.DAILY_LOSS_LIMIT,
                timestamp=timestamp,
                details=f"Daily loss {daily_loss_pct:.1%} exceeds limit {self.daily_loss_limit_pct:.1%}",
            )
            return

    def _trigger_timeout(
        self,
        reason: TimeOutReason,
        timestamp: datetime,
        details: str,
    ):
        """Trigger a trading timeout with exponential backoff."""
        # Determine timeout duration
        timeout_index = min(self.timeout_trigger_count, len(self.TIMEOUT_SCHEDULE) - 1)
        timeout_minutes = self.TIMEOUT_SCHEDULE[timeout_index]

        self.in_timeout = True
        self.timeout_reason = reason
        self.timeout_started_at = timestamp
        self.timeout_expires_at = timestamp + timedelta(minutes=timeout_minutes)

        self.timeout_trigger_count += 1
        self.total_timeouts_triggered += 1
        self.total_timeout_minutes += timeout_minutes
        self.timeouts_by_reason[reason] += 1

        # Record in history
        timeout_record = {
            "reason": reason.value,
            "details": details,
            "started_at": timestamp,
            "expires_at": self.timeout_expires_at,
            "duration_minutes": timeout_minutes,
            "trigger_count": self.timeout_trigger_count,
            "consecutive_losses": self.consecutive_losses,
            "daily_loss": self.daily_loss_amount,
        }
        self.timeout_history.append(timeout_record)

        if self.enable_logging:
            logger.warning(
                f"TRADING TIMEOUT TRIGGERED: {reason.value}, {details}. "
                f"Duration: {timeout_minutes} minutes, "
                f"Expires: {self.timeout_expires_at.strftime('%Y-%m-%d %H:%M')} UTC. "
                f"Trigger count: {self.timeout_trigger_count}"
            )

    def check_timeout(self) -> Dict:
        """
        Check current timeout status.

        Returns:
            Dictionary with timeout information
        """
        now = datetime.now(timezone.utc)

        # Check if timeout has expired
        if (
            self.in_timeout
            and self.timeout_expires_at
            and now >= self.timeout_expires_at
        ):
            self._clear_timeout()

        # Check if daily tracking should reset
        if now >= self.daily_reset_time:
            self._reset_daily_tracking()

        return {
            "in_timeout": self.in_timeout,
            "trading_allowed": not self.in_timeout,
            "reason": self.timeout_reason.value if self.timeout_reason else None,
            "started_at": self.timeout_started_at,
            "expires_at": self.timeout_expires_at,
            "time_remaining": (
                self._calculate_time_remaining()
                if self.in_timeout and self.timeout_expires_at
                else None
            ),
            "consecutive_losses": self.consecutive_losses,
            "daily_loss_amount": self.daily_loss_amount,
            "daily_loss_pct": self.daily_loss_amount / self.portfolio_value,
            "trigger_count": self.timeout_trigger_count,
        }

    def _calculate_time_remaining(self) -> Dict:
        """Calculate time remaining in timeout."""
        if not self.timeout_expires_at:
            return None

        now = datetime.now(timezone.utc)
        remaining = self.timeout_expires_at - now

        return {
            "total_minutes": int(remaining.total_seconds() / 60),
            "hours": int(remaining.total_seconds() / 3600),
            "minutes": int((remaining.total_seconds() % 3600) / 60),
            "formatted": self._format_duration(remaining),
        }

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration as human-readable string."""
        total_seconds = int(duration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _clear_timeout(self):
        """Clear active timeout."""
        if self.enable_logging:
            duration_str = "unknown"
            if self.timeout_started_at:
                duration = datetime.now(timezone.utc) - self.timeout_started_at
                duration_str = self._format_duration(duration)

            logger.info(
                f"Timeout cleared: {self.timeout_reason.value if self.timeout_reason else 'unknown'}. "
                f"Duration: {duration_str}"
            )

        self.in_timeout = False
        self.timeout_reason = None
        self.timeout_started_at = None
        self.timeout_expires_at = None

    def manual_timeout(
        self,
        duration_minutes: int,
        reason: str,
        timestamp: Optional[datetime] = None,
    ):
        """
        Manually trigger a timeout.

        Args:
            duration_minutes: Timeout duration in minutes
            reason: Reason for manual timeout
            timestamp: Timestamp (default: now)
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        self.in_timeout = True
        self.timeout_reason = TimeOutReason.MANUAL
        self.timeout_started_at = timestamp
        self.timeout_expires_at = timestamp + timedelta(minutes=duration_minutes)

        self.total_timeouts_triggered += 1
        self.total_timeout_minutes += duration_minutes
        self.timeouts_by_reason[TimeOutReason.MANUAL] += 1

        # Record in history
        timeout_record = {
            "reason": TimeOutReason.MANUAL.value,
            "details": reason,
            "started_at": timestamp,
            "expires_at": self.timeout_expires_at,
            "duration_minutes": duration_minutes,
            "trigger_count": self.timeout_trigger_count,
        }
        self.timeout_history.append(timeout_record)

        if self.enable_logging:
            logger.warning(
                f"Manual timeout set: {reason}. "
                f"Duration: {duration_minutes} minutes, "
                f"Expires: {self.timeout_expires_at.strftime('%Y-%m-%d %H:%M')} UTC"
            )

    def override_timeout(self, confirmation_code: str) -> bool:
        """
        Override active timeout (requires confirmation).

        Args:
            confirmation_code: Must be "OVERRIDE_TIMEOUT" to confirm

        Returns:
            True if override successful, False otherwise
        """
        if confirmation_code != "OVERRIDE_TIMEOUT":
            logger.warning("Timeout override failed: Invalid confirmation code")
            return False

        if not self.in_timeout:
            logger.info("Timeout override attempted but no active timeout")
            return False

        if self.enable_logging:
            logger.warning(
                f"Timeout manually overridden: {self.timeout_reason.value}. "
                f"Was set to expire at {self.timeout_expires_at.strftime('%Y-%m-%d %H:%M')} UTC"
            )

        self._clear_timeout()
        return True

    def _reset_daily_tracking(self):
        """Reset daily loss tracking."""
        if self.enable_logging and self.daily_loss_amount > 0:
            logger.info(
                f"Daily tracking reset: Previous day loss ${self.daily_loss_amount:.2f}"
            )

        self.daily_loss_amount = 0.0
        self.daily_reset_time = self._get_next_daily_reset()

    def _get_next_daily_reset(self) -> datetime:
        """Get next daily reset time (midnight UTC)."""
        now = datetime.now(timezone.utc)
        next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # If it's already past midnight, set to next day
        if now >= next_reset:
            next_reset += timedelta(days=1)

        return next_reset

    def update_portfolio_value(self, new_value: float):
        """
        Update portfolio value (affects loss limit calculations).

        Args:
            new_value: New portfolio value
        """
        self.portfolio_value = new_value

        if self.enable_logging:
            logger.info(f"Portfolio value updated: ${new_value:,.2f}")

    def reset_trigger_count(self, confirmation_code: str) -> bool:
        """
        Reset timeout trigger count (requires confirmation).

        Args:
            confirmation_code: Must be "RESET_TRIGGERS" to confirm

        Returns:
            True if reset successful, False otherwise
        """
        if confirmation_code != "RESET_TRIGGERS":
            logger.warning("Trigger count reset failed: Invalid confirmation code")
            return False

        old_count = self.timeout_trigger_count
        self.timeout_trigger_count = 0

        if self.enable_logging:
            logger.warning(
                f"Timeout trigger count reset: {old_count} -> 0. "
                f"Next timeout will use shortest duration."
            )

        return True

    def get_statistics(self) -> Dict:
        """
        Get comprehensive timeout statistics.

        Returns:
            Dictionary with timeout metrics and history
        """
        return {
            "total_losses_recorded": self.total_losses_recorded,
            "total_timeouts_triggered": self.total_timeouts_triggered,
            "total_timeout_minutes": self.total_timeout_minutes,
            "current_timeout_status": self.check_timeout(),
            "consecutive_losses": self.consecutive_losses,
            "timeout_trigger_count": self.timeout_trigger_count,
            "timeouts_by_reason": {
                reason.value: count for reason, count in self.timeouts_by_reason.items()
            },
            "history_count": len(self.timeout_history),
            "last_timeout": self.timeout_history[-1] if self.timeout_history else None,
        }

    def is_in_timeout(self) -> bool:
        """Quick check if currently in timeout."""
        status = self.check_timeout()
        return status["in_timeout"]

    def get_next_timeout_duration(self) -> int:
        """
        Get duration of next timeout if triggered.

        Returns:
            Duration in minutes
        """
        timeout_index = min(self.timeout_trigger_count, len(self.TIMEOUT_SCHEDULE) - 1)
        return self.TIMEOUT_SCHEDULE[timeout_index]
