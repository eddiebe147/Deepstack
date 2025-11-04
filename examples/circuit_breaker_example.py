"""
Circuit Breaker Examples - Production-ready trading halt protection

Demonstrates how to use circuit breakers to protect against catastrophic losses.
Shows all breaker types, integration with risk management, and real-world scenarios.

Run this example to learn:
    - How each circuit breaker type works
    - When breakers trip and how to reset them
    - Integration with Kelly + Stop Loss systems
    - Real-world trading scenarios with protection
    - Recovery workflows after breaker trips

Usage:
    python examples/circuit_breaker_example.py
"""

from core.risk.circuit_breaker import BreakerType, CircuitBreaker
from core.risk.kelly_position_sizer import KellyPositionSizer
from core.risk.stop_loss_manager import StopLossManager


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"{title:^70}")
    print(f"{'=' * 70}\n")


def print_breaker_status(status: dict):
    """Pretty print circuit breaker status."""
    print(f"Trading Allowed: {'✓ YES' if status['trading_allowed'] else '✗ NO'}")
    print(f"Breakers Tripped: {len(status['breakers_tripped'])}")

    if status["breakers_tripped"]:
        print("\nTripped Breakers:")
        for i, breaker in enumerate(status["breakers_tripped"]):
            print(f"  {i+1}. {breaker.upper()}")
            print(f"     Reason: {status['reasons'][i]}")

    if status["warnings"]:
        print("\nWarnings:")
        for warning in status["warnings"]:
            print(f"  ⚠ {warning}")

    print(f"\nMetrics:")
    print(f"  Daily Loss: {status['current_daily_loss_pct']:.2%}")
    print(f"  Drawdown: {status['current_drawdown_pct']:.2%}")
    print(f"  Consecutive Losses: {status['consecutive_losses']}")
    if status["current_vix"] is not None:
        print(f"  VIX: {status['current_vix']:.2f}")


def example_1_daily_loss_breaker():
    """Example 1: Daily loss limit circuit breaker."""
    print_section("Example 1: Daily Loss Limit Breaker")

    # Initialize with 3% daily loss limit
    breaker = CircuitBreaker(
        initial_portfolio_value=100000,
        daily_loss_limit=0.03,  # Halt if daily loss exceeds 3%
    )

    print("Scenario: Trading day with increasing losses")
    print("Portfolio starts at $100,000")
    print("Daily loss limit: 3%\n")

    # Start of day
    start_of_day = 100000

    # Trade 1: Small loss
    print("Trade 1: Loss of $1,000")
    portfolio_value = 99000
    status = breaker.check_breakers(
        current_portfolio_value=portfolio_value, start_of_day_value=start_of_day
    )
    print(
        f"Portfolio: ${portfolio_value:,} (down {((start_of_day - portfolio_value) / start_of_day):.1%})"
    )
    print(
        f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}\n"
    )

    # Trade 2: Another loss
    print("Trade 2: Loss of $1,500")
    portfolio_value = 97500
    status = breaker.check_breakers(
        current_portfolio_value=portfolio_value, start_of_day_value=start_of_day
    )
    print(
        f"Portfolio: ${portfolio_value:,} (down {((start_of_day - portfolio_value) / start_of_day):.1%})"
    )
    print(
        f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}"
    )
    if status["warnings"]:
        print(f"Warning: {status['warnings'][0]}\n")

    # Trade 3: Breach daily limit
    print("Trade 3: Loss of $1,000 (total -$3,500, -3.5%)")
    portfolio_value = 96500
    status = breaker.check_breakers(
        current_portfolio_value=portfolio_value, start_of_day_value=start_of_day
    )
    print(
        f"Portfolio: ${portfolio_value:,} (down {((start_of_day - portfolio_value) / start_of_day):.1%})"
    )
    print(
        f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}"
    )

    if not status["trading_allowed"]:
        print(f"\n🚨 CIRCUIT BREAKER TRIPPED!")
        print(f"Reason: {status['reasons'][0]}")
        print(f"\nTrading halted for the day to prevent further losses.")
        print(f"Breaker will auto-reset tomorrow at market open.")


def example_2_max_drawdown_breaker():
    """Example 2: Max drawdown circuit breaker."""
    print_section("Example 2: Max Drawdown Breaker")

    # Initialize with 10% max drawdown
    breaker = CircuitBreaker(
        initial_portfolio_value=100000,
        max_drawdown_limit=0.10,  # Halt if portfolio down 10% from peak
    )

    print("Scenario: Portfolio grows then experiences drawdown")
    print("Starting portfolio: $100,000")
    print("Max drawdown limit: 10% from peak\n")

    # Portfolio grows to new peak
    print("Phase 1: Growth")
    portfolio_value = 120000
    status = breaker.check_breakers(current_portfolio_value=portfolio_value)
    print(f"Portfolio reaches new peak: ${portfolio_value:,}")
    print(f"Peak value: ${breaker.peak_portfolio_value:,}\n")

    # Market correction: 8% drawdown
    print("Phase 2: Market Correction")
    portfolio_value = 110400  # 8% down from 120k
    status = breaker.check_breakers(current_portfolio_value=portfolio_value)
    print(f"Portfolio drops to: ${portfolio_value:,}")
    print(f"Drawdown: {status['current_drawdown_pct']:.1%} from peak")
    print(
        f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}"
    )
    if status["warnings"]:
        print(f"Warning: {status['warnings'][0]}\n")

    # Further decline: 10% drawdown
    print("Phase 3: Further Decline")
    portfolio_value = 108000  # 10% down from 120k
    status = breaker.check_breakers(current_portfolio_value=portfolio_value)
    print(f"Portfolio drops to: ${portfolio_value:,}")
    print(f"Drawdown: {status['current_drawdown_pct']:.1%} from peak")
    print(
        f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}"
    )

    if not status["trading_allowed"]:
        print(f"\n🚨 CIRCUIT BREAKER TRIPPED!")
        print(f"Reason: {status['reasons'][0]}")
        print(f"\nTrading halted until manual review and reset.")
        print(f"This prevents emotional trading during large drawdowns.")


def example_3_consecutive_losses_breaker():
    """Example 3: Consecutive losses circuit breaker."""
    print_section("Example 3: Consecutive Losses Breaker")

    # Initialize with 5 consecutive loss limit
    breaker = CircuitBreaker(
        initial_portfolio_value=100000,
        consecutive_loss_limit=5,  # Halt after 5 losing trades in a row
    )

    print("Scenario: Strategy experiencing losing streak")
    print("Consecutive loss limit: 5 trades")
    print("This protects against strategy breakdown\n")

    # Simulate trades
    trades = [
        ("AAPL", -150, "Stop loss hit"),
        ("TSLA", -200, "Stop loss hit"),
        ("MSFT", -120, "Stop loss hit"),
        ("GOOGL", -180, "Stop loss hit"),
        ("AMZN", 250, "Target hit"),  # Win - resets streak
        ("META", -130, "Stop loss hit"),
        ("NVDA", -160, "Stop loss hit"),
        ("AMD", -140, "Stop loss hit"),
        ("NFLX", -170, "Stop loss hit"),
        ("SPY", -110, "Stop loss hit"),  # 5th consecutive loss
    ]

    portfolio_value = 100000

    for i, (symbol, pnl, reason) in enumerate(trades, 1):
        # Record trade
        breaker.record_trade(pnl, {"symbol": symbol, "reason": reason})

        # Update portfolio
        portfolio_value += pnl

        # Check breakers
        status = breaker.check_breakers(current_portfolio_value=portfolio_value)

        # Print trade result
        result_emoji = "✓" if pnl > 0 else "✗"
        print(f"Trade {i:2d}: {result_emoji} {symbol:5s} ${pnl:+7.0f} ({reason})")
        print(
            f"         Consecutive losses: {status['consecutive_losses']}, Portfolio: ${portfolio_value:,}"
        )

        if status["warnings"]:
            print(f"         ⚠ {status['warnings'][0]}")

        if not status["trading_allowed"]:
            print(f"\n         🚨 CIRCUIT BREAKER TRIPPED!")
            print(f"         Reason: {status['reasons'][0]}")
            print(
                f"\n         Strategy may be broken or market conditions unfavorable."
            )
            print(f"         Halting trading to prevent further losses.\n")
            break

        print()


def example_4_volatility_spike_breaker():
    """Example 4: Volatility spike circuit breaker."""
    print_section("Example 4: Volatility Spike Breaker")

    # Initialize with VIX threshold of 35
    breaker = CircuitBreaker(
        initial_portfolio_value=100000,
        volatility_threshold=35.0,  # Halt if VIX exceeds 35
    )

    print("Scenario: Market volatility monitoring")
    print("VIX threshold: 35 (halt trading during extreme volatility)\n")

    # Normal market conditions
    print("Normal Market Conditions:")
    vix_levels = [
        (15.5, "Low volatility"),
        (22.3, "Moderate volatility"),
        (28.7, "Elevated volatility"),
        (33.2, "High volatility (approaching threshold)"),
        (38.5, "EXTREME VOLATILITY - Market crash conditions"),
    ]

    for vix, description in vix_levels:
        status = breaker.check_breakers(current_portfolio_value=100000, current_vix=vix)

        print(f"VIX: {vix:5.1f} - {description}")
        print(
            f"Status: {'✓ Trading allowed' if status['trading_allowed'] else '✗ Trading halted'}"
        )

        if status["warnings"]:
            print(f"Warning: {status['warnings'][0]}")

        if not status["trading_allowed"]:
            print(f"\n🚨 CIRCUIT BREAKER TRIPPED!")
            print(f"Reason: {status['reasons'][0]}")
            print(f"\nMarket conditions too volatile for safe trading.")
            print(f"Breaker will auto-reset when VIX normalizes.\n")
            break

        print()


def example_5_multiple_breakers():
    """Example 5: Multiple breakers tripped simultaneously."""
    print_section("Example 5: Multiple Breakers Tripped")

    # Initialize with multiple limits
    breaker = CircuitBreaker(
        initial_portfolio_value=100000,
        daily_loss_limit=0.05,
        max_drawdown_limit=0.15,
        consecutive_loss_limit=3,
        volatility_threshold=35.0,
    )

    print("Scenario: Market crash - multiple risk factors triggered")
    print("Simulating catastrophic market conditions\n")

    # Record consecutive losses
    print("Recording trades:")
    breaker.record_trade(-2000, {"symbol": "AAPL"})
    print("Trade 1: AAPL -$2,000")
    breaker.record_trade(-2500, {"symbol": "TSLA"})
    print("Trade 2: TSLA -$2,500")
    breaker.record_trade(-3000, {"symbol": "MSFT"})
    print("Trade 3: MSFT -$3,000")

    # Check with high VIX and portfolio loss
    portfolio_value = 82000  # 18% loss
    start_of_day = 100000
    vix = 65.0  # Extreme volatility

    print(f"\nMarket Conditions:")
    print(f"Portfolio: ${portfolio_value:,} (down 18%)")
    print(f"VIX: {vix}")
    print(f"Daily loss: {((start_of_day - portfolio_value) / start_of_day):.1%}")
    print(f"Consecutive losses: 3\n")

    status = breaker.check_breakers(
        current_portfolio_value=portfolio_value,
        start_of_day_value=start_of_day,
        current_vix=vix,
    )

    print_breaker_status(status)

    if not status["trading_allowed"]:
        print("\n💥 MULTIPLE CIRCUIT BREAKERS TRIPPED!")
        print("This is a severe risk event requiring immediate action:")
        print("  1. Stop all trading immediately")
        print("  2. Review all open positions")
        print("  3. Assess strategy performance")
        print("  4. Wait for market stabilization")
        print("  5. Manual reset required after thorough review")


def example_6_breaker_reset():
    """Example 6: Breaker reset process."""
    print_section("Example 6: Breaker Reset Process")

    breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

    print("Scenario: Resetting a tripped circuit breaker")
    print("This demonstrates the security of the reset process\n")

    # Trip the breaker
    print("Step 1: Trip the breaker")
    status = breaker.check_breakers(
        current_portfolio_value=96500, start_of_day_value=100000
    )
    print(f"Daily loss: 3.5% - Breaker tripped: {not status['trading_allowed']}\n")

    # Get confirmation code
    print("Step 2: Get confirmation code")
    code = breaker.active_confirmation_codes[BreakerType.DAILY_LOSS.value]
    print(f"Confirmation code: {code}")
    print("(This would be logged and/or sent to authorized personnel)\n")

    # Try wrong code
    print("Step 3: Try resetting with WRONG code")
    try:
        breaker.reset_breaker(BreakerType.DAILY_LOSS.value, "WRONG_CODE", "Test reset")
        print("Reset successful")
    except PermissionError as e:
        print(f"✗ Reset failed: {e}\n")

    # Reset with correct code
    print("Step 4: Reset with CORRECT code")
    try:
        reset_result = breaker.reset_breaker(
            BreakerType.DAILY_LOSS.value,
            code,
            "Market stabilized, risk reviewed, resuming trading",
        )
        print(f"✓ Reset successful!")
        print(f"Trip duration: {reset_result['trip_duration']}")
        print(f"Reason: {reset_result['reason']}\n")
    except Exception as e:
        print(f"✗ Reset failed: {e}\n")

    # Verify trading allowed
    print("Step 5: Verify trading resumed")
    status = breaker.check_breakers(current_portfolio_value=96500)
    print(f"Trading allowed: {'✓ YES' if status['trading_allowed'] else '✗ NO'}")


def example_7_integration_with_risk_management():
    """Example 7: Integration with Kelly + Stop Loss."""
    print_section("Example 7: Full Risk Management Integration")

    print("Scenario: Complete risk management system")
    print("Integrating: Circuit Breakers + Kelly Sizer + Stop Loss Manager\n")

    # Initialize all risk management components
    account_balance = 100000

    circuit_breaker = CircuitBreaker(
        initial_portfolio_value=account_balance,
        daily_loss_limit=0.03,
        max_drawdown_limit=0.10,
        consecutive_loss_limit=5,
    )

    kelly_sizer = KellyPositionSizer(
        account_balance=account_balance,
        max_position_pct=0.25,
        max_total_exposure=1.0,
    )

    stop_loss_manager = StopLossManager(
        account_balance=account_balance, max_risk_per_trade=0.02
    )

    print("Risk Management System Initialized:")
    print(f"  Account Balance: ${account_balance:,}")
    print(f"  Daily Loss Limit: 3%")
    print(f"  Max Drawdown: 10%")
    print(f"  Max Position Size: 25%")
    print(f"  Max Risk Per Trade: 2%\n")

    # Simulate a trade
    print("Trade Setup: AAPL Entry")
    print("-" * 70)

    # Step 1: Check circuit breakers
    print("\nStep 1: Check Circuit Breakers")
    cb_status = circuit_breaker.check_breakers(
        current_portfolio_value=account_balance, start_of_day_value=account_balance
    )

    if not cb_status["trading_allowed"]:
        print("✗ Trading halted - circuit breaker tripped")
        print(f"Reason: {cb_status['reasons'][0]}")
        return
    else:
        print("✓ All circuit breakers clear - trading allowed")

    # Step 2: Calculate position size
    print("\nStep 2: Calculate Position Size (Kelly Criterion)")
    position_calc = kelly_sizer.calculate_position_size(
        win_rate=0.55,  # 55% win rate
        avg_win=1200,  # Avg win $1,200
        avg_loss=800,  # Avg loss $800
        kelly_fraction=0.5,  # Half Kelly for safety
        stock_price=150.0,
        symbol="AAPL",
    )

    print(f"Kelly Position Size: ${position_calc['position_size']:,.2f}")
    print(f"Shares: {position_calc['shares']}")
    print(f"Rationale: {position_calc['rationale']}")

    # Step 3: Calculate stop loss
    print("\nStep 3: Calculate Stop Loss")
    stop_calc = stop_loss_manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=150.0,
        position_size=position_calc["position_size"],
        position_side="long",
        stop_type="fixed_pct",
        stop_pct=0.02,  # 2% stop loss
    )

    print(f"Entry Price: ${150.0:.2f}")
    print(f"Stop Loss: ${stop_calc['stop_price']:.2f}")
    print(f"Risk Amount: ${stop_calc['risk_amount']:,.2f}")
    print(f"Account Risk: {stop_calc['account_risk_pct']:.2%}")

    # Step 4: Execute trade (simulated)
    print("\nStep 4: Execute Trade")
    print(f"✓ BUY {position_calc['shares']} shares AAPL @ $150.00")
    print(f"✓ Stop loss set at ${stop_calc['stop_price']:.2f}")
    print(
        f"✓ Position size: ${position_calc['position_size']:,.2f} ({position_calc['adjusted_pct']:.1%} of portfolio)"
    )

    print("\n" + "=" * 70)
    print("Trade executed with full risk management protection:")
    print(f"  ✓ Circuit breakers monitoring")
    print(f"  ✓ Position sized with Kelly Criterion")
    print(f"  ✓ Stop loss protecting downside")
    print(f"  ✓ Max risk per trade: 2%")
    print("=" * 70)


def main():
    """Run all circuit breaker examples."""
    print("\n" + "=" * 70)
    print("CIRCUIT BREAKER EXAMPLES - Production Trading Protection")
    print("=" * 70)

    examples = [
        example_1_daily_loss_breaker,
        example_2_max_drawdown_breaker,
        example_3_consecutive_losses_breaker,
        example_4_volatility_spike_breaker,
        example_5_multiple_breakers,
        example_6_breaker_reset,
        example_7_integration_with_risk_management,
    ]

    for example_func in examples:
        try:
            example_func()
            input("\nPress Enter to continue to next example...")
        except KeyboardInterrupt:
            print("\n\nExamples interrupted by user.")
            break
        except Exception as e:
            print(f"\n❌ Error in example: {e}")
            import traceback

            traceback.print_exc()
            input("\nPress Enter to continue...")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Circuit breakers provide fail-safe protection")
    print("  2. Multiple breaker types catch different risk scenarios")
    print("  3. Reset requires confirmation code (no bypass)")
    print("  4. Integration with Kelly + Stop Loss = comprehensive risk management")
    print("  5. Trading halts are GOOD - they prevent catastrophic losses")
    print("\nRemember: The goal is to survive and keep trading!")
    print("Circuit breakers ensure you live to trade another day.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
