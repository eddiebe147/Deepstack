"""
Drawdown Monitor - Track and prevent cascading losses for DeepStack

Monitors portfolio drawdowns in real-time and automatically reduces position sizes
at progressive thresholds to prevent catastrophic losses. Tracks recovery and
gradually restores position sizing when profitability returns.

Key Features:
    - Real-time peak-to-trough drawdown calculation
    - Progressive position size reduction (5%, 10%, 15%, 20% thresholds)
    - Automatic circuit breaker at 20% drawdown
    - Recovery tracking with gradual size restoration
    - Historical drawdown logging and statistics

Example:
    >>> monitor = DrawdownMonitor(initial_capital=100000)
    >>> status = monitor.update(current_value=95000)
    >>> print(f"Drawdown: {status['current_drawdown']:.1%}")
    >>> print(f"Position sizing: {status['position_size_multiplier']:.1%}")
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DrawdownMonitor:
    """
    Monitor portfolio drawdowns and automatically adjust position sizing
    to prevent cascading losses.

    Progressive Protection:
        - 0-5% drawdown: Full position sizing (100%)
        - 5-10% drawdown: Reduced sizing (75%)
        - 10-15% drawdown: Conservative sizing (50%)
        - 15-20% drawdown: Minimal sizing (25%)
        - 20%+ drawdown: Circuit breaker activated (0%)

    Example:
        >>> monitor = DrawdownMonitor(initial_capital=100000)
        >>> # Portfolio drops to $92,000
        >>> status = monitor.update(current_value=92000)
        >>> if status['circuit_breaker']:
        ...     print("Trading halted due to excessive drawdown")
        >>> else:
        ...     print(f"Use {status['position_size_multiplier']:.0%} sizing")
    """

    # Drawdown thresholds and corresponding position size multipliers
    THRESHOLDS = {
        0.05: 1.00,  # 0-5%: Full size
        0.10: 0.75,  # 5-10%: 75% size
        0.15: 0.50,  # 10-15%: 50% size
        0.20: 0.25,  # 15-20%: 25% size
    }

    # Circuit breaker threshold
    CIRCUIT_BREAKER_THRESHOLD = 0.20

    def __init__(
        self,
        initial_capital: float,
        enable_circuit_breaker: bool = True,
        recovery_profit_target: float = 0.03,
        enable_logging: bool = True,
    ):
        """
        Initialize drawdown monitor.

        Args:
            initial_capital: Starting portfolio value
            enable_circuit_breaker: Whether to halt trading at 20% drawdown
            recovery_profit_target: Profit required to exit recovery mode (3% default)
            enable_logging: Whether to log drawdown events
        """
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        self.initial_capital = initial_capital
        self.enable_circuit_breaker = enable_circuit_breaker
        self.recovery_profit_target = recovery_profit_target
        self.enable_logging = enable_logging

        # Track peak value (high-water mark)
        self.peak_value = initial_capital
        self.peak_timestamp = datetime.now(timezone.utc)

        # Current state
        self.current_value = initial_capital
        self.current_drawdown = 0.0
        self.position_size_multiplier = 1.0

        # Circuit breaker state
        self.circuit_breaker_active = False
        self.circuit_breaker_triggered_at: Optional[datetime] = None

        # Recovery tracking
        self.in_recovery = False
        self.recovery_start_value: Optional[float] = None
        self.recovery_start_time: Optional[datetime] = None

        # Historical tracking
        self.drawdown_history: List[Dict] = []
        self.max_drawdown = 0.0
        self.max_drawdown_timestamp: Optional[datetime] = None

        # Statistics
        self.total_updates = 0
        self.threshold_breaches = {threshold: 0 for threshold in self.THRESHOLDS.keys()}

        if self.enable_logging:
            logger.info(
                f"DrawdownMonitor initialized: capital=${initial_capital:,.2f}, "
                f"circuit_breaker={'enabled' if enable_circuit_breaker else 'disabled'}"
            )

    def update(self, current_value: float) -> Dict:
        """
        Update current portfolio value and recalculate drawdown.

        Args:
            current_value: Current portfolio value

        Returns:
            Status dictionary with drawdown metrics and position sizing
        """
        if current_value < 0:
            raise ValueError("Current value cannot be negative")

        self.total_updates += 1
        self.current_value = current_value

        # Update peak if new high
        if current_value > self.peak_value:
            self.peak_value = current_value
            self.peak_timestamp = datetime.now(timezone.utc)

            # Exit recovery if we hit new peak
            if self.in_recovery:
                self._complete_recovery()

        # Calculate current drawdown
        self.current_drawdown = (self.peak_value - current_value) / self.peak_value

        # Update max drawdown if necessary
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
            self.max_drawdown_timestamp = datetime.now(timezone.utc)

        # Determine position size multiplier
        previous_multiplier = self.position_size_multiplier
        self.position_size_multiplier = self._calculate_position_multiplier()

        # Check circuit breaker
        if (
            self.enable_circuit_breaker
            and self.current_drawdown >= self.CIRCUIT_BREAKER_THRESHOLD
            and not self.circuit_breaker_active
        ):
            self._activate_circuit_breaker()

        # Log threshold breaches
        if self.position_size_multiplier < previous_multiplier:
            self._log_threshold_breach()

        # Check for recovery opportunity
        if not self.in_recovery and self.current_drawdown > 0.05:
            self._enter_recovery()

        # Track drawdown history
        self._record_drawdown_snapshot()

        return self.get_status()

    def _calculate_position_multiplier(self) -> float:
        """Calculate position size multiplier based on current drawdown."""
        if self.circuit_breaker_active:
            return 0.0

        # Determine which range the drawdown falls into
        if self.current_drawdown >= 0.15:  # 15-20%
            return 0.25
        elif self.current_drawdown >= 0.10:  # 10-15%
            return 0.50
        elif self.current_drawdown >= 0.05:  # 5-10%
            return 0.75
        else:  # 0-5%
            return 1.0

    def _activate_circuit_breaker(self):
        """Activate circuit breaker to halt trading."""
        self.circuit_breaker_active = True
        self.circuit_breaker_triggered_at = datetime.now(timezone.utc)
        self.position_size_multiplier = 0.0

        if self.enable_logging:
            logger.critical(
                f"CIRCUIT BREAKER ACTIVATED: Drawdown {self.current_drawdown:.1%} "
                f"exceeds threshold {self.CIRCUIT_BREAKER_THRESHOLD:.1%}. "
                f"Trading halted. Portfolio: ${self.current_value:,.2f} "
                f"(Peak: ${self.peak_value:,.2f})"
            )

    def reset_circuit_breaker(self, confirmation_code: str) -> bool:
        """
        Manually reset circuit breaker (requires confirmation).

        Args:
            confirmation_code: Must be "RESET_TRADING" to confirm

        Returns:
            True if reset successful, False otherwise
        """
        if confirmation_code != "RESET_TRADING":
            logger.warning("Circuit breaker reset failed: Invalid confirmation code")
            return False

        if not self.circuit_breaker_active:
            logger.info("Circuit breaker reset attempted but not active")
            return False

        self.circuit_breaker_active = False
        self.position_size_multiplier = self._calculate_position_multiplier()

        if self.enable_logging:
            logger.warning(
                f"Circuit breaker manually reset. Current drawdown: {self.current_drawdown:.1%}, "
                f"Position sizing: {self.position_size_multiplier:.0%}"
            )

        return True

    def _enter_recovery(self):
        """Enter recovery mode after significant drawdown."""
        self.in_recovery = True
        self.recovery_start_value = self.current_value
        self.recovery_start_time = datetime.now(timezone.utc)

        if self.enable_logging:
            logger.info(
                f"Entering recovery mode: Current value=${self.current_value:,.2f}, "
                f"Drawdown={self.current_drawdown:.1%}, "
                f"Target={self.recovery_profit_target:.1%}"
            )

    def _complete_recovery(self):
        """Complete recovery and return to normal operation."""
        recovery_duration = None
        if self.recovery_start_time:
            recovery_duration = datetime.now(timezone.utc) - self.recovery_start_time

        if self.enable_logging:
            duration_str = (
                f"{recovery_duration.days}d {recovery_duration.seconds // 3600}h"
                if recovery_duration
                else "unknown"
            )
            logger.info(
                f"Recovery completed: New peak ${self.peak_value:,.2f}. "
                f"Duration: {duration_str}"
            )

        self.in_recovery = False
        self.recovery_start_value = None
        self.recovery_start_time = None

    def _log_threshold_breach(self):
        """Log when a new drawdown threshold is breached."""
        # Determine which threshold range was just breached
        if self.current_drawdown >= 0.15:
            self.threshold_breaches[0.20] += 1
        elif self.current_drawdown >= 0.10:
            self.threshold_breaches[0.15] += 1
        elif self.current_drawdown >= 0.05:
            self.threshold_breaches[0.10] += 1
        else:
            self.threshold_breaches[0.05] += 1

        if self.enable_logging:
            logger.warning(
                f"Drawdown threshold breached: {self.current_drawdown:.1%}. "
                f"Position sizing reduced to {self.position_size_multiplier:.0%}. "
                f"Current value: ${self.current_value:,.2f}"
            )

    def _record_drawdown_snapshot(self):
        """Record current drawdown state to history."""
        snapshot = {
            "timestamp": datetime.now(timezone.utc),
            "current_value": self.current_value,
            "peak_value": self.peak_value,
            "drawdown": self.current_drawdown,
            "position_multiplier": self.position_size_multiplier,
            "circuit_breaker_active": self.circuit_breaker_active,
            "in_recovery": self.in_recovery,
        }

        self.drawdown_history.append(snapshot)

        # Keep only last 1000 snapshots to prevent memory issues
        if len(self.drawdown_history) > 1000:
            self.drawdown_history = self.drawdown_history[-1000:]

    def get_status(self) -> Dict:
        """
        Get current drawdown status.

        Returns:
            Dictionary with current drawdown metrics
        """
        return {
            "current_value": self.current_value,
            "peak_value": self.peak_value,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "position_size_multiplier": self.position_size_multiplier,
            "circuit_breaker": self.circuit_breaker_active,
            "circuit_breaker_triggered_at": self.circuit_breaker_triggered_at,
            "in_recovery": self.in_recovery,
            "recovery_progress": self._calculate_recovery_progress(),
            "threshold_breaches": self.threshold_breaches.copy(),
            "total_updates": self.total_updates,
        }

    def _calculate_recovery_progress(self) -> Optional[float]:
        """Calculate recovery progress toward profit target."""
        if not self.in_recovery or self.recovery_start_value is None:
            return None

        gain_from_trough = (
            self.current_value - self.recovery_start_value
        ) / self.recovery_start_value
        progress = gain_from_trough / self.recovery_profit_target

        return min(progress, 1.0)  # Cap at 100%

    def get_statistics(self) -> Dict:
        """
        Get comprehensive drawdown statistics.

        Returns:
            Dictionary with historical metrics and statistics
        """
        return {
            "initial_capital": self.initial_capital,
            "current_value": self.current_value,
            "peak_value": self.peak_value,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_date": self.max_drawdown_timestamp,
            "total_return": (self.current_value - self.initial_capital)
            / self.initial_capital,
            "return_from_peak": (self.current_value - self.peak_value)
            / self.peak_value,
            "threshold_breaches": self.threshold_breaches.copy(),
            "circuit_breaker_triggers": (1 if self.circuit_breaker_triggered_at else 0),
            "in_recovery": self.in_recovery,
            "total_updates": self.total_updates,
            "history_size": len(self.drawdown_history),
        }

    def should_reduce_position_size(self) -> bool:
        """Check if position size should be reduced."""
        return self.position_size_multiplier < 1.0

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed (not circuit breaker)."""
        return not self.circuit_breaker_active

    def get_max_position_size(self, base_size: float) -> float:
        """
        Calculate maximum position size with drawdown adjustment.

        Args:
            base_size: Base position size (before drawdown adjustment)

        Returns:
            Adjusted position size
        """
        return base_size * self.position_size_multiplier
