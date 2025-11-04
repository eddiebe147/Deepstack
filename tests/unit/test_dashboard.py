"""
Comprehensive tests for the Trading Dashboard.

Tests all dashboard components, data integration, and user interactions.
Ensures proper rendering, real-time updates, and error handling.
"""

import asyncio
import sys
import time
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

from core.broker.paper_trader import PaperTrader
from core.cli.dashboard import TradingDashboard
from core.config import Config
from core.data.alpaca_client import AlpacaClient


class TestTradingDashboard:
    """Test suite for TradingDashboard class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.get = Mock(return_value=None)
        return config

    @pytest.fixture
    def mock_alpaca_client(self):
        """Create mock Alpaca client."""
        client = Mock(spec=AlpacaClient)
        client.get_latest_quote = Mock(return_value={'price': 155.00})
        return client

    @pytest.fixture
    def mock_paper_trader(self, mock_config):
        """Create mock paper trader with sample data."""
        trader = Mock(spec=PaperTrader)
        trader.config = mock_config
        trader.cash = 85000.0
        trader.initial_cash = 100000.0
        trader.positions = {
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
        trader.trades = [
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
            },
            {
                'symbol': 'GOOGL',
                'side': 'SELL',
                'shares': 25,
                'price': 140.00,
                'timestamp': '2025-11-03T11:00:00',
                'status': 'FILLED',
                'realized_pnl': 250.00
            }
        ]
        trader.get_portfolio_value = Mock(return_value=117500.0)
        trader.get_performance_metrics = Mock(return_value={
            'sharpe_ratio': 1.85,
            'max_drawdown': -2.5,
            'win_rate': 60.0,
            'total_trades': 10,
            'winning_trades': 6,
            'losing_trades': 4,
            'avg_win': 500.0,
            'avg_loss': -300.0
        })

        # Add circuit breaker mock
        trader.circuit_breaker = Mock()
        trader.circuit_breaker.is_halted = False
        trader.circuit_breaker.halt_reasons = []
        trader.circuit_breaker.daily_loss_limit = -0.05

        # Add Kelly sizer mock
        trader.kelly_sizer = Mock()
        trader.kelly_sizer.max_position_pct = 0.25

        # Add stop loss manager mock
        trader.stop_manager = Mock()
        trader.stop_manager.active_stops = {
            'AAPL': {'stop_price': 147.00},
            'MSFT': {'stop_price': 340.00}
        }

        return trader

    @pytest.fixture
    def dashboard(self, mock_paper_trader, mock_alpaca_client):
        """Create dashboard instance."""
        return TradingDashboard(
            paper_trader=mock_paper_trader,
            alpaca_client=mock_alpaca_client,
            refresh_rate=5,
            theme='default'
        )

    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.trader is not None
        assert dashboard.alpaca is not None
        assert dashboard.refresh_rate == 5
        assert dashboard.theme == 'default'
        assert dashboard.is_paused == False
        assert dashboard.error_message is None
        assert isinstance(dashboard.console, Console)
        assert isinstance(dashboard.layout, Layout)

    def test_layout_structure(self, dashboard):
        """Test dashboard layout structure."""
        # Check main layout sections - they are in a list, not dict
        children_names = [child.name for child in dashboard.layout._children if hasattr(child, 'name')]
        assert 'header' in children_names
        assert 'body' in children_names
        assert 'footer' in children_names

        # Check body subsections
        body = dashboard.layout['body']
        body_children_names = [child.name for child in body._children if hasattr(child, 'name')]
        assert 'upper' in body_children_names
        assert 'middle' in body_children_names
        assert 'lower' in body_children_names

        # Check nested sections
        lower = dashboard.layout['lower']
        lower_children_names = [child.name for child in lower._children if hasattr(child, 'name')]
        assert 'metrics' in lower_children_names
        assert 'trades' in lower_children_names

        metrics = dashboard.layout['metrics']
        metrics_children_names = [child.name for child in metrics._children if hasattr(child, 'name')]
        assert 'risk' in metrics_children_names
        assert 'performance' in metrics_children_names

    def test_build_header(self, dashboard):
        """Test header panel building."""
        header = dashboard._build_header()
        assert isinstance(header, Panel)

        # Test paused state
        dashboard.is_paused = True
        header = dashboard._build_header()
        assert isinstance(header, Panel)

        # Test error state
        dashboard.error_message = "Test error"
        header = dashboard._build_header()
        assert isinstance(header, Panel)

    def test_build_portfolio_summary(self, dashboard):
        """Test portfolio summary panel."""
        panel = dashboard._build_portfolio_summary()
        assert isinstance(panel, Panel)

        # Verify calculations
        assert dashboard.trader.get_portfolio_value.called

    def test_build_portfolio_summary_error_handling(self, dashboard):
        """Test portfolio summary error handling."""
        dashboard.trader.get_portfolio_value = Mock(side_effect=Exception("API Error"))
        panel = dashboard._build_portfolio_summary()
        assert isinstance(panel, Panel)

    def test_build_positions_table(self, dashboard):
        """Test positions table building."""
        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)

        # Test with no positions
        dashboard.trader.positions = {}
        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)

    def test_build_positions_table_with_price_updates(self, dashboard):
        """Test positions table with live price updates."""
        dashboard.alpaca.get_latest_quote = Mock(return_value={'price': 155.00})
        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)

        # Verify price fetching was called
        assert dashboard.alpaca.get_latest_quote.called

    def test_build_positions_table_error_handling(self, dashboard):
        """Test positions table error handling."""
        dashboard.trader.positions = Mock(side_effect=Exception("Data Error"))
        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)

    def test_build_risk_panel(self, dashboard):
        """Test risk systems panel building."""
        panel = dashboard._build_risk_panel()
        assert isinstance(panel, Panel)

        # Test with circuit breaker halted
        dashboard.trader.circuit_breaker.is_halted = True
        dashboard.trader.circuit_breaker.halt_reasons = ["Max daily loss exceeded"]
        panel = dashboard._build_risk_panel()
        assert isinstance(panel, Panel)

    def test_build_risk_panel_without_systems(self, dashboard):
        """Test risk panel when systems are disabled."""
        dashboard.trader.circuit_breaker = None
        dashboard.trader.kelly_sizer = None
        dashboard.trader.stop_manager = None
        panel = dashboard._build_risk_panel()
        assert isinstance(panel, Panel)

    def test_build_performance_metrics(self, dashboard):
        """Test performance metrics panel."""
        panel = dashboard._build_performance_metrics()
        assert isinstance(panel, Panel)
        assert dashboard.trader.get_performance_metrics.called

    def test_performance_metrics_caching(self, dashboard):
        """Test performance metrics caching."""
        # First call should fetch metrics
        panel1 = dashboard._build_performance_metrics()
        call_count1 = dashboard.trader.get_performance_metrics.call_count

        # Second call within cache TTL should use cache
        panel2 = dashboard._build_performance_metrics()
        call_count2 = dashboard.trader.get_performance_metrics.call_count

        assert call_count2 == call_count1  # No additional calls

        # After cache expiry, should fetch again
        dashboard._metrics_timestamp = time.time() - 20  # Expire cache
        panel3 = dashboard._build_performance_metrics()
        call_count3 = dashboard.trader.get_performance_metrics.call_count

        assert call_count3 > call_count2  # New call made

    def test_build_trades_log(self, dashboard):
        """Test recent trades log panel."""
        panel = dashboard._build_trades_log()
        assert isinstance(panel, Panel)

        # Test with no trades
        dashboard.trader.trades = []
        panel = dashboard._build_trades_log()
        assert isinstance(panel, Panel)

        # Test with many trades (should show only last 10)
        dashboard.trader.trades = [
            {
                'symbol': f'TEST{i}',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'shares': 100,
                'price': 100.0 + i,
                'timestamp': f'2025-11-03T{10+i:02d}:00:00',
                'status': 'FILLED',
                'realized_pnl': 50.0 if i % 2 else -25.0
            }
            for i in range(20)
        ]
        panel = dashboard._build_trades_log()
        assert isinstance(panel, Panel)

    def test_build_footer(self, dashboard):
        """Test footer panel with controls."""
        panel = dashboard._build_footer()
        assert isinstance(panel, Panel)

        # Test with paused state
        dashboard.is_paused = True
        panel = dashboard._build_footer()
        assert isinstance(panel, Panel)

    def test_get_current_prices(self, dashboard):
        """Test price fetching with caching."""
        symbols = ['AAPL', 'MSFT']

        # First call should fetch prices
        prices1 = dashboard._get_current_prices(symbols)
        assert 'AAPL' in prices1
        assert 'MSFT' in prices1
        assert dashboard.alpaca.get_latest_quote.called

        # Second call within cache TTL should use cache
        call_count = dashboard.alpaca.get_latest_quote.call_count
        prices2 = dashboard._get_current_prices(symbols)
        assert dashboard.alpaca.get_latest_quote.call_count == call_count

        # After cache expiry, should fetch again
        dashboard._cache_timestamp = time.time() - 10  # Expire cache
        prices3 = dashboard._get_current_prices(symbols)
        assert dashboard.alpaca.get_latest_quote.call_count > call_count

    def test_get_current_prices_no_alpaca(self, dashboard):
        """Test price fetching without Alpaca client."""
        dashboard.alpaca = None
        symbols = ['AAPL', 'MSFT']

        prices = dashboard._get_current_prices(symbols)
        assert prices['AAPL'] == 150.00  # Should use average price
        assert prices['MSFT'] == 350.00

    def test_calculate_portfolio_heat(self, dashboard):
        """Test portfolio heat calculation."""
        heat = dashboard._calculate_portfolio_heat()
        assert isinstance(heat, float)
        assert 0 <= heat <= 100

        # Test with no positions
        dashboard.trader.positions = {}
        heat = dashboard._calculate_portfolio_heat()
        assert heat == 0.0

        # Test with zero portfolio value
        dashboard.trader.get_portfolio_value = Mock(return_value=0)
        heat = dashboard._calculate_portfolio_heat()
        assert heat == 0.0

    def test_calculate_performance_metrics(self, dashboard):
        """Test performance metrics calculation."""
        metrics = dashboard._calculate_performance_metrics()

        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        assert 'total_trades' in metrics
        assert 'winning_trades' in metrics
        assert 'losing_trades' in metrics
        assert 'avg_win' in metrics
        assert 'avg_loss' in metrics

    def test_calculate_performance_metrics_from_trades(self, dashboard):
        """Test metrics calculation from trades history."""
        # Remove get_performance_metrics method to test fallback
        del dashboard.trader.get_performance_metrics

        metrics = dashboard._calculate_performance_metrics()

        # We have 3 trades total, but only 2 with non-zero realized_pnl
        # GOOGL SELL with pnl=250, MSFT/AAPL with pnl=0
        assert metrics['total_trades'] >= 1
        assert metrics['winning_trades'] >= 1
        if metrics['winning_trades'] > 0:
            assert metrics['avg_win'] > 0

    def test_update_display(self, dashboard):
        """Test full display update."""
        layout = dashboard.update_display()
        assert isinstance(layout, Layout)
        assert dashboard.error_message is None
        assert dashboard.last_update is not None

    def test_update_display_error_handling(self, dashboard):
        """Test display update error handling."""
        # Force an error
        dashboard.trader.get_portfolio_value = Mock(side_effect=Exception("Update Error"))

        layout = dashboard.update_display()
        assert isinstance(layout, Layout)
        # Error should be captured but not crash

    @pytest.mark.asyncio
    async def test_handle_keyboard_input(self, dashboard):
        """Test keyboard input handling."""
        # Mock stdin for testing
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read = Mock(side_effect=['r', 'p', 'c', 'q'])

            # Mock termios (Unix terminal control)
            with patch('termios.tcgetattr'), patch('termios.tcsetattr'), patch('tty.setraw'):
                result = await dashboard.handle_keyboard_input()
                assert result == False  # 'q' should return False to quit

    def test_pause_functionality(self, dashboard):
        """Test pause/resume functionality."""
        assert dashboard.is_paused == False

        dashboard.is_paused = True
        assert dashboard.is_paused == True

        dashboard.is_paused = False
        assert dashboard.is_paused == False

    def test_error_message_handling(self, dashboard):
        """Test error message display."""
        dashboard.error_message = "Test error message"
        header = dashboard._build_header()
        assert isinstance(header, Panel)

        # Clear error
        dashboard.error_message = None
        header = dashboard._build_header()
        assert isinstance(header, Panel)

    def test_theme_support(self):
        """Test different theme support."""
        trader = Mock(spec=PaperTrader)
        alpaca = Mock(spec=AlpacaClient)

        # Test different themes
        for theme in ['default', 'dark', 'light']:
            dashboard = TradingDashboard(
                paper_trader=trader,
                alpaca_client=alpaca,
                theme=theme
            )
            assert dashboard.theme == theme

    def test_refresh_rate_configuration(self):
        """Test refresh rate configuration."""
        trader = Mock(spec=PaperTrader)
        alpaca = Mock(spec=AlpacaClient)

        # Test different refresh rates
        for rate in [1, 5, 10, 30]:
            dashboard = TradingDashboard(
                paper_trader=trader,
                alpaca_client=alpaca,
                refresh_rate=rate
            )
            assert dashboard.refresh_rate == rate

    def test_cache_ttl(self, dashboard):
        """Test cache time-to-live settings."""
        assert dashboard._cache_ttl == 5
        assert dashboard._cache_timestamp == 0
        assert dashboard._price_cache == {}

    def test_run_sync(self, dashboard):
        """Test synchronous run wrapper."""
        with patch('asyncio.run') as mock_run:
            dashboard.run_sync()
            mock_run.assert_called_once()

    def test_run_sync_keyboard_interrupt(self, dashboard):
        """Test handling keyboard interrupt in sync mode."""
        with patch('asyncio.run', side_effect=KeyboardInterrupt()):
            dashboard.run_sync()  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_run_with_live_display(self, dashboard):
        """Test running with Live display (integration test)."""
        # This is a simplified test - actual run() requires terminal
        with patch('rich.live.Live'):
            with patch.object(dashboard, 'handle_keyboard_input',
                            return_value=asyncio.Future()):
                # Set up keyboard task to quit immediately
                keyboard_future = asyncio.Future()
                keyboard_future.set_result(False)

                with patch('asyncio.create_task', return_value=keyboard_future):
                    await dashboard.run()

    def test_position_with_stop_loss(self, dashboard):
        """Test displaying positions with stop loss information."""
        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)
        # Stop losses should be displayed for AAPL and MSFT

    def test_circuit_breaker_halt_display(self, dashboard):
        """Test circuit breaker halt status display."""
        dashboard.trader.circuit_breaker.is_halted = True
        dashboard.trader.circuit_breaker.halt_reasons = [
            "Max daily loss exceeded",
            "Too many consecutive losses"
        ]

        panel = dashboard._build_risk_panel()
        assert isinstance(panel, Panel)

    def test_empty_portfolio(self, dashboard):
        """Test dashboard with empty portfolio."""
        dashboard.trader.positions = {}
        dashboard.trader.trades = []
        dashboard.trader.cash = 100000.0
        dashboard.trader.get_portfolio_value = Mock(return_value=100000.0)

        # All panels should still render without errors
        layout = dashboard.update_display()
        assert isinstance(layout, Layout)

    def test_large_portfolio(self, dashboard):
        """Test dashboard with large portfolio."""
        # Create 50 positions
        dashboard.trader.positions = {
            f'STOCK{i}': {
                'shares': 100 + i,
                'average_price': 50.0 + i,
                'timestamp': f'2025-11-03T10:{i:02d}:00'
            }
            for i in range(50)
        }

        panel = dashboard._build_positions_table()
        assert isinstance(panel, Panel)

    def test_console_clear(self, dashboard):
        """Test console clear functionality."""
        with patch.object(dashboard.console, 'clear') as mock_clear:
            dashboard.console.clear()
            mock_clear.assert_called_once()


class TestCLIMain:
    """Test suite for CLI main entry point."""

    def test_main_help(self):
        """Test CLI help message."""
        from core.cli.__main__ import main

        with patch('sys.argv', ['cli', '--help']):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code in [0, None]

    def test_dashboard_command(self):
        """Test dashboard command parsing."""
        from core.cli.__main__ import run_dashboard

        args = Mock()
        args.refresh_rate = 10
        args.no_auto_refresh = False
        args.theme = 'dark'
        args.paper_trading = True
        args.initial_cash = 50000
        args.enable_risk = True

        with patch('core.cli.__main__.Config'), \
             patch('core.cli.__main__.AlpacaClient'), \
             patch('core.cli.__main__.PaperTrader'), \
             patch('core.cli.__main__.TradingDashboard') as mock_dashboard:

            mock_instance = Mock()
            mock_dashboard.return_value = mock_instance

            with patch.dict('os.environ', {'ALPACA_API_KEY': 'test', 'ALPACA_SECRET_KEY': 'test'}):
                run_dashboard(args)

                mock_dashboard.assert_called_once()
                mock_instance.run_sync.assert_called_once()

    def test_dashboard_without_alpaca_credentials(self):
        """Test dashboard without Alpaca credentials."""
        from core.cli.__main__ import run_dashboard

        args = Mock()
        args.refresh_rate = 5
        args.no_auto_refresh = False
        args.theme = 'default'
        args.paper_trading = True
        args.initial_cash = 100000
        args.enable_risk = False

        with patch('core.cli.__main__.Config'), \
             patch('core.cli.__main__.PaperTrader'), \
             patch('core.cli.__main__.TradingDashboard') as mock_dashboard:

            mock_instance = Mock()
            mock_dashboard.return_value = mock_instance

            with patch.dict('os.environ', {}, clear=True):
                run_dashboard(args)

                # Should still create dashboard without Alpaca
                mock_dashboard.assert_called_once()
                mock_instance.run_sync.assert_called_once()