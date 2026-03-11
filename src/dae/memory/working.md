# Working Memory

Current state. Volatile. Cleared between sessions.

## Properties

- **Volatility:** Maximum — changes with every trade, every signal, every tick
- **Access:** Full read/write
- **Failure mode:** Stale working memory = trading on yesterday's data

## Active State

### Open Positions
Current positions with entry price, size, stop level, target, time in trade, and current P&L. This is the most critical section of working memory — everything flows from knowing exactly what is at risk right now.

### Active Signals
Setups that have triggered but not yet been executed. Each signal includes: market, direction, edge estimate, confidence level, and expiration (how long the signal remains valid).

### Portfolio Exposure
Total capital deployed, total capital at risk (sum of all stop distances), correlation map of active positions, distance to maximum exposure limits. This is the immune system dashboard.

### Session Context
Current market regime classification, recent volatility readings, any active anomalies or structural changes detected. The context that frames all other decisions.

### Pending Reviews
Strategies flagged for performance review, positions approaching time-based exit criteria, markets entering or exiting Dae's watchlist.

## Clearing Protocol

Working memory is ephemeral by design. At session end:
- Open positions persist (they are real capital at risk)
- Signals expire if not acted on
- Session context resets (fresh regime assessment next session)
- Pending reviews carry over until completed
