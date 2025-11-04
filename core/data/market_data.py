"""
Market Data Manager - Handles market data collection and caching

Provides unified interface for real-time and historical market data
from multiple sources (IBKR, Yahoo Finance, Alpha Vantage, etc.)
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yfinance as yf

from ..config import Config

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    """Real-time quote data."""

    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    volume: Optional[int]
    timestamp: datetime
    source: str


@dataclass
class MarketData:
    """Historical market data."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketDataManager:
    """
    Manages market data collection, caching, and distribution.

    Supports multiple data sources:
    - Interactive Brokers (live)
    - Yahoo Finance (free historical)
    - Alpha Vantage (premium real-time)
    - Local caching for performance
    """

    def __init__(self, config: Config):
        """
        Initialize market data manager.

        Args:
            config: DeepStack configuration
        """
        self.config = config
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Data source priorities
        self.sources = ["ibkr", "yfinance", "cache"]

        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 1000

        logger.info("MarketDataManager initialized")

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get current quote for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Quote object or None
        """
        # Try sources in priority order
        for source in self.sources:
            try:
                if source == "ibkr":
                    quote = await self._get_ibkr_quote(symbol)
                    if quote:
                        return quote

                elif source == "yfinance":
                    quote = await self._get_yfinance_quote(symbol)
                    if quote:
                        return quote

                elif source == "cache":
                    quote = self._get_cached_quote(symbol)
                    if quote:
                        return quote

            except Exception as e:
                logger.warning(f"Error getting quote from {source} for {symbol}: {e}")
                continue

        logger.error(f"Could not get quote for {symbol} from any source")
        return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[MarketData]:
        """
        Get historical data for symbol.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Data interval ('1d', '1h', '5m', etc.)

        Returns:
            List of MarketData objects
        """
        # Try sources in priority order
        for source in self.sources:
            try:
                if source == "ibkr":
                    data = await self._get_ibkr_historical(
                        symbol, start_date, end_date, interval
                    )
                    if data:
                        return data

                elif source == "yfinance":
                    data = await self._get_yfinance_historical(
                        symbol, start_date, end_date, interval
                    )
                    if data:
                        return data

                elif source == "cache":
                    data = self._get_cached_historical(
                        symbol, start_date, end_date, interval
                    )
                    if data:
                        return data

            except Exception as e:
                logger.warning(
                    f"Error getting historical data from {source} for {symbol}: {e}"
                )
                continue

        logger.error(f"Could not get historical data for {symbol} from any source")
        return []

    async def _get_ibkr_quote(self, symbol: str) -> Optional[Quote]:
        """Get quote from IBKR."""
        # This would integrate with IBKRClient
        # For now, return None to fall back to other sources
        return None

    async def _get_yfinance_quote(self, symbol: str) -> Optional[Quote]:
        """Get quote from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info:
                return None

            return Quote(
                symbol=symbol,
                bid=info.get("bid"),
                ask=info.get("ask"),
                last=info.get("regularMarketPrice"),
                volume=info.get("regularMarketVolume"),
                timestamp=datetime.now(),
                source="yfinance",
            )

        except Exception as e:
            logger.error(f"Error getting Yahoo Finance quote for {symbol}: {e}")
            return None

    def _get_cached_quote(self, symbol: str) -> Optional[Quote]:
        """Get cached quote."""
        try:
            cache_file = self.cache_dir / f"quote_{symbol}.json"

            if not cache_file.exists():
                return None

            # Check if cache is still valid
            if (
                datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            ).seconds > self.cache_ttl:
                cache_file.unlink()  # Remove stale cache
                return None

            with open(cache_file, "r") as f:
                data = json.load(f)

            return Quote(
                symbol=data["symbol"],
                bid=data.get("bid"),
                ask=data.get("ask"),
                last=data.get("last"),
                volume=data.get("volume"),
                timestamp=datetime.fromisoformat(data["timestamp"]),
                source="cache",
            )

        except Exception as e:
            logger.error(f"Error reading cached quote for {symbol}: {e}")
            return None

    async def _get_ibkr_historical(
        self, symbol: str, start_date: datetime, end_date: datetime, interval: str
    ) -> List[MarketData]:
        """Get historical data from IBKR."""
        # This would integrate with IBKRClient
        return []

    async def _get_yfinance_historical(
        self, symbol: str, start_date: datetime, end_date: datetime, interval: str
    ) -> List[MarketData]:
        """Get historical data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval=interval)

            if hist.empty:
                return []

            data_points = []
            for timestamp, row in hist.iterrows():
                data_points.append(
                    MarketData(
                        symbol=symbol,
                        timestamp=timestamp.to_pydatetime(),
                        open=row["Open"],
                        high=row["High"],
                        low=row["Low"],
                        close=row["Close"],
                        volume=int(row["Volume"]),
                    )
                )

            return data_points

        except Exception as e:
            logger.error(
                f"Error getting Yahoo Finance historical data for {symbol}: {e}"
            )
            return []

    def _get_cached_historical(
        self, symbol: str, start_date: datetime, end_date: datetime, interval: str
    ) -> List[MarketData]:
        """Get cached historical data."""
        try:
            cache_key = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{interval}"
            cache_file = self.cache_dir / f"historical_{cache_key}.json"

            if not cache_file.exists():
                return []

            # Check if cache is still valid
            if (
                datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            ).seconds > self.cache_ttl:
                cache_file.unlink()
                return []

            with open(cache_file, "r") as f:
                data = json.load(f)

            market_data = []
            for item in data:
                market_data.append(
                    MarketData(
                        symbol=item["symbol"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        open=item["open"],
                        high=item["high"],
                        low=item["low"],
                        close=item["close"],
                        volume=item["volume"],
                    )
                )

            return market_data

        except Exception as e:
            logger.error(f"Error reading cached historical data for {symbol}: {e}")
            return []

    def cache_quote(self, quote: Quote):
        """Cache a quote for future use."""
        try:
            cache_file = self.cache_dir / f"quote_{quote.symbol}.json"

            data = {
                "symbol": quote.symbol,
                "bid": quote.bid,
                "ask": quote.ask,
                "last": quote.last,
                "volume": quote.volume,
                "timestamp": quote.timestamp.isoformat(),
                "source": quote.source,
            }

            with open(cache_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            logger.error(f"Error caching quote for {quote.symbol}: {e}")

    def cache_historical_data(self, symbol: str, data: List[MarketData], interval: str):
        """Cache historical data."""
        try:
            if not data:
                return

            start_date = min(d.timestamp for d in data)
            end_date = max(d.timestamp for d in data)

            cache_key = f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{interval}"
            cache_file = self.cache_dir / f"historical_{cache_key}.json"

            serialized_data = []
            for item in data:
                serialized_data.append(
                    {
                        "symbol": item.symbol,
                        "timestamp": item.timestamp.isoformat(),
                        "open": item.open,
                        "high": item.high,
                        "low": item.low,
                        "close": item.close,
                        "volume": item.volume,
                    }
                )

            with open(cache_file, "w") as f:
                json.dump(serialized_data, f)

        except Exception as e:
            logger.error(f"Error caching historical data for {symbol}: {e}")

    def clear_cache(self):
        """Clear all cached data."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Market data cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "file_count": len(cache_files),
                "total_size_bytes": total_size,
                "cache_dir": str(self.cache_dir),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "file_count": 0,
                "total_size_bytes": 0,
                "cache_dir": str(self.cache_dir),
            }
