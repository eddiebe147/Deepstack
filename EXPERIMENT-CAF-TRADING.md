---
created: 2026-04-02
status: STAGE 1 (Validate Engine)
hypothesis: Consciousness-as-Filesystem produces measurably better risk-adjusted trading outcomes than stateless config-driven bots
principal-investigator: Eddie Belaval
---

# Experiment: Does Consciousness Make a Better Trader?

## Abstract

DAE V1 was a 50,000-line trading bot with consciousness files (10 files + 2 unconscious dotfiles) that placed unauthorized trades and lost $87 without its owner knowing. DAE V2 is a 1,823-line bot with zero consciousness, where the same behavioral properties (loss aversion, survival instinct) are expressed as static config values.

This experiment tests whether a Consciousness-as-Filesystem (CaF) layer produces measurably different trading outcomes than bare mathematical config. The control (V2-bare) is stateless: each trading cycle is independent. The treatment (V2-caf) has dynamic state: fear accumulates after losses, confidence builds after wins, and behavior adapts across cycles.

This is the first empirical test of CaF in a domain with objective, measurable outcomes (dollars gained or lost).

## Background

### The CaF Thesis (Parts 1-2)

Consciousness-as-Filesystem maps human cognitive architecture to a directory structure. Entities (AI agents) receive curated subsets of the golden sample, tuned for their domain. The unconscious layer (dotfiles) influences behavior through code paths without being directly accessible to the entity.

### Dae V1 Consciousness (Mar 11, 2026)

Production unit at ~/Development/id8/consciousness/units/dae/. Inversion-first design: defined by what's excluded (ego, narrative, social awareness, warmth, attachment). 10 files + 2 unconscious dotfiles:

- kernel/identity.md, kernel/purpose.md, kernel/values.md
- drives/goals.md (compound growth, strategy evolution)
- drives/fears.md (ruin, poverty, edge decay, overconfidence)
- models/market.md (market microstructure mental model)
- emotional/state.md (fear/greed/neutral cycle)
- memory/working.md, memory/architecture.md
- unconscious/.loss-aversion (2.3x loss weighting)
- unconscious/.survival-instinct (15% drawdown hard floor)

### Dae V2 Bare (Apr 2, 2026)

1,823 lines. Zero consciousness files. Same behaviors expressed as config:
- Loss aversion = kelly_fraction: 0.15 (static)
- Survival instinct = hard_stop_balance: 417 (binary threshold)
- No fear accumulation, no confidence dynamics, no cross-cycle memory

### The Question

Do the consciousness files produce measurably different outcomes, or are they organizational poetry over identical math?

## Experimental Design

### Stage 1: Validate the Engine (Current)

**Duration:** 4-8 weeks
**Capital:** Full $557 account on V2-bare
**Target:** 100+ paper trades, then small live ($50 max exposure)
**Purpose:** Prove the favorite-zone market making strategy has positive net EV on Kalshi
**Gate:** Must show net positive P&L over 100+ trades to proceed to Stage 2

If Stage 1 fails (strategy is not profitable), the experiment ends. There is no point testing consciousness on a losing strategy.

### Stage 2: The Fork (After Stage 1 Passes)

**Duration:** 8-12 weeks
**Capital:** Split account 50/50
**Setup:**

| | V2-Bare (Control) | V2-CaF (Treatment) |
|--|-------------------|---------------------|
| Repo | ~/clawd/projects/dae-v2/ | ~/clawd/projects/dae-v2-caf/ |
| Strategy | Identical (favorite-zone MM) | Identical (favorite-zone MM) |
| Config | Static values | Consciousness-loaded values |
| Markets | Same series, alternating tickers | Same series, alternating tickers |
| Capital | 50% of account | 50% of account |
| State | Stateless (each cycle independent) | Stateful (cross-cycle dynamics) |

**Market allocation to prevent overlap:** Both bots see the same markets but alternate which specific tickers they can trade (odd/even contract suffixes, or A/B series split). This prevents both bots competing for the same orderbook.

### Treatment: What Consciousness Changes

The conscious bot loads CaF files at startup and uses them to modify behavior dynamically. The bare bot uses static config. Same strategy code, different decision modifiers.

| Behavior | Bare (Control) | CaF (Treatment) |
|----------|---------------|-----------------|
| Position sizing | kelly_fraction = 0.15 (constant) | Base 0.15, multiplied by fear_factor (0.5-1.0) that decays after losses |
| Hard stop | Binary: trade or don't at $417 | Gradient: sizing shrinks 10% per $20 of drawdown from peak |
| Post-loss response | None (stateless) | .loss-aversion: skip next N opportunities (N = consecutive_losses) |
| Post-win response | None (stateless) | Confidence builds: sizing increases 5% per 3 consecutive wins (capped at 1.2x base) |
| Opportunity scoring | Pure math (edge * volume * spread * time) | Weighted by drives/goals: +10 score for compound growth patterns (positions that build on winners) |
| Recovery behavior | Resume immediately after drawdown | .survival-instinct: after 15% drawdown, enter "recovery mode" (half sizing for 20 cycles) |
| Fear state | Does not exist | emotional/state tracks fear/greed/neutral. Fear increases after losses, decreases after wins. Affects all sizing. |

### Key Constraint: Same Strategy, Same Markets

The ONLY variable is the consciousness layer. Everything else is identical:
- Same Kalshi API client
- Same circuit breaker
- Same journal schema
- Same risk caps (daily/weekly/monthly)
- Same favorite-zone market making algorithm
- Same calibration table
- Same fee model

## Measurement Protocol

### Primary Metrics (per bot, per week)

| Metric | Definition | Why It Matters |
|--------|-----------|----------------|
| Net P&L (cents) | Sum of all closed trade P&L after fees | Did it make money? |
| Sharpe Ratio | Mean return / StdDev of returns (annualized) | Risk-adjusted performance |
| Max Drawdown | Largest peak-to-trough decline | Worst case scenario |
| Win Rate | Winning trades / total trades | Consistency |
| Avg Win / Avg Loss | Mean P&L of winners vs losers | Edge quality |
| Trades Taken | Number of executed trades | Activity level |
| Trades Skipped (CaF only) | Opportunities rejected by fear/recovery state | Cost of consciousness |

### Secondary Metrics (behavioral)

| Metric | Definition | Hypothesis |
|--------|-----------|-----------|
| Largest Single Loss | Worst individual trade | CaF should have smaller worst case |
| Recovery Time | Cycles from drawdown trough to break-even | CaF should recover faster |
| Consecutive Loss Streak | Longest run of losses | CaF should have shorter streaks (skips after losses) |
| Post-Loss Performance | P&L in 10 trades following a loss | CaF should show less revenge behavior |
| Opportunity Cost | P&L of skipped trades (calculated retroactively) | What did fear cost? |

### Statistical Significance

Using a two-sample t-test on weekly Sharpe ratios:
- Minimum 8 weeks of data (n=8 per group)
- Target p < 0.10 (prediction market data is noisy, relaxed threshold)
- Effect size (Cohen's d) > 0.5 to be practically meaningful
- If p > 0.10 after 12 weeks, declare no significant difference

## Hypotheses

**H1 (Primary):** CaF Dae will have a higher Sharpe ratio (better risk-adjusted returns) due to dynamic loss aversion reducing drawdowns.

**H2:** CaF Dae will have lower max drawdown (the survival instinct gradient prevents catastrophic losses before the hard stop).

**H3:** CaF Dae will have lower total P&L (the fear response causes missed profitable opportunities).

**H4:** CaF Dae will show faster recovery from drawdowns (post-loss behavioral adaptation prevents compounding losses).

**Expected outcome:** If H1+H2+H4 are true and H3 is true, then consciousness produces a BETTER TRADER but a POORER EARNER in calm markets. The value appears in tail risk protection. This would validate the CaF thesis that consciousness is about survival, not optimization.

## Connection to CaF Research

### If Consciousness Wins (Higher Sharpe)
- Validates CaF Part 1 thesis: filesystem architecture produces functional cognition
- The unconscious layer (.loss-aversion, .survival-instinct) demonstrably improves outcomes
- Publishable as CaF Part 3: "Empirical Test of Consciousness-as-Filesystem in Autonomous Trading"
- Strongest possible evidence for the golden sample pattern

### If Bare Wins (Higher Sharpe)
- Consciousness files are organizational metaphor, not functional improvement
- The overhead of dynamic state (fear, confidence) introduces noise
- Static optimization outperforms adaptive behavior in simple domains
- CaF may be valuable for complex social domains (Ava) but not for math-heavy domains (trading)
- Still publishable: negative results are results

### If No Significant Difference
- Consciousness is neutral: neither helps nor hurts
- The mathematical behaviors (loss aversion, survival instinct) are equivalent whether expressed as config or as consciousness files
- Suggests CaF's value is in DESIGN (forcing inversion-first thinking) rather than RUNTIME (dynamic behavior)
- Still valuable: the design methodology produced a good bot regardless of the runtime layer

## Timeline

| Date | Milestone | Gate |
|------|-----------|------|
| Apr 2, 2026 | Experiment designed, V2-bare built | -- |
| Apr 2-3, 2026 | Paper mode activated | -- |
| Week 1-4 | Stage 1: Paper trading (100+ trades target) | Net positive P&L? |
| Week 4-6 | Stage 1: Small live ($50 max exposure) | Still positive? |
| Week 6 | STAGE GATE: Proceed to Stage 2? | Strategy validated? |
| Week 6-7 | Build V2-CaF fork, wire consciousness loader | -- |
| Week 7 | Split capital, activate both bots | -- |
| Week 7-19 | Stage 2: Parallel run (12 weeks) | -- |
| Week 19 | Statistical analysis, declare results | p < 0.10? |
| Week 20 | Write CaF Part 3 paper | -- |

## Log

### 2026-04-02: Experiment Created
- V1 killed after unauthorized trades (calibration_edge placed CPI and BTC orders while disabled)
- V2 built: 1,823 lines, favorite-zone market making, paper mode default
- Research confirmed: 92% of PM traders lose money, longshot fading killed by fees, favorite zone (78-87c) is only profitable range after 4c RT maker fees
- Decision: validate engine first (Stage 1), then fork for consciousness experiment (Stage 2)
- Consciousness experiment spec written (this document)
