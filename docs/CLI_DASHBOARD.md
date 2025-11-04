# DeepStack CLI Trading Dashboard

## Overview

The DeepStack CLI Trading Dashboard is a beautiful, real-time terminal interface for monitoring and controlling your trading system. Built with the Python `rich` library, it provides a comprehensive view of your portfolio, positions, risk systems, and performance metrics—all in your terminal.

## Features

### Real-Time Monitoring
- **Portfolio Summary**: Live tracking of cash, positions value, total portfolio value, and P&L
- **Active Positions**: Real-time price updates with profit/loss calculations
- **Risk Systems**: Circuit breaker status, portfolio heat, active stop losses
- **Performance Metrics**: Sharpe ratio, maximum drawdown, win rate, trade statistics
- **Trade History**: Recent trades log with timestamps and realized P&L

### Interactive Controls
- **Keyboard Shortcuts**:
  - `q` - Quit the dashboard
  - `r` - Force refresh
  - `p` - Pause/resume auto-refresh
  - `c` - Clear screen

### Auto-Refresh
- Configurable refresh rate (default: 5 seconds)
- Efficient caching to minimize API calls
- Non-blocking async updates

## Installation

### Prerequisites

```bash
# Install required packages
pip install rich
pip install alpaca-py  # Optional, for live market data
```

### Environment Setup

For live market data, set your Alpaca API credentials:

```bash
export ALPACA_API_KEY='your-api-key'
export ALPACA_SECRET_KEY='your-secret-key'
```

## Usage

### Basic Usage

Run the dashboard from the command line:

```bash
# Run with default settings
python -m core.cli dashboard

# Specify refresh rate (in seconds)
python -m core.cli dashboard --refresh-rate 10

# Disable auto-refresh (manual refresh only)
python -m core.cli dashboard --no-auto-refresh

# Set initial cash for paper trading
python -m core.cli dashboard --initial-cash 50000
```

### Running the Example

The included example demonstrates both demo and live modes:

```bash
python examples/dashboard_example.py
```

This will present a menu:
1. **Demo Mode** - Run with simulated data (no API keys required)
2. **Live Mode** - Connect to Alpaca for real market data

### Command-Line Options

```bash
python -m core.cli dashboard [options]

Options:
  --refresh-rate SECONDS    Auto-refresh interval (default: 5)
  --no-auto-refresh        Disable auto-refresh
  --theme THEME            Color theme: default, dark, light
  --initial-cash AMOUNT    Initial cash for paper trading
  --enable-risk            Enable risk management systems
  --paper-trading          Use paper trading mode (default: True)
```

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│              DeepStack Trading Dashboard                      │
│          2025-11-04 10:30:45 | LIVE                          │
├─────────────────────────────────────────────────────────────┤
│ PORTFOLIO SUMMARY                                            │
│ ─────────────────────────────────────────────────            │
│ Cash Available: $85,000.00                                   │
│ Positions Value: $32,500.00                                  │
│ Total Portfolio: $117,500.00                                 │
│ Total P&L: +$17,500.00 (+17.50%)                            │
├─────────────────────────────────────────────────────────────┤
│                    ACTIVE POSITIONS                          │
│ ┌────────┬────────┬────────────┬─────────────┬────────────┐│
│ │Symbol  │ Shares │Entry Price │Current Price│    P&L     ││
│ ├────────┼────────┼────────────┼─────────────┼────────────┤│
│ │AAPL    │   100  │  $150.00   │   $155.00   │ +$500.00   ││
│ │MSFT    │    50  │  $350.00   │   $360.00   │ +$500.00   ││
│ │GOOGL   │    30  │  $140.00   │   $142.00   │  +$60.00   ││
│ └────────┴────────┴────────────┴─────────────┴────────────┘│
├─────────────────────────────────────────────────────────────┤
│ RISK SYSTEMS              │ PERFORMANCE                      │
│ ──────────────            │ ────────────                     │
│ Circuit Breakers: ✅ OK   │ Sharpe Ratio: 1.85              │
│ Portfolio Heat: 27.7%     │ Max Drawdown: -3.2%             │
│ Active Stops: 3           │ Win Rate: 65.0%                 │
│ Max Position: 25.0%       │ Total Trades: 10                │
│ Daily Loss Limit: 5.0%    │ Winning Trades: 6               │
│                           │ Avg Win: $485.50                │
│                           │ Avg Loss: -$275.00              │
├─────────────────────────────────────────────────────────────┤
│                  RECENT TRADES (Last 10)                     │
│ ┌──────┬──────┬────────┬────────┬──────────┬──────────────┐│
│ │Time  │Type  │Symbol  │Shares  │  Price   │     P&L      ││
│ ├──────┼──────┼────────┼────────┼──────────┼──────────────┤│
│ │15:30 │BUY   │SPY     │   10   │ $440.00  │              ││
│ │15:00 │SELL  │NVDA    │   15   │ $455.00  │   +$75.00    ││
│ │14:30 │BUY   │NVDA    │   15   │ $450.00  │              ││
│ │14:00 │BUY   │AMZN    │   25   │ $130.00  │              ││
│ │11:30 │SELL  │TSLA    │   40   │ $245.00  │  -$200.00    ││
│ └──────┴──────┴────────┴────────┴──────────┴──────────────┘│
├─────────────────────────────────────────────────────────────┤
│ Controls: [q]uit  [r]efresh  [p]ause  [c]lear | Auto: 5s   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Portfolio Summary
Displays current portfolio status:
- **Cash Available**: Unallocated cash
- **Positions Value**: Total value of all positions
- **Total Portfolio**: Combined cash and positions
- **Total P&L**: Profit/loss since inception (amount and percentage)

### Active Positions Table
Real-time position tracking:
- **Symbol**: Stock ticker
- **Shares**: Number of shares held
- **Entry Price**: Average purchase price
- **Current Price**: Latest market price
- **Market Value**: Current position value
- **P&L**: Unrealized profit/loss
- **P&L %**: Percentage gain/loss
- **Stop Loss**: Active stop loss price (if set)

### Risk Systems Panel
Risk management status:
- **Circuit Breakers**: System halt status and reasons
- **Portfolio Heat**: Risk exposure as % of portfolio
- **Active Stops**: Number of active stop-loss orders
- **Max Position**: Maximum allowed position size (Kelly Criterion)
- **Daily Loss Limit**: Maximum allowable daily loss

### Performance Metrics
Trading performance analytics:
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Total Trades**: Number of completed trades
- **Winning/Losing Trades**: Trade outcome breakdown
- **Average Win/Loss**: Average profit and loss amounts

### Recent Trades Log
Historical trade activity:
- **Time**: Trade timestamp
- **Type**: BUY or SELL
- **Symbol**: Stock ticker
- **Shares**: Number of shares
- **Price**: Execution price
- **Total**: Trade value
- **P&L**: Realized profit/loss
- **Status**: FILLED, PENDING, etc.

## Integration with Paper Trader

The dashboard seamlessly integrates with the DeepStack Paper Trader:

```python
from core.broker.paper_trader import PaperTrader
from core.cli.dashboard import TradingDashboard
from core.data.alpaca_client import AlpacaClient

# Setup components
config = Config()
alpaca = AlpacaClient(api_key="...", secret_key="...")
trader = PaperTrader(config, alpaca)

# Create and run dashboard
dashboard = TradingDashboard(trader, alpaca)
dashboard.run_sync()
```

## Risk System Integration

When risk systems are enabled, the dashboard displays:

### Circuit Breaker Status
- **Green (✅)**: System operating normally
- **Red (🔴)**: Trading halted with reasons displayed

### Portfolio Heat Indicator
- **Green (<50%)**: Conservative exposure
- **Yellow (50-75%)**: Moderate exposure
- **Red (>75%)**: High exposure warning

### Stop Loss Monitoring
- Active stop orders displayed per position
- Trailing stop status and adjustments
- Stop hit notifications

## Performance Optimization

### Caching Strategy
- Price data cached for 5 seconds
- Performance metrics cached for 10 seconds
- Reduces API calls by ~80%

### Async Updates
- Non-blocking data fetches
- Parallel API calls when possible
- Smooth UI updates at 2 FPS

### Error Handling
- Graceful degradation on API failures
- Fallback to cached/last known values
- Error messages displayed without crashing

## Customization

### Theme Support
Three built-in color themes:
- **default**: Balanced colors for all terminals
- **dark**: Optimized for dark backgrounds
- **light**: Optimized for light backgrounds

### Refresh Rates
- Configurable from 1 to 999999 seconds
- Set to high value for manual-only refresh
- Balance between responsiveness and API usage

## Troubleshooting

### Common Issues

**Dashboard not updating:**
- Check API credentials are set correctly
- Verify network connectivity
- Look for error messages in the footer

**Prices showing as "N/A":**
- Alpaca API may be unavailable
- Market may be closed (for real-time data)
- API rate limits may be exceeded

**Keyboard controls not working:**
- Ensure terminal supports raw mode
- Try running in a different terminal emulator
- Check for conflicting keyboard shortcuts

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m core.cli dashboard
```

Check the log file:
```bash
tail -f dashboard.log
```

## API Requirements

### Alpaca API (Optional)
For live market data:
- Paper trading account recommended
- API key and secret required
- Rate limits: 200 requests/minute

### Without API
Dashboard runs in demo mode:
- Uses last known prices
- Simulates price movements
- Perfect for development/testing

## Best Practices

1. **Use Paper Trading** for testing strategies
2. **Monitor Risk Systems** - Don't ignore warnings
3. **Set Appropriate Refresh Rates** - Balance responsiveness and API usage
4. **Review Trade History** regularly for patterns
5. **Watch Portfolio Heat** to avoid overexposure
6. **Enable Stop Losses** for all positions
7. **Track Performance Metrics** to improve strategy

## Future Enhancements

Planned features for future versions:

1. **Chart Integration** - Mini sparklines for price trends
2. **Alert System** - Audio/visual alerts for events
3. **Strategy Backtesting** - Historical performance view
4. **Multi-Account Support** - Switch between accounts
5. **Custom Indicators** - Add your own metrics
6. **Export Functionality** - Save data to CSV/JSON
7. **Mobile Companion** - Web-based mobile view
8. **Voice Alerts** - Text-to-speech for important events

## Contributing

To contribute to the dashboard:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure 80%+ test coverage
5. Submit a pull request

## Support

For issues or questions:
- Check the documentation first
- Review the example code
- Check the test suite for usage patterns
- Submit an issue on GitHub

## License

MIT License - See LICENSE file for details.

---

*Dashboard Version: 1.0.0 | Last Updated: November 2024*