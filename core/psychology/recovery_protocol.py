"""
Recovery Protocol - Gradual return to full position sizing for DeepStack

Manages recovery after significant losses through phased position sizing increases.
Requires hitting profit milestones before progressing through recovery phases,
ensuring trader has regained confidence and discipline.

Recovery Phases:
    1. Phase 1 (Conservative): 50% position sizing, extended holding periods
    2. Phase 2 (Cautious): 75% position sizing, normal holding periods
    3. Phase 3 (Full Recovery): 100% position sizing, normal operations

Progression Requirements:
    - Must hit profit targets at each phase
    - Must maintain minimum holding periods
    - Must avoid consecutive losses
    - Can be demoted back to earlier phase on poor performance

Example:
    >>> protocol = RecoveryProtocol(
    ...     entry_drawdown=0.12,
    ...     portfolio_value=88000
    ... )
    >>> # Record profitable trade
    >>> protocol.record_trade(profit_loss=500)
    >>> status = protocol.get_status()
    >>> print(f"Phase: {status['current_phase']}")
    >>> print(f"Position sizing: {status['position_size_multiplier']:.0%}")
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RecoveryPhase(Enum):
    """Recovery phases with increasing position sizes."""

    PHASE_1_CONSERVATIVE = "phase_1_conservative"  # 50% sizing
    PHASE_2_CAUTIOUS = "phase_2_cautious"  # 75% sizing
    PHASE_3_FULL_RECOVERY = "phase_3_full"  # 100% sizing


class RecoveryProtocol:
    """
    Manage gradual recovery after significant losses.

    Implements phased approach to returning to full position sizing after
    drawdowns. Each phase has specific position size limits and profit
    requirements before progression.

    Recovery Phases:
        - Phase 1: 50% sizing, need +3% profit to advance
        - Phase 2: 75% sizing, need +2% profit to advance
        - Phase 3: 100% sizing (full recovery)

    Example:
        >>> protocol = RecoveryProtocol(
        ...     entry_drawdown=0.15,
        ...     portfolio_value=85000
        ... )
        >>>
        >>> # Record trades during recovery
        >>> protocol.record_trade(profit_loss=1500)  # Profitable
        >>> protocol.record_trade(profit_loss=800)   # Profitable
        >>>
        >>> # Check if ready to advance
        >>> if protocol.can_advance_phase():
        ...     protocol.advance_phase()
        ...     print(f"Advanced to {protocol.current_phase.value}")
    """

    # Phase definitions
    PHASE_CONFIG = {
        RecoveryPhase.PHASE_1_CONSERVATIVE: {
            "position_multiplier": 0.50,
            "profit_target_pct": 0.03,  # 3% profit to advance
            "min_trades": 5,  # Minimum trades before advancing
            "max_consecutive_losses": 2,  # Max losses allowed
            "min_win_rate": 0.60,  # 60% win rate required
        },
        RecoveryPhase.PHASE_2_CAUTIOUS: {
            "position_multiplier": 0.75,
            "profit_target_pct": 0.02,  # 2% profit to advance
            "min_trades": 3,
            "max_consecutive_losses": 2,
            "min_win_rate": 0.60,
        },
        RecoveryPhase.PHASE_3_FULL_RECOVERY: {
            "position_multiplier": 1.00,
            "profit_target_pct": None,  # No target, fully recovered
            "min_trades": None,
            "max_consecutive_losses": None,
            "min_win_rate": None,
        },
    }

    def __init__(
        self,
        entry_drawdown: float,
        portfolio_value: float,
        starting_phase: RecoveryPhase = RecoveryPhase.PHASE_1_CONSERVATIVE,
        enable_logging: bool = True,
    ):
        """
        Initialize recovery protocol.

        Args:
            entry_drawdown: Drawdown that triggered recovery mode
            portfolio_value: Portfolio value at recovery start
            starting_phase: Initial recovery phase
            enable_logging: Whether to log recovery events
        """
        if not 0 <= entry_drawdown <= 1:
            raise ValueError("Entry drawdown must be between 0 and 1")

        self.entry_drawdown = entry_drawdown
        self.initial_portfolio_value = portfolio_value
        self.current_portfolio_value = portfolio_value
        self.current_phase = starting_phase
        self.enable_logging = enable_logging

        # Entry tracking
        self.recovery_started_at = datetime.now(timezone.utc)

        # Phase tracking
        self.phase_started_at = datetime.now(timezone.utc)
        self.phase_start_value = portfolio_value

        # Trade tracking for current phase
        self.phase_trades: List[Dict] = []
        self.phase_profit_loss = 0.0
        self.consecutive_losses = 0

        # Recovery history
        self.phase_history: List[Dict] = []
        self.all_trades: List[Dict] = []

        # Statistics
        self.total_phases_completed = 0
        self.phase_demotions = 0
        self.recovery_completed = False
        self.recovery_completed_at: Optional[datetime] = None

        # Record initial phase
        self._record_phase_entry()

        if self.enable_logging:
            logger.info(
                f"Recovery protocol initiated: Drawdown={entry_drawdown:.1%}, "
                f"Portfolio=${portfolio_value:,.2f}, "
                f"Starting phase={starting_phase.value}"
            )

    def record_trade(
        self,
        profit_loss: float,
        symbol: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict:
        """
        Record a trade during recovery period.

        Args:
            profit_loss: Profit or loss from trade (negative for loss)
            symbol: Stock symbol (optional)
            timestamp: Trade timestamp (default: now)

        Returns:
            Dictionary with current recovery status
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        trade = {
            "timestamp": timestamp,
            "symbol": symbol,
            "profit_loss": profit_loss,
            "phase": self.current_phase.value,
            "is_win": profit_loss > 0,
        }

        self.phase_trades.append(trade)
        self.all_trades.append(trade)
        self.phase_profit_loss += profit_loss

        # Update consecutive loss counter
        if profit_loss < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Update portfolio value
        self.current_portfolio_value += profit_loss

        # Check for phase demotion
        self._check_demotion()

        if self.enable_logging:
            logger.info(
                f"Recovery trade recorded: {symbol or 'Unknown'}, "
                f"P/L=${profit_loss:.2f}, "
                f"Phase={self.current_phase.value}, "
                f"Phase P/L=${self.phase_profit_loss:.2f}"
            )

        return self.get_status()

    def can_advance_phase(self) -> Dict:
        """
        Check if requirements are met to advance to next phase.

        Returns:
            Dictionary with advancement eligibility and reasons
        """
        if self.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY:
            return {
                "can_advance": False,
                "reason": "Already at full recovery",
                "requirements_met": {},
            }

        config = self.PHASE_CONFIG[self.current_phase]
        requirements_met = {}
        blocking_reasons = []

        # Check profit target
        phase_return = (
            self.phase_profit_loss / self.phase_start_value
            if self.phase_start_value > 0
            else 0
        )
        profit_target = config["profit_target_pct"]
        profit_met = phase_return >= profit_target
        requirements_met["profit_target"] = profit_met

        if not profit_met:
            blocking_reasons.append(
                f"Profit target not met: {phase_return:.1%} < {profit_target:.1%}"
            )

        # Check minimum trades
        min_trades = config["min_trades"]
        trades_met = len(self.phase_trades) >= min_trades
        requirements_met["min_trades"] = trades_met

        if not trades_met:
            blocking_reasons.append(
                f"Minimum trades not met: {len(self.phase_trades)} < {min_trades}"
            )

        # Check consecutive losses
        max_losses = config["max_consecutive_losses"]
        losses_ok = self.consecutive_losses <= max_losses
        requirements_met["consecutive_losses"] = losses_ok

        if not losses_ok:
            blocking_reasons.append(
                f"Too many consecutive losses: {self.consecutive_losses} > {max_losses}"
            )

        # Check win rate
        if self.phase_trades:
            wins = sum(1 for t in self.phase_trades if t["is_win"])
            win_rate = wins / len(self.phase_trades)
            min_win_rate = config["min_win_rate"]
            win_rate_met = win_rate >= min_win_rate
            requirements_met["win_rate"] = win_rate_met

            if not win_rate_met:
                blocking_reasons.append(
                    f"Win rate too low: {win_rate:.1%} < {min_win_rate:.1%}"
                )
        else:
            requirements_met["win_rate"] = False
            blocking_reasons.append("No trades yet")

        can_advance = all(requirements_met.values())

        return {
            "can_advance": can_advance,
            "requirements_met": requirements_met,
            "blocking_reasons": blocking_reasons if not can_advance else [],
            "current_phase": self.current_phase.value,
            "next_phase": self._get_next_phase().value if can_advance else None,
        }

    def advance_phase(self) -> bool:
        """
        Advance to next recovery phase if requirements are met.

        Returns:
            True if advancement successful, False otherwise
        """
        advancement_check = self.can_advance_phase()

        if not advancement_check["can_advance"]:
            if self.enable_logging:
                logger.warning(
                    f"Cannot advance phase: {advancement_check['blocking_reasons']}"
                )
            return False

        old_phase = self.current_phase
        self.current_phase = self._get_next_phase()

        # Record phase completion
        self._record_phase_completion(old_phase)

        # Reset phase tracking
        self.phase_started_at = datetime.now(timezone.utc)
        self.phase_start_value = self.current_portfolio_value
        self.phase_trades = []
        self.phase_profit_loss = 0.0
        self.consecutive_losses = 0

        self.total_phases_completed += 1

        # Record new phase entry
        self._record_phase_entry()

        # Check if full recovery achieved
        if self.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY:
            self._complete_recovery()

        if self.enable_logging:
            logger.info(
                f"Phase advanced: {old_phase.value} -> {self.current_phase.value}, "
                f"Portfolio=${self.current_portfolio_value:,.2f}"
            )

        return True

    def _get_next_phase(self) -> RecoveryPhase:
        """Get the next phase in recovery progression."""
        if self.current_phase == RecoveryPhase.PHASE_1_CONSERVATIVE:
            return RecoveryPhase.PHASE_2_CAUTIOUS
        elif self.current_phase == RecoveryPhase.PHASE_2_CAUTIOUS:
            return RecoveryPhase.PHASE_3_FULL_RECOVERY
        else:
            return RecoveryPhase.PHASE_3_FULL_RECOVERY

    def _check_demotion(self):
        """Check if performance warrants demotion to earlier phase."""
        # Don't demote from Phase 1 (already most conservative)
        if self.current_phase == RecoveryPhase.PHASE_1_CONSERVATIVE:
            return

        config = self.PHASE_CONFIG[self.current_phase]

        # Check if consecutive losses exceeded
        if self.consecutive_losses > config["max_consecutive_losses"] + 2:
            self._demote_phase("Excessive consecutive losses")
            return

        # Check if phase return is significantly negative
        if len(self.phase_trades) >= 3:
            phase_return = (
                self.phase_profit_loss / self.phase_start_value
                if self.phase_start_value > 0
                else 0
            )

            if phase_return < -0.03:  # -3% phase loss triggers demotion
                self._demote_phase(f"Phase loss too large: {phase_return:.1%}")
                return

    def _demote_phase(self, reason: str):
        """Demote to previous phase due to poor performance."""
        old_phase = self.current_phase

        if self.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY:
            self.current_phase = RecoveryPhase.PHASE_2_CAUTIOUS
        elif self.current_phase == RecoveryPhase.PHASE_2_CAUTIOUS:
            self.current_phase = RecoveryPhase.PHASE_1_CONSERVATIVE

        self.phase_demotions += 1

        # Reset phase tracking
        self.phase_started_at = datetime.now(timezone.utc)
        self.phase_start_value = self.current_portfolio_value
        self.phase_trades = []
        self.phase_profit_loss = 0.0
        self.consecutive_losses = 0

        # Record demotion
        self._record_phase_entry(demotion=True, reason=reason)

        if self.enable_logging:
            logger.warning(
                f"Phase demoted: {old_phase.value} -> {self.current_phase.value}. "
                f"Reason: {reason}"
            )

    def _complete_recovery(self):
        """Mark recovery as complete."""
        self.recovery_completed = True
        self.recovery_completed_at = datetime.now(timezone.utc)

        recovery_duration = self.recovery_completed_at - self.recovery_started_at
        total_return = (
            self.current_portfolio_value - self.initial_portfolio_value
        ) / self.initial_portfolio_value

        if self.enable_logging:
            logger.info(
                f"RECOVERY COMPLETED! Duration: {recovery_duration.days} days, "
                f"Total return from entry: {total_return:+.1%}, "
                f"Portfolio: ${self.current_portfolio_value:,.2f}"
            )

    def _record_phase_entry(self, demotion: bool = False, reason: Optional[str] = None):
        """Record entry into a new phase."""
        pass  # History is recorded in phase_history

    def _record_phase_completion(self, phase: RecoveryPhase):
        """Record completion of a phase."""
        phase_duration = datetime.now(timezone.utc) - self.phase_started_at
        phase_return = (
            self.phase_profit_loss / self.phase_start_value
            if self.phase_start_value > 0
            else 0
        )

        wins = sum(1 for t in self.phase_trades if t["is_win"])
        win_rate = wins / len(self.phase_trades) if self.phase_trades else 0

        record = {
            "phase": phase.value,
            "started_at": self.phase_started_at,
            "completed_at": datetime.now(timezone.utc),
            "duration_days": phase_duration.days,
            "start_value": self.phase_start_value,
            "end_value": self.current_portfolio_value,
            "profit_loss": self.phase_profit_loss,
            "return_pct": phase_return,
            "trades": len(self.phase_trades),
            "win_rate": win_rate,
        }

        self.phase_history.append(record)

    def get_position_size_multiplier(self) -> float:
        """
        Get current position size multiplier based on recovery phase.

        Returns:
            Multiplier (0.5, 0.75, or 1.0)
        """
        return self.PHASE_CONFIG[self.current_phase]["position_multiplier"]

    def get_status(self) -> Dict:
        """
        Get current recovery status.

        Returns:
            Dictionary with comprehensive recovery metrics
        """
        phase_duration = datetime.now(timezone.utc) - self.phase_started_at
        recovery_duration = datetime.now(timezone.utc) - self.recovery_started_at

        phase_return = (
            self.phase_profit_loss / self.phase_start_value
            if self.phase_start_value > 0
            else 0
        )

        total_return = (
            self.current_portfolio_value - self.initial_portfolio_value
        ) / self.initial_portfolio_value

        # Calculate win rate
        if self.phase_trades:
            wins = sum(1 for t in self.phase_trades if t["is_win"])
            win_rate = wins / len(self.phase_trades)
        else:
            win_rate = 0.0

        return {
            "in_recovery": not self.recovery_completed,
            "current_phase": self.current_phase.value,
            "position_size_multiplier": self.get_position_size_multiplier(),
            "entry_drawdown": self.entry_drawdown,
            "recovery_started_at": self.recovery_started_at,
            "recovery_duration_days": recovery_duration.days,
            "phase_started_at": self.phase_started_at,
            "phase_duration_days": phase_duration.days,
            "current_portfolio_value": self.current_portfolio_value,
            "initial_portfolio_value": self.initial_portfolio_value,
            "total_return": total_return,
            "phase_profit_loss": self.phase_profit_loss,
            "phase_return": phase_return,
            "phase_trades_count": len(self.phase_trades),
            "phase_win_rate": win_rate,
            "consecutive_losses": self.consecutive_losses,
            "advancement_check": self.can_advance_phase(),
            "phases_completed": self.total_phases_completed,
            "phase_demotions": self.phase_demotions,
            "recovery_completed": self.recovery_completed,
        }

    def get_statistics(self) -> Dict:
        """
        Get comprehensive recovery statistics.

        Returns:
            Dictionary with full recovery history and metrics
        """
        return {
            "entry_drawdown": self.entry_drawdown,
            "recovery_started_at": self.recovery_started_at,
            "recovery_completed": self.recovery_completed,
            "recovery_completed_at": self.recovery_completed_at,
            "current_phase": self.current_phase.value,
            "total_phases_completed": self.total_phases_completed,
            "phase_demotions": self.phase_demotions,
            "total_trades": len(self.all_trades),
            "initial_value": self.initial_portfolio_value,
            "current_value": self.current_portfolio_value,
            "total_return": (
                self.current_portfolio_value - self.initial_portfolio_value
            )
            / self.initial_portfolio_value,
            "phase_history": self.phase_history,
            "current_phase_status": self.get_status(),
        }

    def force_phase_advance(self, confirmation_code: str) -> bool:
        """
        Force advancement to next phase (requires confirmation).

        Args:
            confirmation_code: Must be "FORCE_ADVANCE" to confirm

        Returns:
            True if successful, False otherwise
        """
        if confirmation_code != "FORCE_ADVANCE":
            logger.warning("Force phase advance failed: Invalid confirmation code")
            return False

        if self.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY:
            logger.info("Force advance attempted but already at full recovery")
            return False

        old_phase = self.current_phase
        self.current_phase = self._get_next_phase()

        if self.enable_logging:
            logger.warning(
                f"Phase FORCE ADVANCED: {old_phase.value} -> {self.current_phase.value}"
            )

        # Reset phase tracking
        self.phase_started_at = datetime.now(timezone.utc)
        self.phase_start_value = self.current_portfolio_value
        self.phase_trades = []
        self.phase_profit_loss = 0.0
        self.consecutive_losses = 0

        return True

    def is_in_recovery(self) -> bool:
        """Check if still in recovery mode."""
        return not self.recovery_completed

    def get_max_position_size(self, base_size: float) -> float:
        """
        Calculate maximum position size with recovery adjustment.

        Args:
            base_size: Base position size (before recovery adjustment)

        Returns:
            Adjusted position size
        """
        return base_size * self.get_position_size_multiplier()
