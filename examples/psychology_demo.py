"""
Psychology Module Demo - Comprehensive demonstration of all components

This demo shows:
1. DrawdownMonitor: Progressive position sizing and circuit breaker
2. EmotionalFirewall: Pattern detection and trade blocking
3. TradingTimeOut: Consecutive losses and exponential backoff
4. RecoveryProtocol: Phased recovery after losses
5. Integration: All components working together

Run: python examples/psychology_demo.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.psychology import (
    DrawdownMonitor,
    EmotionalFirewall,
    RecoveryProtocol,
    TradingTimeOut,
)
from core.psychology.recovery_protocol import RecoveryPhase


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_status(label: str, value: any, color: str = ""):
    """Print a formatted status line."""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "end": "\033[0m",
    }

    if color:
        print(f"{label}: {colors.get(color, '')}{value}{colors['end']}")
    else:
        print(f"{label}: {value}")


def demo_drawdown_monitor():
    """Demonstrate DrawdownMonitor functionality."""
    print_header("1. DRAWDOWN MONITOR - Progressive Position Sizing")

    monitor = DrawdownMonitor(
        initial_capital=100000, enable_circuit_breaker=True, enable_logging=False
    )

    print("Starting portfolio: $100,000")
    print("\nSimulating portfolio drawdown...\n")

    # Simulate progressive drawdown
    scenarios = [
        (98000, "2% loss"),
        (95000, "5% loss - No action yet"),
        (92000, "8% loss - REDUCED to 75% sizing"),
        (88000, "12% loss - REDUCED to 50% sizing"),
        (83000, "17% loss - REDUCED to 25% sizing"),
        (79000, "21% loss - CIRCUIT BREAKER!"),
    ]

    for value, description in scenarios:
        status = monitor.update(current_value=value)

        print(f"Portfolio: ${value:,} ({description})")
        print(f"  Drawdown: {status['current_drawdown']:.1%}")

        if status["circuit_breaker"]:
            print_status("  Status", "CIRCUIT BREAKER ACTIVATED", "red")
            print_status("  Position Sizing", "TRADING HALTED (0%)", "red")
        else:
            sizing_color = (
                "green"
                if status["position_size_multiplier"] == 1.0
                else "yellow" if status["position_size_multiplier"] >= 0.5 else "red"
            )
            print_status(
                "  Position Sizing",
                f"{status['position_size_multiplier']:.0%}",
                sizing_color,
            )

        if status["in_recovery"]:
            print("  Recovery Mode: Active")

        print()

    # Demonstrate circuit breaker reset
    print("\nAttempting to reset circuit breaker...")
    success = monitor.reset_circuit_breaker("RESET_TRADING")
    if success:
        print_status("Circuit breaker reset", "SUCCESS", "green")
    else:
        print_status("Circuit breaker reset", "FAILED", "red")

    # Show statistics
    stats = monitor.get_statistics()
    print("\n📊 STATISTICS:")
    print(f"  Max Drawdown: {stats['max_drawdown']:.1%}")
    print(f"  Total Updates: {stats['total_updates']}")
    print(f"  Circuit Breaker Triggers: {stats['circuit_breaker_triggers']}")


def demo_emotional_firewall():
    """Demonstrate EmotionalFirewall functionality."""
    print_header("2. EMOTIONAL FIREWALL - Pattern Detection & Blocking")

    firewall = EmotionalFirewall()

    print("Testing various emotional trading patterns...\n")

    # Test 1: Revenge trading
    print("TEST 1: Revenge Trading")
    firewall.record_trade("AAPL", profit_loss=-1000)
    print("  Recorded loss: AAPL -$1,000")

    result = firewall.should_block_trade("TSLA")
    if result["blocked"]:
        print_status("  Result", "BLOCKED ❌", "red")
        print(f"  Reason: {result['reasons'][0]}")
    else:
        print_status("  Result", "ALLOWED ✓", "green")
    print()

    # Test 2: Win streak (overconfidence)
    print("TEST 2: Win Streak (Overconfidence Risk)")
    firewall.clear_history()
    for i in range(5):
        firewall.record_trade(f"WIN{i}", profit_loss=500)
    print("  Recorded 5 consecutive wins")

    result = firewall.should_block_trade("OVERCONFIDENT")
    if result["blocked"]:
        print_status("  Result", "BLOCKED ❌", "yellow")
        print(f"  Reason: {result['reasons'][0]}")
    else:
        print_status("  Result", "ALLOWED ✓", "green")
    print()

    # Test 3: Loss streak
    print("TEST 3: Loss Streak (Emotional Risk)")
    firewall.clear_history()
    for i in range(5):
        firewall.record_trade(f"LOSS{i}", profit_loss=-300)
    print("  Recorded 5 consecutive losses")

    result = firewall.should_block_trade("DESPERATE")
    if result["blocked"]:
        print_status("  Result", "BLOCKED ❌", "red")
        print(f"  Reason: {result['reasons'][0]}")
        if result["cooldown_expires"]:
            print(f"  Cooldown expires: {result['cooldown_expires'].strftime('%H:%M')}")
    print()

    # Test 4: Overtrading (hourly)
    print("TEST 4: Overtrading (Too Many Trades)")
    firewall.clear_history()
    base_time = datetime.now(firewall.timezone)

    for i in range(3):
        trade_time = base_time + timedelta(minutes=i * 15)
        firewall.record_trade(f"RAPID{i}", profit_loss=100, timestamp=trade_time)
    print("  Recorded 3 trades in 45 minutes")

    result = firewall.should_block_trade(
        "OVERTRADE", timestamp=base_time + timedelta(minutes=50)
    )
    if result["blocked"]:
        print_status("  Result", "BLOCKED ❌", "red")
        print(f"  Reason: {result['reasons'][0]}")
    else:
        print_status("  Result", "ALLOWED ✓", "green")
    print()

    # Test 5: Position size increase after loss
    print("TEST 5: Position Size Increase After Loss")
    firewall.clear_history()
    firewall.record_trade("NORMAL1", profit_loss=100, position_size=5000)
    firewall.record_trade("LOSS", profit_loss=-500, position_size=5000)
    firewall.record_trade("NORMAL2", profit_loss=100, position_size=5000)
    print("  Recent trades: $5,000 positions, one loss")

    result = firewall.should_block_trade("BIG", position_size=8000)
    print("  Attempting $8,000 position (60% increase)")
    if result["blocked"]:
        print_status("  Result", "BLOCKED ❌", "red")
        print(f"  Reason: {result['reasons'][0]}")
    else:
        print_status("  Result", "ALLOWED ✓", "green")
    print()

    # Show statistics
    stats = firewall.get_statistics()
    print("📊 STATISTICS:")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Blocked Trades: {stats['blocked_trades']}")
    if stats["total_trades"] > 0:
        print(f"  Block Rate: {stats['block_rate']:.1%}")


def demo_trading_timeout():
    """Demonstrate TradingTimeOut functionality."""
    print_header("3. TRADING TIMEOUT - Exponential Backoff")

    timeout = TradingTimeOut(
        consecutive_loss_limit=3,
        daily_loss_limit_pct=0.02,
        portfolio_value=100000,
        enable_logging=False,
    )

    print("Configuration:")
    print("  Consecutive loss limit: 3")
    print("  Daily loss limit: 2% ($2,000)")
    print("  Portfolio value: $100,000\n")

    # Test consecutive losses
    print("Simulating consecutive losses...\n")

    for i in range(3):
        status = timeout.record_loss(f"LOSS{i+1}", loss_amount=500)
        print(f"Loss {i+1}: ${500}")
        print(f"  Consecutive losses: {status['consecutive_losses']}")

        if status["in_timeout"]:
            print_status("  Status", "TIMEOUT TRIGGERED", "red")
            print(f"  Reason: {status['reason']}")
            if status["time_remaining"]:
                print(f"  Duration: {status['time_remaining']['formatted']}")
            break
        else:
            print_status("  Status", "OK", "green")
        print()

    # Show next timeout duration
    next_duration = timeout.get_next_timeout_duration()
    print(f"\nNext timeout would be: {next_duration} minutes")

    # Test timeout override
    print("\nAttempting to override timeout...")
    success = timeout.override_timeout("OVERRIDE_TIMEOUT")
    if success:
        print_status("Override", "SUCCESS", "green")
    else:
        print_status("Override", "FAILED", "red")

    # Test daily loss limit
    print("\n\nTesting daily loss limit...")
    timeout = TradingTimeOut(
        consecutive_loss_limit=10,  # High limit so it doesn't trigger
        daily_loss_limit_pct=0.02,
        portfolio_value=100000,
        enable_logging=False,
    )

    status = timeout.record_loss("BIG_LOSS", loss_amount=2500)
    print(f"Single loss: $2,500 (2.5% of portfolio)")

    if status["in_timeout"]:
        print_status("Status", "TIMEOUT TRIGGERED", "red")
        print(f"Reason: {status['reason']}")
        print(f"Daily loss: ${status['daily_loss_amount']:.2f}")

    # Show statistics
    stats = timeout.get_statistics()
    print("\n📊 STATISTICS:")
    print(f"  Total Losses Recorded: {stats['total_losses_recorded']}")
    print(f"  Total Timeouts Triggered: {stats['total_timeouts_triggered']}")
    print(f"  Total Timeout Minutes: {stats['total_timeout_minutes']}")


def demo_recovery_protocol():
    """Demonstrate RecoveryProtocol functionality."""
    print_header("4. RECOVERY PROTOCOL - Phased Recovery System")

    protocol = RecoveryProtocol(
        entry_drawdown=0.15, portfolio_value=85000, enable_logging=False
    )

    print("Entry Conditions:")
    print("  Entry drawdown: 15%")
    print("  Portfolio value: $85,000")
    print("  Starting phase: Phase 1 (Conservative)\n")

    # Show phase requirements
    print("PHASE REQUIREMENTS:")
    print("  Phase 1: 50% sizing, need 5 trades @ 60% win rate, 3% profit")
    print("  Phase 2: 75% sizing, need 3 trades @ 60% win rate, 2% profit")
    print("  Phase 3: 100% sizing (full recovery)\n")

    # Phase 1: Conservative
    print("📍 PHASE 1: CONSERVATIVE (50% Sizing)")
    print("Recording profitable trades...\n")

    trades = [
        ("AAPL", 550),
        ("TSLA", 600),
        ("MSFT", 450),
        ("GOOGL", 700),
        ("AMZN", 500),
    ]

    for symbol, profit in trades:
        protocol.record_trade(profit_loss=profit, symbol=symbol)
        print(f"  ✓ {symbol}: +${profit}")

    status = protocol.get_status()
    print(f"\nPhase 1 Results:")
    print(f"  Total profit: ${status['phase_profit_loss']:,.2f}")
    print(f"  Phase return: {status['phase_return']:+.1%}")
    print(f"  Win rate: {status['phase_win_rate']:.0%}")

    # Check advancement
    check = protocol.can_advance_phase()
    print(f"\nAdvancement Check:")
    if check["can_advance"]:
        print_status("  Status", "READY TO ADVANCE ✓", "green")
        protocol.advance_phase()
        print(f"  Advanced to: {protocol.current_phase.value}")
    else:
        print_status("  Status", "NOT READY", "yellow")
        for reason in check["blocking_reasons"]:
            print(f"  - {reason}")

    # Phase 2: Cautious
    print("\n📍 PHASE 2: CAUTIOUS (75% Sizing)")
    print("Recording more profitable trades...\n")

    trades = [("NVDA", 450), ("META", 500), ("NFLX", 400)]

    for symbol, profit in trades:
        protocol.record_trade(profit_loss=profit, symbol=symbol)
        print(f"  ✓ {symbol}: +${profit}")

    status = protocol.get_status()
    print(f"\nPhase 2 Results:")
    print(f"  Total profit: ${status['phase_profit_loss']:,.2f}")
    print(f"  Phase return: {status['phase_return']:+.1%}")

    # Check advancement to Phase 3
    check = protocol.can_advance_phase()
    if check["can_advance"]:
        print_status("\nAdvancement Check", "READY TO ADVANCE ✓", "green")
        protocol.advance_phase()
        print(f"Advanced to: {protocol.current_phase.value}")

    # Phase 3: Full Recovery
    if protocol.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY:
        print("\n🎉 FULL RECOVERY ACHIEVED!")
        print_status("  Position Sizing", "100% (FULL)", "green")

    # Show final statistics
    stats = protocol.get_statistics()
    print("\n📊 FINAL STATISTICS:")
    print(f"  Entry Drawdown: {stats['entry_drawdown']:.1%}")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Phases Completed: {stats['total_phases_completed']}")
    print(f"  Total Return: {stats['total_return']:+.1%}")
    print(f"  Final Value: ${stats['current_value']:,.2f}")


def demo_integration():
    """Demonstrate all components working together."""
    print_header("5. INTEGRATION - All Components Working Together")

    # Initialize all components
    monitor = DrawdownMonitor(initial_capital=100000, enable_logging=False)
    firewall = EmotionalFirewall()
    timeout = TradingTimeOut(portfolio_value=100000, enable_logging=False)
    recovery = None

    print("Simulating realistic trading scenario with all psychology guards...\n")

    # Scenario: Series of losing trades
    print("SCENARIO: String of losing trades")
    print("-" * 60)

    trades = [
        ("AAPL", -800),
        ("TSLA", -600),
        ("MSFT", -700),
        ("GOOGL", -500),
    ]

    for i, (symbol, pnl) in enumerate(trades, 1):
        print(f"\nTrade {i}: {symbol} P/L: ${pnl}")

        # Update all systems
        new_value = monitor.current_value + pnl
        monitor.update(new_value)
        firewall.record_trade(symbol, pnl, position_size=5000)
        timeout.record_loss(symbol, abs(pnl))

        # Check drawdown
        status = monitor.get_status()
        print(f"  Portfolio: ${monitor.current_value:,.2f}")
        print(
            f"  Drawdown: {status['current_drawdown']:.1%} "
            f"(Sizing: {status['position_size_multiplier']:.0%})"
        )

        # Check timeout
        timeout_status = timeout.check_timeout()
        if timeout_status["in_timeout"]:
            print_status("  Timeout", "ACTIVE", "red")

        # Check if should enter recovery
        if (
            monitor.current_drawdown > 0.10
            and not recovery
            and not status["circuit_breaker"]
        ):
            recovery = RecoveryProtocol(
                entry_drawdown=monitor.current_drawdown,
                portfolio_value=monitor.current_value,
                enable_logging=False,
            )
            print_status("  Recovery", "ENTERED PHASE 1", "yellow")

    # Try to make another trade
    print("\n" + "-" * 60)
    print("\nAttempting next trade: AMZN")

    # Check all guards
    can_trade = True
    reasons = []

    if not monitor.is_trading_allowed():
        can_trade = False
        reasons.append("Circuit breaker active")

    if timeout.is_in_timeout():
        can_trade = False
        reasons.append("Trading timeout active")

    firewall_check = firewall.should_block_trade("AMZN", position_size=5000)
    if firewall_check["blocked"]:
        can_trade = False
        reasons.extend(firewall_check["reasons"])

    if can_trade:
        print_status("Trade Decision", "ALLOWED ✓", "green")
        if recovery:
            multiplier = recovery.get_position_size_multiplier()
            print(f"  Position sizing: {multiplier:.0%} (recovery adjustment)")
    else:
        print_status("Trade Decision", "BLOCKED ❌", "red")
        print("  Reasons:")
        for reason in reasons:
            print(f"    - {reason}")

    # Show summary
    print("\n" + "=" * 60)
    print("PROTECTION SUMMARY:")
    print("=" * 60)

    mon_stats = monitor.get_statistics()
    fw_stats = firewall.get_statistics()
    to_stats = timeout.get_statistics()

    print(f"\n📊 Drawdown Monitor:")
    print(f"  Max Drawdown: {mon_stats['max_drawdown']:.1%}")
    print(
        f"  Circuit Breaker: {'Active' if monitor.circuit_breaker_active else 'Inactive'}"
    )

    print(f"\n🛡️ Emotional Firewall:")
    print(f"  Trades Blocked: {fw_stats['blocked_trades']}")
    print(
        f"  Current Streak: {fw_stats['current_streak']['count']} {fw_stats['current_streak']['type'] or 'none'}"
    )

    print(f"\n⏰ Trading Timeout:")
    print(f"  Timeouts Triggered: {to_stats['total_timeouts_triggered']}")
    print(f"  In Timeout: {'Yes' if timeout.is_in_timeout() else 'No'}")

    if recovery:
        rec_status = recovery.get_status()
        print(f"\n🏥 Recovery Protocol:")
        print(f"  Current Phase: {rec_status['current_phase']}")
        print(f"  Position Sizing: {rec_status['position_size_multiplier']:.0%}")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "DEEPSTACK PSYCHOLOGY MODULE DEMO" + " " * 31 + "║")
    print("║" + " " * 15 + "Emotional Trading Protection System" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        demo_drawdown_monitor()
        input("\nPress Enter to continue to next demo...")

        demo_emotional_firewall()
        input("\nPress Enter to continue to next demo...")

        demo_trading_timeout()
        input("\nPress Enter to continue to next demo...")

        demo_recovery_protocol()
        input("\nPress Enter to continue to integration demo...")

        demo_integration()

        print_header("DEMO COMPLETE")
        print("All psychology components demonstrated successfully! ✓")
        print("\nKey Takeaways:")
        print("  1. DrawdownMonitor: Prevents cascading losses with progressive sizing")
        print("  2. EmotionalFirewall: Blocks impulsive revenge trading and patterns")
        print("  3. TradingTimeOut: Enforces breaks after losses with backoff")
        print("  4. RecoveryProtocol: Gradual return to full sizing after drawdowns")
        print("  5. Integration: All components work together for maximum protection")
        print("\nFor more information, see: docs/PSYCHOLOGY_MODULE.md")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
