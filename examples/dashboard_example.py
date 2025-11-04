"""
Dashboard Example - Demonstrates the DeepStack Trading Dashboard.

This example shows how to set up and run the trading dashboard with
live paper trading, risk management systems, and real-time data updates.

Usage:
    python examples/dashboard_example.py

Requirements:
    - Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables
    - Or run without them for demo mode with simulated data
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.broker.paper_trader import PaperTrader
from core.cli.dashboard import TradingDashboard
from core.config import Config
from core.data.alpaca_client import AlpacaClient
from core.risk.circuit_breaker import CircuitBreaker
from core.risk.kelly_position_sizer import KellyPositionSizer
from core.risk.stop_loss_manager import StopLossManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_demo_trader():
    """Setup a paper trader with demo data for demonstration."""
    config = Config()

    # Create paper trader without Alpaca for demo
    trader = PaperTrader(
        config=config,
        alpaca_client=None,  # No live data for demo
        enable_risk_systems=False,  # Simplified demo
        commission_per_trade=1.0,
        commission_per_share=0.005,
        enforce_market_hours=False  # Allow demo anytime
    )

    # Set initial cash
    trader.cash = 85000.0
    trader.initial_cash = 100000.0

    # Add demo positions
    trader.positions = {
        'AAPL': {
            'shares': 100,
            'average_price': 150.00,
            'timestamp': '2025-11-03T09:30:00'
        },
        'MSFT': {
            'shares': 50,
            'average_price': 350.00,
            'timestamp': '2025-11-03T09:35:00'
        },
        'GOOGL': {
            'shares': 30,
            'average_price': 140.00,
            'timestamp': '2025-11-03T09:40:00'
        },
        'AMZN': {
            'shares': 25,
            'average_price': 130.00,
            'timestamp': '2025-11-03T10:00:00'
        }
    }

    # Add demo trade history
    trader.trades = [
        # Morning trades
        {'symbol': 'AAPL', 'side': 'BUY', 'shares': 100, 'price': 150.00,
         'timestamp': '2025-11-03T09:30:00', 'status': 'FILLED', 'realized_pnl': 0},
        {'symbol': 'MSFT', 'side': 'BUY', 'shares': 50, 'price': 350.00,
         'timestamp': '2025-11-03T09:35:00', 'status': 'FILLED', 'realized_pnl': 0},
        {'symbol': 'GOOGL', 'side': 'BUY', 'shares': 50, 'price': 138.00,
         'timestamp': '2025-11-03T09:40:00', 'status': 'FILLED', 'realized_pnl': 0},

        # Profitable trade
        {'symbol': 'GOOGL', 'side': 'SELL', 'shares': 20, 'price': 142.00,
         'timestamp': '2025-11-03T10:30:00', 'status': 'FILLED', 'realized_pnl': 80.00},

        # Loss trade
        {'symbol': 'TSLA', 'side': 'BUY', 'shares': 40, 'price': 250.00,
         'timestamp': '2025-11-03T11:00:00', 'status': 'FILLED', 'realized_pnl': 0},
        {'symbol': 'TSLA', 'side': 'SELL', 'shares': 40, 'price': 245.00,
         'timestamp': '2025-11-03T11:30:00', 'status': 'FILLED', 'realized_pnl': -200.00},

        # Recent trades
        {'symbol': 'AMZN', 'side': 'BUY', 'shares': 25, 'price': 130.00,
         'timestamp': '2025-11-03T14:00:00', 'status': 'FILLED', 'realized_pnl': 0},
        {'symbol': 'NVDA', 'side': 'BUY', 'shares': 15, 'price': 450.00,
         'timestamp': '2025-11-03T14:30:00', 'status': 'FILLED', 'realized_pnl': 0},
        {'symbol': 'NVDA', 'side': 'SELL', 'shares': 15, 'price': 455.00,
         'timestamp': '2025-11-03T15:00:00', 'status': 'FILLED', 'realized_pnl': 75.00},

        # Latest trade
        {'symbol': 'SPY', 'side': 'BUY', 'shares': 10, 'price': 440.00,
         'timestamp': '2025-11-03T15:30:00', 'status': 'PENDING', 'realized_pnl': 0}
    ]

    # Add portfolio history for drawdown calculation
    trader.portfolio_history = [
        100000, 99500, 101000, 102500, 101800, 100500,
        99800, 98500, 99200, 100800, 101500, 102000
    ]

    return trader


def setup_live_trader():
    """Setup a paper trader with live Alpaca data and risk systems."""
    config = Config()

    # Get Alpaca credentials from environment
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not secret_key:
        logger.warning("Alpaca credentials not found. Using demo mode.")
        return setup_demo_trader()

    logger.info("Setting up live paper trader with Alpaca...")

    # Initialize Alpaca client
    alpaca = AlpacaClient(
        api_key=api_key,
        secret_key=secret_key,
        paper_trading=True
    )

    # Setup risk management systems
    kelly_sizer = KellyPositionSizer(
        account_balance=100000.0,
        max_position_pct=0.25,
        max_total_exposure=1.0,
        min_position_size=100.0,
        max_position_size=50000.0
    )

    stop_manager = StopLossManager(
        account_balance=100000.0,
        max_risk_per_trade=0.02,
        default_stop_pct=0.02,
        default_trailing_pct=0.03
    )

    circuit_breaker = CircuitBreaker(
        initial_portfolio_value=100000.0,
        daily_loss_limit=0.05,
        max_drawdown_limit=0.10,
        consecutive_loss_limit=3,
        volatility_threshold=40.0
    )

    # Create enhanced paper trader
    trader = PaperTrader(
        config=config,
        alpaca_client=alpaca,
        kelly_sizer=kelly_sizer,
        stop_manager=stop_manager,
        circuit_breaker=circuit_breaker,
        enable_risk_systems=True,
        commission_per_trade=1.0,
        commission_per_share=0.005,
        enforce_market_hours=True,
        slippage_volatility_multiplier=1.0
    )

    # Initialize with starting capital
    trader.cash = 100000.0
    trader.initial_cash = 100000.0

    return trader, alpaca


async def run_demo():
    """Run dashboard in demo mode with simulated data."""
    logger.info("Starting dashboard in DEMO mode...")
    logger.info("Press 'q' to quit, 'p' to pause, 'r' to refresh")

    # Setup demo trader
    trader = setup_demo_trader()

    # Create dashboard without live data
    dashboard = TradingDashboard(
        paper_trader=trader,
        alpaca_client=None,
        refresh_rate=5,
        theme='default'
    )

    # Override get_portfolio_value for demo
    def demo_portfolio_value():
        positions_value = sum(
            pos['shares'] * (pos['average_price'] * 1.02)  # Simulate 2% gain
            for pos in trader.positions.values()
        )
        return trader.cash + positions_value

    trader.get_portfolio_value = demo_portfolio_value

    # Override performance metrics for demo
    def demo_metrics():
        return {
            'sharpe_ratio': 1.85,
            'max_drawdown': -3.2,
            'win_rate': 65.0,
            'total_trades': 10,
            'winning_trades': 6,
            'losing_trades': 3,
            'avg_win': 485.50,
            'avg_loss': -275.00
        }

    trader.get_performance_metrics = demo_metrics

    # Run the dashboard
    try:
        await dashboard.run()
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")


async def run_live():
    """Run dashboard with live Alpaca data."""
    logger.info("Starting dashboard in LIVE mode with Alpaca...")
    logger.info("Press 'q' to quit, 'p' to pause, 'r' to refresh")

    # Setup live trader
    result = setup_live_trader()
    if isinstance(result, tuple):
        trader, alpaca = result
    else:
        # Fallback to demo if live setup failed
        trader = result
        alpaca = None

    # Create dashboard with live data
    dashboard = TradingDashboard(
        paper_trader=trader,
        alpaca_client=alpaca if 'alpaca' in locals() else None,
        refresh_rate=5,
        theme='default'
    )

    # Run the dashboard
    try:
        await dashboard.run()
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")


def main():
    """Main entry point for the example."""
    print("\n" + "=" * 60)
    print("DeepStack Trading Dashboard Example")
    print("=" * 60)
    print("\nOptions:")
    print("1. Run Demo Mode (no API keys required)")
    print("2. Run Live Mode (requires Alpaca API keys)")
    print("3. Exit")
    print("\n" + "=" * 60)

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        asyncio.run(run_demo())
    elif choice == '2':
        # Check for API keys
        if not os.getenv('ALPACA_API_KEY'):
            print("\n⚠️  Warning: ALPACA_API_KEY not found in environment")
            print("   Falling back to demo mode...")
            print("\nTo use live mode, set environment variables:")
            print("   export ALPACA_API_KEY='your-api-key'")
            print("   export ALPACA_SECRET_KEY='your-secret-key'\n")
            input("Press Enter to continue with demo mode...")
            asyncio.run(run_demo())
        else:
            asyncio.run(run_live())
    elif choice == '3':
        print("\nExiting...\n")
        sys.exit(0)
    else:
        print("\nInvalid option. Please run again and select 1, 2, or 3.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDashboard interrupted by user.\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)