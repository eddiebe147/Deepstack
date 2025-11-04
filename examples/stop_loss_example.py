"""
Stop Loss Manager Examples - Production-ready stop loss management demonstrations

This example demonstrates all stop loss features:
1. Fixed percentage stops (simple & predictable)
2. ATR-based stops (volatility-adjusted)
3. Trailing stops (automatic profit locking)
4. Never-downgrade rule enforcement
5. 100% coverage validation
6. Integration with position sizing
7. Emergency stop scenarios

Run this file to see stop loss management in action.
"""

from core.risk.kelly_position_sizer import KellyPositionSizer
from core.risk.stop_loss_manager import StopLossManager


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_stop_details(stop_result: dict):
    """Pretty print stop loss details."""
    print(f"  Symbol: {stop_result.get('symbol', 'N/A')}")
    print(f"  Stop Price: ${stop_result['stop_price']:.2f}")
    print(f"  Stop Type: {stop_result['stop_type']}")
    print(f"  Risk Amount: ${stop_result['risk_amount']:.2f}")
    print(f"  Risk %: {stop_result['risk_pct']:.2%}")
    print(f"  Account Risk %: {stop_result['account_risk_pct']:.2%}")
    print(f"  Stop Distance: {stop_result['stop_distance']:.2%}")
    print(f"  Shares: {stop_result['shares']}")
    print(f"  Rationale: {stop_result['rationale']}")
    if stop_result["warnings"]:
        print(f"  Warnings: {', '.join(stop_result['warnings'])}")
    print()


def example_1_fixed_percentage_stops():
    """Example 1: Fixed percentage stops - simple and predictable."""
    print_section("Example 1: Fixed Percentage Stops")

    manager = StopLossManager(
        account_balance=100000,
        max_risk_per_trade=0.02,
        default_stop_pct=0.02,
    )

    print("Fixed percentage stops are the simplest type:")
    print("- Set a fixed % below entry (e.g., 2% stop)")
    print("- Easy to calculate and understand")
    print("- Predictable risk per trade\n")

    # Long position with 2% stop
    print("Long Position with 2% Stop:")
    print("  Entry: $150.00, Position Size: $10,000")
    stop = manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=150.0,
        position_size=10000.0,
        position_side="long",
        stop_type="fixed_pct",
        stop_pct=0.02,
    )
    stop["symbol"] = "AAPL"
    print_stop_details(stop)

    # Short position with 2% stop
    print("Short Position with 2% Stop:")
    print("  Entry: $200.00, Position Size: $10,000")
    stop = manager.calculate_stop_loss(
        symbol="TSLA",
        entry_price=200.0,
        position_size=10000.0,
        position_side="short",
        stop_type="fixed_pct",
        stop_pct=0.02,
    )
    stop["symbol"] = "TSLA"
    print_stop_details(stop)


def example_2_atr_based_stops():
    """Example 2: ATR-based stops - volatility-adjusted."""
    print_section("Example 2: ATR-Based Stops (Volatility-Adjusted)")

    manager = StopLossManager(
        account_balance=100000,
        default_atr_multiplier=2.0,
    )

    print("ATR-based stops adapt to market volatility:")
    print("- Stop based on Average True Range (ATR)")
    print("- Wider stops in volatile markets, tighter in calm markets")
    print("- Example: 2x ATR stop means stop is 2 ATR units away\n")

    # Low volatility stock (tech blue chip)
    print("Low Volatility Stock (AAPL):")
    print("  Entry: $150.00, ATR: $2.50, Multiplier: 2.0x")
    stop_aapl = manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=150.0,
        position_size=10000.0,
        stop_type="atr_based",
        atr=2.5,
        atr_multiplier=2.0,
    )
    stop_aapl["symbol"] = "AAPL"
    print(f"  Stop Distance: 2.0 * $2.50 = $5.00")
    print_stop_details(stop_aapl)

    # High volatility stock (small cap) - use smaller ATR to stay within limits
    print("High Volatility Stock (VOLATILE):")
    print("  Entry: $100.00, ATR: $4.00, Multiplier: 2.0x")
    stop_volatile = manager.calculate_stop_loss(
        symbol="VOLATILE",
        entry_price=100.0,
        position_size=8000.0,
        stop_type="atr_based",
        atr=4.0,
        atr_multiplier=2.0,
    )
    stop_volatile["symbol"] = "VOLATILE"
    print(f"  Stop Distance: 2.0 * $4.00 = $8.00")
    print_stop_details(stop_volatile)

    print("Notice how the volatile stock has a wider stop ($8 vs $5)")
    print("This prevents getting stopped out by normal price swings.\n")


def example_3_trailing_stops():
    """Example 3: Trailing stops - automatic profit locking."""
    print_section("Example 3: Trailing Stops (Lock in Profits)")

    manager = StopLossManager(
        account_balance=100000,
        default_trailing_pct=0.05,  # 5% trail
    )

    print("Trailing stops lock in profits as price moves favorably:")
    print("- Stop follows price up (for longs) or down (for shorts)")
    print("- Never moves against you (never-downgrade rule)")
    print("- Automatically captures gains\n")

    # Initialize trailing stop
    print("1. Enter Long Position:")
    print("   Entry: $100.00, Position Size: $10,000, Trail: 5%")
    stop_init = manager.calculate_stop_loss(
        symbol="WINNER",
        entry_price=100.0,
        position_size=10000.0,
        stop_type="trailing",
    )
    print(f"   Initial Stop: ${stop_init['stop_price']:.2f} (5% below entry)\n")

    # Price moves up
    print("2. Price Moves to $110 (10% gain):")
    update1 = manager.update_trailing_stop(symbol="WINNER", current_price=110.0)
    print(f"   Stop moves to: ${update1['stop_price']:.2f} (5% below $110)")
    print(f"   Profit locked: ${update1['profit_locked']:.2f}\n")

    # Price continues up
    print("3. Price Moves to $130 (30% gain):")
    update2 = manager.update_trailing_stop(symbol="WINNER", current_price=130.0)
    print(f"   Stop moves to: ${update2['stop_price']:.2f} (5% below $130)")
    print(f"   Profit locked: ${update2['profit_locked']:.2f}\n")

    # Price pulls back (stop doesn't downgrade)
    print("4. Price Pulls Back to $125:")
    update3 = manager.update_trailing_stop(symbol="WINNER", current_price=125.0)
    print(f"   Stop stays at: ${update3['stop_price']:.2f} (NEVER downgrades)")
    print(f"   Stop moved: {update3['stop_moved']}")
    print(f"   Rationale: {update3['rationale']}\n")

    print("Result: Locked in 23.5% profit ($123.50 - $100 = $23.50)")
    print("Even though price pulled back from $130 to $125!\n")


def example_4_never_downgrade_rule():
    """Example 4: Never-downgrade rule enforcement."""
    print_section("Example 4: Never-Downgrade Rule (Critical Safety)")

    manager = StopLossManager(account_balance=100000)

    print("The never-downgrade rule is CRITICAL for risk management:")
    print("- For LONGS: Stop can only move UP, never down")
    print("- For SHORTS: Stop can only move DOWN, never up")
    print("- Prevents increasing risk on winning trades\n")

    # Long example
    print("Long Position Example:")
    print("  Entry: $100, Initial Stop: $98 (2% stop)")
    manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=100.0,
        position_size=10000.0,
        stop_type="fixed_pct",
    )

    print("\n  Attempting to move stop to $99 (tighten stop):")
    valid_tighten = manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=99.0)
    print(f"    Valid: {valid_tighten} ✓ (Stop moved favorably)")

    print("\n  Attempting to move stop to $97 (widen stop):")
    valid_widen = manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=97.0)
    print(f"    Valid: {valid_widen} ✗ (VIOLATION: Stop moved unfavorably)")

    # Short example
    print("\n\nShort Position Example:")
    print("  Entry: $200, Initial Stop: $204 (2% stop)")
    manager.calculate_stop_loss(
        symbol="TSLA",
        entry_price=200.0,
        position_size=10000.0,
        position_side="short",
        stop_type="fixed_pct",
    )

    print("\n  Attempting to move stop to $203 (tighten stop):")
    valid_short_tighten = manager.validate_stop_never_downgrades(
        symbol="TSLA", new_stop=203.0
    )
    print(f"    Valid: {valid_short_tighten} ✓ (Stop moved favorably)")

    print("\n  Attempting to move stop to $205 (widen stop):")
    valid_short_widen = manager.validate_stop_never_downgrades(
        symbol="TSLA", new_stop=205.0
    )
    print(f"    Valid: {valid_short_widen} ✗ (VIOLATION: Stop moved unfavorably)\n")


def example_5_100pct_coverage():
    """Example 5: 100% stop loss coverage validation."""
    print_section("Example 5: 100% Stop Loss Coverage (Mandatory)")

    manager = StopLossManager(account_balance=100000)

    print("EVERY position MUST have a stop loss (100% coverage):")
    print("- No unprotected trades allowed")
    print("- Automated coverage validation")
    print("- Fail-safe risk management\n")

    # Create portfolio with some stops
    print("Portfolio Setup:")
    print("  - AAPL: Entry $150, Stop at $147 ✓")
    print("  - GOOGL: Entry $100, Stop at $98 ✓")
    print("  - TSLA: Entry $200, NO STOP ✗\n")

    manager.calculate_stop_loss(
        symbol="AAPL", entry_price=150.0, position_size=10000.0, stop_type="fixed_pct"
    )
    manager.calculate_stop_loss(
        symbol="GOOGL", entry_price=100.0, position_size=8000.0, stop_type="fixed_pct"
    )
    # Intentionally skip TSLA stop

    # Validate coverage
    symbols = ["AAPL", "GOOGL", "TSLA"]
    coverage = manager.validate_100pct_coverage(symbols)

    print("Coverage Report:")
    print(f"  Total Positions: {coverage['total_positions']}")
    print(f"  Positions with Stops: {coverage['positions_with_stops']}")
    print(f"  Coverage: {coverage['coverage_pct']:.1%}")
    print(f"  Has 100% Coverage: {coverage['has_100pct_coverage']}")
    if not coverage["has_100pct_coverage"]:
        print(f"  Missing Stops: {', '.join(coverage['missing_stops'])}")
        print("\n  ⚠️  WARNING: UNPROTECTED POSITIONS DETECTED!")
        print("  System should REJECT orders without stops.\n")

    # Fix coverage
    print("Fixing Coverage - Adding TSLA stop:")
    manager.calculate_stop_loss(
        symbol="TSLA", entry_price=200.0, position_size=12000.0, stop_type="fixed_pct"
    )

    coverage_fixed = manager.validate_100pct_coverage(symbols)
    print(f"  Coverage: {coverage_fixed['coverage_pct']:.1%}")
    print(f"  Has 100% Coverage: {coverage_fixed['has_100pct_coverage']} ✓\n")


def example_6_integration_with_kelly():
    """Example 6: Integration with Kelly Position Sizer."""
    print_section("Example 6: Integration with Kelly Position Sizer")

    print("Combining position sizing with stop loss management:")
    print("- Kelly Criterion determines position size")
    print("- Stop Loss Manager ensures risk protection\n")

    # Initialize both managers
    kelly = KellyPositionSizer(
        account_balance=100000,
        max_position_pct=0.25,
    )

    stop_manager = StopLossManager(
        account_balance=100000,
        max_risk_per_trade=0.02,
    )

    # Calculate position size
    print("Step 1: Calculate Position Size (Kelly Criterion)")
    print("  Win Rate: 55%, Avg Win: $1,500, Avg Loss: $1,000")
    position = kelly.calculate_position_size(
        win_rate=0.55,
        avg_win=1500,
        avg_loss=1000,
        stock_price=150.0,
        symbol="AAPL",
    )
    print(f"  Recommended Position Size: ${position['position_size']:,.2f}")
    print(f"  Shares: {position['shares']}")
    print(f"  Portfolio %: {position['adjusted_pct']:.2%}\n")

    # Calculate stop loss
    print("Step 2: Calculate Stop Loss (Risk Management)")
    print(f"  Entry Price: $150.00, Position Size: ${position['position_size']:,.2f}")
    stop = stop_manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=150.0,
        position_size=position["position_size"],
        stop_type="fixed_pct",
        stop_pct=0.02,
    )
    print(f"  Stop Price: ${stop['stop_price']:.2f}")
    print(f"  Risk Amount: ${stop['risk_amount']:.2f}")
    print(f"  Account Risk %: {stop['account_risk_pct']:.2%}\n")

    print("Complete Trade Setup:")
    print(f"  Symbol: AAPL")
    print(f"  Entry: $150.00")
    print(
        f"  Position Size: ${position['position_size']:,.2f} ({position['adjusted_pct']:.2%} of portfolio)"
    )
    print(f"  Shares: {position['shares']}")
    print(f"  Stop Loss: ${stop['stop_price']:.2f} (2% below entry)")
    print(
        f"  Risk: ${stop['risk_amount']:.2f} ({stop['account_risk_pct']:.2%} of account)"
    )
    print(f"  Win Rate Edge: {position['win_loss_ratio']:.2f}:1 W/L ratio\n")


def example_7_emergency_stops():
    """Example 7: Emergency stop scenarios."""
    print_section("Example 7: Emergency Stops (Market Crash Scenarios)")

    manager = StopLossManager(account_balance=100000)

    print("Emergency stops handle extreme situations:")
    print("- Market crashes, flash crashes")
    print("- Circuit breakers, trading halts")
    print("- Can bypass never-downgrade rule (USE WITH CAUTION)\n")

    # Normal setup
    print("Normal Market Conditions:")
    print("  Entry: $100, Stop: $98 (2% stop)")
    manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=100.0,
        position_size=10000.0,
        stop_type="fixed_pct",
    )

    old_stop = manager.get_active_stop("AAPL")
    print(f"  Current Stop: ${old_stop['stop_price']:.2f}\n")

    # Market crash scenario
    print("SCENARIO: Market Flash Crash")
    print("  Price drops from $100 to $85 in minutes")
    print("  Need emergency stop at $87 to limit damage")
    print("  (This violates never-downgrade rule)\n")

    emergency = manager.emergency_stop_update(
        symbol="AAPL",
        emergency_stop_price=87.0,
        reason="Flash crash - emergency risk reduction",
    )

    print("Emergency Stop Update:")
    print(f"  Old Stop: ${emergency['old_stop_price']:.2f}")
    print(f"  New Stop: ${emergency['stop_price']:.2f}")
    print(f"  Violated Never-Downgrade: {emergency['violated_never_downgrade']}")
    print(f"  Reason: {emergency['reason']}")
    if emergency["warning"]:
        print(f"  ⚠️  {emergency['warning']}\n")

    print("Emergency stops should be RARE and logged extensively.")
    print("They represent extraordinary market conditions.\n")


def example_8_complete_trade_lifecycle():
    """Example 8: Complete trade lifecycle demonstration."""
    print_section("Example 8: Complete Trade Lifecycle")

    manager = StopLossManager(
        account_balance=100000,
        default_trailing_pct=0.05,
    )

    print("Full lifecycle of a winning trade with trailing stop:\n")

    print("Day 1: Enter Position")
    print("  Buy 100 shares of WINNER at $100.00")
    entry = manager.calculate_stop_loss(
        symbol="WINNER",
        entry_price=100.0,
        position_size=10000.0,
        stop_type="trailing",
    )
    print(f"  Initial trailing stop: ${entry['stop_price']:.2f} (5% trail)")
    print(f"  Risk: ${entry['risk_amount']:.2f}\n")

    print("Day 2: Price moves to $110 (+10%)")
    update1 = manager.update_trailing_stop(symbol="WINNER", current_price=110.0)
    print(f"  Stop raised to: ${update1['stop_price']:.2f}")
    print(f"  Profit locked: ${update1['profit_locked']:.2f}\n")

    print("Day 3: Price moves to $125 (+25%)")
    update2 = manager.update_trailing_stop(symbol="WINNER", current_price=125.0)
    print(f"  Stop raised to: ${update2['stop_price']:.2f}")
    print(f"  Profit locked: ${update2['profit_locked']:.2f}\n")

    print("Day 4: Price moves to $140 (+40%)")
    update3 = manager.update_trailing_stop(symbol="WINNER", current_price=140.0)
    print(f"  Stop raised to: ${update3['stop_price']:.2f}")
    print(f"  Profit locked: ${update3['profit_locked']:.2f}\n")

    print("Day 5: Price pulls back to $135")
    update4 = manager.update_trailing_stop(symbol="WINNER", current_price=135.0)
    print(f"  Stop stays at: ${update4['stop_price']:.2f} (never downgrades)")
    print(f"  Still protected at 33% gain\n")

    print("Day 6: Price drops to $133 - STOPPED OUT")
    print(f"  Exit at stop: ${update4['stop_price']:.2f}")
    print(f"  Entry: $100.00, Exit: $133.00")
    print(f"  Profit: $33.00 per share x 100 shares = $3,300")
    print(f"  Return: 33%\n")

    # Clean up
    manager.remove_stop("WINNER")
    print("Position closed, stop removed from system.\n")


def main():
    """Run all examples."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print(
        "║" + " " * 15 + "STOP LOSS MANAGER - COMPREHENSIVE EXAMPLES" + " " * 21 + "║"
    )
    print("╚" + "=" * 78 + "╝")

    examples = [
        example_1_fixed_percentage_stops,
        example_2_atr_based_stops,
        example_3_trailing_stops,
        example_4_never_downgrade_rule,
        example_5_100pct_coverage,
        example_6_integration_with_kelly,
        example_7_emergency_stops,
        example_8_complete_trade_lifecycle,
    ]

    for example in examples:
        example()

    print_section("Summary")
    print("Key Takeaways:")
    print("  ✓ EVERY trade must have a stop loss (100% coverage)")
    print("  ✓ Stops NEVER downgrade (only move favorably)")
    print("  ✓ Multiple stop types for different scenarios")
    print("  ✓ Trailing stops automatically lock in profits")
    print("  ✓ ATR-based stops adapt to volatility")
    print("  ✓ Default 2% max risk per trade")
    print("  ✓ Integration with position sizing")
    print("  ✓ Emergency stops for extreme situations\n")

    print("Stop Loss Management is the foundation of risk control.")
    print("Without stops, you're gambling. With stops, you're trading.\n")


if __name__ == "__main__":
    main()
