"""
Terminal Trading Dashboard for DeepStack.

Beautiful real-time trading dashboard using the rich library.
Displays portfolio summary, positions, risk systems, performance metrics,
and recent trades with auto-refresh capabilities.

Features:
    - Real-time portfolio value and P&L tracking
    - Live position monitoring with current prices
    - Risk system status (circuit breakers, portfolio heat, stops)
    - Performance metrics (Sharpe ratio, max drawdown, win rate)
    - Recent trades log with color-coded P&L
    - Keyboard controls (q=quit, r=refresh, p=pause)
    - Auto-refresh every 5 seconds
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from ..broker.paper_trader import PaperTrader
from ..config import Config
from ..data.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)


class TradingDashboard:
    """
    Real-time trading dashboard for DeepStack.

    Displays comprehensive trading information in a beautiful terminal UI
    with auto-refresh capabilities and keyboard controls.

    Example:
        >>> config = Config()
        >>> alpaca = AlpacaClient(api_key="...", secret_key="...")
        >>> trader = PaperTrader(config, alpaca)
        >>> dashboard = TradingDashboard(trader, alpaca)
        >>> await dashboard.run()
    """

    def __init__(
        self,
        paper_trader: PaperTrader,
        alpaca_client: AlpacaClient,
        refresh_rate: int = 5,
        theme: str = "default"
    ):
        """
        Initialize the trading dashboard.

        Args:
            paper_trader: Paper trader instance to monitor
            alpaca_client: Alpaca client for market data
            refresh_rate: Auto-refresh interval in seconds (default 5)
            theme: Color theme ("default", "dark", "light")
        """
        self.trader = paper_trader
        self.alpaca = alpaca_client
        self.refresh_rate = refresh_rate
        self.theme = theme

        # Console and layout setup
        self.console = Console()
        self.layout = Layout()

        # Dashboard state
        self.is_paused = False
        self.last_update = datetime.now()
        self.error_message = None

        # Cache for reducing API calls
        self._price_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 5  # 5 seconds cache TTL

        # Performance metrics cache
        self._metrics_cache = None
        self._metrics_timestamp = 0

        # Setup layout structure
        self._setup_layout()

    def _setup_layout(self):
        """Setup the dashboard layout structure."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Split body into upper and lower sections
        self.layout["body"].split_column(
            Layout(name="upper", size=10),
            Layout(name="middle", size=12),
            Layout(name="lower")
        )

        # Split upper section for portfolio summary
        self.layout["upper"].split_row(
            Layout(name="portfolio", ratio=1)
        )

        # Split middle for positions table
        self.layout["middle"].split_row(
            Layout(name="positions", ratio=1)
        )

        # Split lower section for risk/performance and trades
        self.layout["lower"].split_column(
            Layout(name="metrics", size=6),
            Layout(name="trades")
        )

        # Split metrics section horizontally
        self.layout["metrics"].split_row(
            Layout(name="risk", ratio=1),
            Layout(name="performance", ratio=1)
        )

    def _build_header(self) -> Panel:
        """Build the header panel with title and status."""
        status_color = "green" if not self.is_paused else "yellow"
        status_text = "[bold green]LIVE[/bold green]" if not self.is_paused else "[bold yellow]PAUSED[/bold yellow]"

        if self.error_message:
            status_text = f"[bold red]ERROR[/bold red]: {self.error_message}"

        header_text = Text()
        header_text.append("DeepStack Trading Dashboard", style="bold cyan")
        header_text.append("\n")
        header_text.append(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ",
            style="dim"
        )
        header_text.append(status_text)

        return Panel(
            Align.center(header_text),
            border_style="cyan",
            padding=(0, 1)
        )

    def _build_portfolio_summary(self) -> Panel:
        """Build the portfolio summary panel."""
        try:
            # Get portfolio data from paper trader
            cash = self.trader.cash
            portfolio_value = self.trader.get_portfolio_value()
            positions_value = portfolio_value - cash

            # Calculate P&L
            initial_cash = self.trader.initial_cash
            total_pnl = portfolio_value - initial_cash
            pnl_pct = (total_pnl / initial_cash) * 100 if initial_cash > 0 else 0

            # Format values with colors
            pnl_color = "green" if total_pnl >= 0 else "red"
            pnl_sign = "+" if total_pnl >= 0 else ""

            # Create summary text
            summary = Text()
            summary.append("PORTFOLIO SUMMARY\n", style="bold white")
            summary.append("-" * 50 + "\n", style="dim")

            # Cash and positions
            summary.append(f"Cash Available: ", style="white")
            summary.append(f"${cash:,.2f}\n", style="bold cyan")

            summary.append(f"Positions Value: ", style="white")
            summary.append(f"${positions_value:,.2f}\n", style="bold cyan")

            summary.append(f"Total Portfolio: ", style="white")
            summary.append(f"${portfolio_value:,.2f}\n", style="bold cyan")

            # P&L
            summary.append(f"Total P&L: ", style="white")
            summary.append(
                f"{pnl_sign}${abs(total_pnl):,.2f} ({pnl_sign}{abs(pnl_pct):.2f}%)",
                style=f"bold {pnl_color}"
            )

            return Panel(
                summary,
                title="[bold]Portfolio[/bold]",
                border_style="blue",
                padding=(0, 1)
            )

        except Exception as e:
            logger.error(f"Error building portfolio summary: {e}")
            return Panel(
                "[red]Error loading portfolio data[/red]",
                title="[bold]Portfolio[/bold]",
                border_style="red"
            )

    def _build_positions_table(self) -> Panel:
        """Build the active positions table."""
        try:
            positions = self.trader.positions

            # Create table
            table = Table(
                title="ACTIVE POSITIONS",
                show_header=True,
                header_style="bold cyan",
                title_style="bold white",
                border_style="blue"
            )

            # Add columns
            table.add_column("Symbol", style="bold white", width=8)
            table.add_column("Shares", justify="right", width=10)
            table.add_column("Entry Price", justify="right", width=12)
            table.add_column("Current Price", justify="right", width=12)
            table.add_column("Market Value", justify="right", width=12)
            table.add_column("P&L", justify="right", width=12)
            table.add_column("P&L %", justify="right", width=10)
            table.add_column("Stop Loss", justify="right", width=10)

            if not positions:
                table.add_row(
                    "[dim]No active positions[/dim]", "", "", "", "", "", "", ""
                )
            else:
                # Get current prices with caching
                current_prices = self._get_current_prices(list(positions.keys()))

                for symbol, position in positions.items():
                    shares = position['shares']
                    entry_price = position['average_price']
                    current_price = current_prices.get(symbol, entry_price)

                    # Calculate P&L
                    market_value = shares * current_price
                    pnl = (current_price - entry_price) * shares
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100

                    # Format with colors
                    pnl_color = "green" if pnl >= 0 else "red"
                    pnl_sign = "+" if pnl >= 0 else ""

                    # Get stop loss if exists
                    stop_price = "N/A"
                    if hasattr(self.trader, 'stop_manager') and self.trader.stop_manager:
                        stops = self.trader.stop_manager.active_stops.get(symbol, {})
                        if stops:
                            stop_price = f"${stops.get('stop_price', 0):.2f}"

                    table.add_row(
                        symbol,
                        f"{shares:,}",
                        f"${entry_price:.2f}",
                        f"${current_price:.2f}",
                        f"${market_value:,.2f}",
                        f"[{pnl_color}]{pnl_sign}${abs(pnl):,.2f}[/{pnl_color}]",
                        f"[{pnl_color}]{pnl_sign}{abs(pnl_pct):.2f}%[/{pnl_color}]",
                        stop_price
                    )

            return Panel(
                table,
                border_style="blue",
                padding=(0, 1)
            )

        except Exception as e:
            logger.error(f"Error building positions table: {e}")
            return Panel(
                "[red]Error loading positions[/red]",
                title="[bold]Positions[/bold]",
                border_style="red"
            )

    def _build_risk_panel(self) -> Panel:
        """Build the risk systems status panel."""
        try:
            risk_text = Text()
            risk_text.append("RISK SYSTEMS\n", style="bold white")
            risk_text.append("-" * 25 + "\n", style="dim")

            # Circuit breaker status
            if hasattr(self.trader, 'circuit_breaker') and self.trader.circuit_breaker:
                cb = self.trader.circuit_breaker
                # Check if circuit breaker is tripped
                is_halted = hasattr(cb, 'is_halted') and cb.is_halted
                if not is_halted and hasattr(cb, 'state'):
                    from core.risk.circuit_breaker import BreakerState
                    is_halted = cb.state == BreakerState.TRIPPED

                cb_status = "✅ OK" if not is_halted else "🔴 HALTED"
                risk_text.append(f"Circuit Breakers: {cb_status}\n")

                # Show details if halted
                if is_halted and hasattr(cb, 'halt_reasons'):
                    for reason in cb.halt_reasons:
                        risk_text.append(f"  - {reason}\n", style="red")
            else:
                risk_text.append("Circuit Breakers: [dim]Disabled[/dim]\n")

            # Portfolio heat (risk exposure)
            portfolio_heat = self._calculate_portfolio_heat()
            heat_color = "green" if portfolio_heat < 50 else "yellow" if portfolio_heat < 75 else "red"
            risk_text.append(f"Portfolio Heat: ")
            risk_text.append(f"{portfolio_heat:.1f}%\n", style=heat_color)

            # Active stop losses
            active_stops = 0
            if hasattr(self.trader, 'stop_manager') and self.trader.stop_manager:
                active_stops = len(self.trader.stop_manager.active_stops)
            risk_text.append(f"Active Stops: {active_stops}\n")

            # Max position size (Kelly)
            if hasattr(self.trader, 'kelly_sizer') and self.trader.kelly_sizer:
                max_pos = self.trader.kelly_sizer.max_position_pct * 100
                risk_text.append(f"Max Position: {max_pos:.1f}%\n")

            # Daily loss limit
            if hasattr(self.trader, 'circuit_breaker') and self.trader.circuit_breaker:
                cb = self.trader.circuit_breaker
                if hasattr(cb, 'daily_loss_limit'):
                    daily_loss = abs(cb.daily_loss_limit) * 100
                    risk_text.append(f"Daily Loss Limit: {daily_loss:.1f}%\n")

            return Panel(
                risk_text,
                title="[bold]Risk Management[/bold]",
                border_style="yellow",
                padding=(0, 1)
            )

        except Exception as e:
            logger.error(f"Error building risk panel: {e}")
            return Panel(
                "[red]Error loading risk data[/red]",
                title="[bold]Risk Management[/bold]",
                border_style="red"
            )

    def _build_performance_metrics(self) -> Panel:
        """Build the performance metrics panel."""
        try:
            # Use cached metrics if available and fresh
            current_time = time.time()
            if (self._metrics_cache and
                current_time - self._metrics_timestamp < 10):  # 10 second cache
                metrics = self._metrics_cache
            else:
                metrics = self._calculate_performance_metrics()
                self._metrics_cache = metrics
                self._metrics_timestamp = current_time

            perf_text = Text()
            perf_text.append("PERFORMANCE\n", style="bold white")
            perf_text.append("-" * 25 + "\n", style="dim")

            # Sharpe Ratio
            sharpe_color = "green" if metrics['sharpe_ratio'] > 1 else "yellow" if metrics['sharpe_ratio'] > 0 else "red"
            perf_text.append(f"Sharpe Ratio: ")
            perf_text.append(f"{metrics['sharpe_ratio']:.2f}\n", style=sharpe_color)

            # Max Drawdown
            dd_color = "green" if metrics['max_drawdown'] > -5 else "yellow" if metrics['max_drawdown'] > -10 else "red"
            perf_text.append(f"Max Drawdown: ")
            perf_text.append(f"{metrics['max_drawdown']:.2f}%\n", style=dd_color)

            # Win Rate
            wr_color = "green" if metrics['win_rate'] > 60 else "yellow" if metrics['win_rate'] > 50 else "red"
            perf_text.append(f"Win Rate: ")
            perf_text.append(f"{metrics['win_rate']:.1f}%\n", style=wr_color)

            # Trade Statistics
            perf_text.append(f"Total Trades: {metrics['total_trades']}\n")
            perf_text.append(f"Winning Trades: ", style="white")
            perf_text.append(f"{metrics['winning_trades']}\n", style="green")
            perf_text.append(f"Losing Trades: ", style="white")
            perf_text.append(f"{metrics['losing_trades']}\n", style="red")

            # Average P&L
            avg_win_color = "green"
            avg_loss_color = "red"
            perf_text.append(f"Avg Win: ", style="white")
            perf_text.append(f"${metrics['avg_win']:,.2f}\n", style=avg_win_color)
            perf_text.append(f"Avg Loss: ", style="white")
            perf_text.append(f"-${abs(metrics['avg_loss']):,.2f}\n", style=avg_loss_color)

            return Panel(
                perf_text,
                title="[bold]Performance[/bold]",
                border_style="green",
                padding=(0, 1)
            )

        except Exception as e:
            logger.error(f"Error building performance metrics: {e}")
            return Panel(
                "[red]Error loading metrics[/red]",
                title="[bold]Performance[/bold]",
                border_style="red"
            )

    def _build_trades_log(self) -> Panel:
        """Build the recent trades log panel."""
        try:
            # Get recent trades (last 10)
            trades = self.trader.trades[-10:] if hasattr(self.trader, 'trades') else []

            # Create table
            table = Table(
                title="RECENT TRADES (Last 10)",
                show_header=True,
                header_style="bold cyan",
                title_style="bold white",
                border_style="blue"
            )

            # Add columns
            table.add_column("Time", style="dim", width=8)
            table.add_column("Type", width=6)
            table.add_column("Symbol", style="bold white", width=8)
            table.add_column("Shares", justify="right", width=8)
            table.add_column("Price", justify="right", width=10)
            table.add_column("Total", justify="right", width=12)
            table.add_column("P&L", justify="right", width=12)
            table.add_column("Status", width=10)

            if not trades:
                table.add_row(
                    "[dim]No trades yet[/dim]", "", "", "", "", "", "", ""
                )
            else:
                # Reverse to show most recent first
                for trade in reversed(trades):
                    timestamp = datetime.fromisoformat(trade['timestamp'])
                    time_str = timestamp.strftime("%H:%M:%S")

                    # Format trade type with color
                    trade_type = trade['side']
                    type_color = "green" if trade_type == "BUY" else "red"

                    # Calculate total
                    total = trade['shares'] * trade['price']

                    # P&L (if available)
                    pnl = trade.get('realized_pnl', 0)
                    pnl_str = ""
                    if pnl != 0:
                        pnl_color = "green" if pnl > 0 else "red"
                        pnl_sign = "+" if pnl > 0 else ""
                        pnl_str = f"[{pnl_color}]{pnl_sign}${abs(pnl):,.2f}[/{pnl_color}]"

                    # Status
                    status = trade.get('status', 'FILLED')
                    status_color = "green" if status == "FILLED" else "yellow"

                    table.add_row(
                        time_str,
                        f"[{type_color}]{trade_type}[/{type_color}]",
                        trade['symbol'],
                        f"{trade['shares']:,}",
                        f"${trade['price']:.2f}",
                        f"${total:,.2f}",
                        pnl_str,
                        f"[{status_color}]{status}[/{status_color}]"
                    )

            return Panel(
                table,
                border_style="blue",
                padding=(0, 1)
            )

        except Exception as e:
            logger.error(f"Error building trades log: {e}")
            return Panel(
                "[red]Error loading trades[/red]",
                title="[bold]Recent Trades[/bold]",
                border_style="red"
            )

    def _build_footer(self) -> Panel:
        """Build the footer panel with controls."""
        footer_text = Text()
        footer_text.append("[bold cyan]Controls: [/bold cyan]")
        footer_text.append("[q]uit  ", style="yellow")
        footer_text.append("[r]efresh  ", style="green")
        footer_text.append("[p]ause/resume  ", style="blue")
        footer_text.append("[c]lear  ", style="magenta")
        footer_text.append(f"  |  Auto-refresh: {self.refresh_rate}s", style="dim")

        if self.is_paused:
            footer_text.append("  |  [PAUSED]", style="bold yellow")

        return Panel(
            Align.center(footer_text),
            border_style="cyan",
            padding=(0, 1)
        )

    def _get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols with caching."""
        current_time = time.time()

        # Return cached prices if still valid
        if current_time - self._cache_timestamp < self._cache_ttl:
            return self._price_cache

        prices = {}
        for symbol in symbols:
            try:
                # Get price from Alpaca
                if self.alpaca:
                    quote = self.alpaca.get_latest_quote(symbol)
                    if quote:
                        prices[symbol] = quote.get('price', 0)
                    else:
                        # Fallback to position's average price
                        prices[symbol] = self.trader.positions[symbol]['average_price']
                else:
                    # No Alpaca client, use average price
                    prices[symbol] = self.trader.positions[symbol]['average_price']
            except Exception as e:
                logger.warning(f"Could not get price for {symbol}: {e}")
                # Use position's average price as fallback
                if symbol in self.trader.positions:
                    prices[symbol] = self.trader.positions[symbol]['average_price']

        # Update cache
        self._price_cache = prices
        self._cache_timestamp = current_time

        return prices

    def _calculate_portfolio_heat(self) -> float:
        """Calculate portfolio heat (risk exposure as % of portfolio)."""
        try:
            portfolio_value = self.trader.get_portfolio_value()
            if portfolio_value <= 0:
                return 0.0

            positions_value = sum(
                pos['shares'] * pos['average_price']
                for pos in self.trader.positions.values()
            )

            return (positions_value / portfolio_value) * 100
        except Exception:
            return 0.0

    def _calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        metrics = {
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }

        try:
            # Get performance analytics from paper trader
            if hasattr(self.trader, 'get_performance_metrics'):
                trader_metrics = self.trader.get_performance_metrics()
                metrics.update(trader_metrics)
            else:
                # Calculate from trades history
                if hasattr(self.trader, 'trades'):
                    trades = self.trader.trades

                    # Filter completed trades with P&L
                    closed_trades = [t for t in trades if t.get('realized_pnl') is not None]

                    if closed_trades:
                        metrics['total_trades'] = len(closed_trades)

                        # Calculate wins/losses
                        wins = [t for t in closed_trades if t['realized_pnl'] > 0]
                        losses = [t for t in closed_trades if t['realized_pnl'] <= 0]

                        metrics['winning_trades'] = len(wins)
                        metrics['losing_trades'] = len(losses)

                        # Win rate
                        if metrics['total_trades'] > 0:
                            metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100

                        # Average win/loss
                        if wins:
                            metrics['avg_win'] = sum(t['realized_pnl'] for t in wins) / len(wins)
                        if losses:
                            metrics['avg_loss'] = sum(t['realized_pnl'] for t in losses) / len(losses)

                        # Simple Sharpe calculation (annualized)
                        if len(closed_trades) > 1:
                            returns = [t['realized_pnl'] / self.trader.initial_cash for t in closed_trades]
                            if returns:
                                avg_return = sum(returns) / len(returns)
                                if len(returns) > 1:
                                    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
                                    std_dev = variance ** 0.5
                                    if std_dev > 0:
                                        # Annualize (assuming daily returns, 252 trading days)
                                        metrics['sharpe_ratio'] = (avg_return * 252) / (std_dev * (252 ** 0.5))

                        # Max drawdown calculation
                        if hasattr(self.trader, 'portfolio_history'):
                            history = self.trader.portfolio_history
                            if len(history) > 1:
                                peak = history[0]
                                max_dd = 0
                                for value in history[1:]:
                                    if value > peak:
                                        peak = value
                                    dd = ((peak - value) / peak) * 100 if peak > 0 else 0
                                    max_dd = max(max_dd, dd)
                                metrics['max_drawdown'] = -max_dd

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")

        return metrics

    def update_display(self) -> Layout:
        """Update all dashboard components."""
        try:
            # Update all panels
            self.layout["header"].update(self._build_header())
            self.layout["portfolio"].update(self._build_portfolio_summary())
            self.layout["positions"].update(self._build_positions_table())
            self.layout["risk"].update(self._build_risk_panel())
            self.layout["performance"].update(self._build_performance_metrics())
            self.layout["trades"].update(self._build_trades_log())
            self.layout["footer"].update(self._build_footer())

            self.last_update = datetime.now()
            self.error_message = None

        except Exception as e:
            logger.error(f"Error updating display: {e}")
            self.error_message = str(e)

        return self.layout

    async def handle_keyboard_input(self):
        """Handle keyboard input in a separate task."""
        try:
            import termios
            import tty

            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)

            try:
                # Set terminal to raw mode
                tty.setraw(sys.stdin)

                while True:
                    # Non-blocking read
                    char = sys.stdin.read(1)

                    if char.lower() == 'q':
                        # Quit
                        return False
                    elif char.lower() == 'r':
                        # Force refresh
                        self.is_paused = False
                    elif char.lower() == 'p':
                        # Toggle pause
                        self.is_paused = not self.is_paused
                    elif char.lower() == 'c':
                        # Clear screen
                        self.console.clear()

                    await asyncio.sleep(0.1)

            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        except Exception as e:
            logger.error(f"Error handling keyboard input: {e}")
            return True

    async def run(self):
        """Run the dashboard with auto-refresh."""
        print("\n" * 50)  # Clear screen
        self.console.clear()

        try:
            with Live(
                self.update_display(),
                console=self.console,
                refresh_per_second=2,
                screen=True
            ) as live:
                # Start keyboard handler
                keyboard_task = asyncio.create_task(self.handle_keyboard_input())

                while True:
                    # Check if should quit
                    if keyboard_task.done():
                        should_continue = keyboard_task.result()
                        if not should_continue:
                            break

                    # Update display if not paused
                    if not self.is_paused:
                        live.update(self.update_display())

                    # Wait for refresh interval
                    await asyncio.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            self.console.print(f"[red]Dashboard error: {e}[/red]")
        finally:
            # Clean exit
            self.console.print("\n[cyan]Dashboard closed.[/cyan]")

    def run_sync(self):
        """Synchronous wrapper for running the dashboard."""
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard interrupted by user.[/yellow]")
        except Exception as e:
            logger.error(f"Failed to run dashboard: {e}")
            self.console.print(f"[red]Failed to run dashboard: {e}[/red]")