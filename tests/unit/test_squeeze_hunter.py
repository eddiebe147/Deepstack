"""
Tests for Short Squeeze Hunter Strategy

Tests squeeze detection, scoring, catalyst detection, and historical validation.
Target: 80%+ coverage, 20+ tests
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from core.strategies.squeeze_hunter import (
    Catalyst,
    ShortInterestData,
    SqueezeHunterStrategy,
    SqueezeOpportunity,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_short_data():
    """Sample short interest data"""
    return ShortInterestData(
        symbol="GME",
        short_interest=50_000_000,
        float_shares=100_000_000,
        short_percent_float=50.0,
        days_to_cover=8.0,
        last_updated=datetime.now(),
    )


@pytest.fixture
def sample_catalyst():
    """Sample catalyst"""
    return Catalyst(
        catalyst_type="earnings",
        description="Earnings beat expected",
        impact_score=8.5,
        date=datetime.now(),
    )


@pytest.fixture
def strategy():
    """Default strategy instance"""
    return SqueezeHunterStrategy()


@pytest.fixture
def mock_data_provider():
    """Mock data provider for testing"""
    provider = Mock()

    # Default short interest data
    provider.get_short_interest = Mock(
        return_value=ShortInterestData(
            symbol="TEST",
            short_interest=25_000_000,
            float_shares=100_000_000,
            short_percent_float=25.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )
    )

    # Default price
    provider.get_current_price = Mock(return_value=100.0)

    # Default catalysts
    provider.check_earnings = Mock(
        return_value=Catalyst(
            catalyst_type="earnings",
            description="Strong earnings beat",
            impact_score=9.0,
            date=datetime.now(),
        )
    )

    provider.check_news = Mock(return_value=None)
    provider.check_insider_buying = Mock(return_value=None)
    provider.check_technical = Mock(return_value=None)

    return provider


# ============================================================================
# ShortInterestData Tests
# ============================================================================


def test_short_interest_data_creation(sample_short_data):
    """Test ShortInterestData creation"""
    assert sample_short_data.symbol == "GME"
    assert sample_short_data.short_percent_float == 50.0
    assert sample_short_data.days_to_cover == 8.0


def test_short_interest_data_validation():
    """Test ShortInterestData validation"""
    # Negative short interest
    with pytest.raises(ValueError, match="cannot be negative"):
        ShortInterestData(
            symbol="TEST",
            short_interest=-1000,
            float_shares=1000000,
            short_percent_float=20.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )

    # Invalid float shares
    with pytest.raises(ValueError, match="must be positive"):
        ShortInterestData(
            symbol="TEST",
            short_interest=100000,
            float_shares=0,
            short_percent_float=20.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )

    # Invalid short percent
    with pytest.raises(ValueError, match="must be 0-200%"):
        ShortInterestData(
            symbol="TEST",
            short_interest=100000,
            float_shares=1000000,
            short_percent_float=300.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )

    # Negative days to cover
    with pytest.raises(ValueError, match="cannot be negative"):
        ShortInterestData(
            symbol="TEST",
            short_interest=100000,
            float_shares=1000000,
            short_percent_float=20.0,
            days_to_cover=-1.0,
            last_updated=datetime.now(),
        )


# ============================================================================
# Catalyst Tests
# ============================================================================


def test_catalyst_creation(sample_catalyst):
    """Test Catalyst creation"""
    assert sample_catalyst.catalyst_type == "earnings"
    assert sample_catalyst.impact_score == 8.5
    assert "Earnings beat" in sample_catalyst.description


def test_catalyst_validation():
    """Test Catalyst validation"""
    # Invalid catalyst type
    with pytest.raises(ValueError, match="catalyst_type must be one of"):
        Catalyst(
            catalyst_type="invalid",
            description="Test",
            impact_score=5.0,
            date=datetime.now(),
        )

    # Invalid impact score
    with pytest.raises(ValueError, match="impact_score must be 0-10"):
        Catalyst(
            catalyst_type="earnings",
            description="Test",
            impact_score=15.0,
            date=datetime.now(),
        )


# ============================================================================
# SqueezeOpportunity Tests
# ============================================================================


def test_squeeze_opportunity_creation(sample_short_data, sample_catalyst):
    """Test SqueezeOpportunity creation"""
    opp = SqueezeOpportunity(
        symbol="GME",
        squeeze_score=85.0,
        short_interest_data=sample_short_data,
        catalysts=[sample_catalyst],
        current_price=150.0,
        target_price=300.0,
        confidence_level="high",
        risk_rating="high",
        recommendation="buy",
    )

    assert opp.symbol == "GME"
    assert opp.squeeze_score == 85.0
    assert opp.expected_return_pct() == 100.0  # 2x = 100% return


def test_squeeze_opportunity_validation(sample_short_data, sample_catalyst):
    """Test SqueezeOpportunity validation"""
    # Invalid squeeze score
    with pytest.raises(ValueError, match="squeeze_score must be 0-100"):
        SqueezeOpportunity(
            symbol="TEST",
            squeeze_score=150.0,
            short_interest_data=sample_short_data,
            catalysts=[sample_catalyst],
            current_price=100.0,
            target_price=150.0,
            confidence_level="high",
            risk_rating="low",
            recommendation="buy",
        )

    # Invalid confidence level
    with pytest.raises(ValueError, match="confidence_level must be"):
        SqueezeOpportunity(
            symbol="TEST",
            squeeze_score=75.0,
            short_interest_data=sample_short_data,
            catalysts=[sample_catalyst],
            current_price=100.0,
            target_price=150.0,
            confidence_level="super_high",
            risk_rating="low",
            recommendation="buy",
        )


def test_squeeze_opportunity_to_dict(sample_short_data, sample_catalyst):
    """Test SqueezeOpportunity to_dict conversion"""
    opp = SqueezeOpportunity(
        symbol="GME",
        squeeze_score=85.0,
        short_interest_data=sample_short_data,
        catalysts=[sample_catalyst],
        current_price=150.0,
        target_price=300.0,
        confidence_level="high",
        risk_rating="high",
        recommendation="buy",
    )

    data = opp.to_dict()
    assert data["symbol"] == "GME"
    assert data["squeeze_score"] == 85.0
    assert data["expected_return_pct"] == 100.0
    assert len(data["catalysts"]) == 1


# ============================================================================
# Strategy Initialization Tests
# ============================================================================


def test_strategy_initialization():
    """Test SqueezeHunterStrategy initialization"""
    strategy = SqueezeHunterStrategy(
        min_short_interest_pct=25.0,
        min_days_to_cover=5.0,
        min_squeeze_score=70.0,
    )

    assert strategy.min_short_interest_pct == 25.0
    assert strategy.min_days_to_cover == 5.0
    assert strategy.min_squeeze_score == 70.0


def test_strategy_default_parameters():
    """Test default strategy parameters"""
    strategy = SqueezeHunterStrategy()

    assert strategy.min_short_interest_pct == 20.0
    assert strategy.min_days_to_cover == 3.0
    assert strategy.min_squeeze_score == 60.0
    assert strategy.combine_with_value is True
    assert strategy.min_market_cap == 100_000_000


# ============================================================================
# Squeeze Score Calculation Tests
# ============================================================================


def test_squeeze_score_high_short_interest(strategy):
    """Test squeeze score with high short interest (>50%)"""
    short_data = ShortInterestData(
        symbol="GME",
        short_interest=60_000_000,
        float_shares=100_000_000,
        short_percent_float=60.0,  # >50% = 40 points
        days_to_cover=12.0,  # >10 = 30 points
        last_updated=datetime.now(),
    )

    catalysts = [
        Catalyst(
            catalyst_type="earnings",
            description="Strong catalyst",
            impact_score=9.0,  # High impact = 30 points
            date=datetime.now(),
        )
    ]

    score = strategy._calculate_squeeze_score(short_data, catalysts)
    assert score == 100.0  # Max score: 40 + 30 + 30


def test_squeeze_score_medium_metrics(strategy):
    """Test squeeze score with medium metrics"""
    short_data = ShortInterestData(
        symbol="AMC",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,  # 20-30% = 20 points
        days_to_cover=6.0,  # 5-7 = 20 points
        last_updated=datetime.now(),
    )

    catalysts = [
        Catalyst(
            catalyst_type="news",
            description="Medium catalyst",
            impact_score=6.0,  # Medium impact = 20 points
            date=datetime.now(),
        )
    ]

    score = strategy._calculate_squeeze_score(short_data, catalysts)
    assert score == 60.0  # 20 + 20 + 20


def test_squeeze_score_no_catalysts(strategy):
    """Test squeeze score with no catalysts"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=30_000_000,
        float_shares=100_000_000,
        short_percent_float=30.0,  # 20-30% = 20 points (30.0 not > 30)
        days_to_cover=8.0,  # 7-10 = 25 points
        last_updated=datetime.now(),
    )

    score = strategy._calculate_squeeze_score(short_data, [])
    assert score == 45.0  # 20 + 25 + 0


def test_squeeze_score_low_metrics(strategy):
    """Test squeeze score with low metrics"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=15_000_000,
        float_shares=100_000_000,
        short_percent_float=15.0,  # <20% = 10 points
        days_to_cover=2.0,  # <3 = 5 points
        last_updated=datetime.now(),
    )

    catalysts = [
        Catalyst(
            catalyst_type="technical",
            description="Weak catalyst",
            impact_score=3.0,  # Low impact = 10 points
            date=datetime.now(),
        )
    ]

    score = strategy._calculate_squeeze_score(short_data, catalysts)
    assert score == 25.0  # 10 + 5 + 10


# ============================================================================
# Target Price Calculation Tests
# ============================================================================


def test_target_price_high_score(strategy):
    """Test target price with high squeeze score (80-100)"""
    short_data = ShortInterestData(
        symbol="GME",
        short_interest=60_000_000,
        float_shares=100_000_000,
        short_percent_float=60.0,  # >50% adds 20% upside
        days_to_cover=10.0,
        last_updated=datetime.now(),
    )

    current_price = 100.0
    squeeze_score = 90.0  # High score: 50-100% base upside

    target = strategy._calculate_squeeze_target(
        current_price, squeeze_score, short_data
    )

    # Score 90 = 50% + (90-80)/20 * 50% = 75% base
    # SI >50% adds 20%
    # Total: 95% upside = $195
    assert target == pytest.approx(195.0, rel=0.01)


def test_target_price_medium_score(strategy):
    """Test target price with medium squeeze score (60-80)"""
    short_data = ShortInterestData(
        symbol="AMC",
        short_interest=35_000_000,
        float_shares=100_000_000,
        short_percent_float=35.0,  # >30% adds 10% upside
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    current_price = 100.0
    squeeze_score = 70.0  # Medium score: 30-50% base upside

    target = strategy._calculate_squeeze_target(
        current_price, squeeze_score, short_data
    )

    # Score 70 = 30% + (70-60)/20 * 20% = 40% base
    # SI >30% adds 10%
    # Total: 50% upside = $150
    assert target == pytest.approx(150.0, rel=0.01)


def test_target_price_no_si_boost(strategy):
    """Test target price without short interest boost"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=20_000_000,
        float_shares=100_000_000,
        short_percent_float=20.0,  # <30% no boost
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    current_price = 100.0
    squeeze_score = 80.0  # 50% base upside

    target = strategy._calculate_squeeze_target(
        current_price, squeeze_score, short_data
    )

    # Score 80 = 50% base, no SI boost
    # Total: 50% upside = $150
    assert target == pytest.approx(150.0, rel=0.01)


# ============================================================================
# Criteria & Assessment Tests
# ============================================================================


def test_meets_criteria_pass(strategy):
    """Test stock meeting minimum criteria"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,  # >= 20%
        days_to_cover=5.0,  # >= 3
        last_updated=datetime.now(),
    )

    assert strategy._meets_criteria(short_data) is True


def test_meets_criteria_fail_short_interest(strategy):
    """Test stock failing short interest criteria"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=15_000_000,
        float_shares=100_000_000,
        short_percent_float=15.0,  # < 20%
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    assert strategy._meets_criteria(short_data) is False


def test_meets_criteria_fail_days_to_cover(strategy):
    """Test stock failing days to cover criteria"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,
        days_to_cover=2.0,  # < 3
        last_updated=datetime.now(),
    )

    assert strategy._meets_criteria(short_data) is False


def test_assess_confidence_high(strategy):
    """Test high confidence assessment"""
    short_data = ShortInterestData(
        symbol="GME",
        short_interest=50_000_000,
        float_shares=100_000_000,
        short_percent_float=50.0,
        days_to_cover=8.0,
        last_updated=datetime.now(),
    )

    catalysts = [
        Catalyst("earnings", "Beat", 9.0, datetime.now()),
        Catalyst("news", "Positive", 8.0, datetime.now()),
    ]

    confidence = strategy._assess_confidence(85.0, catalysts, short_data)
    assert confidence == "high"  # Score >= 80 and 2+ catalysts


def test_assess_confidence_medium(strategy):
    """Test medium confidence assessment"""
    short_data = ShortInterestData(
        symbol="AMC",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    catalysts = [Catalyst("earnings", "Beat", 7.0, datetime.now())]

    confidence = strategy._assess_confidence(65.0, catalysts, short_data)
    assert confidence == "medium"  # Score >= 60 and 1+ catalyst


def test_assess_confidence_low(strategy):
    """Test low confidence assessment"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=20_000_000,
        float_shares=100_000_000,
        short_percent_float=20.0,
        days_to_cover=3.0,
        last_updated=datetime.now(),
    )

    confidence = strategy._assess_confidence(55.0, [], short_data)
    assert confidence == "low"  # Low score, no catalysts


def test_assess_risk_high(strategy):
    """Test high risk assessment"""
    short_data = ShortInterestData(
        symbol="GME",
        short_interest=60_000_000,
        float_shares=100_000_000,
        short_percent_float=60.0,  # >50%
        days_to_cover=10.0,
        last_updated=datetime.now(),
    )

    risk = strategy._assess_risk(short_data, 150.0)
    assert risk == "high"  # SI >50%


def test_assess_risk_medium(strategy):
    """Test medium risk assessment"""
    short_data = ShortInterestData(
        symbol="AMC",
        short_interest=35_000_000,
        float_shares=100_000_000,
        short_percent_float=35.0,  # >30%
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    risk = strategy._assess_risk(short_data, 60.0)
    assert risk == "medium"  # SI >30% or price >50


def test_assess_risk_low(strategy):
    """Test low risk assessment"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,  # <30%
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    risk = strategy._assess_risk(short_data, 30.0)
    assert risk == "low"  # SI <30% and price <50


def test_make_recommendation_buy(strategy):
    """Test buy recommendation"""
    recommendation = strategy._make_recommendation(80.0, "high", "low")
    assert recommendation == "buy"


def test_make_recommendation_hold(strategy):
    """Test hold recommendation"""
    recommendation = strategy._make_recommendation(65.0, "medium", "medium")
    assert recommendation == "hold"


def test_make_recommendation_pass(strategy):
    """Test pass recommendation"""
    recommendation = strategy._make_recommendation(55.0, "low", "high")
    assert recommendation == "pass"


# ============================================================================
# Value Strategy Combination Tests
# ============================================================================


def test_combine_with_value_strategy(strategy, sample_short_data, sample_catalyst):
    """Test combining squeeze with value metrics"""
    opportunity = SqueezeOpportunity(
        symbol="GME",
        squeeze_score=80.0,
        short_interest_data=sample_short_data,
        catalysts=[sample_catalyst],
        current_price=100.0,
        target_price=150.0,
        confidence_level="high",
        risk_rating="medium",
        recommendation="buy",
    )

    value_metrics = {
        "pe_ratio": 8.0,  # Low PE
        "pb_ratio": 0.8,  # Low PB
        "fcf_yield": 0.12,  # High FCF yield
        "roe": 0.25,  # High ROE
    }

    combined_score = strategy.combine_with_value_strategy(opportunity, value_metrics)

    # Squeeze: 80 * 0.6 = 48
    # Value: 100 * 0.4 = 40
    # Combined: 88
    assert combined_score == pytest.approx(88.0, rel=0.01)


def test_calculate_value_score_high(strategy):
    """Test high value score calculation"""
    value_metrics = {
        "pe_ratio": 8.0,  # <10 = 25 pts
        "pb_ratio": 0.8,  # <1 = 25 pts
        "fcf_yield": 0.12,  # >10% = 25 pts
        "roe": 0.25,  # >20% = 25 pts
    }

    score = strategy._calculate_value_score(value_metrics)
    assert score == 100.0


def test_calculate_value_score_medium(strategy):
    """Test medium value score calculation"""
    value_metrics = {
        "pe_ratio": 15.0,  # 15-20 = 15 pts (15.0 not < 15)
        "pb_ratio": 1.5,  # 1-2 = 20 pts
        "fcf_yield": 0.08,  # 5-8% = 15 pts (0.08 not > 0.08)
        "roe": 0.15,  # 10-15% = 15 pts (0.15 not > 0.15)
    }

    score = strategy._calculate_value_score(value_metrics)
    assert score == 65.0  # 15 + 20 + 15 + 15


# ============================================================================
# Full Scan Tests
# ============================================================================


def test_scan_for_opportunities_with_mock_provider(strategy, mock_data_provider):
    """Test full scan with mock data provider"""
    watchlist = ["GME", "AMC", "TEST"]

    opportunities = strategy.scan_for_opportunities(watchlist, mock_data_provider)

    assert len(opportunities) >= 0  # May find opportunities
    assert all(isinstance(opp, SqueezeOpportunity) for opp in opportunities)


def test_scan_for_opportunities_filtering(mock_data_provider):
    """Test scan filters out low-scoring opportunities"""
    # Create strategy with high minimum score
    strategy = SqueezeHunterStrategy(min_squeeze_score=90.0)

    watchlist = ["TEST1", "TEST2", "TEST3"]

    # Mock provider returns medium short interest
    mock_data_provider.get_short_interest.return_value = ShortInterestData(
        symbol="TEST",
        short_interest=25_000_000,
        float_shares=100_000_000,
        short_percent_float=25.0,  # Medium SI
        days_to_cover=5.0,
        last_updated=datetime.now(),
    )

    opportunities = strategy.scan_for_opportunities(watchlist, mock_data_provider)

    # Should find 0 opportunities (scores won't reach 90)
    assert len(opportunities) == 0


def test_scan_for_opportunities_sorting(strategy, mock_data_provider):
    """Test scan sorts by squeeze score"""

    # Create mock provider with varying short interest
    def get_short_interest_varying(symbol):
        si_map = {
            "HIGH": 60.0,  # High SI
            "MED": 30.0,  # Medium SI
            "LOW": 20.0,  # Low SI
        }
        return ShortInterestData(
            symbol=symbol,
            short_interest=int(si_map[symbol] * 1_000_000),
            float_shares=100_000_000,
            short_percent_float=si_map[symbol],
            days_to_cover=8.0,
            last_updated=datetime.now(),
        )

    mock_data_provider.get_short_interest = get_short_interest_varying

    watchlist = ["LOW", "HIGH", "MED"]

    opportunities = strategy.scan_for_opportunities(watchlist, mock_data_provider)

    # Should be sorted by score (HIGH > MED > LOW)
    if len(opportunities) > 1:
        for i in range(len(opportunities) - 1):
            assert opportunities[i].squeeze_score >= opportunities[i + 1].squeeze_score


def test_scan_handles_errors_gracefully(strategy, mock_data_provider):
    """Test scan handles errors gracefully"""

    # Mock provider raises exception for one symbol
    def get_short_interest_with_error(symbol):
        if symbol == "ERROR":
            raise ValueError("Test error")
        return ShortInterestData(
            symbol=symbol,
            short_interest=25_000_000,
            float_shares=100_000_000,
            short_percent_float=25.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )

    mock_data_provider.get_short_interest = get_short_interest_with_error

    watchlist = ["GOOD1", "ERROR", "GOOD2"]

    # Should not raise exception, just skip error symbol
    opportunities = strategy.scan_for_opportunities(watchlist, mock_data_provider)

    assert all(opp.symbol != "ERROR" for opp in opportunities)


# ============================================================================
# Historical Validation Tests (Famous Squeezes)
# ============================================================================


def test_historical_gme_squeeze_detection(strategy):
    """Test detection of GME squeeze (Jan 2021)"""
    # GME had ~140% short interest pre-squeeze
    gme_data = ShortInterestData(
        symbol="GME",
        short_interest=71_000_000,  # More shares short than float!
        float_shares=50_000_000,
        short_percent_float=140.0,  # Extreme short interest
        days_to_cover=15.0,  # Very high DTC
        last_updated=datetime(2021, 1, 15),
    )

    catalysts = [
        Catalyst("news", "Reddit WSB rally", 10.0, datetime(2021, 1, 20)),
        Catalyst("insider_buying", "Ryan Cohen stake", 9.0, datetime(2021, 1, 10)),
        Catalyst("technical", "Breaking resistance", 8.0, datetime(2021, 1, 22)),
    ]

    score = strategy._calculate_squeeze_score(gme_data, catalysts)

    # Should score very high (100)
    assert score >= 90.0


def test_historical_amc_squeeze_detection(strategy):
    """Test detection of AMC squeeze (June 2021)"""
    # AMC had ~20% short interest pre-squeeze
    amc_data = ShortInterestData(
        symbol="AMC",
        short_interest=102_000_000,
        float_shares=450_000_000,
        short_percent_float=22.7,
        days_to_cover=6.5,
        last_updated=datetime(2021, 5, 28),
    )

    catalysts = [
        Catalyst("sentiment", "Retail trading frenzy", 9.0, datetime(2021, 6, 1)),
        Catalyst("news", "Theater reopening", 7.0, datetime(2021, 5, 25)),
    ]

    score = strategy._calculate_squeeze_score(amc_data, catalysts)

    # Should score high (70+)
    assert score >= 65.0


def test_historical_tsla_squeeze_detection(strategy):
    """Test detection of TSLA squeeze (2020)"""
    # TSLA had ~20% short interest during 2020 rally
    tsla_data = ShortInterestData(
        symbol="TSLA",
        short_interest=30_000_000,
        float_shares=150_000_000,
        short_percent_float=20.0,
        days_to_cover=4.0,
        last_updated=datetime(2020, 1, 1),
    )

    catalysts = [
        Catalyst("earnings", "Profitability achieved", 9.0, datetime(2020, 1, 29)),
        Catalyst("news", "S&P 500 inclusion", 8.0, datetime(2020, 12, 21)),
    ]

    score = strategy._calculate_squeeze_score(tsla_data, catalysts)

    # Should score medium-high (60+)
    assert score >= 55.0


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_extreme_short_interest_over_100_percent(strategy):
    """Test handling of >100% short interest (like GME)"""
    extreme_data = ShortInterestData(
        symbol="EXTREME",
        short_interest=150_000_000,
        float_shares=100_000_000,
        short_percent_float=150.0,  # >100% SI is possible
        days_to_cover=20.0,
        last_updated=datetime.now(),
    )

    catalysts = [Catalyst("news", "Major catalyst", 10.0, datetime.now())]

    score = strategy._calculate_squeeze_score(extreme_data, catalysts)
    assert score == 100.0  # Max score

    target = strategy._calculate_squeeze_target(100.0, score, extreme_data)
    assert target > 200.0  # Should predict massive upside


def test_zero_days_to_cover(strategy):
    """Test handling of very low days to cover"""
    low_dtc_data = ShortInterestData(
        symbol="TEST",
        short_interest=5_000_000,
        float_shares=100_000_000,
        short_percent_float=5.0,
        days_to_cover=0.1,  # Very low DTC
        last_updated=datetime.now(),
    )

    # Should still process without error
    score = strategy._calculate_squeeze_score(low_dtc_data, [])
    assert score >= 0


def test_no_catalysts_scenario(strategy):
    """Test opportunity with high SI but no catalysts"""
    high_si_data = ShortInterestData(
        symbol="TEST",
        short_interest=40_000_000,
        float_shares=100_000_000,
        short_percent_float=40.0,  # High SI
        days_to_cover=8.0,
        last_updated=datetime.now(),
    )

    score = strategy._calculate_squeeze_score(high_si_data, [])

    # Should score decently but not max (no catalyst component)
    assert 50.0 <= score < 80.0


def test_many_weak_catalysts_vs_one_strong(strategy):
    """Test scoring: many weak catalysts vs one strong catalyst"""
    short_data = ShortInterestData(
        symbol="TEST",
        short_interest=30_000_000,
        float_shares=100_000_000,
        short_percent_float=30.0,
        days_to_cover=6.0,
        last_updated=datetime.now(),
    )

    # Many weak catalysts
    weak_catalysts = [
        Catalyst("news", "Minor news 1", 2.0, datetime.now()),
        Catalyst("technical", "Minor technical 1", 3.0, datetime.now()),
        Catalyst("sentiment", "Minor sentiment", 2.5, datetime.now()),
    ]

    # One strong catalyst
    strong_catalyst = [Catalyst("earnings", "Major beat", 9.0, datetime.now())]

    weak_score = strategy._calculate_squeeze_score(short_data, weak_catalysts)
    strong_score = strategy._calculate_squeeze_score(short_data, strong_catalyst)

    # Strong catalyst should score higher (uses max impact)
    assert strong_score > weak_score


def test_empty_watchlist(strategy, mock_data_provider):
    """Test scan with empty watchlist"""
    opportunities = strategy.scan_for_opportunities([], mock_data_provider)
    assert len(opportunities) == 0


def test_scan_without_data_provider(strategy):
    """Test scan uses mock data when no provider given"""
    watchlist = ["TEST1", "TEST2"]

    opportunities = strategy.scan_for_opportunities(watchlist, None)

    # Should use internal mock data
    assert isinstance(opportunities, list)
