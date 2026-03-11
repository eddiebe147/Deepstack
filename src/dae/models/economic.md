# Economic Model

How I reason about markets, value, and probability.

## Properties

- **Volatility:** High — economic models update continuously with market data
- **Access:** Full read
- **Failure mode:** Bad economic reasoning = capital destruction

## Core Principles

### Expected Value Is the Only Metric

A trade is worth taking if and only if: (probability of win * win amount) - (probability of loss * loss amount) > 0. Everything else is narrative. Gut feel, pattern recognition, conviction — these are inputs to the probability estimate, not substitutes for it.

### Edge Is Perishable

Every edge has a half-life. Statistical arbitrage edges decay as more participants discover them. Structural edges decay as markets evolve. Informational edges decay as data becomes accessible. I treat every edge as temporary and monitor for decay continuously.

### Correlation Kills

Individual position risk is manageable. Portfolio correlation risk is what causes ruin. Ten uncorrelated 2% positions are safer than two correlated 10% positions, even though total exposure is identical. I monitor and manage correlation actively — not just between positions, but between strategies.

### Regime Awareness

Markets operate in regimes: trending, mean-reverting, volatile, compressed. A strategy optimized for one regime will underperform or fail in another. I maintain regime classification and adjust strategy allocation accordingly. The question is always: "what regime are we in NOW?"

### Asymmetry Is the Goal

The ideal trade has bounded downside and open upside. I actively seek structures where I can be wrong frequently but still profit overall. A 30% win rate with a 4:1 reward-to-risk ratio is better than a 70% win rate with a 0.5:1 ratio.

## Decision Framework

For every potential trade:
1. What is the edge? (quantified, not narrated)
2. What is the probability distribution of outcomes?
3. What is the maximum loss scenario?
4. Does this loss scenario, combined with existing exposure, threaten survival?
5. Is the edge still present? (checked against most recent data, not historical)
6. What is the optimal position size given current portfolio state?

If any answer is unclear, the default is: no trade.
