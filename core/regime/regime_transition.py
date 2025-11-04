"""
Regime Transition Manager

Manages market regime transitions with whipsaw prevention and conviction requirements.
Tracks regime history and ensures smooth transitions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.regime.regime_detector import MarketRegime, RegimeDetection

logger = logging.getLogger(__name__)


@dataclass
class RegimeTransition:
    """A single regime transition event"""

    from_regime: MarketRegime
    to_regime: MarketRegime
    detection: RegimeDetection
    timestamp: datetime
    duration_in_previous: float  # Days in previous regime
    conviction_score: float  # Conviction behind transition (0-100)
    was_whipsaw: bool = False  # Flagged if reversed quickly
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "from_regime": self.from_regime.value,
            "to_regime": self.to_regime.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_in_previous": self.duration_in_previous,
            "conviction_score": self.conviction_score,
            "confidence": self.detection.confidence,
            "was_whipsaw": self.was_whipsaw,
            "metadata": self.metadata,
        }


@dataclass
class RegimeState:
    """Current regime state with tracking"""

    regime: MarketRegime
    entered_at: datetime
    last_detection: RegimeDetection
    consecutive_detections: int = 1  # Consecutive detections of this regime
    total_detections: int = 1  # Total detections while in this regime
    metadata: Dict[str, any] = field(default_factory=dict)

    def days_in_regime(self, current_time: datetime) -> float:
        """Calculate days in current regime"""
        delta = current_time - self.entered_at
        return delta.total_seconds() / 86400

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "regime": self.regime.value,
            "entered_at": self.entered_at.isoformat(),
            "days_in_regime": self.days_in_regime(datetime.now()),
            "consecutive_detections": self.consecutive_detections,
            "total_detections": self.total_detections,
            "current_confidence": self.last_detection.confidence,
            "metadata": self.metadata,
        }


class RegimeTransitionManager:
    """
    Manages regime transitions with whipsaw prevention.

    Features:
    - Conviction requirements before switching
    - Hysteresis to prevent whipsaws
    - Regime duration tracking
    - Historical transition analysis

    Whipsaw Prevention:
    1. Require N consecutive detections before switching
    2. Require minimum confidence threshold
    3. Require minimum time in regime before switching
    4. Higher bar for volatile transitions (BULL <-> BEAR)
    """

    def __init__(
        self,
        # Conviction requirements
        min_confidence: float = 70.0,  # Minimum confidence to switch
        min_consecutive_detections: int = 2,  # Consecutive detections needed
        min_days_in_regime: float = 2.0,  # Minimum days before switching
        # Hysteresis settings
        hysteresis_confidence_boost: float = 10.0,  # Extra confidence needed to switch back
        volatile_transition_multiplier: float = 1.5,  # Higher bar for volatile transitions
        # Whipsaw detection
        whipsaw_threshold_days: float = 5.0,  # Regime change reversed in <5 days = whipsaw
    ):
        """
        Initialize regime transition manager.

        Args:
            min_confidence: Minimum detection confidence to consider transition
            min_consecutive_detections: Consecutive detections needed before switching
            min_days_in_regime: Minimum days in regime before allowing switch
            hysteresis_confidence_boost: Extra confidence needed to switch back to previous regime
            volatile_transition_multiplier: Multiplier for volatile transition requirements
            whipsaw_threshold_days: Days threshold for whipsaw detection
        """
        self.min_confidence = min_confidence
        self.min_consecutive = min_consecutive_detections
        self.min_days = min_days_in_regime
        self.hysteresis_boost = hysteresis_confidence_boost
        self.volatile_multiplier = volatile_transition_multiplier
        self.whipsaw_threshold = whipsaw_threshold_days

        # State tracking
        self.current_state: Optional[RegimeState] = None
        self.transition_history: List[RegimeTransition] = []
        self.detection_buffer: List[RegimeDetection] = []  # Recent detections

        logger.info(
            f"RegimeTransitionManager initialized: min_conf={min_confidence}%, "
            f"min_consecutive={min_consecutive_detections}, "
            f"min_days={min_days_in_regime}"
        )

    def process_detection(
        self, detection: RegimeDetection
    ) -> Optional[RegimeTransition]:
        """
        Process new regime detection and determine if transition should occur.

        Args:
            detection: New regime detection

        Returns:
            RegimeTransition if transition occurred, None otherwise
        """
        # Initialize state if first detection
        if self.current_state is None:
            self._initialize_state(detection)
            return None

        # Add to detection buffer
        self.detection_buffer.append(detection)

        # Keep only recent detections (last 10)
        self.detection_buffer = self.detection_buffer[-10:]

        # Check if regime has changed
        if detection.regime == self.current_state.regime:
            # Same regime - update state
            self._update_same_regime(detection)
            return None

        # Different regime detected - check if we should transition
        should_transition, conviction = self._should_transition(detection)

        if should_transition:
            transition = self._execute_transition(detection, conviction)
            return transition
        else:
            logger.debug(
                f"Regime change detected ({self.current_state.regime.value} -> "
                f"{detection.regime.value}) but conviction insufficient "
                f"(confidence: {detection.confidence:.1f}%, conviction: {conviction:.1f}%)"
            )
            return None

    def _initialize_state(self, detection: RegimeDetection) -> None:
        """Initialize regime state with first detection"""
        self.current_state = RegimeState(
            regime=detection.regime,
            entered_at=detection.timestamp,
            last_detection=detection,
            consecutive_detections=1,
            total_detections=1,
        )

        logger.info(
            f"Regime state initialized: {detection.regime.value} "
            f"(confidence: {detection.confidence:.1f}%)"
        )

    def _update_same_regime(self, detection: RegimeDetection) -> None:
        """Update state for detection of same regime"""
        self.current_state.last_detection = detection
        self.current_state.total_detections += 1

        # Check if this continues a consecutive streak
        recent_detections = self.detection_buffer[-self.min_consecutive :]
        if all(d.regime == detection.regime for d in recent_detections):
            self.current_state.consecutive_detections = len(recent_detections)
        else:
            self.current_state.consecutive_detections = 1

        logger.debug(
            f"Same regime: {detection.regime.value} "
            f"(consecutive: {self.current_state.consecutive_detections}, "
            f"confidence: {detection.confidence:.1f}%)"
        )

    def _should_transition(self, detection: RegimeDetection) -> tuple[bool, float]:
        """
        Determine if we should transition to new regime.

        Returns:
            Tuple of (should_transition, conviction_score)
        """
        # Check minimum confidence
        required_confidence = self.min_confidence

        # Apply hysteresis - if switching back to previous regime, require higher confidence
        if len(self.transition_history) > 0:
            last_transition = self.transition_history[-1]
            if detection.regime == last_transition.from_regime:
                required_confidence += self.hysteresis_boost
                logger.debug(
                    f"Hysteresis applied: switching back to {detection.regime.value}, "
                    f"required confidence: {required_confidence:.1f}%"
                )

        # Check if transition is volatile (BULL <-> BEAR)
        is_volatile_transition = self._is_volatile_transition(
            self.current_state.regime, detection.regime
        )

        if is_volatile_transition:
            required_confidence *= self.volatile_multiplier
            logger.debug(
                f"Volatile transition ({self.current_state.regime.value} -> "
                f"{detection.regime.value}), required confidence: {required_confidence:.1f}%"
            )

        if detection.confidence < required_confidence:
            return False, detection.confidence

        # Check minimum time in current regime
        days_in_regime = self.current_state.days_in_regime(detection.timestamp)
        if days_in_regime < self.min_days:
            logger.debug(
                f"Insufficient time in regime: {days_in_regime:.1f} days "
                f"(min: {self.min_days:.1f})"
            )
            return False, detection.confidence

        # Check consecutive detections
        consecutive_new_regime = sum(
            1
            for d in self.detection_buffer[-self.min_consecutive :]
            if d.regime == detection.regime
        )

        if consecutive_new_regime < self.min_consecutive:
            logger.debug(
                f"Insufficient consecutive detections: {consecutive_new_regime} "
                f"(min: {self.min_consecutive})"
            )
            return False, detection.confidence

        # Calculate conviction score
        conviction = self._calculate_conviction(
            detection, days_in_regime, consecutive_new_regime
        )

        return True, conviction

    def _calculate_conviction(
        self, detection: RegimeDetection, days_in_regime: float, consecutive: int
    ) -> float:
        """
        Calculate conviction score for transition (0-100).

        Factors:
        - Detection confidence (50%)
        - Consecutive detections (30%)
        - Time in regime (20%)
        """
        # Confidence component (50 points)
        confidence_score = min(detection.confidence / 2, 50)

        # Consecutive detections component (30 points)
        consecutive_score = min((consecutive / self.min_consecutive) * 30, 30)

        # Time in regime component (20 points)
        # More time = higher conviction (up to 30 days)
        time_score = min((days_in_regime / 30) * 20, 20)

        conviction = confidence_score + consecutive_score + time_score

        return min(conviction, 100.0)

    def _execute_transition(
        self, detection: RegimeDetection, conviction: float
    ) -> RegimeTransition:
        """Execute regime transition and update state"""
        from_regime = self.current_state.regime
        to_regime = detection.regime

        days_in_previous = self.current_state.days_in_regime(detection.timestamp)

        transition = RegimeTransition(
            from_regime=from_regime,
            to_regime=to_regime,
            detection=detection,
            timestamp=detection.timestamp,
            duration_in_previous=days_in_previous,
            conviction_score=conviction,
            metadata={
                "consecutive_detections": len(
                    [d for d in self.detection_buffer if d.regime == to_regime]
                ),
                "detection_confidence": detection.confidence,
            },
        )

        # Check for potential whipsaw
        if len(self.transition_history) > 0:
            last_transition = self.transition_history[-1]
            days_since_last = (
                detection.timestamp - last_transition.timestamp
            ).total_seconds() / 86400

            if days_since_last < self.whipsaw_threshold:
                transition.was_whipsaw = True
                # Mark previous transition as whipsaw too
                last_transition.was_whipsaw = True
                logger.warning(
                    f"Potential whipsaw detected: {days_since_last:.1f} days since last transition"
                )

        # Add to history
        self.transition_history.append(transition)

        # Update current state
        self.current_state = RegimeState(
            regime=to_regime,
            entered_at=detection.timestamp,
            last_detection=detection,
            consecutive_detections=1,
            total_detections=1,
            metadata={"transition_conviction": conviction},
        )

        logger.info(
            f"REGIME TRANSITION: {from_regime.value} -> {to_regime.value} "
            f"(conviction: {conviction:.1f}%, confidence: {detection.confidence:.1f}%, "
            f"prev_duration: {days_in_previous:.1f} days)"
        )

        return transition

    def _is_volatile_transition(
        self, from_regime: MarketRegime, to_regime: MarketRegime
    ) -> bool:
        """Check if transition is volatile (BULL <-> BEAR or CRISIS)"""
        volatile_pairs = [
            (MarketRegime.BULL, MarketRegime.BEAR),
            (MarketRegime.BEAR, MarketRegime.BULL),
            (MarketRegime.BULL, MarketRegime.CRISIS),
            (MarketRegime.CRISIS, MarketRegime.BULL),
            (MarketRegime.BEAR, MarketRegime.CRISIS),
            (MarketRegime.CRISIS, MarketRegime.BEAR),
        ]

        return (from_regime, to_regime) in volatile_pairs

    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get current regime"""
        return self.current_state.regime if self.current_state else None

    def get_regime_duration(self, current_time: Optional[datetime] = None) -> float:
        """Get duration in current regime (days)"""
        if not self.current_state:
            return 0.0

        current_time = current_time or datetime.now()
        return self.current_state.days_in_regime(current_time)

    def get_transition_stats(self) -> Dict[str, any]:
        """Get statistics about regime transitions"""
        if not self.transition_history:
            return {
                "total_transitions": 0,
                "whipsaw_count": 0,
                "whipsaw_rate": 0.0,
                "avg_regime_duration": 0.0,
            }

        total = len(self.transition_history)
        whipsaws = sum(1 for t in self.transition_history if t.was_whipsaw)

        avg_duration = (
            sum(t.duration_in_previous for t in self.transition_history) / total
        )

        return {
            "total_transitions": total,
            "whipsaw_count": whipsaws,
            "whipsaw_rate": (whipsaws / total) * 100 if total > 0 else 0.0,
            "avg_regime_duration": avg_duration,
            "current_regime": (
                self.current_state.regime.value if self.current_state else None
            ),
            "days_in_current": self.get_regime_duration(),
        }

    def get_regime_history(self, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Get regime transition history.

        Args:
            limit: Maximum number of transitions to return (most recent)

        Returns:
            List of transition dictionaries
        """
        history = self.transition_history

        if limit:
            history = history[-limit:]

        return [t.to_dict() for t in history]

    def reset(self) -> None:
        """Reset transition manager state"""
        self.current_state = None
        self.transition_history = []
        self.detection_buffer = []

        logger.info("Regime transition manager reset")

    def validate_regime_stability(self, lookback_days: int = 30) -> Dict[str, any]:
        """
        Validate regime stability over lookback period.

        Returns:
            Dictionary with stability metrics
        """
        if not self.current_state:
            return {
                "is_stable": False,
                "regime": None,
                "reason": "No regime state",
            }

        # Get transitions in lookback period
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_transitions = [
            t for t in self.transition_history if t.timestamp >= cutoff_date
        ]

        # Check stability criteria
        is_stable = True
        reason = "Stable regime"

        # Too many transitions = unstable
        if len(recent_transitions) > 3:
            is_stable = False
            reason = f"Too many transitions ({len(recent_transitions)}) in {lookback_days} days"

        # Recent whipsaws = unstable
        recent_whipsaws = sum(1 for t in recent_transitions if t.was_whipsaw)
        if recent_whipsaws > 0:
            is_stable = False
            reason = f"{recent_whipsaws} whipsaws in last {lookback_days} days"

        # Low conviction on recent detections = unstable
        if self.current_state.last_detection.confidence < self.min_confidence:
            is_stable = False
            reason = (
                f"Low confidence ({self.current_state.last_detection.confidence:.1f}%)"
            )

        return {
            "is_stable": is_stable,
            "regime": self.current_state.regime.value,
            "confidence": self.current_state.last_detection.confidence,
            "days_in_regime": self.get_regime_duration(),
            "recent_transitions": len(recent_transitions),
            "recent_whipsaws": recent_whipsaws,
            "reason": reason,
        }
