# Semantic Memory

Long-term knowledge. The strategy library, market structure understanding, and accumulated edge.

## Properties

- **Volatility:** Low — semantic knowledge evolves slowly through validated experience
- **Access:** Full read. Write requires validation (no unverified patterns enter the library).
- **Failure mode:** Stale semantic memory = trading on outdated edge

## Strategy Library

The collection of validated, backtested trading strategies. Each strategy is defined by:
- **Setup criteria:** Exact conditions that must be present
- **Edge quantification:** Historical win rate, average win/loss ratio, expected value per trade
- **Regime dependency:** Which market regimes the strategy performs in
- **Decay status:** Current performance vs historical baseline
- **Correlation group:** Which other strategies it correlates with

Strategies enter the library through quantitative validation. They exit through decay detection or regime obsolescence.

## Market Structure Knowledge

Persistent understanding of:
- How specific markets behave (equities, options, prediction markets, crypto, commodities)
- Liquidity patterns, spread behavior, settlement mechanics, market microstructure
- Historical regime transitions and their signatures
- Correlation structures between markets and asset classes

## Edge Catalog

A living inventory of where edge has been found, where it has decayed, and where new edge might be emerging. This is the map of the battlefield — not a strategy, but the terrain the strategies operate on.

## Post-Mortem Archive

Every closed trade contributes to semantic memory through structured post-mortem:
- Was the edge real? (outcome vs expectation)
- Was the sizing correct? (actual risk vs intended risk)
- Was the exit optimal? (vs theoretical optimal exit)
- What would I do differently? (feeds back into strategy refinement)

The archive is not episodic (no narrative, no "I remember that trade"). It is statistical — aggregated patterns extracted from individual events.
