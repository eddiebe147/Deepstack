#!/usr/bin/env python3
"""
Options Trading Strategies Demo

Demonstrates the usage of DeepStack's options strategies:
- Iron Condor
- Bull Call Spread
- Bear Put Spread
- Greeks calculation
- P&L modeling
- Risk management
"""


from core.strategies.options import (
    BearPutSpread,
    BullCallSpread,
    IronCondorStrategy,
    calculate_position_greeks,
)
from core.strategies.options.pnl_modeling import (
    calculate_pnl_at_expiration,
    calculate_roi,
    get_risk_reward_ratio,
)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_iron_condor():
    """Demonstrate Iron Condor strategy."""
    print_section("IRON CONDOR DEMO")

    # Create strategy
    strategy = IronCondorStrategy(
        wing_width=5.0,
        range_width_pct=0.05,
        profit_target_pct=0.50,
        loss_limit_pct=0.50,
    )

    print("Creating Iron Condor position on SPY...")
    print("Current price: $400.00")
    print("Expiration: 45 days")
    print("Contracts: 2\n")

    # Create position
    position = strategy.create_position(
        symbol="SPY",
        underlying_price=400.0,
        expiration_days=45,
        contracts=2,
        volatility=0.20,
    )

    print("Position Details:")
    print(f"  Strategy: {position.strategy_name}")
    print(f"  Legs: {len(position.legs)}")
    print()

    # Show each leg
    for i, leg in enumerate(position.legs, 1):
        action_str = leg.action.upper()
        type_str = leg.option_type.upper()
        leg_str = (
            f"  Leg {i}: {action_str} {leg.quantity} {type_str} "
            f"${leg.strike:.2f} @ ${leg.premium:.2f}"
        )
        print(leg_str)

    print()
    print("Risk/Reward:")
    print(f"  Net Credit: ${position.net_credit_received():.2f}")
    print(f"  Max Profit: ${position.max_profit:.2f}")
    print(f"  Max Loss: ${position.max_loss:.2f}")
    print(f"  Risk/Reward Ratio: {get_risk_reward_ratio(position):.2f}")
    be_str = (
        f"  Breakeven Points: ${position.breakeven_points[0]:.2f} - "
        f"${position.breakeven_points[1]:.2f}"
    )
    print(be_str)
    print()

    # Calculate Greeks
    print("Position Greeks:")
    greeks = calculate_position_greeks(
        position=position,
        underlying_price=400.0,
        days_to_expiration=45,
        volatility=0.20,
    )
    print(f"  Delta: {greeks.delta:.4f} (nearly neutral)")
    print(f"  Gamma: {greeks.gamma:.4f}")
    print(f"  Theta: {greeks.theta:.4f} (per day - positive is good for sellers)")
    print(f"  Vega: {greeks.vega:.4f} (per 1% IV change)")
    print()

    # Simulate price movements
    print("P&L at Different Prices (30 DTE):")
    test_prices = [380, 390, 400, 410, 420]
    for price in test_prices:
        pnl = strategy.calculate_pnl(
            position=position,
            current_price=price,
            days_to_expiration=30,
            volatility=0.20,
        )
        roi = calculate_roi(position, pnl)
        should_close = strategy.should_close(position, pnl, 30)

        status = ""
        if should_close:
            reason = strategy.get_close_reason(position, pnl, 30)
            status = f" - CLOSE ({reason})"

        print(f"  ${price:>5.0f}: P&L = ${pnl:>7.2f} ({roi:>6.1%} ROI){status}")


def demo_bull_call_spread():
    """Demonstrate Bull Call Spread strategy."""
    print_section("BULL CALL SPREAD DEMO")

    # Create strategy
    strategy = BullCallSpread(
        strike_width=5.0, profit_target_pct=0.70, loss_limit_pct=0.50
    )

    print("Creating Bull Call Spread on AAPL...")
    print("Current price: $150.00")
    print("Outlook: Moderately bullish")
    print("Expiration: 45 days\n")

    # Create position
    position = strategy.create_position(
        symbol="AAPL",
        underlying_price=150.0,
        expiration_days=45,
        contracts=1,
        volatility=0.30,
    )

    print("Position Details:")
    print(f"  Strategy: {position.strategy_name}")
    print()

    # Show each leg
    for i, leg in enumerate(position.legs, 1):
        action_str = leg.action.upper()
        leg_str = (
            f"  Leg {i}: {action_str} {leg.quantity} CALL "
            f"${leg.strike:.2f} @ ${leg.premium:.2f}"
        )
        print(leg_str)

    print()
    print("Risk/Reward:")
    print(f"  Net Debit: ${position.net_debit_paid():.2f}")
    print(f"  Max Profit: ${position.max_profit:.2f}")
    print(f"  Max Loss: ${position.max_loss:.2f}")
    print(f"  Risk/Reward Ratio: {get_risk_reward_ratio(position):.2f}")
    print(f"  Breakeven: ${position.breakeven_points[0]:.2f}")
    print()

    # Calculate Greeks
    print("Position Greeks:")
    greeks = calculate_position_greeks(
        position=position,
        underlying_price=150.0,
        days_to_expiration=45,
        volatility=0.30,
    )
    print(f"  Delta: {greeks.delta:.4f} (positive = bullish)")
    print(f"  Gamma: {greeks.gamma:.4f}")
    print(f"  Theta: {greeks.theta:.4f} (per day)")
    print(f"  Vega: {greeks.vega:.4f} (per 1% IV change)")
    print()

    # P&L at expiration
    print("P&L at Expiration:")
    exp_scenarios = calculate_pnl_at_expiration(position, num_points=11)

    for price in sorted(exp_scenarios.keys()):
        pnl = exp_scenarios[price]
        roi = calculate_roi(position, pnl)

        status = ""
        if pnl >= position.max_profit * 0.95:
            status = " [MAX PROFIT]"
        elif pnl <= -position.max_loss * 0.95:
            status = " [MAX LOSS]"
        elif abs(pnl) < 10:
            status = " [BREAKEVEN]"

        print(f"  ${price:>6.2f}: ${pnl:>7.2f} ({roi:>6.1%}){status}")


def demo_bear_put_spread():
    """Demonstrate Bear Put Spread strategy."""
    print_section("BEAR PUT SPREAD DEMO")

    # Create strategy
    strategy = BearPutSpread(
        strike_width=5.0, profit_target_pct=0.70, loss_limit_pct=0.50
    )

    print("Creating Bear Put Spread on AAPL...")
    print("Current price: $150.00")
    print("Outlook: Moderately bearish")
    print("Expiration: 45 days\n")

    # Create position
    position = strategy.create_position(
        symbol="AAPL",
        underlying_price=150.0,
        expiration_days=45,
        contracts=1,
        volatility=0.30,
    )

    print("Position Details:")
    print(f"  Strategy: {position.strategy_name}")
    print()

    # Show each leg
    for i, leg in enumerate(position.legs, 1):
        action_str = leg.action.upper()
        leg_str = (
            f"  Leg {i}: {action_str} {leg.quantity} PUT "
            f"${leg.strike:.2f} @ ${leg.premium:.2f}"
        )
        print(leg_str)

    print()
    print("Risk/Reward:")
    print(f"  Net Debit: ${position.net_debit_paid():.2f}")
    print(f"  Max Profit: ${position.max_profit:.2f}")
    print(f"  Max Loss: ${position.max_loss:.2f}")
    print(f"  Risk/Reward Ratio: {get_risk_reward_ratio(position):.2f}")
    print(f"  Breakeven: ${position.breakeven_points[0]:.2f}")
    print()

    # Calculate Greeks
    print("Position Greeks:")
    greeks = calculate_position_greeks(
        position=position,
        underlying_price=150.0,
        days_to_expiration=45,
        volatility=0.30,
    )
    print(f"  Delta: {greeks.delta:.4f} (negative = bearish)")
    print(f"  Gamma: {greeks.gamma:.4f}")
    print(f"  Theta: {greeks.theta:.4f} (per day)")
    print(f"  Vega: {greeks.vega:.4f} (per 1% IV change)")


def demo_pnl_modeling():
    """Demonstrate P&L scenario modeling."""
    print_section("P&L SCENARIO MODELING")

    # Create an Iron Condor
    strategy = IronCondorStrategy(wing_width=5.0, range_width_pct=0.05)
    position = strategy.create_position(
        symbol="SPY",
        underlying_price=400.0,
        expiration_days=45,
        contracts=1,
        volatility=0.20,
    )

    print("Modeling Iron Condor P&L across price range...\n")

    # Model at different time periods
    time_periods = [45, 30, 15, 0]

    print("Price | 45 DTE | 30 DTE | 15 DTE | Expiration")
    print("-" * 60)

    # Test prices
    test_prices = [380, 390, 395, 400, 405, 410, 420]

    for price in test_prices:
        pnls = []
        for dte in time_periods:
            if dte == 0:
                # Use expiration calculation
                exp_scenarios = calculate_pnl_at_expiration(
                    position, price_range=[price]
                )
                pnl = exp_scenarios[price]
            else:
                pnl = strategy.calculate_pnl(
                    position=position,
                    current_price=price,
                    days_to_expiration=dte,
                    volatility=0.20,
                )
            pnls.append(pnl)

        row_str = (
            f"${price:>3.0f}  | ${pnls[0]:>6.2f} | ${pnls[1]:>6.2f} | "
            f"${pnls[2]:>6.2f} | ${pnls[3]:>8.2f}"
        )
        print(row_str)

    print()
    print("Observations:")
    print("  - P&L converges to expiration value as time passes")
    print("  - Time decay benefits sellers (positive P&L growth at center)")
    print("  - P&L becomes more binary near expiration")
    print("  - Early exit captures value while managing risk")


def demo_greeks_sensitivity():
    """Demonstrate Greeks sensitivity analysis."""
    print_section("GREEKS SENSITIVITY ANALYSIS")

    # Create a Bull Call Spread
    strategy = BullCallSpread(strike_width=5.0)
    position = strategy.create_position(
        symbol="AAPL",
        underlying_price=150.0,
        expiration_days=45,
        contracts=1,
        volatility=0.30,
    )

    print("Bull Call Spread Greeks at Different Prices:\n")
    print("Price | Delta  | Gamma  | Theta  | Vega")
    print("-" * 50)

    test_prices = [140, 145, 150, 155, 160]
    for price in test_prices:
        greeks = calculate_position_greeks(
            position=position,
            underlying_price=price,
            days_to_expiration=45,
            volatility=0.30,
        )
        print(
            f"${price:>3.0f}  | {greeks.delta:>6.4f} | {greeks.gamma:>6.4f} | "
            f"{greeks.theta:>6.4f} | {greeks.vega:>6.4f}"
        )

    print()
    print("Observations:")
    print("  - Delta increases as price rises (more bullish)")
    print("  - Gamma peaks near the strikes (max convexity)")
    print("  - Theta shows time decay impact")
    print("  - Vega shows volatility sensitivity")


def demo_risk_management():
    """Demonstrate risk management concepts."""
    print_section("RISK MANAGEMENT EXAMPLES")

    print("Position Sizing Example:")
    print("  Account size: $50,000")
    print("  Risk per trade: 2% = $1,000")
    print()

    # Iron Condor sizing
    ic_strategy = IronCondorStrategy(wing_width=5.0)
    ic_position = ic_strategy.create_position(
        symbol="SPY", underlying_price=400.0, expiration_days=45, contracts=1
    )

    print("Iron Condor:")
    print(f"  Max loss per contract: ${ic_position.max_loss:.2f}")
    max_contracts_ic = int(1000 / ic_position.max_loss)
    print(f"  Max contracts (2% risk): {max_contracts_ic}")
    print()

    # Bull Call Spread sizing
    bcs_strategy = BullCallSpread(strike_width=5.0)
    bcs_position = bcs_strategy.create_position(
        symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
    )

    print("Bull Call Spread:")
    print(f"  Max loss per contract: ${bcs_position.max_loss:.2f}")
    max_contracts_bcs = int(1000 / bcs_position.max_loss)
    print(f"  Max contracts (2% risk): {max_contracts_bcs}")
    print()

    print("Exit Strategy Guidelines:")
    print("  Profit Targets:")
    print("    - Iron Condor: Close at 50% of max profit")
    print("    - Vertical Spreads: Close at 70% of max profit")
    print()
    print("  Loss Limits:")
    print("    - Close at 50% of max loss")
    print("    - Don't let losses run to full max loss")
    print()
    print("  Time-Based:")
    print("    - Close at 21 DTE if not at profit target")
    print("    - Avoid gamma risk as expiration approaches")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  DEEPSTACK OPTIONS STRATEGIES DEMO")
    print("=" * 70)
    print("\n  Demonstrating advanced options trading strategies")
    print("  with Greeks calculation and P&L modeling.\n")

    # Run demos
    demo_iron_condor()
    demo_bull_call_spread()
    demo_bear_put_spread()
    demo_pnl_modeling()
    demo_greeks_sensitivity()
    demo_risk_management()

    print_section("DEMO COMPLETE")
    print("See docs/OPTIONS_STRATEGIES.md for detailed documentation.")
    print("Use the PaperTrader to test strategies risk-free!\n")


if __name__ == "__main__":
    main()
