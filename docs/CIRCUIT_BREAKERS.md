# Circuit Breakers - Production Trading Protection

## Overview

Circuit breakers are the **final line of defense** against catastrophic losses in the DeepStack trading system. They automatically halt trading when risk thresholds are breached, protecting capital during extreme market conditions, strategy breakdowns, or operational errors.

### Why Circuit Breakers Matter

> "The best traders know when NOT to trade." - Ed Seykota

Circuit breakers enforce discipline when emotions run high. They prevent:
- **Revenge trading** after losses
- **Overtrading** in volatile markets
- **Strategy failure** cascades
- **Catastrophic drawdowns**
- **Emotional decision-making** during stress

### Key Principle: Fail-Safe Design

All circuit breakers follow **fail-safe** principles:
- If uncertain → trip the breaker (halt trading)
- If check fails → assume breaker tripped
- No bypass without confirmation code
- Extensive logging for audit trail

## Circuit Breaker Types

### 1. Daily Loss Limit Breaker

**Purpose**: Halt trading after excessive daily losses

**When it trips**:
- Daily loss exceeds threshold (default: 3%)
- Calculated from start-of-day portfolio value

**Auto-reset**:
- Yes - resets at market open next day

**Use case**:
```python
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.03  # Halt at 3% daily loss
)

# Start of day: $100,000
# Current value: $96,500 (-3.5%)
status = breaker.check_breakers(
    current_portfolio_value=96500,
    start_of_day_value=100000
)

# status["trading_allowed"] = False
# Breaker tripped - stop trading for today
```

**Best practices**:
- Set limit at 2-5% for conservative approach
- Tighter limits (1-2%) for aggressive risk management
- Consider your typical daily volatility
- Account for intraday swings (don't set too tight)

---

### 2. Max Drawdown Breaker

**Purpose**: Halt trading during severe portfolio drawdowns

**When it trips**:
- Portfolio drops X% from all-time peak (default: 10%)
- Tracks highest portfolio value achieved

**Auto-reset**:
- No - requires manual reset after review

**Use case**:
```python
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    max_drawdown_limit=0.10  # Halt at 10% drawdown from peak
)

# Portfolio grew to $120,000 (new peak)
breaker.check_breakers(current_portfolio_value=120000)

# Portfolio drops to $108,000 (10% down from $120k peak)
status = breaker.check_breakers(current_portfolio_value=108000)

# status["trading_allowed"] = False
# Breaker tripped - manual intervention required
```

**Best practices**:
- Set limit at 10-20% for most traders
- Tighter limits (5-10%) for lower risk tolerance
- Review strategy when this trips (may indicate fundamental issues)
- Consider market conditions (bear vs bull market)

**Why no auto-reset?**

Drawdowns signal potential strategy failure or regime change. Manual reset forces you to:
1. Review what went wrong
2. Assess if strategy still valid
3. Adjust parameters if needed
4. Make conscious decision to resume

---

### 3. Consecutive Losses Breaker

**Purpose**: Halt trading after multiple losing trades in a row

**When it trips**:
- N consecutive losing trades (default: 5)
- Indicates strategy breakdown or unfavorable conditions

**Auto-reset**:
- No - requires manual reset (though counter resets on first win)

**Use case**:
```python
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    consecutive_loss_limit=5  # Halt after 5 losing trades
)

# Record trades
breaker.record_trade(-150)  # Loss 1
breaker.record_trade(-200)  # Loss 2
breaker.record_trade(-120)  # Loss 3
breaker.record_trade(-180)  # Loss 4
breaker.record_trade(-160)  # Loss 5

status = breaker.check_breakers(current_portfolio_value=99000)

# status["trading_allowed"] = False
# Breaker tripped - strategy may be broken
```

**Best practices**:
- Set limit at 5-10 trades for most strategies
- Lower limits (3-5) for high-frequency strategies
- Higher limits (10+) for lower frequency
- Consider your typical win rate

**What it detects**:
- Strategy no longer working (market regime change)
- Bad execution (slippage, timing issues)
- Overfitting (backtest vs reality divergence)
- Emotional trading (revenge trading spiral)

---

### 4. Volatility Spike Breaker

**Purpose**: Halt trading during extreme market volatility

**When it trips**:
- VIX exceeds threshold (default: 40)
- Protects against chaotic market conditions

**Auto-reset**:
- Yes - resets when VIX normalizes (after auto_reset_hours)

**Use case**:
```python
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    volatility_threshold=35.0  # Halt when VIX > 35
)

# Normal market: VIX = 20
status = breaker.check_breakers(
    current_portfolio_value=100000,
    current_vix=20.0
)
# Trading allowed

# Market crash: VIX = 55
status = breaker.check_breakers(
    current_portfolio_value=98000,
    current_vix=55.0
)
# status["trading_allowed"] = False
# Too volatile - halt trading
```

**VIX thresholds guide**:
- VIX < 15: Very low volatility (calm market)
- VIX 15-25: Normal volatility
- VIX 25-35: Elevated volatility (caution)
- VIX 35-50: High volatility (halt recommended)
- VIX > 50: Extreme volatility (market crisis)

**Best practices**:
- Set threshold at 35-45 for most traders
- Lower threshold (25-35) for conservative approach
- Consider your strategy's sensitivity to volatility
- May miss opportunities but prevents disasters

---

### 5. Manual Breaker

**Purpose**: Allow manual trading halt for any reason

**When it trips**:
- Manually triggered by operator
- Emergency halt capability

**Auto-reset**:
- No - requires manual reset

**Use case**:
```python
breaker = CircuitBreaker(initial_portfolio_value=100000)

# Emergency situation detected
trip_result = breaker.trip_breaker(
    BreakerType.MANUAL.value,
    "Data feed issue - halting until resolved"
)

# Get confirmation code for later reset
code = trip_result["confirmation_code"]

# ... resolve issue ...

# Reset when ready
breaker.reset_breaker(
    BreakerType.MANUAL.value,
    code,
    "Data feed restored and verified"
)
```

**When to use**:
- Data feed issues
- System anomalies
- External events (geopolitical, company-specific)
- Debugging/testing
- End of day shutdown

---

## Integration with Risk Management

### Complete Risk Stack

```python
# Initialize all risk components
circuit_breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.03,
    max_drawdown_limit=0.10,
    consecutive_loss_limit=5,
    volatility_threshold=35.0
)

kelly_sizer = KellyPositionSizer(
    account_balance=100000,
    max_position_pct=0.25,
    max_total_exposure=1.0
)

stop_loss_manager = StopLossManager(
    account_balance=100000,
    max_risk_per_trade=0.02
)
```

### Trade Execution Workflow

```python
# STEP 1: Check circuit breakers FIRST
status = circuit_breaker.check_breakers(
    current_portfolio_value=portfolio_value,
    start_of_day_value=start_of_day,
    current_vix=vix
)

if not status["trading_allowed"]:
    print(f"Trading halted: {status['reasons']}")
    return  # STOP - do not trade

# STEP 2: Calculate position size (Kelly)
position = kelly_sizer.calculate_position_size(
    win_rate=0.55,
    avg_win=1200,
    avg_loss=800,
    stock_price=150.0
)

if position["position_size"] == 0:
    print(f"No position: {position['rationale']}")
    return

# STEP 3: Calculate stop loss
stop = stop_loss_manager.calculate_stop_loss(
    symbol="AAPL",
    entry_price=150.0,
    position_size=position["position_size"],
    stop_type="fixed_pct",
    stop_pct=0.02
)

# STEP 4: Execute trade (all risk checks passed)
execute_trade(
    symbol="AAPL",
    shares=position["shares"],
    entry=150.0,
    stop=stop["stop_price"]
)

# STEP 5: Record trade result (for consecutive loss tracking)
# ... after trade closes ...
circuit_breaker.record_trade(trade_pnl)
```

---

## Breaker Reset Procedures

### Security Model

Circuit breakers use **confirmation codes** to prevent unauthorized resets:

1. When breaker trips → generates unique confirmation code
2. Code logged and/or sent to authorized personnel
3. Reset requires exact code match
4. Invalid code → reset denied, attempt logged

### Reset Workflow

```python
# 1. Trip occurs
status = breaker.check_breakers(...)
if not status["trading_allowed"]:
    # 2. Get confirmation code
    code = breaker.active_confirmation_codes[BreakerType.DAILY_LOSS.value]
    print(f"Confirmation code: {code}")

    # 3. Log code securely
    # (in production, send to authorized personnel)

    # 4. Try reset with wrong code (fails)
    try:
        breaker.reset_breaker(BreakerType.DAILY_LOSS.value, "WRONG", "Reset")
    except PermissionError:
        print("Reset denied - invalid code")

    # 5. Reset with correct code (succeeds)
    result = breaker.reset_breaker(
        BreakerType.DAILY_LOSS.value,
        code,
        "Market stabilized, reviewed losses, resuming trading"
    )
    print(f"Reset successful after {result['trip_duration']}")
```

### Reset Checklist

Before resetting a tripped breaker, verify:

**Daily Loss Breaker**:
- [ ] Understood what caused losses
- [ ] Reviewed all trades from today
- [ ] Verified strategy still valid
- [ ] Confirmed no system issues
- [ ] Ready to resume with reduced size/risk

**Max Drawdown Breaker**:
- [ ] Comprehensive strategy review completed
- [ ] Analyzed what changed in market/strategy
- [ ] Adjusted parameters if needed
- [ ] Tested adjustments in paper trading
- [ ] Confirmed emotional readiness to trade

**Consecutive Losses Breaker**:
- [ ] Identified why losses occurred
- [ ] Determined if strategy broken or unlucky streak
- [ ] Reviewed strategy assumptions
- [ ] Checked for execution issues
- [ ] Plan for smaller sizes initially

**Volatility Breaker**:
- [ ] VIX returned to normal levels
- [ ] Market conditions stabilized
- [ ] Confirmed data feeds accurate
- [ ] Ready for potentially wider stops

---

## Monitoring and Alerts

### Warning Thresholds

Breakers emit warnings at 80-90% of limits:

```python
status = breaker.check_breakers(...)

if status["warnings"]:
    for warning in status["warnings"]:
        print(f"⚠ {warning}")
        # Send alert via email/SMS/Discord
```

**Example warnings**:
- "Approaching daily loss limit: 2.5% (limit: 3%)"
- "Approaching max drawdown limit: 8.5% (limit: 10%)"
- "Approaching consecutive loss limit: 4 (limit: 5)"
- "VIX approaching threshold: 33 (threshold: 35)"

### Logging

All breaker events are logged:
- Initialization with parameters
- Threshold approaches (warnings)
- Breaker trips (with reason)
- Reset attempts (success/failure)
- Auto-reset events

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Logs automatically generated:
# "CircuitBreaker initialized: daily_loss=3%, max_drawdown=10%..."
# "CIRCUIT BREAKER TRIPPED: DAILY_LOSS - Daily loss limit breached..."
# "CIRCUIT BREAKER RESET: DAILY_LOSS - Manual reset after review"
```

---

## Best Practices

### 1. Conservative Initial Settings

Start with **tight limits** and loosen as you gain confidence:

```python
# Conservative (recommended for new strategies)
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.02,      # 2% daily
    max_drawdown_limit=0.08,    # 8% drawdown
    consecutive_loss_limit=3,   # 3 losses
    volatility_threshold=30.0   # VIX > 30
)

# Moderate (proven strategy)
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.03,      # 3% daily
    max_drawdown_limit=0.10,    # 10% drawdown
    consecutive_loss_limit=5,   # 5 losses
    volatility_threshold=35.0   # VIX > 35
)

# Aggressive (experienced, tested strategy)
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.05,      # 5% daily
    max_drawdown_limit=0.15,    # 15% drawdown
    consecutive_loss_limit=7,   # 7 losses
    volatility_threshold=40.0   # VIX > 40
)
```

### 2. Don't Fight the Breakers

When a breaker trips:
- **STOP IMMEDIATELY** - don't try to "make it back"
- **REVIEW OBJECTIVELY** - what went wrong?
- **LEARN AND ADJUST** - improve strategy/execution
- **RESET DELIBERATELY** - only when truly ready

### 3. Track Breaker Trips

Keep a journal of all breaker trips:
- Date/time of trip
- Breaker type(s)
- What caused it
- What you learned
- Changes made before reset

This creates valuable feedback for improving your system.

### 4. Test Breakers Regularly

In paper trading or backtesting:
- Verify breakers trip when expected
- Ensure no bypass methods exist
- Test reset procedures
- Validate warning thresholds

### 5. Coordinate with Account Size

Adjust limits as account grows:

```python
# Small account ($10k)
daily_loss_limit = 0.02  # 2% = $200 max daily loss

# Medium account ($100k)
daily_loss_limit = 0.03  # 3% = $3,000 max daily loss

# Large account ($1M)
daily_loss_limit = 0.03  # 3% = $30,000 max daily loss

# Update when account changes
breaker.update_peak_portfolio_value(new_account_value)
```

---

## Common Scenarios

### Scenario 1: New Strategy Testing

```python
# Very tight limits for untested strategy
breaker = CircuitBreaker(
    initial_portfolio_value=10000,  # Start small
    daily_loss_limit=0.01,          # 1% daily ($100)
    max_drawdown_limit=0.05,        # 5% max drawdown
    consecutive_loss_limit=3,       # 3 losses max
    volatility_threshold=25.0       # Low VIX threshold
)
```

**Goal**: Catch issues early with minimal damage

### Scenario 2: Proven Strategy Scaling

```python
# Standard limits for proven strategy
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.03,
    max_drawdown_limit=0.10,
    consecutive_loss_limit=5,
    volatility_threshold=35.0
)
```

**Goal**: Balance protection with trading flexibility

### Scenario 3: Market Crisis

```python
# During known high volatility period
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=0.02,          # Tighter daily limit
    max_drawdown_limit=0.08,        # Tighter drawdown
    consecutive_loss_limit=3,       # Tighter loss limit
    volatility_threshold=30.0       # Lower VIX threshold
)
```

**Goal**: Extra protection during uncertain times

---

## FAQ

### Q: What if I want to override a breaker?

**A:** You can't bypass without the confirmation code. This is **intentional**.

If you think you need to override:
1. You're probably wrong (emotions talking)
2. If you're right, use the reset procedure
3. Document WHY you think override needed
4. Seriously consider if your limits are too tight instead

### Q: Can I disable circuit breakers?

**A:** Yes, but **strongly discouraged** in production.

For testing only:
```python
# Set very high limits (effectively disabled, not recommended)
breaker = CircuitBreaker(
    initial_portfolio_value=100000,
    daily_loss_limit=1.0,           # 100% (entire account)
    max_drawdown_limit=1.0,         # 100%
    consecutive_loss_limit=999,     # Unrealistic
    volatility_threshold=999.0      # Never trips
)
```

### Q: What if breakers trip too often?

**A:** Three possibilities:

1. **Limits too tight** → Adjust thresholds higher
2. **Strategy issues** → Review and improve strategy
3. **Market conditions** → Accept that not trading is correct

Review trip frequency:
- 1-2x per month → Limits probably right
- Multiple per week → Limits too tight OR strategy broken
- Never → Limits too loose OR not trading enough

### Q: How do I backtest with circuit breakers?

**A:** Include them in your backtest:

```python
# In backtest loop
for bar in historical_data:
    # Check breakers each bar
    status = breaker.check_breakers(
        current_portfolio_value=portfolio.value(),
        start_of_day_value=start_of_day,
        current_vix=bar["vix"]
    )

    if not status["trading_allowed"]:
        print(f"Breaker tripped on {bar['date']}: {status['reasons']}")
        continue  # Skip this bar, no trading

    # Normal trading logic...
```

This gives realistic performance with breakers active.

---

## Summary

Circuit breakers are **essential risk management tools** that:

1. **Prevent catastrophic losses** through automatic halts
2. **Enforce discipline** when emotions run high
3. **Protect capital** during strategy breakdowns
4. **Create mandatory review points** for learning
5. **Work 24/7** without human oversight

### Key Principles

- **Fail-safe design**: When in doubt, halt trading
- **No bypass**: Reset requires confirmation code
- **Comprehensive**: Multiple breaker types for different scenarios
- **Integration**: Works with Kelly + Stop Loss for complete protection

### Remember

> "The most important rule of trading is to play great defense, not great offense." - Paul Tudor Jones

Circuit breakers ensure you **survive to trade another day**. They're not about maximizing profits - they're about **avoiding catastrophic failure**.

**Trading halts are GOOD.** They prevent emotional decisions and force objective review. Embrace them as valuable feedback, not obstacles to overcome.

---

## See Also

- [Kelly Criterion Guide](KELLY_CRITERION.md) - Position sizing
- [Stop Loss Management](STOP_LOSS_MANAGEMENT.md) - Trade-level protection
- [Examples](../examples/circuit_breaker_example.py) - Working code examples
- [Tests](../tests/unit/test_circuit_breaker.py) - Comprehensive test suite
