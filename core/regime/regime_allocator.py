"""
Regime-Based Allocation Manager

Adjusts strategy allocation based on detected market regime.
Includes blending logic for low-confidence regime transitions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from core.regime.regime_detector import MarketRegime, RegimeDetection

logger = logging.getLogger(__name__)


@dataclass
class AllocationConfig:
    """
    Strategy allocation configuration for a specific regime.

    Each strategy gets a target allocation percentage (0-100).
    Allocations should sum to 100% for a given regime.
    """

    regime: MarketRegime
    allocations: Dict[str, float]  # strategy_name -> allocation %
    cash_reserve: float = 0.0  # Cash reserve % (0-100)
    max_position_size: float = 10.0  # Max single position %
    min_position_size: float = 1.0  # Min single position %

    def __post_init__(self):
        """Validate allocation configuration"""
        if self.cash_reserve < 0 or self.cash_reserve > 100:
            raise ValueError("Cash reserve must be 0-100%")

        total_allocation = sum(self.allocations.values()) + self.cash_reserve
        if abs(total_allocation - 100.0) > 0.01:  # Allow small rounding errors
            raise ValueError(
                f"Allocations must sum to 100%, got {total_allocation:.2f}%"
            )

        if self.max_position_size <= 0 or self.max_position_size > 100:
            raise ValueError("Max position size must be 0-100%")

        if (
            self.min_position_size <= 0
            or self.min_position_size > self.max_position_size
        ):
            raise ValueError(f"Min position size must be 0-{self.max_position_size}%")

        for strategy, allocation in self.allocations.items():
            if allocation < 0 or allocation > 100:
                raise ValueError(
                    f"Allocation for {strategy} must be 0-100%, got {allocation}%"
                )


@dataclass
class RebalanceAction:
    """A single rebalance action for a strategy"""

    strategy: str
    current_allocation: float  # Current allocation %
    target_allocation: float  # Target allocation %
    delta: float  # Change needed (positive = increase, negative = decrease)
    priority: int = 1  # Execution priority (1 = highest)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "strategy": self.strategy,
            "current_allocation": self.current_allocation,
            "target_allocation": self.target_allocation,
            "delta": self.delta,
            "priority": self.priority,
        }


@dataclass
class RebalancePlan:
    """Complete rebalance plan for regime transition"""

    from_regime: MarketRegime
    to_regime: MarketRegime
    confidence: float  # Regime detection confidence
    actions: List[RebalanceAction]
    execute_gradually: bool  # Execute over time vs all at once
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    def total_turnover(self) -> float:
        """Calculate total portfolio turnover percentage"""
        return sum(abs(action.delta) for action in self.actions) / 2

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "from_regime": self.from_regime.value,
            "to_regime": self.to_regime.value,
            "confidence": self.confidence,
            "total_turnover": self.total_turnover(),
            "execute_gradually": self.execute_gradually,
            "timestamp": self.timestamp.isoformat(),
            "actions": [action.to_dict() for action in self.actions],
            "metadata": self.metadata,
        }


class RegimeBasedAllocator:
    """
    Regime-based strategy allocator.

    Manages strategy allocation based on market regime:
    - BULL: Aggressive growth strategies
    - BEAR: Defensive strategies, higher cash
    - SIDEWAYS: Mean reversion, options strategies
    - CRISIS: Maximum cash, capital preservation

    Features:
    - Blending logic for uncertain regimes
    - Gradual execution to avoid whipsaws
    - Position sizing constraints
    """

    def __init__(
        self,
        allocation_configs: Optional[Dict[MarketRegime, AllocationConfig]] = None,
        blend_threshold: float = 70.0,  # Blend if confidence < 70%
        gradual_threshold: float = 20.0,  # Gradual execution if turnover > 20%
        max_turnover_per_day: float = 10.0,  # Max 10% turnover per day
    ):
        """
        Initialize regime-based allocator.

        Args:
            allocation_configs: Allocation config for each regime
            blend_threshold: Confidence threshold for blending
            gradual_threshold: Turnover threshold for gradual execution
            max_turnover_per_day: Maximum daily turnover percentage
        """
        self.allocation_configs = allocation_configs or self._default_allocations()
        self.blend_threshold = blend_threshold
        self.gradual_threshold = gradual_threshold
        self.max_turnover_per_day = max_turnover_per_day

        logger.info(
            f"RegimeBasedAllocator initialized with {len(self.allocation_configs)} "
            f"regime configs"
        )

    def _default_allocations(self) -> Dict[MarketRegime, AllocationConfig]:
        """
        Create default allocation configurations.

        BULL: Aggressive growth
        BEAR: Defensive + cash
        SIDEWAYS: Mean reversion + options
        CRISIS: Maximum capital preservation
        """
        return {
            MarketRegime.BULL: AllocationConfig(
                regime=MarketRegime.BULL,
                allocations={
                    "deep_value": 40.0,
                    "growth": 30.0,
                    "squeeze_hunter": 20.0,
                    "momentum": 10.0,
                },
                cash_reserve=0.0,
                max_position_size=10.0,
                min_position_size=2.0,
            ),
            MarketRegime.BEAR: AllocationConfig(
                regime=MarketRegime.BEAR,
                allocations={
                    "deep_value": 30.0,
                    "defensive": 25.0,
                    "puts": 15.0,
                },
                cash_reserve=30.0,  # 30% cash in bear market
                max_position_size=8.0,
                min_position_size=1.5,
            ),
            MarketRegime.SIDEWAYS: AllocationConfig(
                regime=MarketRegime.SIDEWAYS,
                allocations={
                    "deep_value": 35.0,
                    "mean_reversion": 25.0,
                    "iron_condor": 15.0,
                    "pairs_trading": 15.0,
                },
                cash_reserve=10.0,
                max_position_size=8.0,
                min_position_size=2.0,
            ),
            MarketRegime.CRISIS: AllocationConfig(
                regime=MarketRegime.CRISIS,
                allocations={
                    "deep_value": 20.0,  # Only best opportunities
                    "defensive": 20.0,
                    "puts": 10.0,
                },
                cash_reserve=50.0,  # 50% cash in crisis
                max_position_size=5.0,
                min_position_size=1.0,
            ),
        }

    def calculate_target_allocation(
        self, detection: RegimeDetection
    ) -> Dict[str, float]:
        """
        Calculate target allocation based on regime detection.

        If confidence is high (>= threshold), use pure regime allocation.
        If confidence is low (< threshold), blend current and target regimes.

        Args:
            detection: Regime detection result

        Returns:
            Dictionary of strategy -> target allocation %
        """
        regime = detection.regime
        confidence = detection.confidence

        # Get base allocation for detected regime
        base_config = self.allocation_configs.get(regime)
        if not base_config:
            logger.warning(f"No allocation config for {regime.value}, using defaults")
            base_config = self._default_allocations()[regime]

        # High confidence - use pure allocation
        if confidence >= self.blend_threshold:
            logger.info(
                f"High confidence ({confidence:.1f}%), using pure {regime.value} allocation"
            )
            return base_config.allocations.copy()

        # Low confidence - blend with neutral (SIDEWAYS) allocation
        logger.info(
            f"Low confidence ({confidence:.1f}%), blending {regime.value} with SIDEWAYS"
        )

        neutral_config = self.allocation_configs[MarketRegime.SIDEWAYS]

        # Blend factor: 0 (all neutral) to 1 (all detected regime)
        blend_factor = confidence / self.blend_threshold

        # Blend allocations
        all_strategies = set(base_config.allocations.keys()) | set(
            neutral_config.allocations.keys()
        )

        blended = {}
        for strategy in all_strategies:
            base_alloc = base_config.allocations.get(strategy, 0.0)
            neutral_alloc = neutral_config.allocations.get(strategy, 0.0)
            blended[strategy] = base_alloc * blend_factor + neutral_alloc * (
                1 - blend_factor
            )

        return blended

    def create_rebalance_plan(
        self,
        detection: RegimeDetection,
        current_allocations: Dict[str, float],
        current_regime: Optional[MarketRegime] = None,
    ) -> RebalancePlan:
        """
        Create rebalance plan for regime transition.

        Args:
            detection: New regime detection
            current_allocations: Current strategy allocations (%)
            current_regime: Current regime (if known)

        Returns:
            Rebalance plan with actions
        """
        target_allocations = self.calculate_target_allocation(detection)

        # Calculate rebalance actions
        actions = []
        all_strategies = set(current_allocations.keys()) | set(
            target_allocations.keys()
        )

        for strategy in all_strategies:
            current = current_allocations.get(strategy, 0.0)
            target = target_allocations.get(strategy, 0.0)
            delta = target - current

            # Only create action if meaningful change (>0.5%)
            if abs(delta) > 0.5:
                # Priority: Reduce positions first (1), then increase (2)
                priority = 1 if delta < 0 else 2

                action = RebalanceAction(
                    strategy=strategy,
                    current_allocation=current,
                    target_allocation=target,
                    delta=delta,
                    priority=priority,
                )
                actions.append(action)

        # Sort by priority
        actions.sort(key=lambda a: (a.priority, abs(a.delta)), reverse=True)

        # Determine if gradual execution needed
        total_turnover = sum(abs(a.delta) for a in actions) / 2
        execute_gradually = total_turnover > self.gradual_threshold

        plan = RebalancePlan(
            from_regime=current_regime or MarketRegime.SIDEWAYS,
            to_regime=detection.regime,
            confidence=detection.confidence,
            actions=actions,
            execute_gradually=execute_gradually,
            timestamp=detection.timestamp,
            metadata={
                "total_turnover": total_turnover,
                "num_actions": len(actions),
                "blend_applied": detection.confidence < self.blend_threshold,
            },
        )

        logger.info(
            f"Rebalance plan created: {current_regime} -> {detection.regime.value}, "
            f"{len(actions)} actions, {total_turnover:.1f}% turnover, "
            f"gradual: {execute_gradually}"
        )

        return plan

    def execute_gradual_rebalance(
        self, plan: RebalancePlan, days: int = 5
    ) -> List[Dict[str, float]]:
        """
        Execute rebalance plan gradually over multiple days.

        Args:
            plan: Rebalance plan to execute
            days: Number of days to spread execution

        Returns:
            List of daily allocation adjustments
        """
        if not plan.execute_gradually:
            logger.info("Plan doesn't require gradual execution")
            return [{action.strategy: action.delta for action in plan.actions}]

        # Calculate daily maximum turnover
        total_turnover = plan.total_turnover()
        daily_max_turnover = min(self.max_turnover_per_day, total_turnover / days)

        daily_adjustments = []

        # Create copy of actions to track remaining deltas
        remaining_actions = [
            RebalanceAction(
                strategy=a.strategy,
                current_allocation=a.current_allocation,
                target_allocation=a.target_allocation,
                delta=a.delta,
                priority=a.priority,
            )
            for a in plan.actions
        ]

        for day in range(days):
            day_adjustments = {}
            day_turnover = 0.0

            # Process actions by priority until daily limit reached
            for action in remaining_actions:
                if abs(action.delta) < 0.01:  # Already executed
                    continue

                # Calculate how much we can execute today
                available_turnover = daily_max_turnover - day_turnover

                if available_turnover < 0.5:  # Not enough room
                    break

                # Execute portion of delta
                execute_amount = action.delta
                if abs(execute_amount) > available_turnover:
                    execute_amount = (
                        available_turnover if action.delta > 0 else -available_turnover
                    )

                day_adjustments[action.strategy] = execute_amount
                day_turnover += abs(execute_amount)
                action.delta -= execute_amount

            daily_adjustments.append(day_adjustments)

            logger.debug(
                f"Day {day + 1}: {len(day_adjustments)} adjustments, "
                f"{day_turnover:.1f}% turnover"
            )

            # Check if we're done
            remaining_total = sum(abs(a.delta) for a in remaining_actions)
            if remaining_total < 0.5:
                logger.info(f"Gradual rebalance completed in {day + 1} days")
                break

        return daily_adjustments

    def get_position_sizing_constraints(self, regime: MarketRegime) -> Dict[str, float]:
        """
        Get position sizing constraints for a regime.

        Returns:
            Dictionary with max_position_size, min_position_size, cash_reserve
        """
        config = self.allocation_configs.get(regime)
        if not config:
            config = self._default_allocations()[regime]

        return {
            "max_position_size": config.max_position_size,
            "min_position_size": config.min_position_size,
            "cash_reserve": config.cash_reserve,
        }

    def validate_allocation(
        self, allocations: Dict[str, float], regime: MarketRegime
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that allocation adheres to regime constraints.

        Args:
            allocations: Strategy allocations to validate
            regime: Current regime

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = self.allocation_configs.get(regime)
        if not config:
            return False, f"No configuration for regime {regime.value}"

        # Check total allocation
        total = sum(allocations.values())
        if abs(total - 100.0) > 0.01:
            return False, f"Total allocation must be 100%, got {total:.2f}%"

        # Check individual position sizes
        for strategy, allocation in allocations.items():
            if allocation > config.max_position_size:
                return (
                    False,
                    f"{strategy} allocation {allocation:.1f}% exceeds max "
                    f"{config.max_position_size:.1f}%",
                )

            if allocation > 0 and allocation < config.min_position_size:
                return (
                    False,
                    f"{strategy} allocation {allocation:.1f}% below min "
                    f"{config.min_position_size:.1f}%",
                )

        return True, None
