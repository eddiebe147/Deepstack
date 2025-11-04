"""
Command-line interface for DeepStack Trading Dashboard.

Provides the main entry point for running the trading dashboard from the command line.
Supports various options for configuring the dashboard behavior.

Usage:
    python -m core.cli dashboard [options]
    python -m core.cli dashboard --refresh-rate 10
    python -m core.cli dashboard --no-auto-refresh
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.broker.paper_trader import PaperTrader
from core.cli.dashboard import TradingDashboard
from core.config import Config
from core.data.alpaca_client import AlpacaClient
from core.risk.circuit_breaker import CircuitBreaker
from core.risk.kelly_position_sizer import KellyPositionSizer
from core.risk.stop_loss_manager import StopLossManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the CLI dashboard."""
    parser = argparse.ArgumentParser(
        description="DeepStack Trading Dashboard - Real-time terminal trading interface",
        epilog="Keyboard controls: [q]uit, [r]efresh, [p]ause"
    )

    # Add command subparser
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        'dashboard',
        help='Launch the trading dashboard'
    )

    dashboard_parser.add_argument(
        '--refresh-rate',
        type=int,
        default=5,
        help='Auto-refresh interval in seconds (default: 5)'
    )

    dashboard_parser.add_argument(
        '--no-auto-refresh',
        action='store_true',
        help='Disable auto-refresh (manual refresh only)'
    )

    dashboard_parser.add_argument(
        '--theme',
        choices=['default', 'dark', 'light'],
        default='default',
        help='Color theme for the dashboard (default: default)'
    )

    dashboard_parser.add_argument(
        '--paper-trading',
        action='store_true',
        default=True,
        help='Use paper trading mode (default: True)'
    )

    dashboard_parser.add_argument(
        '--initial-cash',
        type=float,
        default=100000,
        help='Initial cash for paper trading (default: $100,000)'
    )

    dashboard_parser.add_argument(
        '--enable-risk',
        action='store_true',
        default=True,
        help='Enable risk management systems (default: True)'
    )

    args = parser.parse_args()

    if args.command == 'dashboard':
        run_dashboard(args)
    else:
        parser.print_help()
        sys.exit(1)


def run_dashboard(args):
    """Run the trading dashboard with given arguments."""
    try:
        logger.info("Starting DeepStack Trading Dashboard...")

        # Load configuration
        config = Config()

        # Setup Alpaca client (get credentials from environment)
        alpaca_api_key = os.getenv('ALPACA_API_KEY')
        alpaca_secret_key = os.getenv('ALPACA_SECRET_KEY')

        alpaca_client = None
        if alpaca_api_key and alpaca_secret_key:
            logger.info("Initializing Alpaca client...")
            alpaca_client = AlpacaClient(
                api_key=alpaca_api_key,
                secret_key=alpaca_secret_key,
                paper_trading=True
            )
        else:
            logger.warning("Alpaca credentials not found. Running without market data.")

        # Setup risk management systems if enabled
        kelly_sizer = None
        stop_manager = None
        circuit_breaker = None

        if args.enable_risk:
            logger.info("Initializing risk management systems...")
            kelly_sizer = KellyPositionSizer(
                account_balance=args.initial_cash,
                max_position_pct=0.25,
                max_total_exposure=1.0,
                min_position_size=100.0,
                max_position_size=50000.0
            )

            stop_manager = StopLossManager(
                account_balance=args.initial_cash,
                max_risk_per_trade=0.02,
                default_stop_pct=0.02,
                default_trailing_pct=0.03
            )

            circuit_breaker = CircuitBreaker(
                initial_portfolio_value=args.initial_cash,
                daily_loss_limit=0.05,
                max_drawdown_limit=0.10,
                consecutive_loss_limit=3,
                volatility_threshold=40.0
            )

        # Initialize paper trader
        logger.info(f"Initializing paper trader with ${args.initial_cash:,.2f}...")
        paper_trader = PaperTrader(
            config=config,
            alpaca_client=alpaca_client,
            kelly_sizer=kelly_sizer,
            stop_manager=stop_manager,
            circuit_breaker=circuit_breaker,
            enable_risk_systems=args.enable_risk,
            commission_per_trade=1.0,  # $1 per trade
            commission_per_share=0.005,  # $0.005 per share
            enforce_market_hours=True,
            slippage_volatility_multiplier=1.0
        )

        # Set initial cash
        paper_trader.cash = args.initial_cash
        paper_trader.initial_cash = args.initial_cash

        # Add some sample data for demonstration
        if not paper_trader.positions:
            logger.info("Adding sample positions for demonstration...")
            # Add sample positions
            paper_trader.positions = {
                'AAPL': {
                    'shares': 100,
                    'average_price': 150.00,
                    'timestamp': '2025-11-03T10:00:00'
                },
                'MSFT': {
                    'shares': 50,
                    'average_price': 350.00,
                    'timestamp': '2025-11-03T10:15:00'
                }
            }

            # Add sample trades
            paper_trader.trades = [
                {
                    'symbol': 'AAPL',
                    'side': 'BUY',
                    'shares': 100,
                    'price': 150.00,
                    'timestamp': '2025-11-03T10:00:00',
                    'status': 'FILLED',
                    'realized_pnl': 0
                },
                {
                    'symbol': 'MSFT',
                    'side': 'BUY',
                    'shares': 50,
                    'price': 350.00,
                    'timestamp': '2025-11-03T10:15:00',
                    'status': 'FILLED',
                    'realized_pnl': 0
                }
            ]

        # Initialize dashboard
        refresh_rate = 999999 if args.no_auto_refresh else args.refresh_rate
        logger.info(f"Starting dashboard with {refresh_rate}s refresh rate...")

        dashboard = TradingDashboard(
            paper_trader=paper_trader,
            alpaca_client=alpaca_client,
            refresh_rate=refresh_rate,
            theme=args.theme
        )

        # Run dashboard
        dashboard.run_sync()

    except KeyboardInterrupt:
        logger.info("Dashboard interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to run dashboard: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()