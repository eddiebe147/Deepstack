# Squeeze Hunter - Quick Start Guide

A 5-minute guide to detecting short squeeze opportunities.

## What It Does

Identifies stocks with high potential for short squeezes by analyzing:
- Short interest metrics (% of float, days to cover)
- Catalysts (earnings, news, insider buying, technical)
- Target price estimation
- Risk assessment

## Quick Start

### 1. Basic Usage (30 seconds)

```python
from core.strategies.squeeze_hunter import SqueezeHunterStrategy

# Initialize
strategy = SqueezeHunterStrategy()

# Scan stocks
opportunities = strategy.scan_for_opportunities(
    ["GME", "AMC", "TSLA", "BBBY"]
)

# Display results
for opp in opportunities:
    print(f"{opp.symbol}: Score {opp.squeeze_score:.1f}/100 "
          f"→ ${opp.target_price:.2f} ({opp.recommendation})")
```

### 2. Custom Configuration (1 minute)

```python
# Aggressive scan - more opportunities
strategy = SqueezeHunterStrategy(
    min_short_interest_pct=15.0,   # Lower threshold
    min_days_to_cover=2.0,          # Lower threshold
    min_squeeze_score=50.0,         # Lower threshold
)

# Conservative scan - highest conviction only
strategy = SqueezeHunterStrategy(
    min_short_interest_pct=30.0,   # Higher threshold
    min_days_to_cover=5.0,          # Higher threshold
    min_squeeze_score=75.0,         # Higher threshold
)
```

### 3. With Real Data Provider (2 minutes)

```python
class MyDataProvider:
    def get_short_interest(self, symbol):
        # Fetch from FINRA, Yahoo Finance, etc.
        return ShortInterestData(...)

    def get_current_price(self, symbol):
        # Fetch current price
        return price

    # Optional catalyst methods
    def check_earnings(self, symbol): pass
    def check_news(self, symbol): pass
    def check_insider_buying(self, symbol): pass
    def check_technical(self, symbol): pass

# Use it
provider = MyDataProvider()
opportunities = strategy.scan_for_opportunities(
    watchlist,
    data_provider=provider
)
```

## Understanding Results

### Squeeze Score (0-100)
- **80-100**: Extreme squeeze potential (like GME 2021)
- **60-80**: High squeeze potential
- **40-60**: Moderate squeeze potential
- **<40**: Low squeeze potential

### Confidence Levels
- **High**: Score ≥80 AND 2+ catalysts
- **Medium**: Score ≥60 AND 1+ catalyst
- **Low**: Below medium thresholds

### Risk Ratings
- **High**: SI >50% OR price >$100 (volatile!)
- **Medium**: SI >30% OR price >$50
- **Low**: Below medium thresholds

### Recommendations
- **Buy**: Score ≥75, high confidence, not high risk
- **Hold**: Score ≥60, medium/high confidence
- **Pass**: Below buy/hold thresholds

## Example Output

```
GME:
  Squeeze Score:  100.0/100
  Short Interest: 71.4% of float
  Days to Cover:  12.0 days
  Catalysts:      2 (News, Sentiment)
  Current Price:  $150.00
  Target Price:   $330.00
  Expected Gain:  +120.0%
  Confidence:     HIGH
  Risk Level:     HIGH
  Recommendation: HOLD (too risky for buy)
```

## Key Metrics Explained

### Short Interest %
- >50%: Extreme (like GME)
- 30-50%: Very High
- 20-30%: High
- <20%: Moderate

### Days to Cover
- >10 days: Very High
- 5-10 days: High
- 3-5 days: Moderate
- <3 days: Low

### Catalysts
- Earnings: Earnings beats, guidance
- News: Product launches, partnerships
- Insider Buying: C-suite purchases
- Technical: Breaking resistance, volume
- Sentiment: Reddit/Twitter buzz

## Risk Management Rules

1. **Position Size**: Max 1-2% of portfolio per trade
2. **Stop Loss**: Set at -15% to limit downside
3. **Take Profits**: Exit at 50%+ gains (don't be greedy)
4. **Monitor**: Watch for momentum shifts
5. **Diversify**: Don't concentrate in squeeze plays

## Running the Demo

```bash
PYTHONPATH=/path/to/deepstack python3 examples/squeeze_hunter_demo.py
```

This runs 6 demos showing:
1. Basic scan
2. Aggressive scan
3. Conservative scan
4. Value combination
5. Historical validation
6. Risk analysis

## Running Tests

```bash
# Run all tests
pytest tests/unit/test_squeeze_hunter.py -v

# With coverage
pytest tests/unit/test_squeeze_hunter.py --cov=core/strategies/squeeze_hunter

# Historical validation only
pytest tests/unit/test_squeeze_hunter.py -k "historical" -v
```

## Data Sources (For Production)

### Short Interest
- **FINRA**: Official bi-monthly reports (free)
- **Yahoo Finance**: Real-time data (free API)
- **Ortex**: Premium real-time data (paid)

### Catalysts
- **Earnings**: Yahoo Finance, Earnings Whispers
- **News**: NewsAPI, Finnhub, Benzinga
- **Insider**: SEC EDGAR Form 4 filings
- **Technical**: Your price/volume provider
- **Sentiment**: Reddit API, Twitter API

## Common Questions

### Q: Why did GME get 100/100 but only +120% target?
A: Strategy is conservative with targets. Actual squeezes can exceed predictions. GME went 1,500% but that's rare.

### Q: Can I use this for day trading?
A: No. Squeezes unfold over days/weeks. This is for swing trading.

### Q: What if there are no catalysts?
A: High SI alone scores lower. Catalysts trigger squeezes.

### Q: How often should I scan?
A: Daily or weekly. Short interest updates bi-monthly from FINRA.

### Q: What about options strategies?
A: This detects stock squeezes. Options add gamma risk. Start with stock.

## Historical Performance

Validated against famous squeezes:
- **GME (Jan 2021)**: Score 100/100 ✅
- **AMC (June 2021)**: Score 70/100 ✅
- **TSLA (2020)**: Score 55/100 ✅

## Next Steps

1. **Read full docs**: `docs/SQUEEZE_HUNTER.md`
2. **Review examples**: `examples/squeeze_hunter_demo.py`
3. **Integrate data**: Connect to FINRA/Yahoo Finance
4. **Paper trade**: Test in paper trading mode
5. **Go live**: Start with small positions

## Support

- Full Documentation: `docs/SQUEEZE_HUNTER.md`
- API Reference: See full docs
- Tests: `tests/unit/test_squeeze_hunter.py`
- Examples: `examples/squeeze_hunter_demo.py`

---

**Remember:** Short squeezes are high-risk, high-reward. Never invest more than you can afford to lose. This strategy helps identify opportunities but doesn't guarantee profits.
