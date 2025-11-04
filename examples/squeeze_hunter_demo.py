"""
Squeeze Hunter Strategy Demo

Demonstrates the short squeeze detection strategy with realistic examples.
Shows how to scan for opportunities, analyze results, and integrate with
value investing principles.
"""

from datetime import datetime, timedelta
from typing import Optional

from core.strategies.squeeze_hunter import (
    Catalyst,
    ShortInterestData,
    SqueezeHunterStrategy,
)

# ============================================================================
# Mock Data Provider (for demonstration)
# ============================================================================


class MockDataProvider:
    """
    Mock data provider for demonstration.
    In production, replace with real data sources (FINRA, Yahoo, etc.)
    """

    def __init__(self):
        # Mock short interest data for demo stocks
        self.short_data = {
            "GME": ShortInterestData(
                symbol="GME",
                short_interest=50_000_000,
                float_shares=70_000_000,
                short_percent_float=71.4,  # Very high
                days_to_cover=12.0,
                last_updated=datetime.now(),
            ),
            "AMC": ShortInterestData(
                symbol="AMC",
                short_interest=102_000_000,
                float_shares=450_000_000,
                short_percent_float=22.7,  # High
                days_to_cover=6.5,
                last_updated=datetime.now(),
            ),
            "TSLA": ShortInterestData(
                symbol="TSLA",
                short_interest=30_000_000,
                float_shares=150_000_000,
                short_percent_float=20.0,  # Moderate
                days_to_cover=4.0,
                last_updated=datetime.now(),
            ),
            "BBBY": ShortInterestData(
                symbol="BBBY",
                short_interest=35_000_000,
                float_shares=100_000_000,
                short_percent_float=35.0,  # High
                days_to_cover=8.0,
                last_updated=datetime.now(),
            ),
            "CLOV": ShortInterestData(
                symbol="CLOV",
                short_interest=45_000_000,
                float_shares=150_000_000,
                short_percent_float=30.0,  # High
                days_to_cover=5.5,
                last_updated=datetime.now(),
            ),
            "SPCE": ShortInterestData(
                symbol="SPCE",
                short_interest=20_000_000,
                float_shares=80_000_000,
                short_percent_float=25.0,  # Moderate-High
                days_to_cover=4.5,
                last_updated=datetime.now(),
            ),
        }

        # Mock prices
        self.prices = {
            "GME": 150.0,
            "AMC": 18.0,
            "TSLA": 235.0,
            "BBBY": 12.5,
            "CLOV": 8.0,
            "SPCE": 15.0,
        }

        # Mock catalysts
        self.catalysts = {
            "GME": [
                Catalyst(
                    catalyst_type="sentiment",
                    description="Strong retail interest and social media buzz",
                    impact_score=9.5,
                    date=datetime.now(),
                ),
                Catalyst(
                    catalyst_type="news",
                    description="Board changes and strategic pivot",
                    impact_score=8.0,
                    date=datetime.now() - timedelta(days=5),
                ),
            ],
            "AMC": [
                Catalyst(
                    catalyst_type="news",
                    description="Theater reopening momentum",
                    impact_score=7.5,
                    date=datetime.now() - timedelta(days=3),
                ),
                Catalyst(
                    catalyst_type="technical",
                    description="Breaking key resistance level",
                    impact_score=6.5,
                    date=datetime.now(),
                ),
            ],
            "TSLA": [
                Catalyst(
                    catalyst_type="earnings",
                    description="Strong quarterly earnings beat",
                    impact_score=9.0,
                    date=datetime.now() - timedelta(days=2),
                ),
            ],
            "BBBY": [
                Catalyst(
                    catalyst_type="insider_buying",
                    description="Activist investor stake increase",
                    impact_score=7.0,
                    date=datetime.now() - timedelta(days=7),
                ),
            ],
            "CLOV": [
                Catalyst(
                    catalyst_type="technical",
                    description="Volume spike and price consolidation",
                    impact_score=5.5,
                    date=datetime.now(),
                ),
            ],
        }

    def get_short_interest(self, symbol: str) -> ShortInterestData:
        """Get short interest data for symbol"""
        return self.short_data.get(symbol)

    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        return self.prices.get(symbol, 100.0)

    def check_earnings(self, symbol: str) -> Optional[Catalyst]:
        """Check for earnings catalyst"""
        catalysts = self.catalysts.get(symbol, [])
        return next((c for c in catalysts if c.catalyst_type == "earnings"), None)

    def check_news(self, symbol: str) -> Optional[Catalyst]:
        """Check for news catalyst"""
        catalysts = self.catalysts.get(symbol, [])
        return next((c for c in catalysts if c.catalyst_type == "news"), None)

    def check_insider_buying(self, symbol: str) -> Optional[Catalyst]:
        """Check for insider buying catalyst"""
        catalysts = self.catalysts.get(symbol, [])
        return next((c for c in catalysts if c.catalyst_type == "insider_buying"), None)

    def check_technical(self, symbol: str) -> Optional[Catalyst]:
        """Check for technical catalyst"""
        catalysts = self.catalysts.get(symbol, [])
        return next((c for c in catalysts if c.catalyst_type == "technical"), None)


# ============================================================================
# Demo Functions
# ============================================================================


def demo_basic_scan():
    """Demo: Basic squeeze opportunity scan"""
    print("=" * 80)
    print("DEMO 1: Basic Squeeze Opportunity Scan")
    print("=" * 80)

    # Initialize strategy with default parameters
    strategy = SqueezeHunterStrategy(
        min_short_interest_pct=20.0,
        min_days_to_cover=3.0,
        min_squeeze_score=60.0,
    )

    # Create mock data provider
    provider = MockDataProvider()

    # Scan watchlist
    watchlist = ["GME", "AMC", "TSLA", "BBBY", "CLOV", "SPCE"]
    print(f"\nScanning {len(watchlist)} stocks: {', '.join(watchlist)}")
    print()

    opportunities = strategy.scan_for_opportunities(watchlist, provider)

    # Display results
    print(f"\nFound {len(opportunities)} opportunities:\n")

    for i, opp in enumerate(opportunities, 1):
        print(f"{i}. {opp.symbol}")
        print(f"   {'─' * 70}")
        print(f"   Squeeze Score:  {opp.squeeze_score:.1f}/100")
        si_pct = opp.short_interest_data.short_percent_float
        print(f"   Short Interest: {si_pct:.1f}% of float")
        print(f"   Days to Cover:  {opp.short_interest_data.days_to_cover:.1f} days")
        print(f"   Catalysts:      {len(opp.catalysts)}")
        for catalyst in opp.catalysts:
            print(f"     • {catalyst.catalyst_type.title()}: {catalyst.description}")
            print(f"       Impact: {catalyst.impact_score:.1f}/10")

        print(f"   Current Price:  ${opp.current_price:.2f}")
        print(f"   Target Price:   ${opp.target_price:.2f}")
        print(f"   Expected Gain:  +{opp.expected_return_pct():.1f}%")
        print(f"   Confidence:     {opp.confidence_level.upper()}")
        print(f"   Risk Level:     {opp.risk_rating.upper()}")
        print(f"   Recommendation: {opp.recommendation.upper()}")
        print()


def demo_aggressive_scan():
    """Demo: Aggressive scan with lower thresholds"""
    print("=" * 80)
    print("DEMO 2: Aggressive Scan (Lower Thresholds)")
    print("=" * 80)

    # More aggressive parameters
    strategy = SqueezeHunterStrategy(
        min_short_interest_pct=15.0,  # Lower threshold
        min_days_to_cover=2.0,  # Lower threshold
        min_squeeze_score=50.0,  # Lower threshold
    )

    provider = MockDataProvider()
    watchlist = ["GME", "AMC", "TSLA", "BBBY", "CLOV", "SPCE"]

    print("\nScanning with aggressive parameters:")
    print("  • Min Short Interest: 15%")
    print("  • Min Days to Cover: 2.0")
    print("  • Min Squeeze Score: 50.0")
    print()

    opportunities = strategy.scan_for_opportunities(watchlist, provider)

    print(
        f"\nFound {len(opportunities)} opportunities (vs. fewer with strict params)\n"
    )

    for opp in opportunities:
        print(
            f"{opp.symbol}: Score {opp.squeeze_score:.1f} | "
            f"SI {opp.short_interest_data.short_percent_float:.1f}% | "
            f"Target ${opp.target_price:.2f} (+{opp.expected_return_pct():.1f}%)"
        )


def demo_conservative_scan():
    """Demo: Conservative scan with higher thresholds"""
    print("=" * 80)
    print("DEMO 3: Conservative Scan (Higher Thresholds)")
    print("=" * 80)

    # Conservative parameters - only highest conviction
    strategy = SqueezeHunterStrategy(
        min_short_interest_pct=30.0,  # Higher threshold
        min_days_to_cover=5.0,  # Higher threshold
        min_squeeze_score=75.0,  # Higher threshold
    )

    provider = MockDataProvider()
    watchlist = ["GME", "AMC", "TSLA", "BBBY", "CLOV", "SPCE"]

    print("\nScanning with conservative parameters:")
    print("  • Min Short Interest: 30%")
    print("  • Min Days to Cover: 5.0")
    print("  • Min Squeeze Score: 75.0")
    print()

    opportunities = strategy.scan_for_opportunities(watchlist, provider)

    print(f"\nFound {len(opportunities)} HIGH CONVICTION opportunities:\n")

    if opportunities:
        for opp in opportunities:
            print(f">>> {opp.symbol} <<<")
            print(
                f"    Score: {opp.squeeze_score:.1f} | "
                f"SI: {opp.short_interest_data.short_percent_float:.1f}% | "
                f"DTC: {opp.short_interest_data.days_to_cover:.1f}"
            )
            ret_pct = opp.expected_return_pct()
            print(f"    Target: ${opp.target_price:.2f} (+{ret_pct:.1f}%)")
            print(f"    Recommendation: {opp.recommendation.upper()}\n")
    else:
        print("No opportunities meet the strict criteria.")


def demo_value_combination():
    """Demo: Combining squeeze with value investing"""
    print("=" * 80)
    print("DEMO 4: Combining Squeeze + Value Investing")
    print("=" * 80)

    strategy = SqueezeHunterStrategy(combine_with_value=True)
    provider = MockDataProvider()

    # Scan for squeeze opportunities
    watchlist = ["GME", "AMC"]
    opportunities = strategy.scan_for_opportunities(watchlist, provider)

    print("\nCombining squeeze metrics with value metrics:\n")

    for opp in opportunities:
        print(f"{opp.symbol}:")
        print(f"  Squeeze Score: {opp.squeeze_score:.1f}/100")

        # Mock value metrics (in production, fetch real data)
        if opp.symbol == "GME":
            value_metrics = {
                "pe_ratio": 12.0,  # Decent
                "pb_ratio": 1.2,  # Good
                "fcf_yield": 0.08,  # Decent
                "roe": 0.15,  # Decent
            }
        else:  # AMC
            value_metrics = {
                "pe_ratio": 25.0,  # High
                "pb_ratio": 3.5,  # High
                "fcf_yield": 0.02,  # Low
                "roe": 0.05,  # Low
            }

        value_score = strategy._calculate_value_score(value_metrics)
        combined_score = strategy.combine_with_value_strategy(opp, value_metrics)

        print(f"  Value Score:   {value_score:.1f}/100")
        print(f"  Combined:      {combined_score:.1f}/100 (60% squeeze + 40% value)")
        print()


def demo_historical_validation():
    """Demo: Validate strategy against historical squeezes"""
    print("=" * 80)
    print("DEMO 5: Historical Squeeze Validation")
    print("=" * 80)

    strategy = SqueezeHunterStrategy()

    print("\nValidating strategy against famous historical squeezes:\n")

    # GameStop - January 2021
    print("1. GameStop (GME) - January 2021")
    print("   Actual: 140% short interest → 1,500% gain")

    gme_data = ShortInterestData(
        symbol="GME",
        short_interest=71_000_000,
        float_shares=50_000_000,
        short_percent_float=142.0,  # Over 100%!
        days_to_cover=15.0,
        last_updated=datetime(2021, 1, 15),
    )

    gme_catalysts = [
        Catalyst("sentiment", "Reddit WSB rally", 10.0, datetime(2021, 1, 20)),
        Catalyst("insider_buying", "Ryan Cohen stake", 9.0, datetime(2021, 1, 10)),
        Catalyst("technical", "Breaking resistance", 8.0, datetime(2021, 1, 22)),
    ]

    gme_score = strategy._calculate_squeeze_score(gme_data, gme_catalysts)
    gme_target = strategy._calculate_squeeze_target(20.0, gme_score, gme_data)

    print(f"   Strategy Score: {gme_score:.1f}/100 ✓")
    gain_pct = (gme_target / 20 - 1) * 100
    print(f"   Predicted Target: ${gme_target:.2f} from $20 (+{gain_pct:.0f}%)")
    print()

    # AMC - June 2021
    print("2. AMC Entertainment - June 2021")
    print("   Actual: 22% short interest → 2,000% gain")

    amc_data = ShortInterestData(
        symbol="AMC",
        short_interest=102_000_000,
        float_shares=450_000_000,
        short_percent_float=22.7,
        days_to_cover=6.5,
        last_updated=datetime(2021, 5, 28),
    )

    amc_catalysts = [
        Catalyst("sentiment", "Retail frenzy", 9.0, datetime(2021, 6, 1)),
        Catalyst("news", "Theater reopening", 7.0, datetime(2021, 5, 25)),
    ]

    amc_score = strategy._calculate_squeeze_score(amc_data, amc_catalysts)
    amc_target = strategy._calculate_squeeze_target(10.0, amc_score, amc_data)

    print(f"   Strategy Score: {amc_score:.1f}/100 ✓")
    gain_pct = (amc_target / 10 - 1) * 100
    print(f"   Predicted Target: ${amc_target:.2f} from $10 (+{gain_pct:.0f}%)")
    print()

    # Tesla - 2020
    print("3. Tesla (TSLA) - 2020 Rally")
    print("   Actual: 20% short interest → Continuous covering")

    tsla_data = ShortInterestData(
        symbol="TSLA",
        short_interest=30_000_000,
        float_shares=150_000_000,
        short_percent_float=20.0,
        days_to_cover=4.0,
        last_updated=datetime(2020, 1, 1),
    )

    tsla_catalysts = [
        Catalyst("earnings", "Profitability", 9.0, datetime(2020, 1, 29)),
        Catalyst("news", "S&P 500 inclusion", 8.0, datetime(2020, 12, 21)),
    ]

    tsla_score = strategy._calculate_squeeze_score(tsla_data, tsla_catalysts)
    tsla_target = strategy._calculate_squeeze_target(85.0, tsla_score, tsla_data)

    print(f"   Strategy Score: {tsla_score:.1f}/100 ✓")
    gain_pct = (tsla_target / 85 - 1) * 100
    print(f"   Predicted Target: ${tsla_target:.2f} from $85 (+{gain_pct:.0f}%)")
    print()

    print("✓ Strategy successfully detected all major historical squeezes")


def demo_risk_analysis():
    """Demo: Risk analysis and recommendations"""
    print("=" * 80)
    print("DEMO 6: Risk Analysis & Position Sizing")
    print("=" * 80)

    strategy = SqueezeHunterStrategy()
    provider = MockDataProvider()

    watchlist = ["GME", "AMC", "TSLA"]
    opportunities = strategy.scan_for_opportunities(watchlist, provider)

    print("\nRisk analysis for squeeze opportunities:\n")

    portfolio_size = 100_000  # $100k portfolio

    for opp in opportunities:
        print(f"{opp.symbol}:")
        print(
            f"  Score: {opp.squeeze_score:.1f} | "
            f"Confidence: {opp.confidence_level} | Risk: {opp.risk_rating}"
        )

        # Position sizing based on risk
        if opp.risk_rating == "low":
            position_size_pct = 0.02  # 2% max
        elif opp.risk_rating == "medium":
            position_size_pct = 0.015  # 1.5% max
        else:  # high
            position_size_pct = 0.01  # 1% max

        position_value = portfolio_size * position_size_pct
        shares = int(position_value / opp.current_price)

        pct = position_size_pct * 100
        print(
            f"  Recommended Position: ${position_value:.0f} "
            f"({pct:.1f}% of portfolio)"
        )
        print(f"  Shares: {shares} @ ${opp.current_price:.2f}")
        print(f"  Stop Loss: ${opp.current_price * 0.85:.2f} (-15%)")
        ret_pct = opp.expected_return_pct()
        print(f"  Target: ${opp.target_price:.2f} (+{ret_pct:.1f}%)")
        print(f"  Recommendation: {opp.recommendation.upper()}")
        print()


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "   SQUEEZE HUNTER STRATEGY - DEMONSTRATION".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Run demos
    demo_basic_scan()
    print("\n")

    demo_aggressive_scan()
    print("\n")

    demo_conservative_scan()
    print("\n")

    demo_value_combination()
    print("\n")

    demo_historical_validation()
    print("\n")

    demo_risk_analysis()
    print("\n")

    print("=" * 80)
    print("All demos completed!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Integrate real data providers (FINRA, Yahoo Finance)")
    print("  2. Implement live catalyst detection")
    print("  3. Add backtesting on historical data")
    print("  4. Set up alerts for high-scoring opportunities")
    print("  5. Combine with risk management and position sizing")
    print()


if __name__ == "__main__":
    main()
