# Stop Loss Management - Complete Guide

## Overview

The Stop Loss Manager is a production-ready risk management system that ensures **100% stop loss coverage** for all trades. It implements multiple stop types, automatic profit locking with trailing stops, and enforces the critical **never-downgrade rule**.

## Critical Rules

### 1. 100% Coverage Rule
**EVERY order MUST have a stop loss.** No exceptions.

- Unprotected positions are rejected
- System validates coverage before order execution
- Fail-safe mechanism prevents unprotected trades

### 2. Never-Downgrade Rule
**Stops only move in favorable direction.**

- **For LONGS**: Stop can only move UP (or stay same), never down
- **For SHORTS**: Stop can only move DOWN (or stay same), never up
- Prevents increasing risk on active positions
- Emergency stops can override (use with extreme caution)

### 3. Maximum Risk Rule
**Default 2% account risk per trade.**

- Calculated as: (Entry - Stop) × Shares ÷ Account Balance
- Positions exceeding max risk are rejected
- Customizable per trading strategy

## Stop Loss Types

### Fixed Percentage Stop

**Best for**: Simple, predictable risk management.

```python
manager = StopLossManager(account_balance=100000, default_stop_pct=0.02)

stop = manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=150.0,
    position_size=10000.0,
    stop_type="fixed_pct",
    stop_pct=0.02,  # 2% stop
)
# Result: Stop at $147 (2% below entry)
```

**Advantages:**
- Easy to calculate and understand
- Consistent risk per trade
- Works well for most stocks

**Disadvantages:**
- Doesn't adapt to volatility
- May be too tight for volatile stocks
- May be too wide for stable stocks

**When to use:**
- Standard trading conditions
- Well-established stocks with normal volatility
- When simplicity is preferred

### ATR-Based Stop

**Best for**: Volatility-adjusted risk management.

```python
stop = manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=150.0,
    position_size=10000.0,
    stop_type="atr_based",
    atr=2.5,           # Average True Range
    atr_multiplier=2.0,  # 2x ATR
)
# Result: Stop at $145 (2.0 × $2.50 = $5 below entry)
```

**Advantages:**
- Adapts to market volatility
- Wider stops in volatile markets (prevents premature stops)
- Tighter stops in calm markets (better risk control)

**Disadvantages:**
- Requires ATR calculation
- More complex than fixed percentage
- Stop distance varies by stock

**When to use:**
- Highly volatile stocks (small caps, meme stocks)
- Very stable stocks (utilities, bonds)
- When volatility is a key consideration

### Trailing Stop

**Best for**: Automatic profit locking on winning trades.

```python
# Initialize trailing stop
stop = manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=100.0,
    position_size=10000.0,
    stop_type="trailing",
)
# Initial stop: $95 (5% below entry)

# Price moves to $120
update = manager.update_trailing_stop(symbol="AAPL", current_price=120.0)
# Stop moves to: $114 (5% below $120)
# Profit locked: $14 per share

# Price pulls back to $115
update = manager.update_trailing_stop(symbol="AAPL", current_price=115.0)
# Stop stays at: $114 (never downgrades!)
```

**Advantages:**
- Automatically locks in profits
- Follows price up (for longs) or down (for shorts)
- Reduces emotional decision-making
- Captures trend momentum

**Disadvantages:**
- Can exit prematurely on normal pullbacks
- Requires active monitoring
- Not ideal for range-bound markets

**When to use:**
- Strong trending markets
- Momentum trades
- When you want to capture large moves
- Positions showing significant profit

## Never-Downgrade Rule Explained

### Why It Matters

The never-downgrade rule is **critical** for risk management:

1. **Prevents Risk Escalation**: Widening a stop increases your risk on an active position
2. **Protects Profits**: Once you've locked in gains, you shouldn't give them back
3. **Forces Discipline**: Can't "give trades more room" when they're going wrong

### How It Works

#### For Long Positions
```python
# Entry: $100, Initial Stop: $98
manager.calculate_stop_loss(symbol="AAPL", entry_price=100.0, position_size=10000.0)

# ✓ Valid: Moving stop UP to $99 (tighter risk)
manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=99.0)  # True

# ✗ Invalid: Moving stop DOWN to $97 (wider risk)
manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=97.0)  # False
```

#### For Short Positions
```python
# Entry: $200, Initial Stop: $204
manager.calculate_stop_loss(
    symbol="TSLA", entry_price=200.0, position_size=10000.0, position_side="short"
)

# ✓ Valid: Moving stop DOWN to $203 (tighter risk)
manager.validate_stop_never_downgrades(symbol="TSLA", new_stop=203.0)  # True

# ✗ Invalid: Moving stop UP to $205 (wider risk)
manager.validate_stop_never_downgrades(symbol="TSLA", new_stop=205.0)  # False
```

### Emergency Override

Emergency stops can violate the never-downgrade rule in extreme situations:

```python
# Market crash scenario
emergency = manager.emergency_stop_update(
    symbol="AAPL",
    emergency_stop_price=87.0,
    reason="Flash crash - emergency risk reduction",
)

if emergency['violated_never_downgrade']:
    print(f"WARNING: {emergency['warning']}")
    # Log extensively, notify risk management team
```

**Use emergency stops ONLY for:**
- Market flash crashes
- Circuit breaker events
- Company-specific disasters (fraud, bankruptcy)
- Trading halts
- System failures

## 100% Coverage Validation

### Why 100% Coverage?

**Unprotected positions = uncontrolled risk.**

Without stops, a single bad trade can wipe out months of gains. 100% coverage ensures:
- Every position has defined maximum loss
- Portfolio-wide risk is calculable
- No "forgotten" positions without protection

### How to Validate Coverage

```python
# Create stops for all positions
manager.calculate_stop_loss(symbol="AAPL", entry_price=150.0, position_size=10000.0)
manager.calculate_stop_loss(symbol="GOOGL", entry_price=100.0, position_size=8000.0)
manager.calculate_stop_loss(symbol="TSLA", entry_price=200.0, position_size=12000.0)

# Validate coverage
symbols = ["AAPL", "GOOGL", "TSLA"]
coverage = manager.validate_100pct_coverage(symbols)

print(f"Coverage: {coverage['coverage_pct']:.1%}")
print(f"Has 100% Coverage: {coverage['has_100pct_coverage']}")

if not coverage['has_100pct_coverage']:
    print(f"Missing stops: {coverage['missing_stops']}")
    # REJECT NEW ORDERS - Fix coverage first!
```

## Integration with Position Sizing

Stop loss management works hand-in-hand with position sizing:

```python
# Step 1: Calculate position size (Kelly Criterion)
kelly = KellyPositionSizer(account_balance=100000, max_position_pct=0.25)
position = kelly.calculate_position_size(
    win_rate=0.55,
    avg_win=1500,
    avg_loss=1000,
    stock_price=150.0,
)

# Step 2: Calculate stop loss
stop_manager = StopLossManager(account_balance=100000, max_risk_per_trade=0.02)
stop = stop_manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=150.0,
    position_size=position['position_size'],
    stop_type="fixed_pct",
)

# Step 3: Validate risk
if stop['account_risk_pct'] > 0.02:
    print("REJECT: Risk too high - reduce position size or tighten stop")
else:
    print(f"✓ Position size: ${position['position_size']:,.2f}")
    print(f"✓ Stop: ${stop['stop_price']:.2f}")
    print(f"✓ Risk: ${stop['risk_amount']:.2f} ({stop['account_risk_pct']:.2%})")
```

## Best Practices

### 1. Choose the Right Stop Type

- **Standard stocks**: Fixed 2-3% stop
- **Volatile stocks**: ATR-based stop (2-3x ATR)
- **Trending winners**: Trailing stop (3-5% trail)
- **Mix and match**: Use ATR initially, switch to trailing when profitable

### 2. Set Appropriate Stop Distances

- **Too tight** (< 0.5%): High probability of premature stop-out
- **Too wide** (> 10%): Excessive risk, violates 2% rule
- **Goldilocks zone**: 1-5% depending on volatility

### 3. Monitor Active Stops

```python
# Get all active stops
all_stops = manager.get_all_stops()

for symbol, stop_data in all_stops.items():
    print(f"{symbol}: Stop at ${stop_data['stop_price']:.2f}")
```

### 4. Update Trailing Stops Regularly

```python
# Daily update for each position
for symbol in portfolio.get_symbols():
    current_price = market_data.get_current_price(symbol)
    update = manager.update_trailing_stop(symbol=symbol, current_price=current_price)

    if update['stop_moved']:
        print(f"{symbol}: Stop raised to ${update['stop_price']:.2f}")
        print(f"  Profit locked: ${update['profit_locked']:.2f}")
```

### 5. Remove Stops When Positions Close

```python
# When position is sold/closed
manager.remove_stop(symbol="AAPL")
```

## Risk Calculation Details

### Risk Metrics

The system calculates multiple risk metrics:

```python
{
    "risk_amount": 200.0,        # Dollar risk: (Entry - Stop) × Shares
    "risk_pct": 0.02,           # % of position at risk
    "account_risk_pct": 0.002,  # % of total account at risk
    "stop_distance": 0.02,      # Distance from entry to stop (%)
}
```

### Max Risk Validation

Positions exceeding max account risk are **automatically rejected**:

```python
# This will raise ValueError
stop = manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=100.0,
    position_size=30000.0,  # Large position
    stop_type="fixed_pct",
    stop_pct=0.10,  # Wide stop
)
# Risk: $3,000 = 3% of $100k account > 2% max → REJECTED
```

### High Risk Warnings

Positions approaching max risk generate warnings:

```python
if stop['account_risk_pct'] > max_risk * 0.8:
    print(f"WARNING: High risk {stop['account_risk_pct']:.2%}")
    # Consider reducing position size or tightening stop
```

## Complete Trade Lifecycle Example

```python
# 1. Initialize manager
manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

# 2. Enter position with trailing stop
entry = manager.calculate_stop_loss(
    symbol="WINNER",
    entry_price=100.0,
    position_size=10000.0,
    stop_type="trailing",
)
print(f"Initial stop: ${entry['stop_price']:.2f}")  # $95

# 3. Daily updates as price moves
for day, price in enumerate([110, 125, 140, 135, 133], start=1):
    update = manager.update_trailing_stop(symbol="WINNER", current_price=price)
    print(f"Day {day}: Price ${price}, Stop ${update['stop_price']:.2f}")

# Output:
# Day 1: Price $110, Stop $104.50
# Day 2: Price $125, Stop $118.75
# Day 3: Price $140, Stop $133.00
# Day 4: Price $135, Stop $133.00 (never downgrades!)
# Day 5: Price $133, Stop $133.00 (STOPPED OUT)

# 4. Position closed
manager.remove_stop("WINNER")
print("Profit: $33 per share (33% return)")
```

## Common Pitfalls to Avoid

### 1. Moving Stops Away (Downgrading)

```python
# ✗ WRONG: "Give the trade more room"
# This violates the never-downgrade rule
```

**Why it's bad**: You're increasing risk on a losing position. If your original stop was wrong, exit and re-enter with better parameters.

### 2. Not Using Stops

```python
# ✗ WRONG: "I'll watch it closely and exit manually"
```

**Why it's bad**: Emotional decisions, distraction, system failures. Stops are non-negotiable.

### 3. Stops Too Tight

```python
# ✗ WRONG: 0.2% stop on a volatile stock
```

**Why it's bad**: Normal price oscillation will stop you out. Use ATR-based stops for volatile stocks.

### 4. Stops Too Wide

```python
# ✗ WRONG: 20% stop
```

**Why it's bad**: Excessive risk. A single loss wipes out months of gains. Keep stops within 2-10% range.

### 5. Ignoring Trailing Stops

```python
# ✗ WRONG: Never updating trailing stops
```

**Why it's bad**: You're leaving profit on the table. Update trailing stops daily or when price moves significantly.

## Error Handling

The system includes comprehensive error handling:

```python
# Invalid inputs are rejected
try:
    stop = manager.calculate_stop_loss(
        symbol="",  # Empty symbol
        entry_price=-100,  # Negative price
        position_size=0,  # Zero position
    )
except ValueError as e:
    print(f"Error: {e}")

# Risk violations are rejected
try:
    stop = manager.calculate_stop_loss(
        symbol="AAPL",
        entry_price=100.0,
        position_size=100000.0,  # Too large
        stop_type="fixed_pct",
        stop_pct=0.20,  # Too wide
    )
except ValueError as e:
    print(f"Risk violation: {e}")
```

## Testing & Validation

The system includes 53+ comprehensive tests covering:

- All stop types (fixed %, ATR, trailing)
- Never-downgrade rule enforcement
- 100% coverage validation
- Risk calculation accuracy
- Edge cases and error conditions
- Integration scenarios

Run tests:
```bash
pytest tests/unit/test_stop_loss_manager.py -v
```

## Performance Considerations

- **Lightweight**: Stop calculations are O(1) operations
- **Memory efficient**: Only stores active stops
- **Thread-safe**: Can be used in multi-threaded environments (with proper locking)
- **Scalable**: Tested with 1000+ concurrent positions

## API Reference

### StopLossManager

#### Constructor
```python
StopLossManager(
    account_balance: float,
    max_risk_per_trade: float = 0.02,
    default_stop_pct: float = 0.02,
    default_atr_multiplier: float = 2.0,
    default_trailing_pct: float = 0.05,
    min_stop_distance: float = 0.005,
    max_stop_distance: float = 0.10,
)
```

#### calculate_stop_loss()
Calculate stop loss for a new position.

**Returns**: Dict with stop details (stop_price, risk_amount, etc.)

#### update_trailing_stop()
Update trailing stop based on new price.

**Returns**: Dict with update details (stop_price, stop_moved, profit_locked)

#### validate_stop_never_downgrades()
Validate that a new stop doesn't violate never-downgrade rule.

**Returns**: bool (True if valid, False if violation)

#### validate_100pct_coverage()
Validate that all positions have stops.

**Returns**: Dict with coverage report

#### emergency_stop_update()
Emergency stop update (bypasses never-downgrade rule).

**Returns**: Dict with update details and warnings

## Summary

The Stop Loss Manager provides:

✓ **100% Coverage** - Every trade protected
✓ **Never-Downgrade Rule** - Stops only move favorably
✓ **Multiple Stop Types** - Fixed %, ATR, trailing
✓ **Automatic Profit Locking** - Trailing stops capture gains
✓ **Risk Control** - Max 2% account risk per trade
✓ **Integration** - Works with Kelly position sizer
✓ **Production Ready** - Comprehensive testing, error handling

**Remember**: Stop loss management is not optional. It's the foundation of professional trading. Without stops, you're gambling. With stops, you're trading.
