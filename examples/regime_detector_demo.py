"""
Market Regime Detection Demo

Demonstrates the complete regime detection system including:
1. Basic regime detection
2. Allocation management
3. Transition handling
4. Historical validation
5. Real-world scenarios
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

from core.regime import (
    MarketRegime,
    RegimeBasedAllocator,
    RegimeDetection,
    RegimeDetector,
    RegimeFactors,
    RegimeTransitionManager,
)


def print_section(title: str):
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_1_basic_detection():
    """Demo 1: Basic regime detection"""
    print_section("Demo 1: Basic Regime Detection")

    detector = RegimeDetector()

    # Example 1: Bull market conditions
    print("1. BULL MARKET CONDITIONS:")
    print("   - Golden cross (price > SMA50 > SMA200)")
    print("   - Low VIX (12)")
    print("   - Positive breadth\n")

    bull_factors = RegimeFactors(
        sma_50=4500.0,
        sma_200=4300.0,
        adx=28.0,
        price=4600.0,
        vix=12.0,
        realized_volatility=0.10,
        advance_decline_ratio=2.0,
        new_highs_lows_ratio=3.0,
        correlation=0.35,
        timestamp=datetime.now(),
    )

    detection = detector.detect_regime(bull_factors)
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Factor Scores:")
    for factor, score in detection.factor_scores.items():
        print(f"     - {factor}: {score:.1f}")

    # Example 2: Bear market conditions
    print("\n2. BEAR MARKET CONDITIONS:")
    print("   - Death cross (price < SMA50 < SMA200)")
    print("   - Elevated VIX (30)")
    print("   - Negative breadth\n")

    bear_factors = RegimeFactors(
        sma_50=4200.0,
        sma_200=4400.0,
        adx=35.0,
        price=4000.0,
        vix=30.0,
        realized_volatility=0.25,
        advance_decline_ratio=0.6,
        new_highs_lows_ratio=0.4,
        correlation=0.75,
        timestamp=datetime.now(),
    )

    detection = detector.detect_regime(bear_factors)
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Factor Scores:")
    for factor, score in detection.factor_scores.items():
        print(f"     - {factor}: {score:.1f}")

    # Example 3: Crisis conditions
    print("\n3. CRISIS CONDITIONS:")
    print("   - Extreme VIX (55)")
    print("   - Panic selling")
    print("   - Very high correlation\n")

    crisis_factors = RegimeFactors(
        sma_50=3800.0,
        sma_200=4000.0,
        adx=45.0,
        price=3200.0,
        vix=55.0,
        realized_volatility=0.50,
        advance_decline_ratio=0.2,
        new_highs_lows_ratio=0.1,
        correlation=0.95,
        timestamp=datetime.now(),
    )

    detection = detector.detect_regime(crisis_factors)
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")


def demo_2_allocation_management():
    """Demo 2: Regime-based allocation"""
    print_section("Demo 2: Regime-Based Allocation Management")

    allocator = RegimeBasedAllocator()

    # Show default allocations for each regime
    print("DEFAULT ALLOCATIONS BY REGIME:\n")

    for regime in MarketRegime:
        config = allocator.allocation_configs[regime]
        print(f"{regime.value} Market:")
        for strategy, allocation in config.allocations.items():
            print(f"  {strategy:20s}: {allocation:5.1f}%")
        print(f"  {'Cash Reserve':20s}: {config.cash_reserve:5.1f}%")
        print(f"  Max Position Size: {config.max_position_size:.1f}%")
        print(f"  Min Position Size: {config.min_position_size:.1f}%\n")


def demo_3_transition_management():
    """Demo 3: Regime transition with whipsaw prevention"""
    print_section("Demo 3: Regime Transition Management")

    manager = RegimeTransitionManager(
        min_confidence=70.0,
        min_consecutive_detections=2,
        min_days_in_regime=2.0,
    )

    print("SCENARIO: Transition from BULL to BEAR")
    print("----------------------------------------\n")

    # Initialize with BULL
    print("Day 1: Initialize in BULL regime")
    bull_factors = RegimeFactors(
        sma_50=4500.0,
        sma_200=4300.0,
        adx=28.0,
        price=4600.0,
        vix=15.0,
        realized_volatility=0.12,
        advance_decline_ratio=1.8,
        new_highs_lows_ratio=2.5,
        correlation=0.40,
        timestamp=datetime.now(),
    )

    bull_detection = RegimeDetection(
        regime=MarketRegime.BULL,
        confidence=80.0,
        factors=bull_factors,
        factor_scores={},
        timestamp=datetime.now(),
    )

    manager.process_detection(bull_detection)
    print(f"  Current Regime: {manager.get_current_regime().value}\n")

    # First SIDEWAYS detection
    print("Day 4: First SIDEWAYS detection (confidence 65%)")
    sideways_factors = RegimeFactors(
        sma_50=4450.0,
        sma_200=4400.0,
        adx=18.0,
        price=4460.0,
        vix=18.0,
        realized_volatility=0.15,
        advance_decline_ratio=1.1,
        new_highs_lows_ratio=1.2,
        correlation=0.48,
        timestamp=datetime.now() + timedelta(days=3),
    )

    sideways_detection = RegimeDetection(
        regime=MarketRegime.SIDEWAYS,
        confidence=65.0,
        factors=sideways_factors,
        factor_scores={},
        timestamp=datetime.now() + timedelta(days=3),
    )

    transition = manager.process_detection(sideways_detection)
    if transition:
        print(
            f"  TRANSITION: {transition.from_regime.value} → {transition.to_regime.value}"
        )
    else:
        print(f"  NO TRANSITION: Still in {manager.get_current_regime().value}")
        print(f"  Reason: Insufficient confidence or consecutive detections\n")

    # Second SIDEWAYS detection
    print("Day 5: Second SIDEWAYS detection (confidence 72%)")
    sideways_detection2 = RegimeDetection(
        regime=MarketRegime.SIDEWAYS,
        confidence=72.0,
        factors=sideways_factors,
        factor_scores={},
        timestamp=datetime.now() + timedelta(days=4),
    )

    transition = manager.process_detection(sideways_detection2)
    if transition:
        print(
            f"  TRANSITION: {transition.from_regime.value} → {transition.to_regime.value}"
        )
        print(f"  Conviction: {transition.conviction_score:.1f}%")
        print(f"  Duration in previous: {transition.duration_in_previous:.1f} days\n")
    else:
        print(f"  NO TRANSITION: Still in {manager.get_current_regime().value}\n")

    # Check transition stats
    stats = manager.get_transition_stats()
    print("TRANSITION STATISTICS:")
    print(f"  Total Transitions: {stats['total_transitions']}")
    print(f"  Whipsaw Count: {stats['whipsaw_count']}")
    print(f"  Whipsaw Rate: {stats['whipsaw_rate']:.1f}%")
    print(f"  Current Regime: {stats['current_regime']}")
    print(f"  Days in Current: {stats['days_in_current']:.1f}")


def demo_4_rebalance_planning():
    """Demo 4: Rebalance plan creation"""
    print_section("Demo 4: Rebalance Plan Creation")

    allocator = RegimeBasedAllocator()

    # Current allocation (BULL)
    current_allocations = {
        "deep_value": 40.0,
        "growth": 30.0,
        "squeeze_hunter": 20.0,
        "momentum": 10.0,
    }

    # New regime detected (BEAR)
    bear_factors = RegimeFactors(
        sma_50=4200.0,
        sma_200=4400.0,
        adx=35.0,
        price=4000.0,
        vix=28.0,
        realized_volatility=0.22,
        advance_decline_ratio=0.6,
        new_highs_lows_ratio=0.4,
        correlation=0.72,
        timestamp=datetime.now(),
    )

    bear_detection = RegimeDetection(
        regime=MarketRegime.BEAR,
        confidence=75.0,
        factors=bear_factors,
        factor_scores={},
        timestamp=datetime.now(),
    )

    print("CURRENT ALLOCATION (BULL regime):")
    for strategy, allocation in current_allocations.items():
        print(f"  {strategy:20s}: {allocation:5.1f}%")

    print(f"\nNEW REGIME DETECTED: {bear_detection.regime.value}")
    print(f"Confidence: {bear_detection.confidence:.1f}%\n")

    # Create rebalance plan
    plan = allocator.create_rebalance_plan(
        detection=bear_detection,
        current_allocations=current_allocations,
        current_regime=MarketRegime.BULL,
    )

    print("REBALANCE PLAN:")
    print(f"  From: {plan.from_regime.value}")
    print(f"  To: {plan.to_regime.value}")
    print(f"  Total Turnover: {plan.total_turnover():.1f}%")
    print(f"  Execute Gradually: {plan.execute_gradually}")
    print(f"  Number of Actions: {len(plan.actions)}\n")

    print("ACTIONS (sorted by priority):")
    for i, action in enumerate(plan.actions, 1):
        direction = "▲" if action.delta > 0 else "▼"
        print(
            f"  {i}. {action.strategy:20s}: "
            f"{action.current_allocation:5.1f}% → {action.target_allocation:5.1f}% "
            f"({direction} {abs(action.delta):5.1f}%) [Priority: {action.priority}]"
        )

    # Show gradual execution if needed
    if plan.execute_gradually:
        print("\nGRADUAL EXECUTION (5 days):")
        daily_adjustments = allocator.execute_gradual_rebalance(plan, days=5)

        for day, adjustments in enumerate(daily_adjustments, 1):
            if adjustments:
                print(f"\n  Day {day}:")
                for strategy, delta in adjustments.items():
                    direction = "▲" if delta > 0 else "▼"
                    print(f"    {strategy:20s}: {direction} {abs(delta):5.2f}%")


def demo_5_historical_validation():
    """Demo 5: Historical validation on known market regimes"""
    print_section("Demo 5: Historical Validation")

    detector = RegimeDetector()

    print("TESTING ON KNOWN HISTORICAL REGIMES:\n")

    # COVID Crash - March 2020
    print("1. COVID-19 CRASH (March 23, 2020)")
    print("   Expected: CRISIS\n")

    covid_factors = RegimeFactors(
        sma_50=2800.0,
        sma_200=3000.0,
        adx=45.0,
        price=2400.0,
        vix=65.0,  # Record high VIX
        realized_volatility=0.60,
        advance_decline_ratio=0.2,
        new_highs_lows_ratio=0.05,
        correlation=0.95,
        timestamp=datetime(2020, 3, 23),
    )

    detection = detector.detect_regime(covid_factors)
    result = "✅ CORRECT" if detection.regime == MarketRegime.CRISIS else "❌ WRONG"
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Result: {result}\n")

    # Bull Market 2020-2021
    print("2. BULL MARKET RECOVERY (March 2021)")
    print("   Expected: BULL\n")

    bull_2021_factors = RegimeFactors(
        sma_50=3800.0,
        sma_200=3500.0,
        adx=28.0,
        price=3900.0,
        vix=16.0,
        realized_volatility=0.12,
        advance_decline_ratio=2.2,
        new_highs_lows_ratio=3.5,
        correlation=0.38,
        timestamp=datetime(2021, 3, 1),
    )

    detection = detector.detect_regime(bull_2021_factors)
    result = "✅ CORRECT" if detection.regime == MarketRegime.BULL else "❌ WRONG"
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Result: {result}\n")

    # Bear Market 2022
    print("3. BEAR MARKET 2022 (June 2022)")
    print("   Expected: BEAR\n")

    bear_2022_factors = RegimeFactors(
        sma_50=4000.0,
        sma_200=4300.0,
        adx=32.0,
        price=3800.0,
        vix=28.0,
        realized_volatility=0.22,
        advance_decline_ratio=0.6,
        new_highs_lows_ratio=0.4,
        correlation=0.72,
        timestamp=datetime(2022, 6, 1),
    )

    detection = detector.detect_regime(bear_2022_factors)
    result = "✅ CORRECT" if detection.regime == MarketRegime.BEAR else "❌ WRONG"
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Result: {result}\n")

    # Sideways 2023
    print("4. RANGE-BOUND MARKET (June 2023)")
    print("   Expected: SIDEWAYS\n")

    sideways_2023_factors = RegimeFactors(
        sma_50=4200.0,
        sma_200=4180.0,
        adx=18.0,
        price=4210.0,
        vix=17.0,
        realized_volatility=0.14,
        advance_decline_ratio=1.1,
        new_highs_lows_ratio=1.2,
        correlation=0.48,
        timestamp=datetime(2023, 6, 1),
    )

    detection = detector.detect_regime(sideways_2023_factors)
    result = "✅ CORRECT" if detection.regime == MarketRegime.SIDEWAYS else "❌ WRONG"
    print(f"   Detected: {detection.regime.value}")
    print(f"   Confidence: {detection.confidence:.1f}%")
    print(f"   Result: {result}")


def demo_6_confidence_blending():
    """Demo 6: Allocation blending with low confidence"""
    print_section("Demo 6: Confidence Blending")

    allocator = RegimeBasedAllocator(blend_threshold=70.0)

    print("SCENARIO: BULL regime detected with varying confidence\n")

    bull_factors = RegimeFactors(
        sma_50=4500.0,
        sma_200=4300.0,
        adx=28.0,
        price=4600.0,
        vix=18.0,
        realized_volatility=0.15,
        advance_decline_ratio=1.5,
        new_highs_lows_ratio=2.0,
        correlation=0.40,
        timestamp=datetime.now(),
    )

    # High confidence - pure allocation
    print("1. HIGH CONFIDENCE (85%): Pure BULL allocation")
    high_conf_detection = RegimeDetection(
        regime=MarketRegime.BULL,
        confidence=85.0,
        factors=bull_factors,
        factor_scores={},
        timestamp=datetime.now(),
    )

    target = allocator.calculate_target_allocation(high_conf_detection)
    print(f"   Confidence: {high_conf_detection.confidence:.1f}%")
    print("   Allocation:")
    for strategy, allocation in sorted(
        target.items(), key=lambda x: x[1], reverse=True
    ):
        if allocation > 0:
            print(f"     {strategy:20s}: {allocation:5.1f}%")

    # Low confidence - blended allocation
    print("\n2. LOW CONFIDENCE (50%): Blended with SIDEWAYS")
    low_conf_detection = RegimeDetection(
        regime=MarketRegime.BULL,
        confidence=50.0,
        factors=bull_factors,
        factor_scores={},
        timestamp=datetime.now(),
    )

    target = allocator.calculate_target_allocation(low_conf_detection)
    print(f"   Confidence: {low_conf_detection.confidence:.1f}%")
    print("   Allocation (blended):")
    for strategy, allocation in sorted(
        target.items(), key=lambda x: x[1], reverse=True
    ):
        if allocation > 0:
            print(f"     {strategy:20s}: {allocation:5.1f}%")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  MARKET REGIME DETECTION SYSTEM - COMPREHENSIVE DEMO")
    print("=" * 70)

    try:
        demo_1_basic_detection()
        demo_2_allocation_management()
        demo_3_transition_management()
        demo_4_rebalance_planning()
        demo_5_historical_validation()
        demo_6_confidence_blending()

        print_section("Demo Complete")
        print("All demonstrations completed successfully!")
        print("\nNext Steps:")
        print("  1. Review docs/REGIME_DETECTION.md for detailed documentation")
        print("  2. Check tests/unit/test_regime_*.py for more examples")
        print("  3. Integrate with your data provider")
        print("  4. Backtest on historical data")
        print("  5. Start paper trading with regime-based allocation")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
