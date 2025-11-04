# Options Trading Strategies

DeepStack supports advanced options trading strategies with full Greeks calculation and P&L modeling.

## Supported Strategies

### 1. Iron Condor (Neutral Strategy)

A neutral strategy that profits from low volatility and range-bound markets.

**Structure:**
- Sell OTM put (collect premium)
- Buy further OTM put (limit risk)
- Sell OTM call (collect premium)
- Buy further OTM call (limit risk)

**Characteristics:**
- **Strategy Type:** Credit spread (receive money upfront)
- **Max Profit:** Net credit received
- **Max Loss:** Wing width - net credit
- **Best Case:** Stock stays between short strikes until expiration
- **Risk/Reward:** Defined risk, limited profit

**Example:**
```
Stock at $400:
- Sell $380 put @ $2.00
- Buy $375 put @ $1.00
- Sell $420 call @ $2.00
- Buy $425 call @ $1.00

Net credit: $2.00 per spread = $200 total
Max profit: $200 (if SPY stays $380-$420)
Max loss: $300 ($500 width - $200 credit)
Breakevens: $378 and $422
```

**When to Use:**
- Expect low volatility
- Stock likely to trade in a range
- Want to collect premium from time decay
- 30-60 days to expiration optimal

### 2. Bull Call Spread (Bullish Strategy)

A bullish directional strategy with defined risk.

**Structure:**
- Buy call at lower strike (typically ATM or slightly OTM)
- Sell call at higher strike

**Characteristics:**
- **Strategy Type:** Debit spread (pay money upfront)
- **Max Profit:** Strike width - debit paid
- **Max Loss:** Debit paid
- **Best Case:** Stock rises above short strike
- **Risk/Reward:** Defined risk, limited profit

**Example:**
```
Stock at $150:
- Buy $150 call @ $5.00
- Sell $155 call @ $2.00

Net debit: $3.00 per spread = $300 total
Max profit: $200 (if AAPL >= $155)
Max loss: $300 (if AAPL <= $150)
Breakeven: $153
```

**When to Use:**
- Moderately bullish on stock
- Want defined risk
- Stock expected to rise but not explode
- Cheaper than buying calls outright

### 3. Bear Put Spread (Bearish Strategy)

A bearish directional strategy with defined risk.

**Structure:**
- Buy put at higher strike (typically ATM or slightly OTM)
- Sell put at lower strike

**Characteristics:**
- **Strategy Type:** Debit spread (pay money upfront)
- **Max Profit:** Strike width - debit paid
- **Max Loss:** Debit paid
- **Best Case:** Stock falls below short strike
- **Risk/Reward:** Defined risk, limited profit

**Example:**
```
Stock at $150:
- Buy $150 put @ $5.00
- Sell $145 put @ $2.00

Net debit: $3.00 per spread = $300 total
Max profit: $200 (if AAPL <= $145)
Max loss: $300 (if AAPL >= $150)
Breakeven: $147
```

**When to Use:**
- Moderately bearish on stock
- Want defined risk
- Stock expected to fall but not crash
- Cheaper than buying puts outright

---

## Greeks Explained

Options Greeks measure sensitivity to various factors:

### Delta (Δ)
**What it measures:** Price change per $1 move in underlying

- **Call delta:** 0 to +1
- **Put delta:** 0 to -1
- **ATM options:** ~0.5 delta (50% probability of expiring ITM)
- **Deep ITM:** Close to 1.0 (moves nearly 1:1 with stock)
- **Deep OTM:** Close to 0 (barely moves with stock)

**Example:**
- Call with 0.60 delta gains ~$0.60 if stock rises $1
- Put with -0.40 delta gains ~$0.40 if stock falls $1

### Gamma (Γ)
**What it measures:** Rate of change in delta

- **High gamma:** Delta changes rapidly (near ATM, short DTE)
- **Low gamma:** Delta changes slowly (far ITM/OTM, long DTE)
- **Long options:** Positive gamma (delta moves in your favor)
- **Short options:** Negative gamma (delta moves against you)

**Example:**
- Option with delta 0.50 and gamma 0.10:
  - If stock rises $1, new delta = 0.60
  - If stock falls $1, new delta = 0.40

### Theta (Θ)
**What it measures:** Time decay (value lost per day)

- **Long options:** Negative theta (lose value daily)
- **Short options:** Positive theta (gain value daily)
- **Accelerates:** Near expiration, especially ATM options
- **Typical values:** -$0.10 to -$0.50 per day per contract

**Example:**
- Option with theta -0.30 loses ~$0.30 in value tomorrow (all else equal)
- Selling options with +0.30 theta means you gain $0.30/day

### Vega (ν)
**What it measures:** Sensitivity to volatility changes

- **Long options:** Positive vega (benefit from volatility increase)
- **Short options:** Negative vega (benefit from volatility decrease)
- **Higher for:** ATM options and longer DTE
- **Units:** Change per 1% volatility move

**Example:**
- Option with vega 0.15 gains ~$0.15 if IV rises 1%
- Short option with -0.15 vega loses $0.15 if IV rises 1%

---

## Usage Examples

### Creating an Iron Condor

```python
from core.strategies.options import IronCondorStrategy

strategy = IronCondorStrategy(
    wing_width=5.0,           # $5 between long/short strikes
    range_width_pct=0.05,     # 5% OTM for short strikes
    profit_target_pct=0.50,   # Close at 50% of max profit
    loss_limit_pct=0.50       # Close at 50% of max loss
)

position = strategy.create_position(
    symbol="SPY",
    underlying_price=400.0,
    expiration_days=45,
    contracts=2,
    volatility=0.20
)

print(f"Max Profit: ${position.max_profit:.2f}")
print(f"Max Loss: ${position.max_loss:.2f}")
print(f"Breakevens: {position.breakeven_points}")
```

### Creating a Bull Call Spread

```python
from core.strategies.options import BullCallSpread

strategy = BullCallSpread(
    strike_width=5.0,
    profit_target_pct=0.70,
    loss_limit_pct=0.50
)

position = strategy.create_position(
    symbol="AAPL",
    underlying_price=150.0,
    expiration_days=45,
    contracts=1,
    volatility=0.30
)

print(f"Debit Paid: ${position.net_debit_paid():.2f}")
print(f"Max Profit: ${position.max_profit:.2f}")
print(f"Breakeven: ${position.breakeven_points[0]:.2f}")
```

### Calculating P&L and Greeks

```python
from core.strategies.options import (
    calculate_position_greeks,
    model_pnl_scenarios,
)

# Calculate current P&L
current_pnl = strategy.calculate_pnl(
    position=position,
    current_price=405.0,
    days_to_expiration=30,
    volatility=0.20
)

print(f"Current P&L: ${current_pnl:.2f}")

# Calculate Greeks
greeks = calculate_position_greeks(
    position=position,
    underlying_price=405.0,
    days_to_expiration=30,
    volatility=0.20
)

print(f"Delta: {greeks.delta:.4f}")
print(f"Theta: {greeks.theta:.4f} (per day)")
print(f"Vega: {greeks.vega:.4f} (per 1% IV)")

# Check if should close
should_close = strategy.should_close(
    position=position,
    current_pnl=current_pnl,
    days_to_expiration=30
)

if should_close:
    reason = strategy.get_close_reason(position, current_pnl, 30)
    print(f"Should close: {reason}")
```

### P&L Scenario Modeling

```python
from core.strategies.options import model_pnl_scenarios
from core.strategies.options.pnl_modeling import calculate_pnl_at_expiration
import matplotlib.pyplot as plt

# Model P&L across price range
scenarios = model_pnl_scenarios(
    position=position,
    days_to_expiration=30,
    volatility=0.20,
    num_points=100
)

# Also get expiration P&L
expiration_pnl = calculate_pnl_at_expiration(
    position=position,
    num_points=100
)

# Plot the P&L diagram
prices = sorted(scenarios.keys())
current_pnls = [scenarios[p] for p in prices]
exp_pnls = [expiration_pnl[p] for p in prices]

plt.figure(figsize=(10, 6))
plt.plot(prices, current_pnls, label='30 DTE')
plt.plot(prices, exp_pnls, label='At Expiration')
plt.axhline(y=0, color='black', linestyle='--', alpha=0.3)
plt.axhline(y=position.max_profit, color='green', linestyle='--', alpha=0.3)
plt.axhline(y=-position.max_loss, color='red', linestyle='--', alpha=0.3)
plt.xlabel('Stock Price')
plt.ylabel('P&L ($)')
plt.title(f'{position.strategy_name} P&L Diagram')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

---

## Risk Management

### Position Sizing

**Conservative approach:**
- Risk 1-2% of account per trade
- Maximum 5 positions at once
- Don't allocate more than 20% to options

**Example:**
```
Account size: $50,000
Risk per trade: 2% = $1,000
Max loss per Iron Condor: $500
Position size: 2 contracts
```

### Exit Strategies

**Profit Targets:**
- Iron Condors: Close at 50% of max profit
- Vertical Spreads: Close at 70% of max profit
- Capture most of the gain while reducing risk

**Loss Limits:**
- Close at 50% of max loss
- Prevents letting losses run to full max loss
- Cut losses early and move on

**Time-Based:**
- Close at 21 DTE (3 weeks) if not at profit target
- Avoid gamma risk as expiration approaches
- Re-enter with new expiration if still bullish

### Greeks-Based Risk Management

**Delta:**
- Iron Condor: Keep delta near 0 (neutral)
- Bull Call Spread: Positive delta (bullish)
- Bear Put Spread: Negative delta (bearish)

**Theta:**
- Credit spreads benefit from positive theta (time decay)
- Monitor daily theta decay
- Most theta capture occurs in last 30 days

**Vega:**
- Short options benefit from falling volatility
- Avoid entering credit spreads when IV is very low
- Enter when IV is elevated (more premium)

**Gamma:**
- Short options have negative gamma (risk increases near expiration)
- Close positions before gamma explodes (< 7 DTE)

---

## Best Practices

### 1. Use Appropriate Timeframes
- **Iron Condors:** 30-60 DTE optimal
- **Vertical Spreads:** 30-90 DTE
- **Avoid:** < 21 DTE unless actively managing

### 2. Select Good Underlyings
- High liquidity (SPY, QQQ, AAPL, etc.)
- Tight bid-ask spreads
- Sufficient implied volatility

### 3. Volatility Considerations
- Enter Iron Condors when IV is elevated (25th-75th percentile)
- Enter debit spreads when IV is low (cheap premiums)
- Monitor IV rank/percentile

### 4. Strike Selection
- Iron Condors: 1 SD (standard deviation) out
- Vertical Spreads: ATM to 1 SD out
- Further OTM = higher win rate but lower profit

### 5. Position Management
- Set alerts for profit targets and loss limits
- Don't let winners become losers
- Take profits early rather than waiting for max profit
- Review positions daily

### 6. Paper Trading First
- Practice with the PaperTrader before using real money
- Test strategies across different market conditions
- Understand P&L behavior as price moves

---

## Common Mistakes to Avoid

1. **Holding to Expiration**
   - Gamma risk explodes
   - One bad move can wipe out weeks of profits
   - Close early, especially credit spreads

2. **Ignoring Volatility**
   - Selling options when IV is low (not enough premium)
   - Buying options when IV is high (overpaying)
   - Use IV percentile to guide entry

3. **Over-Leveraging**
   - Options can be wiped out completely
   - Size positions appropriately
   - Keep max loss per trade small

4. **No Exit Plan**
   - Always know your profit target and loss limit before entry
   - Stick to the plan
   - Don't move targets emotionally

5. **Trading Illiquid Options**
   - Wide bid-ask spreads eat into profits
   - Hard to exit at fair price
   - Stick to high-volume underlyings

---

## Technical Details

### Black-Scholes Model

The system uses Black-Scholes for option pricing and Greeks calculation:

```
Call Price = S * N(d1) - K * e^(-rT) * N(d2)
Put Price = K * e^(-rT) * N(-d2) - S * N(-d1)

Where:
d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
d2 = d1 - σ√T

S = underlying price
K = strike price
T = time to expiration (years)
σ = volatility
r = risk-free rate
N() = cumulative normal distribution
```

### Limitations

- Black-Scholes assumes European-style options (can't exercise early)
- American options (most stock options) can be exercised early
- Model assumes constant volatility (volatility smile/skew exists)
- For production: use real market data instead of theoretical prices

---

## Integration with DeepStack

Options strategies integrate seamlessly with:

- **PaperTrader:** Test strategies without real money
- **Risk Management:** Position limits and portfolio Greeks
- **Tax System:** Track wash sales on option legs
- **API Server:** REST endpoints for strategy execution

See `/examples/options_demo.py` for complete working examples.
