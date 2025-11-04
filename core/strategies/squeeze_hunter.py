"""
Short Squeeze Hunter Strategy

Identifies stocks with high potential for short squeezes by analyzing:
1. Short interest metrics (% of float, days to cover)
2. Potential catalysts (earnings, news, insider buying, technical)
3. Deep value characteristics (optional)

Target accuracy: 80%+ squeeze detection on historical data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShortInterestData:
    """Short interest metrics for a stock"""

    symbol: str
    short_interest: int  # Shares sold short
    float_shares: int  # Total tradable shares
    short_percent_float: float  # % of float sold short
    days_to_cover: float  # Days to cover at avg volume
    last_updated: datetime

    def __post_init__(self):
        """Validate short interest data"""
        if self.short_interest < 0:
            raise ValueError(
                f"short_interest cannot be negative: {self.short_interest}"
            )
        if self.float_shares <= 0:
            raise ValueError(f"float_shares must be positive: {self.float_shares}")
        if self.short_percent_float < 0 or self.short_percent_float > 200:
            raise ValueError(
                f"short_percent_float must be 0-200%: {self.short_percent_float}"
            )
        if self.days_to_cover < 0:
            raise ValueError(f"days_to_cover cannot be negative: {self.days_to_cover}")


@dataclass
class Catalyst:
    """Potential squeeze catalyst"""

    catalyst_type: str  # "earnings", "news", "insider_buying", "technical", "sentiment"
    description: str
    impact_score: float  # 0-10 (10 = highest impact)
    date: datetime

    def __post_init__(self):
        """Validate catalyst data"""
        valid_types = ["earnings", "news", "insider_buying", "technical", "sentiment"]
        if self.catalyst_type not in valid_types:
            raise ValueError(
                f"catalyst_type must be one of {valid_types}, got {self.catalyst_type}"
            )
        if self.impact_score < 0 or self.impact_score > 10:
            raise ValueError(f"impact_score must be 0-10, got {self.impact_score}")


@dataclass
class SqueezeOpportunity:
    """A potential short squeeze opportunity"""

    symbol: str
    squeeze_score: float  # 0-100 (100 = highest probability)
    short_interest_data: ShortInterestData
    catalysts: List[Catalyst]
    current_price: float
    target_price: float  # Estimated squeeze target
    confidence_level: str  # "low", "medium", "high"
    risk_rating: str  # "low", "medium", "high"
    recommendation: str  # "buy", "hold", "pass"
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate squeeze opportunity"""
        if self.squeeze_score < 0 or self.squeeze_score > 100:
            raise ValueError(f"squeeze_score must be 0-100, got {self.squeeze_score}")
        if self.current_price <= 0:
            raise ValueError(
                f"current_price must be positive, got {self.current_price}"
            )
        if self.target_price <= 0:
            raise ValueError(f"target_price must be positive, got {self.target_price}")
        if self.confidence_level not in ["low", "medium", "high"]:
            raise ValueError(
                f"confidence_level must be low/medium/high, got {self.confidence_level}"
            )
        if self.risk_rating not in ["low", "medium", "high"]:
            raise ValueError(
                f"risk_rating must be low/medium/high, got {self.risk_rating}"
            )
        if self.recommendation not in ["buy", "hold", "pass"]:
            raise ValueError(
                f"recommendation must be buy/hold/pass, got {self.recommendation}"
            )

    def expected_return_pct(self) -> float:
        """Calculate expected return percentage"""
        return ((self.target_price / self.current_price) - 1) * 100

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary representation"""
        return {
            "symbol": self.symbol,
            "squeeze_score": self.squeeze_score,
            "short_interest_data": {
                "short_percent_float": self.short_interest_data.short_percent_float,
                "days_to_cover": self.short_interest_data.days_to_cover,
            },
            "catalysts": [
                {
                    "type": c.catalyst_type,
                    "description": c.description,
                    "impact_score": c.impact_score,
                }
                for c in self.catalysts
            ],
            "current_price": self.current_price,
            "target_price": self.target_price,
            "expected_return_pct": self.expected_return_pct(),
            "confidence_level": self.confidence_level,
            "risk_rating": self.risk_rating,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


class SqueezeHunterStrategy:
    """
    Short Squeeze Hunter Strategy

    Identifies stocks with:
    1. High short interest (>20% of float)
    2. Low days to cover (>3 days ideally)
    3. Positive catalysts (earnings, news, etc.)
    4. Deep value characteristics (optional)

    Target: 80%+ squeeze detection accuracy
    """

    def __init__(
        self,
        min_short_interest_pct: float = 20.0,  # Minimum 20% short interest
        min_days_to_cover: float = 3.0,  # Minimum 3 days to cover
        min_squeeze_score: float = 60.0,  # Minimum squeeze score
        combine_with_value: bool = True,  # Combine with deep value
        min_market_cap: float = 100_000_000,  # $100M minimum
    ):
        self.min_short_interest_pct = min_short_interest_pct
        self.min_days_to_cover = min_days_to_cover
        self.min_squeeze_score = min_squeeze_score
        self.combine_with_value = combine_with_value
        self.min_market_cap = min_market_cap

        logger.info(
            f"SqueezeHunterStrategy initialized: min_si={min_short_interest_pct}%, "
            f"min_dtc={min_days_to_cover}, min_score={min_squeeze_score}"
        )

    def scan_for_opportunities(
        self, watchlist: List[str], data_provider: Optional[any] = None
    ) -> List[SqueezeOpportunity]:
        """
        Scan watchlist for squeeze opportunities.

        Args:
            watchlist: List of stock symbols to scan
            data_provider: Optional data provider for real data (uses mock if None)

        Returns:
            List of opportunities ranked by squeeze score
        """
        opportunities = []

        logger.info(f"Scanning {len(watchlist)} symbols for squeeze opportunities")

        for symbol in watchlist:
            try:
                # Get short interest data
                short_data = self._get_short_interest(symbol, data_provider)

                # Check minimum thresholds
                if not self._meets_criteria(short_data):
                    logger.debug(
                        f"{symbol}: Does not meet criteria "
                        f"(SI: {short_data.short_percent_float}%, "
                        f"DTC: {short_data.days_to_cover})"
                    )
                    continue

                # Detect catalysts
                catalysts = self._detect_catalysts(symbol, data_provider)

                # Calculate squeeze score
                squeeze_score = self._calculate_squeeze_score(short_data, catalysts)

                if squeeze_score >= self.min_squeeze_score:
                    # Get current price and calculate target
                    current_price = self._get_current_price(symbol, data_provider)
                    target_price = self._calculate_squeeze_target(
                        current_price, squeeze_score, short_data
                    )

                    # Determine confidence and risk
                    confidence = self._assess_confidence(
                        squeeze_score, catalysts, short_data
                    )
                    risk = self._assess_risk(short_data, current_price)
                    recommendation = self._make_recommendation(
                        squeeze_score, confidence, risk
                    )

                    opportunity = SqueezeOpportunity(
                        symbol=symbol,
                        squeeze_score=squeeze_score,
                        short_interest_data=short_data,
                        catalysts=catalysts,
                        current_price=current_price,
                        target_price=target_price,
                        confidence_level=confidence,
                        risk_rating=risk,
                        recommendation=recommendation,
                    )
                    opportunities.append(opportunity)

                    logger.info(
                        f"{symbol}: Squeeze opportunity found - "
                        f"Score: {squeeze_score:.1f}, "
                        f"Recommendation: {recommendation}"
                    )
                else:
                    logger.debug(
                        f"{symbol}: Squeeze score too low ({squeeze_score:.1f})"
                    )

            except Exception as e:
                logger.warning(f"{symbol}: Error scanning - {e}")
                continue

        # Sort by squeeze score (highest first)
        opportunities.sort(key=lambda x: x.squeeze_score, reverse=True)

        logger.info(
            f"Found {len(opportunities)} squeeze opportunities "
            f"from {len(watchlist)} symbols"
        )

        return opportunities

    def _calculate_squeeze_score(
        self, short_data: ShortInterestData, catalysts: List[Catalyst]
    ) -> float:
        """
        Calculate squeeze probability score (0-100).

        Factors:
        1. Short interest % (40 points max)
           - >50%: 40 pts
           - 40-50%: 35 pts
           - 30-40%: 30 pts
           - 20-30%: 20 pts
           - <20%: 10 pts

        2. Days to cover (30 points max)
           - >10 days: 30 pts
           - 7-10 days: 25 pts
           - 5-7 days: 20 pts
           - 3-5 days: 15 pts
           - <3 days: 5 pts

        3. Catalysts (30 points max)
           - Strong catalysts (8-10 impact): 30 pts
           - Medium catalysts (5-7 impact): 20 pts
           - Weak catalysts (1-4 impact): 10 pts
           - No catalysts: 0 pts
        """
        score = 0.0

        # Short interest component (40 points)
        si_pct = short_data.short_percent_float
        if si_pct > 50:
            score += 40
        elif si_pct > 40:
            score += 35
        elif si_pct > 30:
            score += 30
        elif si_pct > 20:
            score += 20
        else:
            score += 10

        # Days to cover component (30 points)
        dtc = short_data.days_to_cover
        if dtc > 10:
            score += 30
        elif dtc > 7:
            score += 25
        elif dtc > 5:
            score += 20
        elif dtc > 3:
            score += 15
        else:
            score += 5

        # Catalyst component (30 points)
        if catalysts:
            max_catalyst_impact = max(c.impact_score for c in catalysts)
            if max_catalyst_impact >= 8:
                score += 30
            elif max_catalyst_impact >= 5:
                score += 20
            else:
                score += 10

        return min(score, 100.0)

    def _detect_catalysts(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> List[Catalyst]:
        """
        Detect potential squeeze catalysts.

        Types:
        1. Earnings Beat - upcoming/recent earnings surprise
        2. News - positive company news, product launches
        3. Insider Buying - insiders purchasing shares
        4. Technical - breaking resistance, volume spike
        5. Social Sentiment - Reddit/Twitter mentions (optional)

        Args:
            symbol: Stock symbol
            data_provider: Optional data provider

        Returns:
            List of detected catalysts
        """
        catalysts = []

        # For demo/testing, use mock detection
        # In production, integrate with real data sources

        # Earnings catalyst
        earnings_cat = self._check_earnings_catalyst(symbol, data_provider)
        if earnings_cat:
            catalysts.append(earnings_cat)

        # News catalyst
        news_cat = self._check_news_catalyst(symbol, data_provider)
        if news_cat:
            catalysts.append(news_cat)

        # Insider buying
        insider_cat = self._check_insider_buying(symbol, data_provider)
        if insider_cat:
            catalysts.append(insider_cat)

        # Technical catalyst
        technical_cat = self._check_technical_catalyst(symbol, data_provider)
        if technical_cat:
            catalysts.append(technical_cat)

        return catalysts

    def _calculate_squeeze_target(
        self, current_price: float, squeeze_score: float, short_data: ShortInterestData
    ) -> float:
        """
        Calculate potential squeeze target price.

        Formula:
        - High squeeze score (80-100): 50-100% upside
        - Medium squeeze score (60-80): 30-50% upside
        - Lower squeeze score (40-60): 20-30% upside

        Adjusted by short interest:
        - >50% SI: Add 20% to target
        - >30% SI: Add 10% to target

        Args:
            current_price: Current stock price
            squeeze_score: Calculated squeeze score
            short_data: Short interest data

        Returns:
            Target price
        """
        base_upside = 0.0

        if squeeze_score >= 80:
            base_upside = 0.50 + (squeeze_score - 80) / 20 * 0.50  # 50-100%
        elif squeeze_score >= 60:
            base_upside = 0.30 + (squeeze_score - 60) / 20 * 0.20  # 30-50%
        else:
            base_upside = 0.20 + (squeeze_score - 40) / 20 * 0.10  # 20-30%

        # Adjust for short interest
        si_pct = short_data.short_percent_float
        if si_pct > 50:
            base_upside += 0.20
        elif si_pct > 30:
            base_upside += 0.10

        target_price = current_price * (1 + base_upside)

        return target_price

    def combine_with_value_strategy(
        self, opportunity: SqueezeOpportunity, value_metrics: Dict[str, float]
    ) -> float:
        """
        Combine squeeze score with deep value metrics.

        Value metrics:
        - pe_ratio: Price-to-earnings ratio
        - pb_ratio: Price-to-book ratio
        - fcf_yield: Free cash flow yield
        - roe: Return on equity

        Args:
            opportunity: Squeeze opportunity
            value_metrics: Dictionary of value metrics

        Returns:
            Combined score (0-100)
        """
        squeeze_weight = 0.60  # 60% squeeze
        value_weight = 0.40  # 40% value

        # Calculate value score
        value_score = self._calculate_value_score(value_metrics)

        # Combined score
        combined_score = (
            opportunity.squeeze_score * squeeze_weight + value_score * value_weight
        )

        return combined_score

    def _calculate_value_score(self, value_metrics: Dict[str, float]) -> float:
        """
        Calculate value score from metrics (0-100).

        Args:
            value_metrics: Dictionary of value metrics

        Returns:
            Value score
        """
        score = 0.0

        # P/E ratio (25 points) - lower is better
        pe_ratio = value_metrics.get("pe_ratio", 20)
        if pe_ratio < 10:
            score += 25
        elif pe_ratio < 15:
            score += 20
        elif pe_ratio < 20:
            score += 15
        elif pe_ratio < 30:
            score += 10
        else:
            score += 5

        # P/B ratio (25 points) - lower is better
        pb_ratio = value_metrics.get("pb_ratio", 2)
        if pb_ratio < 1:
            score += 25
        elif pb_ratio < 2:
            score += 20
        elif pb_ratio < 3:
            score += 15
        else:
            score += 10

        # FCF yield (25 points) - higher is better
        fcf_yield = value_metrics.get("fcf_yield", 0.05)
        if fcf_yield > 0.10:
            score += 25
        elif fcf_yield > 0.08:
            score += 20
        elif fcf_yield > 0.05:
            score += 15
        elif fcf_yield > 0.03:
            score += 10
        else:
            score += 5

        # ROE (25 points) - higher is better
        roe = value_metrics.get("roe", 0.10)
        if roe > 0.20:
            score += 25
        elif roe > 0.15:
            score += 20
        elif roe > 0.10:
            score += 15
        elif roe > 0.05:
            score += 10
        else:
            score += 5

        return min(score, 100.0)

    def _get_short_interest(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> ShortInterestData:
        """
        Get short interest data.

        In production, integrate with:
        - FINRA short interest data
        - Yahoo Finance
        - Financial Modeling Prep API
        - Ortex (paid service)

        Args:
            symbol: Stock symbol
            data_provider: Optional data provider

        Returns:
            Short interest data
        """
        # For demo/testing, return mock data
        # In production, use real data provider
        if data_provider and hasattr(data_provider, "get_short_interest"):
            return data_provider.get_short_interest(symbol)

        # Mock data for testing
        return ShortInterestData(
            symbol=symbol,
            short_interest=10_000_000,
            float_shares=50_000_000,
            short_percent_float=20.0,
            days_to_cover=5.0,
            last_updated=datetime.now(),
        )

    def _get_current_price(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> float:
        """Get current stock price"""
        if data_provider and hasattr(data_provider, "get_current_price"):
            return data_provider.get_current_price(symbol)

        # Mock price for testing
        return 50.0

    def _meets_criteria(self, short_data: ShortInterestData) -> bool:
        """Check if stock meets minimum criteria"""
        return (
            short_data.short_percent_float >= self.min_short_interest_pct
            and short_data.days_to_cover >= self.min_days_to_cover
        )

    def _assess_confidence(
        self,
        squeeze_score: float,
        catalysts: List[Catalyst],
        short_data: ShortInterestData,
    ) -> str:
        """Assess confidence level: low, medium, high"""
        if squeeze_score >= 80 and len(catalysts) >= 2:
            return "high"
        elif squeeze_score >= 60 and len(catalysts) >= 1:
            return "medium"
        else:
            return "low"

    def _assess_risk(self, short_data: ShortInterestData, current_price: float) -> str:
        """Assess risk level: low, medium, high"""
        # Higher short interest = higher risk (can go lower first)
        # Higher price = higher risk (more to lose)

        if short_data.short_percent_float > 50 or current_price > 100:
            return "high"
        elif short_data.short_percent_float > 30 or current_price > 50:
            return "medium"
        else:
            return "low"

    def _make_recommendation(
        self, squeeze_score: float, confidence: str, risk: str
    ) -> str:
        """Make buy/hold/pass recommendation"""
        if squeeze_score >= 75 and confidence == "high" and risk != "high":
            return "buy"
        elif squeeze_score >= 60 and confidence in ["medium", "high"]:
            return "hold"
        else:
            return "pass"

    def _check_earnings_catalyst(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> Optional[Catalyst]:
        """Check for earnings catalyst"""
        # Mock implementation - in production, check earnings calendar and surprises
        if data_provider and hasattr(data_provider, "check_earnings"):
            return data_provider.check_earnings(symbol)
        return None

    def _check_news_catalyst(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> Optional[Catalyst]:
        """Check for news catalyst"""
        # Mock implementation - in production, analyze news sentiment
        if data_provider and hasattr(data_provider, "check_news"):
            return data_provider.check_news(symbol)
        return None

    def _check_insider_buying(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> Optional[Catalyst]:
        """Check for insider buying catalyst"""
        # Mock implementation - in production, check SEC Form 4 filings
        if data_provider and hasattr(data_provider, "check_insider_buying"):
            return data_provider.check_insider_buying(symbol)
        return None

    def _check_technical_catalyst(
        self, symbol: str, data_provider: Optional[any] = None
    ) -> Optional[Catalyst]:
        """Check for technical catalyst"""
        # Mock implementation - in production, analyze price action and volume
        if data_provider and hasattr(data_provider, "check_technical"):
            return data_provider.check_technical(symbol)
        return None
