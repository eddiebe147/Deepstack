# Pairs Trading Strategy

**Statistical arbitrage through mean-reverting cointegrated pairs**

## Overview

The Pairs Trading Strategy identifies and trades cointegrated asset pairs that exhibit mean-reverting behavior. When the spread between two cointegrated assets deviates significantly from its historical mean, the strategy takes positions expecting the spread to revert.

### Key Concepts

**Cointegration**: Two securities that move together over the long term, even if they have independent short-term fluctuations. Their spread is mean-reverting.

**Spread**: The difference between two assets adjusted by a hedge ratio:
```
spread = asset_a - (hedge_ratio × asset_b)
```

**Z-Score**: Standardized measure of how far the current spread is from its mean:
```
z_score = (current_spread - mean_spread) / std_spread
```

## Strategy Logic

### 1. Pair Selection

The strategy screens asset pairs for cointegration using the Augmented Dickey-Fuller (ADF) test:

1. **Linear Regression**: Calculate hedge ratio (β) between two assets
2. **Spread Calculation**: Compute residuals (spread) from regression
3. **Stationarity Test**: Apply ADF test to spread
4. **Cointegration**: If p-value < 0.05, pair is cointegrated

### 2. Entry Signals

Enter positions when spread deviates significantly from mean:

- **Long Spread** (z < -2.0): Buy asset A, sell asset B
  - Spread is abnormally low
  - Expect mean reversion upward

- **Short Spread** (z > +2.0): Sell asset A, buy asset B
  - Spread is abnormally high
  - Expect mean reversion downward

### 3. Exit Signals

Exit positions when spread reverts to mean:

- **Mean Reversion Exit** (|z| < 0.5): Close position
  - Spread has returned to normal range
  - Take profit

- **Stop Loss** (|z| > 3.5): Force exit
  - Spread has moved too far against us
  - Cointegration may be broken
  - Cut losses

## Implementation

### Basic Usage

```python
from core.strategies.pairs_trading import PairsTradingStrategy
import pandas as pd

# Initialize strategy
strategy = PairsTradingStrategy(
    adf_p_value_threshold=0.05,  # 5% significance for cointegration
    entry_z_threshold=2.0,        # Enter at |z| > 2.0
    exit_z_threshold=0.5,         # Exit at |z| < 0.5
    stop_z_threshold=3.5,         # Stop at |z| > 3.5
    z_score_window=20             # 20-day rolling window
)

# Screen for pairs
universe = ["KO", "PEP", "DAL", "UAL", "F", "GM", "V", "MA", "XOM", "CVX"]
price_data = pd.DataFrame(...)  # Your price data

pairs = strategy.screen_for_pairs(universe, price_data)

print(f"Found {len(pairs)} cointegrated pairs")
```

### Generate Trading Signals

```python
# Monitor pairs for signals
signals = strategy.monitor_pairs(pairs, price_data)

for signal in signals:
    print(f"{signal.asset_a}/{signal.asset_b}: {signal.signal_type}")
    print(f"  Z-score: {signal.z_score:.2f}")
    print(f"  Confidence: {signal.confidence:.1f}%")
    print(f"  Hedge ratio: {signal.hedge_ratio:.4f}")
```

### Backtest Pairs

```python
# Backtest a single pair
results = strategy.backtest_pair(
    pair=pairs[0],
    price_data=price_data,
    initial_capital=100000
)

print(f"Total Trades: {results['total_trades']}")
print(f"Win Rate: {results['win_rate']*100:.1f}%")
print(f"Total Return: {results['return_pct']:.2f}%")

# Validate all pairs
all_results = strategy.validate_pairs(pairs, price_data)

for result in all_results:
    print(f"{result['pair']}: {result['return_pct']:+.2f}%")
```

## API Reference

### PairsTradingStrategy

Main strategy class for pairs trading.

**Constructor Parameters:**
- `adf_p_value_threshold` (float): Max p-value for cointegration (default: 0.05)
- `min_lookback_days` (int): Minimum data required (default: 60)
- `z_score_window` (int): Rolling window for z-score (default: 20)
- `entry_z_threshold` (float): Entry threshold (default: 2.0)
- `exit_z_threshold` (float): Exit threshold (default: 0.5)
- `stop_z_threshold` (float): Stop loss threshold (default: 3.5)
- `max_holding_days` (int): Maximum hold period (default: 30)
- `min_confidence` (float): Minimum signal confidence (default: 60.0)

**Methods:**

#### screen_for_pairs(universe, price_data)

Screen assets for cointegrated pairs.

**Args:**
- `universe` (List[str]): List of asset symbols
- `price_data` (pd.DataFrame): Price data with symbol columns

**Returns:**
- List[TradingPair]: Cointegrated pairs

**Example:**
```python
pairs = strategy.screen_for_pairs(
    universe=["KO", "PEP", "XOM", "CVX"],
    price_data=price_df
)
```

#### test_cointegration(price_series_a, price_series_b, asset_a, asset_b)

Test two assets for cointegration.

**Args:**
- `price_series_a` (pd.Series): Price series for asset A
- `price_series_b` (pd.Series): Price series for asset B
- `asset_a` (str): Symbol for asset A
- `asset_b` (str): Symbol for asset B

**Returns:**
- CointegrationTest: Test results with p-value and hedge ratio

**Example:**
```python
test = strategy.test_cointegration(
    price_series_a=df["KO"],
    price_series_b=df["PEP"],
    asset_a="KO",
    asset_b="PEP"
)

if test.is_cointegrated:
    print(f"Cointegrated! p-value: {test.p_value:.4f}")
    print(f"Hedge ratio: {test.hedge_ratio:.4f}")
```

#### calculate_spread_statistics(pair, price_data)

Calculate current spread statistics.

**Args:**
- `pair` (TradingPair): Trading pair
- `price_data` (pd.DataFrame): Recent price data

**Returns:**
- SpreadStatistics: Current spread stats including z-score

**Example:**
```python
stats = strategy.calculate_spread_statistics(pair, price_data)

print(f"Current spread: {stats.current_spread:.2f}")
print(f"Mean: {stats.mean:.2f}")
print(f"Std: {stats.std:.2f}")
print(f"Z-score: {stats.z_score:.2f}")
```

#### generate_signals(pair, price_data)

Generate trading signal for a pair.

**Args:**
- `pair` (TradingPair): Trading pair
- `price_data` (pd.DataFrame): Recent price data

**Returns:**
- Optional[PairSignal]: Trading signal or None

**Example:**
```python
signal = strategy.generate_signals(pair, price_data)

if signal:
    if signal.signal_type == "entry_long":
        # Buy asset A, sell asset B
        pass
    elif signal.signal_type == "exit":
        # Close positions
        pass
```

#### monitor_pairs(pairs, price_data)

Monitor multiple pairs for signals.

**Args:**
- `pairs` (List[TradingPair]): Pairs to monitor
- `price_data` (pd.DataFrame): Recent price data

**Returns:**
- List[PairSignal]: All generated signals

**Example:**
```python
signals = strategy.monitor_pairs(all_pairs, price_data)

for signal in signals:
    if signal.confidence >= 80:
        # High confidence signal
        execute_trade(signal)
```

#### backtest_pair(pair, price_data, initial_capital)

Backtest a pair on historical data.

**Args:**
- `pair` (TradingPair): Pair to backtest
- `price_data` (pd.DataFrame): Historical price data
- `initial_capital` (float): Starting capital (default: 100000)

**Returns:**
- Dict: Backtest results with metrics and trades

**Example:**
```python
results = strategy.backtest_pair(
    pair=pair,
    price_data=historical_data,
    initial_capital=100000
)

print(f"Total trades: {results['total_trades']}")
print(f"Win rate: {results['win_rate']*100:.1f}%")
print(f"Total PnL: ${results['total_pnl']:,.2f}")
print(f"Return: {results['return_pct']:.2f}%")
```

#### validate_pairs(pairs, price_data)

Backtest multiple pairs.

**Args:**
- `pairs` (List[TradingPair]): Pairs to validate
- `price_data` (pd.DataFrame): Historical price data

**Returns:**
- List[Dict]: Results for each pair, sorted by return

**Example:**
```python
results = strategy.validate_pairs(all_pairs, price_data)

# Find top performers
top_5 = results[:5]
for result in top_5:
    print(f"{result['pair']}: {result['return_pct']:+.2f}%")
```

### Data Classes

#### TradingPair

Represents a cointegrated trading pair.

**Attributes:**
- `asset_a` (str): First asset symbol
- `asset_b` (str): Second asset symbol
- `hedge_ratio` (float): Beta coefficient from regression
- `cointegration_test` (CointegrationTest): Test results
- `status` (PairStatus): Current position status
- `entry_z_score` (float): Z-score at entry
- `pnl` (float): Current profit/loss

**Example:**
```python
pair = TradingPair(
    asset_a="KO",
    asset_b="PEP",
    hedge_ratio=1.05,
    cointegration_test=test,
    status=PairStatus.NO_POSITION
)

# Update status
pair.update_status(PairStatus.LONG_SPREAD)
pair.update_pnl(1500.0)
```

#### CointegrationTest

Results from cointegration testing.

**Attributes:**
- `asset_a` (str): First asset
- `asset_b` (str): Second asset
- `test_type` (str): "adf" or "johansen"
- `is_cointegrated` (bool): Whether pair is cointegrated
- `test_statistic` (float): Test statistic value
- `p_value` (float): P-value (0-1)
- `critical_value` (float): Critical value at 5%
- `hedge_ratio` (float): Beta coefficient
- `timestamp` (datetime): Test timestamp

#### SpreadStatistics

Current spread statistics.

**Attributes:**
- `mean` (float): Mean of spread over window
- `std` (float): Standard deviation
- `z_score` (float): Current z-score
- `current_spread` (float): Current spread value
- `lookback_window` (int): Window size used
- `timestamp` (datetime): Calculation timestamp

#### PairSignal

Trading signal for a pair.

**Attributes:**
- `asset_a` (str): First asset
- `asset_b` (str): Second asset
- `signal_type` (str): "entry_long", "entry_short", "exit", "stop"
- `z_score` (float): Current z-score
- `spread` (float): Current spread
- `hedge_ratio` (float): Position sizing ratio
- `confidence` (float): Signal confidence (0-100)
- `timestamp` (datetime): Signal timestamp
- `metadata` (dict): Additional information

**Example:**
```python
signal = PairSignal(
    asset_a="KO",
    asset_b="PEP",
    signal_type="entry_long",
    z_score=-2.5,
    spread=-3.75,
    hedge_ratio=1.05,
    confidence=85.0,
    timestamp=datetime.now()
)

signal_dict = signal.to_dict()
```

### Enums

#### PairStatus

Current status of a trading pair.

Values:
- `NO_POSITION`: No active position
- `LONG_SPREAD`: Long asset A, short asset B
- `SHORT_SPREAD`: Short asset A, long asset B
- `COINTEGRATION_BROKEN`: Pair no longer cointegrated

## Examples

### Example 1: Basic Pair Trading

```python
from core.strategies.pairs_trading import PairsTradingStrategy
import pandas as pd

# Load your price data
price_data = pd.read_csv("prices.csv", index_col=0, parse_dates=True)

# Initialize strategy
strategy = PairsTradingStrategy()

# Screen for pairs
universe = ["KO", "PEP", "XOM", "CVX", "V", "MA"]
pairs = strategy.screen_for_pairs(universe, price_data)

# Monitor and trade
while True:
    # Get latest prices
    latest_data = get_latest_prices()

    # Generate signals
    signals = strategy.monitor_pairs(pairs, latest_data)

    # Execute trades
    for signal in signals:
        if signal.confidence >= 75:
            execute_signal(signal)
```

### Example 2: Backtesting Portfolio

```python
# Screen and backtest
pairs = strategy.screen_for_pairs(universe, historical_data)
results = strategy.validate_pairs(pairs, historical_data)

# Analyze results
profitable_pairs = [r for r in results if r["return_pct"] > 0]

print(f"Profitable pairs: {len(profitable_pairs)}/{len(results)}")

# Select best pairs for live trading
top_pairs = results[:5]  # Top 5 by return

for result in top_pairs:
    print(f"{result['pair']}")
    print(f"  Return: {result['return_pct']:+.2f}%")
    print(f"  Win rate: {result['win_rate']*100:.1f}%")
    print(f"  Trades: {result['total_trades']}")
```

### Example 3: Live Monitoring Dashboard

```python
import time

# Initialize
strategy = PairsTradingStrategy()
pairs = load_selected_pairs()

# Monitor continuously
while True:
    # Get current prices
    current_data = fetch_current_prices()

    # Check each pair
    for pair in pairs:
        # Calculate spread
        stats = strategy.calculate_spread_statistics(pair, current_data)

        # Generate signal
        signal = strategy.generate_signals(pair, current_data)

        # Display status
        print(f"{pair.asset_a}/{pair.asset_b}: z={stats.z_score:.2f}, "
              f"status={pair.status.value}")

        if signal:
            print(f"  SIGNAL: {signal.signal_type} "
                  f"(confidence={signal.confidence:.1f}%)")

            # Execute if high confidence
            if signal.confidence >= 80:
                execute_trade(signal)

    # Wait before next update
    time.sleep(60)  # Update every minute
```

## Performance Metrics

### Target Quality Gates

- **Pairs Found**: 5+ valid cointegrated pairs from test universe
- **Backtest Win Rate**: 60%+ win rate
- **Backtest Return**: Positive returns on validation
- **Test Coverage**: 80%+ code coverage

### Expected Performance

Based on academic research and historical data:

- **Win Rate**: 60-70% (mean reversion tendency)
- **Sharpe Ratio**: 1.5-2.5 (market-neutral strategy)
- **Max Drawdown**: 10-20% (stop losses limit downside)
- **Annual Return**: 10-25% (depending on market conditions)

### Risk Factors

1. **Cointegration Break**: Pairs can become non-cointegrated
   - **Mitigation**: Regular cointegration retesting
   - **Stop loss** at |z| > 3.5

2. **Execution Risk**: Simultaneous execution of both legs
   - **Mitigation**: Use limit orders, check fills

3. **Transaction Costs**: Frequent trading can erode returns
   - **Mitigation**: Optimize thresholds, reduce turnover

4. **Regime Changes**: Market conditions affect mean reversion
   - **Mitigation**: Integrate with regime detector

## Best Practices

### Pair Selection

1. **Similar Sectors**: Choose pairs from same industry
2. **Liquid Assets**: Ensure sufficient liquidity
3. **Stable Correlation**: Check long-term relationship
4. **Periodic Retesting**: Verify cointegration monthly

### Position Sizing

1. **Equal Dollar Amounts**: Use hedge ratio for sizing
2. **Portfolio Allocation**: Limit per-pair exposure to 10%
3. **Stop Losses**: Always use stop at |z| > 3.5
4. **Diversification**: Trade multiple uncorrelated pairs

### Parameter Tuning

1. **Entry Threshold**: 2.0-2.5 standard deviations
2. **Exit Threshold**: 0.3-0.7 standard deviations
3. **Stop Threshold**: 3.0-4.0 standard deviations
4. **Window Size**: 20-60 days for z-score

### Integration

```python
# Integrate with regime detector
from core.regime.regime_detector import RegimeDetector

regime_detector = RegimeDetector()
pairs_strategy = PairsTradingStrategy()

# Adjust strategy by regime
regime = regime_detector.detect_regime(market_factors)

if regime.regime == MarketRegime.CRISIS:
    # Tighten stops in crisis
    pairs_strategy.stop_z_threshold = 3.0
elif regime.regime == MarketRegime.BULL:
    # More aggressive in bull market
    pairs_strategy.entry_z_threshold = 1.8
```

## Common Asset Pairs

### Consumer Staples
- **KO/PEP**: Coca-Cola / PepsiCo
- **PG/CL**: Procter & Gamble / Colgate-Palmolive

### Airlines
- **DAL/UAL**: Delta / United Airlines
- **AAL/LUV**: American Airlines / Southwest

### Automotive
- **F/GM**: Ford / General Motors
- **TM/HMC**: Toyota / Honda

### Financials
- **V/MA**: Visa / Mastercard
- **JPM/BAC**: JPMorgan / Bank of America

### Energy
- **XOM/CVX**: Exxon Mobil / Chevron
- **COP/EOG**: ConocoPhillips / EOG Resources

### Technology
- **MSFT/GOOGL**: Microsoft / Alphabet
- **ORCL/SAP**: Oracle / SAP

## Troubleshooting

### No Pairs Found

**Problem**: Screen returns 0 cointegrated pairs

**Solutions:**
1. Increase p-value threshold (try 0.10)
2. Use more historical data (180+ days)
3. Choose assets from same sector
4. Check data quality (no missing values)

### Too Many False Signals

**Problem**: Signals don't lead to profitable trades

**Solutions:**
1. Increase entry threshold (try 2.5)
2. Increase minimum confidence (try 75%)
3. Add volume filters
4. Verify cointegration is still valid

### Large Losses

**Problem**: Stop losses triggered frequently

**Solutions:**
1. Lower stop threshold (try 3.0)
2. Retest cointegration more frequently
3. Reduce position sizes
4. Avoid pairs with low liquidity

## References

1. **Gatev, E., Goetzmann, W., & Rouwenhorst, K.** (2006). "Pairs trading: Performance of a relative-value arbitrage rule." Review of Financial Studies.

2. **Vidyamurthy, G.** (2004). "Pairs Trading: Quantitative Methods and Analysis." Wiley Finance.

3. **Engle, R. F., & Granger, C. W.** (1987). "Co-integration and error correction: representation, estimation, and testing." Econometrica.

4. **Dickey, D. A., & Fuller, W. A.** (1979). "Distribution of the estimators for autoregressive time series with a unit root." Journal of the American Statistical Association.
