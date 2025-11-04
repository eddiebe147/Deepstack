# Psychology Module Documentation

## Overview

The Psychology Module is the final protection layer in the DeepStack Trading System, designed to prevent emotional trading patterns and enforce disciplined execution. It consists of four integrated components that work together to protect traders from their own psychological weaknesses.

## Components

### 1. DrawdownMonitor

**Purpose:** Track portfolio drawdowns in real-time and automatically reduce position sizes at progressive thresholds to prevent catastrophic losses.

**Key Features:**
- Real-time peak-to-trough drawdown calculation
- Progressive position size reduction (100% → 75% → 50% → 25%)
- Automatic circuit breaker at 20% drawdown
- Recovery tracking and gradual size restoration
- Historical drawdown logging and statistics

**Thresholds:**
| Drawdown Range | Position Sizing | Action Required |
|----------------|----------------|-----------------|
| 0-5%           | 100%           | Normal trading |
| 5-10%          | 75%            | Reduced risk |
| 10-15%         | 50%            | Conservative |
| 15-20%         | 25%            | Minimal risk |
| 20%+           | 0%             | Circuit breaker activated |

**Usage Example:**
```python
from core.psychology import DrawdownMonitor

# Initialize monitor
monitor = DrawdownMonitor(
    initial_capital=100000,
    enable_circuit_breaker=True,
    recovery_profit_target=0.03  # 3% profit to exit recovery
)

# Update with current portfolio value
status = monitor.update(current_value=95000)

# Check position sizing
if status['circuit_breaker']:
    print("Trading halted!")
else:
    position_size = monitor.get_max_position_size(base_size=10000)
    print(f"Max position size: ${position_size:,.2f}")
    print(f"Position multiplier: {status['position_size_multiplier']:.0%}")

# Manual circuit breaker reset (requires confirmation)
if monitor.circuit_breaker_active:
    monitor.reset_circuit_breaker("RESET_TRADING")
```

**API Reference:**

```python
class DrawdownMonitor:
    def __init__(
        self,
        initial_capital: float,
        enable_circuit_breaker: bool = True,
        recovery_profit_target: float = 0.03,
        enable_logging: bool = True
    )

    def update(self, current_value: float) -> Dict
    def get_status(self) -> Dict
    def get_statistics(self) -> Dict
    def reset_circuit_breaker(self, confirmation_code: str) -> bool
    def get_max_position_size(self, base_size: float) -> float
    def is_trading_allowed(self) -> bool
```

---

### 2. EmotionalFirewall

**Purpose:** Detect and block emotional trading patterns including revenge trading, overtrading, and late-night trading.

**Blocked Patterns:**
- **Revenge Trading:** Trading within 30 minutes of a loss
- **Overtrading:** More than 3 trades per hour or 10 per day
- **Win/Loss Streaks:** 5+ consecutive wins or losses (emotional risk)
- **Late Night Trading:** After 8 PM EST
- **Weekend Trading:** Saturday/Sunday trading attempts
- **Position Size Increases:** After recent losses

**Cooling Periods:**
| Pattern          | Cooldown Duration | Severity |
|------------------|-------------------|----------|
| Revenge Trading  | 60 minutes        | Medium   |
| Win Streak       | 180 minutes       | High     |
| Loss Streak      | 180 minutes       | Critical |
| Overtrading      | 240 minutes       | High     |
| Late Night       | 480 minutes       | Medium   |

**Usage Example:**
```python
from core.psychology import EmotionalFirewall

# Initialize firewall
firewall = EmotionalFirewall(
    enable_late_night_check=True,
    enable_weekend_check=True,
    enable_revenge_check=True,
    timezone_name="America/New_York"
)

# Record completed trades
firewall.record_trade("AAPL", profit_loss=-1000, position_size=5000)
firewall.record_trade("TSLA", profit_loss=500, position_size=5000)

# Check if trade should be blocked
result = firewall.should_block_trade(
    symbol="MSFT",
    position_size=5000
)

if result['blocked']:
    print(f"Trade blocked!")
    print(f"Reasons: {result['reasons']}")
    print(f"Patterns: {result['patterns_detected']}")
    print(f"Cooldown expires: {result['cooldown_expires']}")
else:
    print("Trade allowed")

# Get statistics
stats = firewall.get_statistics()
print(f"Total trades: {stats['total_trades']}")
print(f"Blocked trades: {stats['blocked_trades']}")
print(f"Block rate: {stats['block_rate']:.1%}")
```

**API Reference:**

```python
class EmotionalFirewall:
    def __init__(
        self,
        enable_all_checks: bool = True,
        enable_late_night_check: bool = True,
        enable_weekend_check: bool = True,
        enable_revenge_check: bool = True,
        enable_overtrading_check: bool = True,
        enable_streak_check: bool = True,
        timezone_name: str = "America/New_York"
    )

    def should_block_trade(
        self,
        symbol: str,
        position_size: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict

    def record_trade(
        self,
        symbol: str,
        profit_loss: float,
        position_size: Optional[float] = None,
        timestamp: Optional[datetime] = None
    )

    def override_cooldown(self, confirmation_code: str) -> bool
    def get_statistics(self) -> Dict
    def reset_streak(self)
    def clear_history(self)
```

---

### 3. TradingTimeOut

**Purpose:** Enforce mandatory cooling-off periods after consecutive losses or daily loss limits, using exponential backoff to prevent emotional revenge trading.

**Timeout Triggers:**
- **Consecutive Losses:** 3, 5, or 7+ losses in a row
- **Daily Loss Limit:** 2% of portfolio value (configurable)
- **Drawdown Threshold:** 10% drawdown (configurable)
- **Manual Timeout:** Set by user or system

**Exponential Backoff Schedule:**
| Trigger Count | Timeout Duration | Severity |
|---------------|------------------|----------|
| 1st trigger   | 60 minutes       | Warning  |
| 2nd trigger   | 4 hours          | Serious  |
| 3rd trigger   | 24 hours         | Critical |
| 4th+ trigger  | 7 days           | Lockdown |

**Usage Example:**
```python
from core.psychology import TradingTimeOut

# Initialize timeout system
timeout = TradingTimeOut(
    consecutive_loss_limit=3,
    daily_loss_limit_pct=0.02,  # 2% daily loss limit
    drawdown_limit_pct=0.10,     # 10% drawdown limit
    portfolio_value=100000
)

# Record losses
status = timeout.record_loss("AAPL", loss_amount=500)
status = timeout.record_loss("TSLA", loss_amount=700)
status = timeout.record_loss("MSFT", loss_amount=600)

# Check if in timeout
if timeout.is_in_timeout():
    status = timeout.check_timeout()
    print(f"Trading suspended!")
    print(f"Reason: {status['reason']}")
    print(f"Time remaining: {status['time_remaining']['formatted']}")
    print(f"Expires at: {status['expires_at']}")
else:
    print("Trading allowed")

# Record win (resets consecutive losses)
timeout.record_win("GOOGL", profit_amount=1000)

# Manual timeout
timeout.manual_timeout(
    duration_minutes=120,
    reason="Manual halt for strategy review"
)

# Override timeout (requires confirmation)
timeout.override_timeout("OVERRIDE_TIMEOUT")
```

**API Reference:**

```python
class TradingTimeOut:
    def __init__(
        self,
        consecutive_loss_limit: int = 3,
        daily_loss_limit_pct: float = 0.02,
        drawdown_limit_pct: float = 0.10,
        portfolio_value: float = 100000,
        enable_timeouts: bool = True,
        enable_logging: bool = True
    )

    def record_loss(
        self,
        symbol: str,
        loss_amount: float,
        timestamp: Optional[datetime] = None
    ) -> Dict

    def record_win(
        self,
        symbol: str,
        profit_amount: float,
        timestamp: Optional[datetime] = None
    )

    def check_timeout(self) -> Dict
    def manual_timeout(
        self,
        duration_minutes: int,
        reason: str,
        timestamp: Optional[datetime] = None
    )
    def override_timeout(self, confirmation_code: str) -> bool
    def get_statistics(self) -> Dict
    def is_in_timeout(self) -> bool
    def update_portfolio_value(self, new_value: float)
```

---

### 4. RecoveryProtocol

**Purpose:** Manage gradual recovery after significant losses through phased position sizing increases, ensuring trader has regained confidence and discipline.

**Recovery Phases:**

| Phase | Position Sizing | Requirements to Advance |
|-------|----------------|------------------------|
| Phase 1: Conservative | 50% | 5 trades, 3% profit, 60% win rate |
| Phase 2: Cautious | 75% | 3 trades, 2% profit, 60% win rate |
| Phase 3: Full Recovery | 100% | Automatic (recovery complete) |

**Progression Requirements:**
- Minimum number of profitable trades
- Profit target percentage
- Minimum win rate threshold
- Maximum consecutive losses allowed
- No excessive drawdowns during recovery

**Demotion Triggers:**
- Excessive consecutive losses (>4)
- Phase loss exceeding -3%
- Poor risk management

**Usage Example:**
```python
from core.psychology import RecoveryProtocol

# Initialize recovery protocol after significant loss
protocol = RecoveryProtocol(
    entry_drawdown=0.15,      # Entered recovery after 15% drawdown
    portfolio_value=85000,    # Current portfolio value
    starting_phase=RecoveryPhase.PHASE_1_CONSERVATIVE
)

# Record trades during recovery
protocol.record_trade(profit_loss=500, symbol="AAPL")
protocol.record_trade(profit_loss=700, symbol="TSLA")
protocol.record_trade(profit_loss=400, symbol="MSFT")

# Check current status
status = protocol.get_status()
print(f"Current phase: {status['current_phase']}")
print(f"Position sizing: {status['position_size_multiplier']:.0%}")
print(f"Phase P/L: ${status['phase_profit_loss']:,.2f}")
print(f"Phase return: {status['phase_return']:+.1%}")

# Check if can advance to next phase
check = protocol.can_advance_phase()
if check['can_advance']:
    print("Ready to advance!")
    protocol.advance_phase()
else:
    print("Requirements not met:")
    for reason in check['blocking_reasons']:
        print(f"  - {reason}")

# Calculate position size with recovery adjustment
base_position = 10000
adjusted_position = protocol.get_max_position_size(base_position)
print(f"Adjusted position: ${adjusted_position:,.2f}")

# Check if recovery complete
if protocol.recovery_completed:
    print("Full recovery achieved!")
```

**API Reference:**

```python
class RecoveryProtocol:
    def __init__(
        self,
        entry_drawdown: float,
        portfolio_value: float,
        starting_phase: RecoveryPhase = RecoveryPhase.PHASE_1_CONSERVATIVE,
        enable_logging: bool = True
    )

    def record_trade(
        self,
        profit_loss: float,
        symbol: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict

    def can_advance_phase(self) -> Dict
    def advance_phase(self) -> bool
    def get_status(self) -> Dict
    def get_statistics(self) -> Dict
    def get_position_size_multiplier(self) -> float
    def get_max_position_size(self, base_size: float) -> float
    def is_in_recovery(self) -> bool
    def force_phase_advance(self, confirmation_code: str) -> bool
```

---

## Integration Example

Here's how all four components work together:

```python
from core.psychology import (
    DrawdownMonitor,
    EmotionalFirewall,
    TradingTimeOut,
    RecoveryProtocol
)

# Initialize all components
monitor = DrawdownMonitor(initial_capital=100000)
firewall = EmotionalFirewall()
timeout = TradingTimeOut(portfolio_value=100000)
recovery = None  # Only initialized when needed

# Before each trade
def can_trade(symbol: str, position_size: float) -> bool:
    """Check all psychology guards before trading."""

    # 1. Check circuit breaker
    if not monitor.is_trading_allowed():
        print("Trade blocked: Circuit breaker active")
        return False

    # 2. Check timeout
    if timeout.is_in_timeout():
        print("Trade blocked: In timeout period")
        return False

    # 3. Check emotional firewall
    firewall_check = firewall.should_block_trade(symbol, position_size)
    if firewall_check['blocked']:
        print(f"Trade blocked: {firewall_check['reasons']}")
        return False

    # 4. Apply recovery position sizing if in recovery
    if recovery and recovery.is_in_recovery():
        multiplier = recovery.get_position_size_multiplier()
        position_size *= multiplier
        print(f"Recovery mode: Position size reduced to {multiplier:.0%}")

    return True

# After each trade
def record_trade_result(symbol: str, profit_loss: float, position_size: float):
    """Record trade result in all systems."""

    # Update drawdown monitor
    new_value = monitor.current_value + profit_loss
    monitor.update(new_value)

    # Record in firewall
    firewall.record_trade(symbol, profit_loss, position_size)

    # Record in timeout
    if profit_loss < 0:
        timeout.record_loss(symbol, abs(profit_loss))
    else:
        timeout.record_win(symbol, profit_loss)

    # Record in recovery protocol if active
    if recovery and recovery.is_in_recovery():
        recovery.record_trade(profit_loss, symbol)

        # Check if can advance phase
        if recovery.can_advance_phase()['can_advance']:
            recovery.advance_phase()
            print(f"Recovery phase advanced: {recovery.current_phase.value}")

    # Enter recovery if significant drawdown
    if monitor.current_drawdown > 0.10 and not recovery:
        recovery = RecoveryProtocol(
            entry_drawdown=monitor.current_drawdown,
            portfolio_value=monitor.current_value
        )
        print("Entered recovery protocol")
```

---

## Configuration

### Environment Variables

None required - all configuration is done through constructor parameters.

### Recommended Settings

**Conservative (Beginner):**
```python
monitor = DrawdownMonitor(
    initial_capital=100000,
    enable_circuit_breaker=True,
    recovery_profit_target=0.05  # 5% profit required
)

firewall = EmotionalFirewall(
    enable_all_checks=True,
    enable_late_night_check=True,
    enable_weekend_check=True
)

timeout = TradingTimeOut(
    consecutive_loss_limit=2,     # Timeout after 2 losses
    daily_loss_limit_pct=0.015,   # 1.5% daily limit
    portfolio_value=100000
)
```

**Moderate (Intermediate):**
```python
monitor = DrawdownMonitor(
    initial_capital=100000,
    enable_circuit_breaker=True,
    recovery_profit_target=0.03  # 3% profit required
)

firewall = EmotionalFirewall(
    enable_all_checks=True,
    enable_late_night_check=True,
    enable_weekend_check=False    # Allow weekend trading
)

timeout = TradingTimeOut(
    consecutive_loss_limit=3,     # Timeout after 3 losses
    daily_loss_limit_pct=0.02,    # 2% daily limit
    portfolio_value=100000
)
```

**Aggressive (Advanced):**
```python
monitor = DrawdownMonitor(
    initial_capital=100000,
    enable_circuit_breaker=True,
    recovery_profit_target=0.02   # 2% profit required
)

firewall = EmotionalFirewall(
    enable_all_checks=True,
    enable_late_night_check=False,  # Allow late trading
    enable_weekend_check=False,     # Allow weekend trading
    enable_revenge_check=True       # Still block revenge trading
)

timeout = TradingTimeOut(
    consecutive_loss_limit=5,      # Timeout after 5 losses
    daily_loss_limit_pct=0.03,     # 3% daily limit
    portfolio_value=100000
)
```

---

## Logging

All components support comprehensive logging. Configure Python logging to see psychology module activity:

```python
import logging

# Set psychology module logging level
logging.getLogger('core.psychology').setLevel(logging.INFO)

# Or set specific component logging
logging.getLogger('core.psychology.drawdown_monitor').setLevel(logging.WARNING)
logging.getLogger('core.psychology.emotional_firewall').setLevel(logging.INFO)
```

---

## Testing

Run the comprehensive test suite:

```bash
# Run all psychology tests
pytest tests/unit/test_psychology.py -v

# Run with coverage report
pytest tests/unit/test_psychology.py --cov=core.psychology --cov-report=term-missing

# Run specific test class
pytest tests/unit/test_psychology.py::TestDrawdownMonitor -v

# Run integration tests only
pytest tests/unit/test_psychology.py::TestPsychologyIntegration -v
```

**Current Test Coverage:**
- DrawdownMonitor: 94.62%
- EmotionalFirewall: 94.82%
- RecoveryProtocol: 94.65%
- TradingTimeOut: 95.98%
- **Overall: 95%+ coverage**

---

## Best Practices

### 1. Always Initialize at System Start
Initialize all psychology components when your trading system starts, not mid-session.

### 2. Never Bypass Without Confirmation
All overrides require confirmation codes. This prevents impulsive bypassing of safety measures.

### 3. Monitor Statistics Regularly
Check psychology statistics daily to understand your trading patterns:

```python
# Daily review
drawdown_stats = monitor.get_statistics()
firewall_stats = firewall.get_statistics()
timeout_stats = timeout.get_statistics()

print(f"Max Drawdown: {drawdown_stats['max_drawdown']:.1%}")
print(f"Trades Blocked: {firewall_stats['blocked_trades']}")
print(f"Block Rate: {firewall_stats['block_rate']:.1%}")
print(f"Timeouts Triggered: {timeout_stats['total_timeouts_triggered']}")
```

### 4. Respect Recovery Phases
Don't force advancement through recovery phases. The requirements exist for your protection.

### 5. Keep Logs for Review
Enable logging to review why trades were blocked:

```python
# Review blocked trades
stats = firewall.get_statistics()
for pattern, count in stats['blocks_by_pattern'].items():
    if count > 0:
        print(f"{pattern}: {count} blocks")
```

---

## Troubleshooting

### Circuit Breaker Won't Reset

**Problem:** Circuit breaker remains active even after portfolio recovers.

**Solution:** Circuit breaker requires manual reset with confirmation code:
```python
monitor.reset_circuit_breaker("RESET_TRADING")
```

### Firewall Blocking All Trades

**Problem:** Cooldown period is active and blocking all trades.

**Solution:** Check cooldown status and wait for expiration, or override with confirmation:
```python
stats = firewall.get_statistics()
if stats['active_cooldown']:
    print(f"Cooldown reason: {stats['cooldown_reason']}")
    print(f"Expires: {stats['cooldown_expires']}")

# Only override if truly necessary
firewall.override_cooldown("OVERRIDE_COOLDOWN")
```

### Stuck in Recovery Phase 1

**Problem:** Cannot advance from Phase 1 despite profitable trades.

**Solution:** Check advancement requirements:
```python
check = protocol.can_advance_phase()
print(f"Can advance: {check['can_advance']}")
print(f"Requirements met: {check['requirements_met']}")
print(f"Blocking reasons: {check['blocking_reasons']}")
```

Common issues:
- Not enough trades (need 5 minimum)
- Win rate too low (need 60%)
- Profit target not reached (need 3%)

---

## Security Considerations

### Confirmation Codes
All override operations require specific confirmation codes to prevent accidental bypassing of safety measures.

**Valid confirmation codes:**
- Circuit Breaker Reset: `"RESET_TRADING"`
- Cooldown Override: `"OVERRIDE_COOLDOWN"`
- Timeout Override: `"OVERRIDE_TIMEOUT"`
- Trigger Count Reset: `"RESET_TRIGGERS"`
- Force Phase Advance: `"FORCE_ADVANCE"`

### Logging of Overrides
All override operations are logged with WARNING level for audit trail.

---

## Performance Impact

The Psychology Module has minimal performance impact:
- **Memory Usage:** ~1-2 MB per component
- **CPU Overhead:** < 0.1ms per trade check
- **Storage:** Historical data limited to 1000 recent snapshots

---

## Support

For issues or questions about the Psychology Module:
1. Check this documentation
2. Review test cases in `tests/unit/test_psychology.py`
3. Check logs for detailed error messages
4. Run demo script: `python examples/psychology_demo.py`

---

## Version History

**v1.0.0** (Current)
- Initial release
- DrawdownMonitor with progressive sizing
- EmotionalFirewall with 7 pattern types
- TradingTimeOut with exponential backoff
- RecoveryProtocol with 3-phase system
- 95%+ test coverage
- Complete API documentation

---

## License

Part of the DeepStack Trading System. All rights reserved.
