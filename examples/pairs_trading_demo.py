"""
Pairs Trading Strategy Demo

Demonstrates:
1. Screening for cointegrated pairs
2. Real-time signal generation
3. Backtesting pairs
4. Live monitoring dashboard

Example pairs:
- KO/PEP (Coca-Cola / PepsiCo)
- DAL/UAL (Delta / United Airlines)
- F/GM (Ford / General Motors)
- V/MA (Visa / Mastercard)
- XOM/CVX (Exxon / Chevron)
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategies.pairs_trading import (
    PairStatus,
    PairsTradingStrategy,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_mock_price_data(
    symbols: list, days: int = 252, cointegrated: bool = True
) -> pd.DataFrame:
    """
    Generate mock price data for testing.

    Args:
        symbols: List of symbols
        days: Number of days of data
        cointegrated: Whether to make pairs cointegrated

    Returns:
        DataFrame with price data
    """
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    if cointegrated and len(symbols) >= 2:
        # Create cointegrated pairs
        data = {}

        for i in range(0, len(symbols), 2):
            if i + 1 < len(symbols):
                # Base price series (random walk)
                base = 100 + np.cumsum(np.random.randn(days) * 0.5)

                # First asset
                data[symbols[i]] = base + np.random.randn(days) * 2

                # Second asset (cointegrated with first)
                hedge_ratio = 0.9 + np.random.rand() * 0.4  # 0.9 to 1.3
                data[symbols[i + 1]] = base * hedge_ratio + np.random.randn(days) * 2
            else:
                # Odd one out - independent
                data[symbols[i]] = 100 + np.cumsum(np.random.randn(days))

    else:
        # Independent random walks
        data = {symbol: 100 + np.cumsum(np.random.randn(days)) for symbol in symbols}

    df = pd.DataFrame(data, index=dates)
    return df


def demo_pair_screening():
    """Demo: Screen for cointegrated pairs"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 1: Pair Screening")
    logger.info("=" * 60)

    # Initialize strategy
    strategy = PairsTradingStrategy(
        adf_p_value_threshold=0.05,
        entry_z_threshold=2.0,
        exit_z_threshold=0.5,
        stop_z_threshold=3.5,
    )

    # Define universe of potential pairs
    universe = ["KO", "PEP", "DAL", "UAL", "F", "GM", "V", "MA", "XOM", "CVX"]

    logger.info(f"Screening {len(universe)} assets for cointegrated pairs...")

    # Generate mock price data (cointegrated pairs)
    price_data = generate_mock_price_data(universe, days=252, cointegrated=True)

    logger.info(f"Price data shape: {price_data.shape}")
    logger.info(f"Date range: {price_data.index[0]} to {price_data.index[-1]}")

    # Screen for pairs
    pairs = strategy.screen_for_pairs(universe, price_data)

    logger.info(f"\nFound {len(pairs)} cointegrated pairs:")

    for i, pair in enumerate(pairs, 1):
        logger.info(
            f"{i}. {pair.asset_a}/{pair.asset_b}: "
            f"hedge_ratio={pair.hedge_ratio:.4f}, "
            f"p_value={pair.cointegration_test.p_value:.4f}"
        )

    return pairs, price_data


def demo_signal_generation(pairs, price_data):
    """Demo: Generate trading signals"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 2: Signal Generation")
    logger.info("=" * 60)

    if not pairs:
        logger.warning("No pairs available for signal generation")
        return

    strategy = PairsTradingStrategy()

    # Monitor all pairs for signals
    logger.info(f"Monitoring {len(pairs)} pairs for trading signals...")

    signals = strategy.monitor_pairs(pairs, price_data)

    if signals:
        logger.info(f"\nGenerated {len(signals)} trading signals:")

        for i, signal in enumerate(signals, 1):
            logger.info(
                f"{i}. {signal.asset_a}/{signal.asset_b}: "
                f"{signal.signal_type} (z={signal.z_score:.2f}, "
                f"confidence={signal.confidence:.1f}%)"
            )
    else:
        logger.info("No signals generated (no extreme z-scores)")

    # Force demonstration by creating extreme spread
    if len(pairs) > 0:
        logger.info("\nDemonstrating signal types with modified data...")

        demo_pair = pairs[0]

        # Create entry signal (high z-score)
        logger.info(
            f"\nTesting entry signal for {demo_pair.asset_a}/{demo_pair.asset_b}"
        )

        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        np.random.seed(123)

        # Create spread with high z-score
        base = pd.Series(100 + np.random.randn(30) * 0.5, index=dates)
        modified_data = pd.DataFrame(
            {
                demo_pair.asset_a: base + 10,  # Push spread high
                demo_pair.asset_b: base * demo_pair.hedge_ratio - 5,
            }
        )

        signal = strategy.generate_signals(demo_pair, modified_data)

        if signal:
            logger.info(
                f"Signal: {signal.signal_type}, z-score: {signal.z_score:.2f}, "
                f"confidence: {signal.confidence:.1f}%"
            )
        else:
            logger.info("No signal generated")


def demo_backtesting(pairs, price_data):
    """Demo: Backtest pairs"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 3: Backtesting")
    logger.info("=" * 60)

    if not pairs:
        logger.warning("No pairs available for backtesting")
        return []

    strategy = PairsTradingStrategy()

    logger.info(f"Backtesting {len(pairs)} pairs...")

    # Validate all pairs
    results = strategy.validate_pairs(pairs, price_data)

    logger.info("\nBacktest Results (sorted by return):\n")

    for i, result in enumerate(results, 1):
        logger.info(
            f"{i}. {result['pair']}: "
            f"{result['total_trades']} trades, "
            f"{result['win_rate']*100:.1f}% win rate, "
            f"{result['return_pct']:+.2f}% return"
        )

        if result["total_trades"] > 0:
            avg_win = np.mean(
                [t.get("pnl", 0) for t in result["trades"] if t.get("pnl", 0) > 0]
                or [0]
            )
            avg_loss = np.mean(
                [t.get("pnl", 0) for t in result["trades"] if t.get("pnl", 0) < 0]
                or [0]
            )

            logger.info(f"   Avg Win: ${avg_win:.2f}, Avg Loss: ${avg_loss:.2f}")

    # Show top performing pair details
    if results and results[0]["total_trades"] > 0:
        logger.info(f"\nTop Performer: {results[0]['pair']}")
        logger.info("First 5 trades:")

        for i, trade in enumerate(results[0]["trades"][:5], 1):
            if "exit_date" in trade:
                logger.info(
                    f"  {i}. {trade['position']} entry @ z={trade['entry_z']:.2f}, "
                    f"exit @ z={trade['exit_z']:.2f}, PnL: ${trade['pnl']:.2f}"
                )

    return results


def demo_live_monitoring():
    """Demo: Simulate live monitoring"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 4: Live Monitoring Simulation")
    logger.info("=" * 60)

    strategy = PairsTradingStrategy()

    # Create a sample pair
    universe = ["STOCK_A", "STOCK_B"]
    logger.info(f"Setting up live monitoring for {universe[0]}/{universe[1]}...")

    # Generate initial data
    price_data = generate_mock_price_data(universe, days=100, cointegrated=True)

    # Find pair
    pairs = strategy.screen_for_pairs(universe, price_data)

    if not pairs:
        logger.warning("Failed to create cointegrated pair for demo")
        return

    pair = pairs[0]

    logger.info(
        f"Monitoring pair: {pair.asset_a}/{pair.asset_b} "
        f"(hedge_ratio={pair.hedge_ratio:.4f})"
    )

    # Simulate 10 days of live monitoring
    logger.info("\nSimulating 10 days of live trading...")

    for day in range(10):
        # Add one more day of data
        new_price_a = price_data[pair.asset_a].iloc[-1] + np.random.randn() * 2
        new_price_b = price_data[pair.asset_b].iloc[-1] + np.random.randn() * 2

        new_date = price_data.index[-1] + timedelta(days=1)
        new_row = pd.DataFrame(
            {pair.asset_a: [new_price_a], pair.asset_b: [new_price_b]},
            index=[new_date],
        )

        price_data = pd.concat([price_data, new_row])

        # Calculate current spread statistics
        spread_stats = strategy.calculate_spread_statistics(pair, price_data)

        # Generate signal
        signal = strategy.generate_signals(pair, price_data)

        logger.info(
            f"Day {day+1}: {pair.asset_a}=${new_price_a:.2f}, "
            f"{pair.asset_b}=${new_price_b:.2f}, "
            f"z-score={spread_stats.z_score:.2f}"
        )

        if signal:
            logger.info(
                f"  >>> SIGNAL: {signal.signal_type} "
                f"(confidence={signal.confidence:.1f}%)"
            )

            # Update pair status based on signal
            if signal.signal_type == "entry_long":
                pair.update_status(PairStatus.LONG_SPREAD)
                pair.entry_z_score = signal.z_score
                logger.info("  >>> ENTERED LONG POSITION")

            elif signal.signal_type == "entry_short":
                pair.update_status(PairStatus.SHORT_SPREAD)
                pair.entry_z_score = signal.z_score
                logger.info("  >>> ENTERED SHORT POSITION")

            elif signal.signal_type in ["exit", "stop"]:
                if pair.status != PairStatus.NO_POSITION:
                    logger.info(
                        f"  >>> EXITED POSITION (entered @ z={pair.entry_z_score:.2f})"
                    )
                pair.update_status(PairStatus.NO_POSITION)
                pair.entry_z_score = None

    logger.info("\nLive monitoring simulation complete")


def demo_portfolio_statistics():
    """Demo: Calculate portfolio-level statistics"""
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 5: Portfolio Statistics")
    logger.info("=" * 60)

    # Run screening and backtesting
    pairs, price_data = demo_pair_screening()

    if not pairs:
        logger.warning("No pairs found for portfolio analysis")
        return

    strategy = PairsTradingStrategy()
    results = strategy.validate_pairs(pairs, price_data)

    # Calculate portfolio metrics
    total_trades = sum(r["total_trades"] for r in results)
    winning_trades = sum(r["winning_trades"] for r in results)
    total_pnl = sum(r["total_pnl"] for r in results)

    logger.info("\nPortfolio-Level Statistics:")
    logger.info(f"Total Pairs: {len(pairs)}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Winning Trades: {winning_trades}")
    logger.info(f"Overall Win Rate: {winning_trades/total_trades*100:.1f}%")
    logger.info(f"Total PnL: ${total_pnl:,.2f}")

    # Find best and worst pairs
    if results:
        best_pair = max(results, key=lambda x: x["return_pct"])
        worst_pair = min(results, key=lambda x: x["return_pct"])

        logger.info(
            f"\nBest Pair: {best_pair['pair']} ({best_pair['return_pct']:+.2f}%)"
        )
        logger.info(
            f"Worst Pair: {worst_pair['pair']} ({worst_pair['return_pct']:+.2f}%)"
        )

        # Profitable pairs
        profitable = [r for r in results if r["return_pct"] > 0]
        prof_pct = len(profitable) / len(results) * 100
        logger.info(
            f"\nProfitable Pairs: {len(profitable)}/{len(results)} "
            f"({prof_pct:.1f}%)"
        )


def main():
    """Run all demos"""
    logger.info("=" * 60)
    logger.info("PAIRS TRADING STRATEGY DEMO")
    logger.info("=" * 60)

    try:
        # Demo 1: Pair screening
        pairs, price_data = demo_pair_screening()

        # Demo 2: Signal generation
        demo_signal_generation(pairs, price_data)

        # Demo 3: Backtesting
        demo_backtesting(pairs, price_data)

        # Demo 4: Live monitoring
        demo_live_monitoring()

        # Demo 5: Portfolio statistics
        demo_portfolio_statistics()

        logger.info("\n" + "=" * 60)
        logger.info("ALL DEMOS COMPLETE")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
