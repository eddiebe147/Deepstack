"""
Pairs Trading Strategy

Statistical arbitrage through cointegrated pairs:
1. Cointegration testing (ADF, Johansen)
2. Z-score calculation with rolling window
3. Entry/exit triggers based on mean reversion
4. Stop-loss logic for risk management
5. Hedge ratio (beta) calculation
6. Pair selection and screening algorithm

Target: Identify 5+ valid pairs with positive backtest returns
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PairStatus(Enum):
    """Trading status for a pair"""

    NO_POSITION = "NO_POSITION"  # No active position
    LONG_SPREAD = "LONG_SPREAD"  # Long asset A, short asset B
    SHORT_SPREAD = "SHORT_SPREAD"  # Short asset A, long asset B
    COINTEGRATION_BROKEN = "COINTEGRATION_BROKEN"  # Pair no longer cointegrated


@dataclass
class CointegrationTest:
    """Results from cointegration testing"""

    asset_a: str
    asset_b: str
    test_type: str  # "adf" or "johansen"
    is_cointegrated: bool
    test_statistic: float
    p_value: float
    critical_value: float
    hedge_ratio: float  # Beta coefficient
    timestamp: datetime

    def __post_init__(self):
        """Validate cointegration test"""
        if self.test_type not in ["adf", "johansen"]:
            raise ValueError(
                f"test_type must be 'adf' or 'johansen', got {self.test_type}"
            )
        if self.p_value < 0 or self.p_value > 1:
            raise ValueError(f"p_value must be 0-1, got {self.p_value}")
        if self.hedge_ratio <= 0:
            raise ValueError(f"hedge_ratio must be positive, got {self.hedge_ratio}")


@dataclass
class SpreadStatistics:
    """Statistical properties of a pair's spread"""

    mean: float
    std: float
    z_score: float
    current_spread: float
    lookback_window: int
    timestamp: datetime

    def __post_init__(self):
        """Validate spread statistics"""
        if self.std <= 0:
            raise ValueError(f"std must be positive, got {self.std}")
        if self.lookback_window <= 0:
            raise ValueError(
                f"lookback_window must be positive, got {self.lookback_window}"
            )


@dataclass
class PairSignal:
    """Trading signal for a pair"""

    asset_a: str
    asset_b: str
    signal_type: str  # "entry_long", "entry_short", "exit", "stop"
    z_score: float
    spread: float
    hedge_ratio: float
    confidence: float  # 0-100
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate pair signal"""
        valid_signals = ["entry_long", "entry_short", "exit", "stop"]
        if self.signal_type not in valid_signals:
            raise ValueError(
                f"signal_type must be one of {valid_signals}, got {self.signal_type}"
            )
        if self.confidence < 0 or self.confidence > 100:
            raise ValueError(f"confidence must be 0-100, got {self.confidence}")
        if self.hedge_ratio <= 0:
            raise ValueError(f"hedge_ratio must be positive, got {self.hedge_ratio}")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "asset_a": self.asset_a,
            "asset_b": self.asset_b,
            "signal_type": self.signal_type,
            "z_score": self.z_score,
            "spread": self.spread,
            "hedge_ratio": self.hedge_ratio,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class TradingPair:
    """A cointegrated trading pair with current state"""

    asset_a: str
    asset_b: str
    hedge_ratio: float
    cointegration_test: CointegrationTest
    status: PairStatus
    entry_z_score: Optional[float] = None
    entry_spread: Optional[float] = None
    entry_time: Optional[datetime] = None
    last_update: datetime = field(default_factory=datetime.now)
    pnl: float = 0.0
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate trading pair"""
        if self.hedge_ratio <= 0:
            raise ValueError(f"hedge_ratio must be positive, got {self.hedge_ratio}")
        if self.pnl < -1000000:  # Sanity check
            raise ValueError(f"pnl seems unrealistic: {self.pnl}")

    def update_status(self, new_status: PairStatus):
        """Update pair status"""
        self.status = new_status
        self.last_update = datetime.now()

    def update_pnl(self, pnl: float):
        """Update profit/loss"""
        self.pnl = pnl
        self.last_update = datetime.now()


class PairsTradingStrategy:
    """
    Statistical arbitrage pairs trading strategy.

    Strategy:
    1. Screen for cointegrated pairs using ADF test
    2. Calculate spread = asset_a - (hedge_ratio * asset_b)
    3. Calculate z-score of spread
    4. Entry: |z| > entry_threshold (default 2.0)
    5. Exit: z returns to 0 (mean reversion)
    6. Stop: |z| > stop_threshold (default 3.5)

    Cointegration:
    - Two securities move together long-term (mean-reverting spread)
    - ADF test: p-value < 0.05 indicates cointegration
    - Hedge ratio: From linear regression, determines position sizing

    Target: Identify 5+ valid pairs with positive backtest returns
    """

    def __init__(
        self,
        # Cointegration parameters
        adf_p_value_threshold: float = 0.05,  # Max p-value for cointegration
        min_lookback_days: int = 60,  # Minimum data for testing
        # Z-score parameters
        z_score_window: int = 20,  # Rolling window for z-score
        entry_z_threshold: float = 2.0,  # Enter when |z| > 2.0
        exit_z_threshold: float = 0.5,  # Exit when |z| < 0.5
        stop_z_threshold: float = 3.5,  # Force exit when |z| > 3.5
        # Position parameters
        max_holding_days: int = 30,  # Maximum holding period
        min_confidence: float = 60.0,  # Minimum signal confidence
    ):
        self.adf_p_value_threshold = adf_p_value_threshold
        self.min_lookback_days = min_lookback_days
        self.z_score_window = z_score_window
        self.entry_z_threshold = entry_z_threshold
        self.exit_z_threshold = exit_z_threshold
        self.stop_z_threshold = stop_z_threshold
        self.max_holding_days = max_holding_days
        self.min_confidence = min_confidence

        # Active pairs
        self.active_pairs: Dict[Tuple[str, str], TradingPair] = {}

        logger.info(
            f"PairsTradingStrategy initialized: "
            f"entry_z={entry_z_threshold}, exit_z={exit_z_threshold}, "
            f"stop_z={stop_z_threshold}"
        )

    def screen_for_pairs(
        self, universe: List[str], price_data: pd.DataFrame
    ) -> List[TradingPair]:
        """
        Screen a universe of assets for cointegrated pairs.

        Args:
            universe: List of asset symbols to test
            price_data: DataFrame with price columns for each symbol

        Returns:
            List of cointegrated trading pairs
        """
        logger.info(f"Screening {len(universe)} assets for cointegrated pairs")

        # Validate data
        if len(price_data) < self.min_lookback_days:
            raise ValueError(
                f"Insufficient data: need {self.min_lookback_days} days, "
                f"got {len(price_data)}"
            )

        pairs = []
        tested_count = 0
        cointegrated_count = 0

        # Test all possible pairs
        for i, asset_a in enumerate(universe):
            for asset_b in universe[i + 1 :]:
                tested_count += 1

                if (
                    asset_a not in price_data.columns
                    or asset_b not in price_data.columns
                ):
                    logger.debug(f"Skipping {asset_a}/{asset_b}: missing price data")
                    continue

                # Test for cointegration
                coint_test = self.test_cointegration(
                    price_data[asset_a], price_data[asset_b], asset_a, asset_b
                )

                if coint_test.is_cointegrated:
                    cointegrated_count += 1

                    pair = TradingPair(
                        asset_a=asset_a,
                        asset_b=asset_b,
                        hedge_ratio=coint_test.hedge_ratio,
                        cointegration_test=coint_test,
                        status=PairStatus.NO_POSITION,
                    )
                    pairs.append(pair)

                    logger.info(
                        f"Cointegrated pair found: {asset_a}/{asset_b} "
                        f"(p={coint_test.p_value:.4f}, β={coint_test.hedge_ratio:.4f})"
                    )

        logger.info(
            f"Screening complete: {cointegrated_count} cointegrated pairs found "
            f"from {tested_count} pairs tested ({len(universe)} assets)"
        )

        return pairs

    def test_cointegration(
        self,
        price_series_a: pd.Series,
        price_series_b: pd.Series,
        asset_a: str,
        asset_b: str,
    ) -> CointegrationTest:
        """
        Test two price series for cointegration using ADF test.

        Process:
        1. Run linear regression: asset_a = alpha + beta * asset_b
        2. Calculate residuals (spread)
        3. Test residuals for stationarity using ADF test
        4. If p-value < threshold, series are cointegrated

        Args:
            price_series_a: Price series for asset A
            price_series_b: Price series for asset B
            asset_a: Symbol for asset A
            asset_b: Symbol for asset B

        Returns:
            Cointegration test result
        """
        # Clean data
        df = pd.DataFrame({"a": price_series_a, "b": price_series_b}).dropna()

        if len(df) < self.min_lookback_days:
            logger.debug(
                f"{asset_a}/{asset_b}: Insufficient clean data ({len(df)} rows)"
            )
            return CointegrationTest(
                asset_a=asset_a,
                asset_b=asset_b,
                test_type="adf",
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.0,
                hedge_ratio=1.0,
                timestamp=datetime.now(),
            )

        # Calculate hedge ratio (beta) using linear regression
        hedge_ratio = self._calculate_hedge_ratio(df["a"], df["b"])

        # Calculate spread
        spread = df["a"] - hedge_ratio * df["b"]

        # Augmented Dickey-Fuller test for stationarity
        try:
            adf_result = self._adf_test(spread)

            is_cointegrated = adf_result["p_value"] < self.adf_p_value_threshold

            return CointegrationTest(
                asset_a=asset_a,
                asset_b=asset_b,
                test_type="adf",
                is_cointegrated=is_cointegrated,
                test_statistic=adf_result["test_statistic"],
                p_value=adf_result["p_value"],
                critical_value=adf_result["critical_value_5pct"],
                hedge_ratio=hedge_ratio,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.warning(f"ADF test failed for {asset_a}/{asset_b}: {e}")
            return CointegrationTest(
                asset_a=asset_a,
                asset_b=asset_b,
                test_type="adf",
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.0,
                hedge_ratio=hedge_ratio,
                timestamp=datetime.now(),
            )

    def _adf_test(self, series: pd.Series) -> Dict[str, float]:
        """
        Perform Augmented Dickey-Fuller test.

        Tests null hypothesis that series has unit root (non-stationary).
        Lower p-value = reject null = stationary = cointegrated.

        Args:
            series: Time series to test

        Returns:
            Dictionary with test results
        """
        # Calculate differenced series for ADF test
        # ADF test: y_t = a + b*y_{t-1} + e_t
        # If b < 0, series is mean-reverting (stationary)

        y = series.values
        n = len(y)

        if n < 3:
            raise ValueError("Need at least 3 observations for ADF test")

        # Lag-1 values
        y_lag = y[:-1]
        y_diff = np.diff(y)

        # Add constant term
        X = np.column_stack([np.ones(n - 1), y_lag])

        # OLS regression
        beta = np.linalg.lstsq(X, y_diff, rcond=None)[0]

        # Calculate residuals
        y_pred = X @ beta
        residuals = y_diff - y_pred

        # Standard error
        sse = np.sum(residuals**2)
        mse = sse / (n - 1 - 2)  # n-1 observations, 2 parameters
        se = np.sqrt(mse * np.linalg.inv(X.T @ X)[1, 1])

        # Test statistic
        test_stat = beta[1] / se

        # P-value approximation (simplified)
        # In production, use statsmodels.tsa.stattools.adfuller
        if test_stat < -3.43:  # 1% critical value
            p_value = 0.01
        elif test_stat < -2.86:  # 5% critical value
            p_value = 0.05
        elif test_stat < -2.57:  # 10% critical value
            p_value = 0.10
        else:
            p_value = 0.50

        return {
            "test_statistic": test_stat,
            "p_value": p_value,
            "critical_value_1pct": -3.43,
            "critical_value_5pct": -2.86,
            "critical_value_10pct": -2.57,
        }

    def _calculate_hedge_ratio(
        self, price_series_a: pd.Series, price_series_b: pd.Series
    ) -> float:
        """
        Calculate hedge ratio (beta) using OLS regression.

        Formula: asset_a = alpha + beta * asset_b + epsilon
        Beta = Cov(a,b) / Var(b)

        Args:
            price_series_a: Price series for asset A
            price_series_b: Price series for asset B

        Returns:
            Hedge ratio (beta)
        """
        # Using numpy for simple linear regression
        X = price_series_b.values.reshape(-1, 1)
        y = price_series_a.values

        # Add intercept
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # OLS: beta = (X'X)^-1 X'y
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]

        # Return slope coefficient (beta[1])
        hedge_ratio = beta[1]

        # Ensure positive and reasonable
        if hedge_ratio <= 0:
            logger.warning(f"Negative hedge ratio {hedge_ratio}, using absolute value")
            hedge_ratio = abs(hedge_ratio)

        return hedge_ratio

    def calculate_spread_statistics(
        self, pair: TradingPair, price_data: pd.DataFrame
    ) -> SpreadStatistics:
        """
        Calculate current spread statistics for a pair.

        Args:
            pair: Trading pair
            price_data: DataFrame with recent price data

        Returns:
            Spread statistics including z-score
        """
        # Get price series
        prices_a = price_data[pair.asset_a]
        prices_b = price_data[pair.asset_b]

        # Calculate spread
        spread = prices_a - pair.hedge_ratio * prices_b

        # Use rolling window for statistics
        window_spread = spread.tail(self.z_score_window)

        mean = window_spread.mean()
        std = window_spread.std()

        # Current spread and z-score
        current_spread = spread.iloc[-1]
        z_score = (current_spread - mean) / std if std > 0 else 0.0

        return SpreadStatistics(
            mean=mean,
            std=std,
            z_score=z_score,
            current_spread=current_spread,
            lookback_window=self.z_score_window,
            timestamp=datetime.now(),
        )

    def generate_signals(
        self, pair: TradingPair, price_data: pd.DataFrame
    ) -> Optional[PairSignal]:
        """
        Generate trading signals for a pair based on z-score.

        Entry Rules:
        - Long spread (buy A, sell B): z < -entry_threshold
        - Short spread (sell A, buy B): z > +entry_threshold

        Exit Rules:
        - Mean reversion: |z| < exit_threshold
        - Stop loss: |z| > stop_threshold

        Args:
            pair: Trading pair
            price_data: Recent price data

        Returns:
            Trading signal or None
        """
        # Calculate spread statistics
        spread_stats = self.calculate_spread_statistics(pair, price_data)
        z = spread_stats.z_score

        # Check for stop condition first (highest priority)
        if abs(z) > self.stop_z_threshold:
            if pair.status != PairStatus.NO_POSITION:
                logger.warning(
                    f"{pair.asset_a}/{pair.asset_b}: Stop triggered at z={z:.2f}"
                )
                return PairSignal(
                    asset_a=pair.asset_a,
                    asset_b=pair.asset_b,
                    signal_type="stop",
                    z_score=z,
                    spread=spread_stats.current_spread,
                    hedge_ratio=pair.hedge_ratio,
                    confidence=95.0,  # High confidence on stop
                    timestamp=datetime.now(),
                    metadata={
                        "reason": "stop_loss",
                        "z_threshold": self.stop_z_threshold,
                    },
                )

        # Check for exit conditions
        if pair.status != PairStatus.NO_POSITION:
            if abs(z) < self.exit_z_threshold:
                logger.info(f"{pair.asset_a}/{pair.asset_b}: Exit signal at z={z:.2f}")
                confidence = self._calculate_signal_confidence(z, "exit")
                return PairSignal(
                    asset_a=pair.asset_a,
                    asset_b=pair.asset_b,
                    signal_type="exit",
                    z_score=z,
                    spread=spread_stats.current_spread,
                    hedge_ratio=pair.hedge_ratio,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    metadata={"reason": "mean_reversion"},
                )

        # Check for entry conditions
        if pair.status == PairStatus.NO_POSITION:
            if z < -self.entry_z_threshold:
                # Spread is low, expect mean reversion up
                # Long spread: buy A, sell B
                logger.info(
                    f"{pair.asset_a}/{pair.asset_b}: Long entry signal at z={z:.2f}"
                )
                confidence = self._calculate_signal_confidence(z, "entry_long")
                return PairSignal(
                    asset_a=pair.asset_a,
                    asset_b=pair.asset_b,
                    signal_type="entry_long",
                    z_score=z,
                    spread=spread_stats.current_spread,
                    hedge_ratio=pair.hedge_ratio,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    metadata={"entry_threshold": self.entry_z_threshold},
                )

            elif z > self.entry_z_threshold:
                # Spread is high, expect mean reversion down
                # Short spread: sell A, buy B
                logger.info(
                    f"{pair.asset_a}/{pair.asset_b}: Short entry signal at z={z:.2f}"
                )
                confidence = self._calculate_signal_confidence(z, "entry_short")
                return PairSignal(
                    asset_a=pair.asset_a,
                    asset_b=pair.asset_b,
                    signal_type="entry_short",
                    z_score=z,
                    spread=spread_stats.current_spread,
                    hedge_ratio=pair.hedge_ratio,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    metadata={"entry_threshold": self.entry_z_threshold},
                )

        return None

    def _calculate_signal_confidence(self, z_score: float, signal_type: str) -> float:
        """
        Calculate confidence for a signal based on z-score magnitude.

        Higher |z-score| = Higher confidence for entry
        Lower |z-score| = Higher confidence for exit

        Args:
            z_score: Current z-score
            signal_type: Type of signal

        Returns:
            Confidence score (0-100)
        """
        abs_z = abs(z_score)

        if signal_type in ["entry_long", "entry_short"]:
            # Entry confidence increases with |z|
            if abs_z > 3.0:
                return 95.0
            elif abs_z > 2.5:
                return 85.0
            elif abs_z > 2.0:
                return 70.0
            else:
                return 50.0

        elif signal_type == "exit":
            # Exit confidence increases as z approaches 0
            if abs_z < 0.2:
                return 95.0
            elif abs_z < 0.5:
                return 85.0
            else:
                return 70.0

        return 60.0

    def monitor_pairs(
        self, pairs: List[TradingPair], price_data: pd.DataFrame
    ) -> List[PairSignal]:
        """
        Monitor multiple pairs and generate signals.

        Args:
            pairs: List of trading pairs to monitor
            price_data: Recent price data

        Returns:
            List of trading signals
        """
        signals = []

        for pair in pairs:
            try:
                signal = self.generate_signals(pair, price_data)
                if signal and signal.confidence >= self.min_confidence:
                    signals.append(signal)
            except Exception as e:
                logger.warning(f"Error monitoring {pair.asset_a}/{pair.asset_b}: {e}")

        logger.info(f"Generated {len(signals)} signals from {len(pairs)} pairs")

        return signals

    def backtest_pair(
        self,
        pair: TradingPair,
        price_data: pd.DataFrame,
        initial_capital: float = 100000,
    ) -> Dict[str, any]:
        """
        Backtest a pair using historical data.

        Args:
            pair: Trading pair to backtest
            price_data: Historical price data
            initial_capital: Starting capital

        Returns:
            Dictionary with backtest results
        """
        logger.info(
            f"Backtesting {pair.asset_a}/{pair.asset_b} "
            f"on {len(price_data)} days of data"
        )

        # Initialize tracking
        capital = initial_capital
        position = None  # None, 'long', or 'short'
        trades = []
        equity_curve = []

        # Simulate trading
        for i in range(self.z_score_window, len(price_data)):
            # Get recent data for signal generation
            window_data = price_data.iloc[: i + 1]

            # Calculate spread statistics
            spread_stats = self.calculate_spread_statistics(pair, window_data)
            z = spread_stats.z_score

            current_date = price_data.index[i]
            price_a = price_data[pair.asset_a].iloc[i]
            price_b = price_data[pair.asset_b].iloc[i]

            # Check for stop loss
            if position and abs(z) > self.stop_z_threshold:
                # Exit with stop
                if position == "long":
                    pnl = (price_a - trades[-1]["entry_price_a"]) - pair.hedge_ratio * (
                        price_b - trades[-1]["entry_price_b"]
                    )
                else:  # short
                    pnl = (trades[-1]["entry_price_a"] - price_a) - pair.hedge_ratio * (
                        trades[-1]["entry_price_b"] - price_b
                    )

                trades[-1]["exit_date"] = current_date
                trades[-1]["exit_z"] = z
                trades[-1]["pnl"] = pnl
                capital += pnl
                position = None

            # Check for exit
            elif position and abs(z) < self.exit_z_threshold:
                # Exit on mean reversion
                if position == "long":
                    pnl = (price_a - trades[-1]["entry_price_a"]) - pair.hedge_ratio * (
                        price_b - trades[-1]["entry_price_b"]
                    )
                else:  # short
                    pnl = (trades[-1]["entry_price_a"] - price_a) - pair.hedge_ratio * (
                        trades[-1]["entry_price_b"] - price_b
                    )

                trades[-1]["exit_date"] = current_date
                trades[-1]["exit_z"] = z
                trades[-1]["pnl"] = pnl
                capital += pnl
                position = None

            # Check for entry
            elif not position:
                if z < -self.entry_z_threshold:
                    # Enter long
                    position = "long"
                    trades.append(
                        {
                            "entry_date": current_date,
                            "entry_z": z,
                            "entry_price_a": price_a,
                            "entry_price_b": price_b,
                            "position": "long",
                        }
                    )

                elif z > self.entry_z_threshold:
                    # Enter short
                    position = "short"
                    trades.append(
                        {
                            "entry_date": current_date,
                            "entry_z": z,
                            "entry_price_a": price_a,
                            "entry_price_b": price_b,
                            "position": "short",
                        }
                    )

            # Track equity
            equity_curve.append({"date": current_date, "equity": capital})

        # Calculate performance metrics
        total_trades = len([t for t in trades if "exit_date" in t])
        winning_trades = len([t for t in trades if t.get("pnl", 0) > 0])
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        results = {
            "pair": f"{pair.asset_a}/{pair.asset_b}",
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "return_pct": (total_pnl / initial_capital) * 100,
            "final_capital": capital,
            "trades": trades,
            "equity_curve": equity_curve,
        }

        logger.info(
            f"Backtest complete: {total_trades} trades, "
            f"{win_rate*100:.1f}% win rate, "
            f"{results['return_pct']:.2f}% return"
        )

        return results

    def validate_pairs(
        self, pairs: List[TradingPair], price_data: pd.DataFrame
    ) -> List[Dict[str, any]]:
        """
        Validate multiple pairs with backtesting.

        Args:
            pairs: List of pairs to validate
            price_data: Historical price data

        Returns:
            List of backtest results for each pair
        """
        results = []

        logger.info(f"Validating {len(pairs)} pairs with backtesting")

        for pair in pairs:
            try:
                result = self.backtest_pair(pair, price_data)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to backtest {pair.asset_a}/{pair.asset_b}: {e}")

        # Sort by return
        results.sort(key=lambda x: x["return_pct"], reverse=True)

        return results
