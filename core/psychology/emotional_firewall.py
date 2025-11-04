"""
Emotional Firewall - Prevent impulsive trading patterns for DeepStack

Detects and blocks emotional trading behaviors including revenge trading,
overtrading, late-night trading, and loss-chasing. Enforces cooling-off
periods when suspicious patterns are detected.

Blocked Patterns:
    - Revenge trading: Trading within 30 minutes of a loss
    - Overtrading: More than 3 trades per hour or 10 per day
    - Win/loss streaks: 5+ consecutive wins/losses (heightened emotion)
    - Late night trading: After 8 PM EST
    - Weekend trading: Saturday/Sunday trading attempts
    - Position size increases after losses

Example:
    >>> firewall = EmotionalFirewall()
    >>> firewall.record_trade("AAPL", profit_loss=-500)
    >>> # Try to trade again immediately
    >>> if firewall.should_block_trade("TSLA"):
    ...     print("Blocked: Revenge trading detected")
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Deque, Dict, List, Optional

import pytz

logger = logging.getLogger(__name__)


class EmotionalPattern(Enum):
    """Types of emotional trading patterns."""

    REVENGE_TRADING = "revenge_trading"
    OVERTRADING = "overtrading"
    WIN_STREAK = "win_streak"
    LOSS_STREAK = "loss_streak"
    LATE_NIGHT = "late_night_trading"
    WEEKEND = "weekend_trading"
    SIZE_INCREASE_AFTER_LOSS = "size_increase_after_loss"


class EmotionalFirewall:
    """
    Firewall to detect and prevent emotional trading patterns.

    Monitors trading activity in real-time and blocks trades that match
    known emotional patterns. Enforces mandatory cooling-off periods to
    promote disciplined trading.

    Example:
        >>> firewall = EmotionalFirewall()
        >>>
        >>> # Record a losing trade
        >>> firewall.record_trade("AAPL", profit_loss=-1000)
        >>>
        >>> # Check if next trade should be blocked
        >>> result = firewall.should_block_trade("TSLA", position_size=5000)
        >>> if result["blocked"]:
        ...     print(f"Trade blocked: {result['reasons']}")
        ...     print(f"Cooldown expires: {result['cooldown_expires']}")
    """

    # Time thresholds
    REVENGE_WINDOW_MINUTES = 30  # Block trades within 30 min of loss
    HOURLY_TRADE_LIMIT = 3  # Max 3 trades per hour
    DAILY_TRADE_LIMIT = 10  # Max 10 trades per day
    LATE_NIGHT_HOUR = 20  # 8 PM EST
    EARLY_MORNING_HOUR = 6  # 6 AM EST

    # Streak thresholds
    LOSS_STREAK_LIMIT = 5  # Halt after 5 consecutive losses
    WIN_STREAK_LIMIT = 5  # Flag after 5 consecutive wins (overconfidence)

    # Cooling periods (minutes)
    REVENGE_COOLDOWN = 60  # 1 hour after loss
    OVERTRADING_COOLDOWN = 240  # 4 hours after overtrading
    STREAK_COOLDOWN = 180  # 3 hours after 5-trade streak
    LATE_NIGHT_COOLDOWN = 480  # 8 hours (until next morning)

    def __init__(
        self,
        enable_all_checks: bool = True,
        enable_late_night_check: bool = True,
        enable_weekend_check: bool = True,
        enable_revenge_check: bool = True,
        enable_overtrading_check: bool = True,
        enable_streak_check: bool = True,
        timezone_name: str = "America/New_York",
    ):
        """
        Initialize emotional firewall.

        Args:
            enable_all_checks: Master switch for all checks
            enable_late_night_check: Block late night trading
            enable_weekend_check: Block weekend trading
            enable_revenge_check: Block revenge trading
            enable_overtrading_check: Block rapid/excessive trading
            enable_streak_check: Block during win/loss streaks
            timezone_name: Timezone for time-based checks (default: EST)
        """
        self.enable_all_checks = enable_all_checks
        self.enable_late_night_check = enable_late_night_check
        self.enable_weekend_check = enable_weekend_check
        self.enable_revenge_check = enable_revenge_check
        self.enable_overtrading_check = enable_overtrading_check
        self.enable_streak_check = enable_streak_check

        try:
            self.timezone = pytz.timezone(timezone_name)
        except Exception:
            logger.warning(f"Invalid timezone {timezone_name}, using UTC")
            self.timezone = pytz.UTC

        # Trade history
        self.trade_history: Deque[Dict] = deque(maxlen=1000)

        # Recent trades for pattern detection
        self.recent_trades: Deque[Dict] = deque(maxlen=50)

        # Streak tracking
        self.current_streak_type: Optional[str] = None  # 'win' or 'loss'
        self.current_streak_count = 0

        # Cooldown tracking
        self.cooldown_expires_at: Optional[datetime] = None
        self.cooldown_reason: Optional[str] = None

        # Statistics
        self.total_trades = 0
        self.blocked_trades = 0
        self.blocks_by_pattern: Dict[EmotionalPattern, int] = {
            pattern: 0 for pattern in EmotionalPattern
        }

        logger.info(
            f"EmotionalFirewall initialized: "
            f"revenge_check={enable_revenge_check}, "
            f"overtrading_check={enable_overtrading_check}, "
            f"streak_check={enable_streak_check}, "
            f"timezone={timezone_name}"
        )

    def should_block_trade(
        self,
        symbol: str,
        position_size: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict:
        """
        Check if a trade should be blocked due to emotional patterns.

        Args:
            symbol: Stock symbol
            position_size: Proposed position size (for size increase check)
            timestamp: Trade timestamp (default: now)

        Returns:
            Dictionary with blocking decision and reasons
        """
        if not self.enable_all_checks:
            return {
                "blocked": False,
                "reasons": [],
                "patterns_detected": [],
                "cooldown_expires": None,
            }

        timestamp = timestamp or datetime.now(self.timezone)
        reasons = []
        patterns = []

        # Check active cooldown
        if self._is_in_cooldown(timestamp):
            reasons.append(f"Active cooldown: {self.cooldown_reason}")
            return {
                "blocked": True,
                "reasons": reasons,
                "patterns_detected": patterns,
                "cooldown_expires": self.cooldown_expires_at,
            }

        # Check weekend trading
        if self.enable_weekend_check and self._is_weekend(timestamp):
            patterns.append(EmotionalPattern.WEEKEND)
            reasons.append("Weekend trading blocked")

        # Check late night trading
        if self.enable_late_night_check and self._is_late_night(timestamp):
            patterns.append(EmotionalPattern.LATE_NIGHT)
            reasons.append(
                f"Late night trading blocked (after {self.LATE_NIGHT_HOUR}:00)"
            )

        # Check revenge trading
        if self.enable_revenge_check and self._is_revenge_trading(timestamp):
            patterns.append(EmotionalPattern.REVENGE_TRADING)
            reasons.append(
                f"Revenge trading detected (trade within {self.REVENGE_WINDOW_MINUTES} min of loss)"
            )

        # Check overtrading
        if self.enable_overtrading_check:
            overtrading = self._check_overtrading(timestamp)
            if overtrading["is_overtrading"]:
                patterns.append(EmotionalPattern.OVERTRADING)
                reasons.append(overtrading["reason"])

        # Check loss streak
        if (
            self.enable_streak_check
            and self.current_streak_type == "loss"
            and self.current_streak_count >= self.LOSS_STREAK_LIMIT
        ):
            patterns.append(EmotionalPattern.LOSS_STREAK)
            reasons.append(
                f"Loss streak: {self.current_streak_count} consecutive losses"
            )

        # Check win streak (overconfidence warning)
        if (
            self.enable_streak_check
            and self.current_streak_type == "win"
            and self.current_streak_count >= self.WIN_STREAK_LIMIT
        ):
            patterns.append(EmotionalPattern.WIN_STREAK)
            reasons.append(
                f"Win streak warning: {self.current_streak_count} consecutive wins (overconfidence risk)"
            )

        # Check position size increase after recent loss
        if position_size and self._is_size_increase_after_loss(position_size):
            patterns.append(EmotionalPattern.SIZE_INCREASE_AFTER_LOSS)
            reasons.append("Position size increase after loss (loss-chasing)")

        blocked = len(patterns) > 0

        if blocked:
            self.blocked_trades += 1
            for pattern in patterns:
                self.blocks_by_pattern[pattern] += 1

            # Set cooldown
            self._set_cooldown(patterns, timestamp)

            logger.warning(
                f"Trade blocked: {symbol}, Patterns: {[p.value for p in patterns]}, "
                f"Reasons: {reasons}"
            )

        return {
            "blocked": blocked,
            "reasons": reasons,
            "patterns_detected": [p.value for p in patterns],
            "cooldown_expires": self.cooldown_expires_at,
        }

    def record_trade(
        self,
        symbol: str,
        profit_loss: float,
        position_size: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Record a completed trade for pattern analysis.

        Args:
            symbol: Stock symbol
            profit_loss: Profit or loss from trade (negative for loss)
            position_size: Position size
            timestamp: Trade timestamp (default: now)
        """
        timestamp = timestamp or datetime.now(self.timezone)

        trade = {
            "symbol": symbol,
            "timestamp": timestamp,
            "profit_loss": profit_loss,
            "position_size": position_size,
            "is_win": profit_loss > 0,
        }

        self.trade_history.append(trade)
        self.recent_trades.append(trade)
        self.total_trades += 1

        # Update streak tracking
        self._update_streak(profit_loss > 0)

        logger.info(
            f"Trade recorded: {symbol}, P/L=${profit_loss:.2f}, "
            f"Streak: {self.current_streak_count} {self.current_streak_type or 'none'}"
        )

    def _is_weekend(self, timestamp: datetime) -> bool:
        """Check if timestamp falls on weekend."""
        return timestamp.weekday() >= 5  # Saturday=5, Sunday=6

    def _is_late_night(self, timestamp: datetime) -> bool:
        """Check if timestamp is during late night hours."""
        hour = timestamp.hour
        return hour >= self.LATE_NIGHT_HOUR or hour < self.EARLY_MORNING_HOUR

    def _is_revenge_trading(self, timestamp: datetime) -> bool:
        """Check if this is revenge trading (trade shortly after loss)."""
        if not self.recent_trades:
            return False

        # Find most recent losing trade
        last_loss = None
        for trade in reversed(self.recent_trades):
            if trade["profit_loss"] < 0:
                last_loss = trade
                break

        if last_loss is None:
            return False

        # Check if within revenge window
        time_since_loss = (timestamp - last_loss["timestamp"]).total_seconds() / 60
        return time_since_loss <= self.REVENGE_WINDOW_MINUTES

    def _check_overtrading(self, timestamp: datetime) -> Dict:
        """Check if trader is overtrading (too many trades too quickly)."""
        # Check hourly limit
        one_hour_ago = timestamp - timedelta(hours=1)
        recent_hour_trades = [
            t for t in self.recent_trades if t["timestamp"] > one_hour_ago
        ]

        if len(recent_hour_trades) >= self.HOURLY_TRADE_LIMIT:
            return {
                "is_overtrading": True,
                "reason": f"Hourly trade limit exceeded ({len(recent_hour_trades)} trades in last hour)",
            }

        # Check daily limit
        start_of_day = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        today_trades = [t for t in self.recent_trades if t["timestamp"] > start_of_day]

        if len(today_trades) >= self.DAILY_TRADE_LIMIT:
            return {
                "is_overtrading": True,
                "reason": f"Daily trade limit exceeded ({len(today_trades)} trades today)",
            }

        return {"is_overtrading": False, "reason": None}

    def _is_size_increase_after_loss(self, proposed_size: float) -> bool:
        """Check if position size is increasing after recent loss."""
        if not self.recent_trades:
            return False

        # Get last 3 trades
        recent = list(self.recent_trades)[-3:]

        # Check if any recent losses
        has_recent_loss = any(t["profit_loss"] < 0 for t in recent)
        if not has_recent_loss:
            return False

        # Get average position size from recent trades
        recent_sizes = [t["position_size"] for t in recent if t["position_size"]]
        if not recent_sizes:
            return False

        avg_size = sum(recent_sizes) / len(recent_sizes)

        # Check if proposed size is significantly larger (>20% increase)
        return proposed_size > avg_size * 1.2

    def _update_streak(self, is_win: bool):
        """Update win/loss streak tracking."""
        if self.current_streak_type is None:
            # Start new streak
            self.current_streak_type = "win" if is_win else "loss"
            self.current_streak_count = 1
        elif (is_win and self.current_streak_type == "win") or (
            not is_win and self.current_streak_type == "loss"
        ):
            # Continue current streak
            self.current_streak_count += 1
        else:
            # Streak broken, start new one
            self.current_streak_type = "win" if is_win else "loss"
            self.current_streak_count = 1

    def _is_in_cooldown(self, timestamp: datetime) -> bool:
        """Check if currently in cooldown period."""
        if self.cooldown_expires_at is None:
            return False

        return timestamp < self.cooldown_expires_at

    def _set_cooldown(self, patterns: List[EmotionalPattern], timestamp: datetime):
        """Set cooldown period based on detected patterns."""
        # Determine cooldown duration based on most severe pattern
        cooldown_minutes = 0

        if EmotionalPattern.LOSS_STREAK in patterns:
            cooldown_minutes = max(cooldown_minutes, self.STREAK_COOLDOWN)
            self.cooldown_reason = "Loss streak cooldown"
        elif EmotionalPattern.OVERTRADING in patterns:
            cooldown_minutes = max(cooldown_minutes, self.OVERTRADING_COOLDOWN)
            self.cooldown_reason = "Overtrading cooldown"
        elif EmotionalPattern.REVENGE_TRADING in patterns:
            cooldown_minutes = max(cooldown_minutes, self.REVENGE_COOLDOWN)
            self.cooldown_reason = "Revenge trading cooldown"
        elif EmotionalPattern.LATE_NIGHT in patterns:
            cooldown_minutes = max(cooldown_minutes, self.LATE_NIGHT_COOLDOWN)
            self.cooldown_reason = "Late night trading cooldown"
        elif EmotionalPattern.WIN_STREAK in patterns:
            cooldown_minutes = max(cooldown_minutes, self.STREAK_COOLDOWN)
            self.cooldown_reason = "Win streak cooldown (overconfidence)"

        self.cooldown_expires_at = timestamp + timedelta(minutes=cooldown_minutes)

        logger.info(
            f"Cooldown set: {self.cooldown_reason}, "
            f"expires at {self.cooldown_expires_at.strftime('%Y-%m-%d %H:%M')}"
        )

    def override_cooldown(self, confirmation_code: str) -> bool:
        """
        Manually override cooldown (requires confirmation).

        Args:
            confirmation_code: Must be "OVERRIDE_COOLDOWN" to confirm

        Returns:
            True if override successful, False otherwise
        """
        if confirmation_code != "OVERRIDE_COOLDOWN":
            logger.warning("Cooldown override failed: Invalid confirmation code")
            return False

        if self.cooldown_expires_at is None:
            logger.info("Cooldown override attempted but no active cooldown")
            return False

        logger.warning(
            f"Cooldown manually overridden: {self.cooldown_reason}. "
            f"Was set to expire at {self.cooldown_expires_at.strftime('%Y-%m-%d %H:%M')}"
        )

        self.cooldown_expires_at = None
        self.cooldown_reason = None

        return True

    def get_statistics(self) -> Dict:
        """
        Get comprehensive firewall statistics.

        Returns:
            Dictionary with blocking statistics and patterns
        """
        return {
            "total_trades": self.total_trades,
            "blocked_trades": self.blocked_trades,
            "block_rate": (
                self.blocked_trades / self.total_trades if self.total_trades > 0 else 0
            ),
            "current_streak": {
                "type": self.current_streak_type,
                "count": self.current_streak_count,
            },
            "blocks_by_pattern": {
                pattern.value: count
                for pattern, count in self.blocks_by_pattern.items()
            },
            "active_cooldown": self.cooldown_expires_at is not None,
            "cooldown_reason": self.cooldown_reason,
            "cooldown_expires": self.cooldown_expires_at,
            "recent_trades_count": len(self.recent_trades),
        }

    def reset_streak(self):
        """Manually reset win/loss streak counter."""
        logger.info(
            f"Streak manually reset: Was {self.current_streak_count} {self.current_streak_type}"
        )
        self.current_streak_type = None
        self.current_streak_count = 0

    def clear_history(self):
        """Clear trade history (useful for testing or new trading period)."""
        logger.info(
            f"Trade history cleared: {len(self.trade_history)} trades, "
            f"{self.blocked_trades} blocks"
        )
        self.trade_history.clear()
        self.recent_trades.clear()
        self.current_streak_type = None
        self.current_streak_count = 0
        self.total_trades = 0
        self.blocked_trades = 0
        self.blocks_by_pattern = {pattern: 0 for pattern in EmotionalPattern}
