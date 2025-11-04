"""
Market Regime Detector

Detects market regime using multi-factor analysis:
1. Trend analysis (SMA crossovers, ADX)
2. Volatility analysis (VIX, realized volatility)
3. Breadth analysis (advance-decline, new highs/lows)
4. Correlation analysis (market correlation levels)

Target: 70%+ historical accuracy on regime detection
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classifications"""

    BULL = "BULL"  # Strong uptrend, low volatility
    BEAR = "BEAR"  # Downtrend, elevated volatility
    SIDEWAYS = "SIDEWAYS"  # Range-bound, low momentum
    CRISIS = "CRISIS"  # Extreme volatility, panic selling


@dataclass
class RegimeFactors:
    """Individual regime factors and their signals"""

    # Trend factors
    sma_50: float  # 50-day simple moving average
    sma_200: float  # 200-day simple moving average
    adx: float  # Average Directional Index (trend strength)
    price: float  # Current market price

    # Volatility factors
    vix: float  # VIX index level
    realized_volatility: float  # Historical volatility (annualized)

    # Breadth factors
    advance_decline_ratio: float  # Advancing vs declining stocks
    new_highs_lows_ratio: float  # New highs vs new lows

    # Correlation factors
    correlation: float  # Average stock correlation to market

    timestamp: datetime

    def __post_init__(self):
        """Validate factor data"""
        if self.sma_50 <= 0 or self.sma_200 <= 0:
            raise ValueError("SMA values must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.adx < 0 or self.adx > 100:
            raise ValueError("ADX must be 0-100")
        if self.vix < 0:
            raise ValueError("VIX cannot be negative")
        if self.realized_volatility < 0:
            raise ValueError("Realized volatility cannot be negative")
        if self.advance_decline_ratio <= 0:
            raise ValueError("Advance-decline ratio must be positive")
        if self.new_highs_lows_ratio <= 0:
            raise ValueError("New highs-lows ratio must be positive")
        if self.correlation < -1 or self.correlation > 1:
            raise ValueError("Correlation must be -1 to 1")


@dataclass
class RegimeDetection:
    """Market regime detection result"""

    regime: MarketRegime
    confidence: float  # 0-100 confidence score
    factors: RegimeFactors
    factor_scores: Dict[str, float]  # Individual factor contributions
    timestamp: datetime
    metadata: Dict[str, any] = None

    def __post_init__(self):
        """Validate detection result"""
        if self.confidence < 0 or self.confidence > 100:
            raise ValueError(f"Confidence must be 0-100, got {self.confidence}")
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "regime": self.regime.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "factor_scores": self.factor_scores,
            "factors": {
                "sma_50": self.factors.sma_50,
                "sma_200": self.factors.sma_200,
                "adx": self.factors.adx,
                "price": self.factors.price,
                "vix": self.factors.vix,
                "realized_volatility": self.factors.realized_volatility,
                "advance_decline_ratio": self.factors.advance_decline_ratio,
                "new_highs_lows_ratio": self.factors.new_highs_lows_ratio,
                "correlation": self.factors.correlation,
            },
            "metadata": self.metadata,
        }


class RegimeDetector:
    """
    Multi-factor market regime detector.

    Analyzes:
    1. Trend: SMA crossovers (golden/death cross), ADX strength
    2. Volatility: VIX levels, realized volatility
    3. Breadth: Advance-decline ratio, new highs/lows
    4. Correlation: Market correlation levels

    Classification Rules:
    - BULL: Strong uptrend, low volatility, positive breadth
    - BEAR: Downtrend, elevated volatility, negative breadth
    - SIDEWAYS: Weak trend, moderate volatility, mixed breadth
    - CRISIS: Extreme volatility (VIX >40), panic conditions

    Target: 70%+ historical accuracy
    """

    def __init__(
        self,
        # Trend thresholds
        adx_strong_threshold: float = 25.0,  # Strong trend if ADX > 25
        adx_weak_threshold: float = 20.0,  # Weak trend if ADX < 20
        # Volatility thresholds
        vix_crisis_threshold: float = 40.0,  # Crisis if VIX > 40
        vix_elevated_threshold: float = 25.0,  # Elevated if VIX > 25
        vix_low_threshold: float = 15.0,  # Low if VIX < 15
        realized_vol_high_threshold: float = 0.30,  # High if >30% annualized
        # Breadth thresholds
        advance_decline_bullish: float = 1.5,  # Bullish if > 1.5
        advance_decline_bearish: float = 0.67,  # Bearish if < 0.67
        new_highs_lows_bullish: float = 2.0,  # Bullish if > 2.0
        new_highs_lows_bearish: float = 0.5,  # Bearish if < 0.5
        # Correlation thresholds
        correlation_high: float = 0.70,  # High correlation (crisis/bear)
        correlation_low: float = 0.40,  # Low correlation (bull)
        # Confidence thresholds
        min_confidence: float = 60.0,  # Minimum confidence for clear regime
    ):
        self.adx_strong = adx_strong_threshold
        self.adx_weak = adx_weak_threshold
        self.vix_crisis = vix_crisis_threshold
        self.vix_elevated = vix_elevated_threshold
        self.vix_low = vix_low_threshold
        self.realized_vol_high = realized_vol_high_threshold
        self.ad_bullish = advance_decline_bullish
        self.ad_bearish = advance_decline_bearish
        self.nh_nl_bullish = new_highs_lows_bullish
        self.nh_nl_bearish = new_highs_lows_bearish
        self.corr_high = correlation_high
        self.corr_low = correlation_low
        self.min_confidence = min_confidence

        logger.info("RegimeDetector initialized with multi-factor analysis")

    def detect_regime(self, factors: RegimeFactors) -> RegimeDetection:
        """
        Detect current market regime from factors.

        Args:
            factors: Market regime factors

        Returns:
            Regime detection with confidence score
        """
        # Calculate individual factor scores
        trend_score = self._calculate_trend_score(factors)
        volatility_score = self._calculate_volatility_score(factors)
        breadth_score = self._calculate_breadth_score(factors)
        correlation_score = self._calculate_correlation_score(factors)

        factor_scores = {
            "trend": trend_score,
            "volatility": volatility_score,
            "breadth": breadth_score,
            "correlation": correlation_score,
        }

        # Detect regime based on factor scores
        regime, confidence = self._classify_regime(
            trend_score, volatility_score, breadth_score, correlation_score, factors
        )

        detection = RegimeDetection(
            regime=regime,
            confidence=confidence,
            factors=factors,
            factor_scores=factor_scores,
            timestamp=factors.timestamp,
            metadata={
                "detection_method": "multi_factor",
                "factor_weights": {
                    "trend": 0.30,
                    "volatility": 0.25,
                    "breadth": 0.25,
                    "correlation": 0.20,
                },
            },
        )

        logger.info(
            f"Regime detected: {regime.value} (confidence: {confidence:.1f}%) - "
            f"Trend: {trend_score:.1f}, Vol: {volatility_score:.1f}, "
            f"Breadth: {breadth_score:.1f}, Corr: {correlation_score:.1f}"
        )

        return detection

    def _calculate_trend_score(self, factors: RegimeFactors) -> float:
        """
        Calculate trend score (-100 to +100).

        Positive = Bullish trend
        Negative = Bearish trend
        Near zero = No trend

        Factors:
        1. SMA position (price vs SMA 50 vs SMA 200) - 60 points
        2. ADX strength - 40 points
        """
        score = 0.0

        # SMA position component (60 points max)
        price = factors.price
        sma_50 = factors.sma_50
        sma_200 = factors.sma_200

        if price > sma_50 > sma_200:
            # Golden cross - strong bullish
            score += 60
        elif price > sma_50 and price > sma_200:
            # Above both SMAs - bullish
            score += 45
        elif price < sma_50 and sma_50 > sma_200:
            # Below 50 but 50 above 200 - weak bullish
            score += 20
        elif price < sma_50 < sma_200:
            # Death cross - strong bearish
            score -= 60
        elif price < sma_50 and price < sma_200:
            # Below both SMAs - bearish
            score -= 45
        elif price > sma_50 and sma_50 < sma_200:
            # Above 50 but 50 below 200 - weak bearish
            score -= 20

        # ADX strength component (40 points max)
        # ADX shows trend strength regardless of direction
        # Use with SMA to determine bullish/bearish strength
        adx = factors.adx
        if adx > self.adx_strong:
            # Strong trend - amplify SMA signal
            adx_multiplier = min((adx - self.adx_strong) / 25.0, 1.0)
            if score > 0:
                score += 40 * adx_multiplier
            else:
                score -= 40 * adx_multiplier
        elif adx < self.adx_weak:
            # Weak trend - reduce conviction
            score *= 0.5

        return max(min(score, 100.0), -100.0)

    def _calculate_volatility_score(self, factors: RegimeFactors) -> float:
        """
        Calculate volatility score (0 to 100).

        Lower score = Lower volatility (bullish)
        Higher score = Higher volatility (bearish/crisis)

        Factors:
        1. VIX level - 60 points
        2. Realized volatility - 40 points
        """
        score = 0.0

        # VIX component (60 points)
        vix = factors.vix
        if vix > self.vix_crisis:
            # Crisis level volatility
            score += 60
        elif vix > self.vix_elevated:
            # Elevated volatility
            score += 40 + 20 * (vix - self.vix_elevated) / (
                self.vix_crisis - self.vix_elevated
            )
        elif vix > self.vix_low:
            # Moderate volatility
            score += 20 + 20 * (vix - self.vix_low) / (self.vix_elevated - self.vix_low)
        else:
            # Low volatility
            score += 20 * vix / self.vix_low

        # Realized volatility component (40 points)
        real_vol = factors.realized_volatility
        if real_vol > self.realized_vol_high:
            score += 40
        else:
            score += 40 * (real_vol / self.realized_vol_high)

        return min(score, 100.0)

    def _calculate_breadth_score(self, factors: RegimeFactors) -> float:
        """
        Calculate market breadth score (-100 to +100).

        Positive = Bullish breadth
        Negative = Bearish breadth

        Factors:
        1. Advance-decline ratio - 50 points
        2. New highs-lows ratio - 50 points
        """
        score = 0.0

        # Advance-decline component (50 points)
        ad_ratio = factors.advance_decline_ratio
        if ad_ratio >= self.ad_bullish:
            # Strong bullish breadth
            score += 50
        elif ad_ratio > 1.0:
            # Moderate bullish breadth
            score += 50 * (ad_ratio - 1.0) / (self.ad_bullish - 1.0)
        elif ad_ratio > self.ad_bearish:
            # Neutral breadth
            score += 0
        else:
            # Bearish breadth
            score -= 50 * (self.ad_bearish - ad_ratio) / self.ad_bearish

        # New highs-lows component (50 points)
        nh_nl_ratio = factors.new_highs_lows_ratio
        if nh_nl_ratio >= self.nh_nl_bullish:
            # Strong bullish breadth
            score += 50
        elif nh_nl_ratio > 1.0:
            # Moderate bullish breadth
            score += 50 * (nh_nl_ratio - 1.0) / (self.nh_nl_bullish - 1.0)
        elif nh_nl_ratio > self.nh_nl_bearish:
            # Neutral breadth
            score += 0
        else:
            # Bearish breadth
            score -= 50 * (self.nh_nl_bearish - nh_nl_ratio) / self.nh_nl_bearish

        return max(min(score, 100.0), -100.0)

    def _calculate_correlation_score(self, factors: RegimeFactors) -> float:
        """
        Calculate correlation score (0 to 100).

        Lower score = Lower correlation (normal market)
        Higher score = Higher correlation (stress/crisis)

        High correlation indicates:
        - Crisis conditions (everything falls together)
        - Bear markets (high correlation to downside)
        - Risk-off environments
        """
        correlation = factors.correlation

        if correlation > self.corr_high:
            # High correlation - crisis/bear signal
            return 100.0
        elif correlation > self.corr_low:
            # Moderate correlation
            return 50 + 50 * (correlation - self.corr_low) / (
                self.corr_high - self.corr_low
            )
        else:
            # Low correlation - normal/bull market
            return 50 * correlation / self.corr_low

    def _classify_regime(
        self,
        trend_score: float,
        volatility_score: float,
        breadth_score: float,
        correlation_score: float,
        factors: RegimeFactors,
    ) -> tuple[MarketRegime, float]:
        """
        Classify market regime based on factor scores.

        Returns:
            Tuple of (regime, confidence_score)
        """
        # CRISIS: Extreme volatility dominates
        if volatility_score > 80 or factors.vix > self.vix_crisis:
            confidence = min(volatility_score, 100.0)
            return MarketRegime.CRISIS, confidence

        # BULL: Positive trend + low volatility + positive breadth
        bull_score = (
            max(trend_score, 0) * 0.30
            + (100 - volatility_score) * 0.25
            + max(breadth_score, 0) * 0.25
            + (100 - correlation_score) * 0.20
        )

        # BEAR: Negative trend + elevated volatility + negative breadth
        bear_score = (
            abs(min(trend_score, 0)) * 0.30
            + volatility_score * 0.25
            + abs(min(breadth_score, 0)) * 0.25
            + correlation_score * 0.20
        )

        # SIDEWAYS: Weak trend + moderate volatility
        sideways_score = (
            (100 - abs(trend_score)) * 0.40
            + (50 - abs(volatility_score - 50)) * 0.30
            + (50 - abs(breadth_score)) * 0.30
        )

        # Determine regime
        scores = {
            MarketRegime.BULL: bull_score,
            MarketRegime.BEAR: bear_score,
            MarketRegime.SIDEWAYS: sideways_score,
        }

        regime = max(scores, key=scores.get)
        confidence = scores[regime]

        # Adjust confidence based on factor agreement
        factor_agreement = self._calculate_factor_agreement(
            trend_score, volatility_score, breadth_score, correlation_score
        )
        confidence = confidence * (0.7 + 0.3 * factor_agreement)

        return regime, min(confidence, 100.0)

    def _calculate_factor_agreement(
        self,
        trend_score: float,
        volatility_score: float,
        breadth_score: float,
        correlation_score: float,
    ) -> float:
        """
        Calculate how well factors agree (0-1).

        Higher agreement = Higher confidence in regime
        """
        # Normalize all scores to 0-1 scale
        # Bull-aligned signals
        bull_signals = [
            (trend_score + 100) / 200,  # Trend
            (100 - volatility_score) / 100,  # Low volatility
            (breadth_score + 100) / 200,  # Breadth
            (100 - correlation_score) / 100,  # Low correlation
        ]

        # Calculate standard deviation (lower = more agreement)
        std = np.std(bull_signals)

        # Convert to agreement score (0-1)
        # std of 0 = perfect agreement = 1.0
        # std of 0.5 = no agreement = 0.0
        agreement = max(0, 1 - 2 * std)

        return agreement

    def detect_regime_series(
        self, factors_list: List[RegimeFactors]
    ) -> List[RegimeDetection]:
        """
        Detect regime for a series of factor data points.

        Args:
            factors_list: List of regime factors over time

        Returns:
            List of regime detections
        """
        detections = []

        for factors in factors_list:
            detection = self.detect_regime(factors)
            detections.append(detection)

        logger.info(f"Processed {len(detections)} regime detections")

        return detections

    def validate_historical_accuracy(
        self, detections: List[RegimeDetection], actual_regimes: List[MarketRegime]
    ) -> float:
        """
        Validate detection accuracy against known historical regimes.

        Args:
            detections: List of regime detections
            actual_regimes: List of actual known regimes

        Returns:
            Accuracy percentage (0-100)
        """
        if len(detections) != len(actual_regimes):
            raise ValueError("Detection and actual regime lists must be same length")

        if len(detections) == 0:
            return 0.0

        correct = sum(
            1 for det, actual in zip(detections, actual_regimes) if det.regime == actual
        )

        accuracy = (correct / len(detections)) * 100

        logger.info(
            f"Historical validation: {correct}/{len(detections)} correct "
            f"({accuracy:.1f}% accuracy)"
        )

        return accuracy
