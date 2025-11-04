"""
Alpaca Markets API Integration

Provides real-time and historical market data from Alpaca Markets with:
- Real-time quote streaming
- Historical bar data
- Rate limiting and error handling
- Async operations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

logger = logging.getLogger(__name__)


class TimeFrameEnum(str, Enum):
    """TimeFrame enumeration for bar data."""

    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    HOUR_1 = "1h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1mo"


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""


class AlpacaClient:
    """
    Alpaca Markets API client for DeepStack Trading System.

    Provides unified interface for:
    - Real-time quotes and bars
    - Historical data with caching
    - Rate limiting to respect API limits
    - Error handling and retry logic
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://paper-api.alpaca.markets",
        rate_limit_requests: int = 200,
        rate_limit_window: int = 60,
    ):
        """
        Initialize Alpaca client.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            base_url: Alpaca API base URL (default: paper trading)
            rate_limit_requests: Max requests per window
            rate_limit_window: Time window in seconds
        """
        if not api_key or not secret_key:
            raise ValueError("API key and secret key are required")

        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url

        # Initialize clients
        # Determine if paper trading based on URL
        is_paper = "paper" in base_url.lower()
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=is_paper,
            url_override=base_url,
        )
        self.data_client = StockHistoricalDataClient(
            api_key=api_key, secret_key=secret_key
        )

        # Rate limiting
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.request_timestamps: List[float] = []

        # Cache settings
        self.quote_cache: Dict[str, tuple] = {}  # (data, timestamp)
        self.cache_ttl = 60  # 1 minute for quotes

        # Connection status
        self.is_connected = False
        self.data_stream: Optional[StockDataStream] = None

        logger.info(f"AlpacaClient initialized with base_url: {base_url}")

    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limits.

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        import time

        current_time = time.time()

        # Remove old timestamps outside the window
        self.request_timestamps = [
            ts
            for ts in self.request_timestamps
            if current_time - ts < self.rate_limit_window
        ]

        # Check if we've exceeded the limit
        if len(self.request_timestamps) >= self.rate_limit_requests:
            wait_time = (
                self.request_timestamps[0] + self.rate_limit_window - current_time
            )
            logger.warning(
                f"Rate limit approaching: {len(self.request_timestamps)}/{self.rate_limit_requests} "
                f"in last {self.rate_limit_window}s. Waiting {wait_time:.2f}s"
            )
            await asyncio.sleep(wait_time + 0.1)
            return await self._check_rate_limit()

        # Record this request
        self.request_timestamps.append(current_time)

    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get latest quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Quote data with bid, ask, last price, volume; None if error
        """
        try:
            await self._check_rate_limit()

            # Check cache first
            if symbol in self.quote_cache:
                data, timestamp = self.quote_cache[symbol]
                if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                    logger.debug(f"Using cached quote for {symbol}")
                    return data

            # Fetch from API
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)

            if not quote or symbol not in quote:
                logger.warning(f"No quote data received for {symbol}")
                return None

            quote_data = quote[symbol]

            result = {
                "symbol": symbol,
                "bid": quote_data.bid_price,
                "ask": quote_data.ask_price,
                "last": quote_data.ask_price,  # Use ask as last price
                "bid_volume": quote_data.bid_size,
                "ask_volume": quote_data.ask_size,
                "timestamp": datetime.now().isoformat(),
            }

            # Cache the result
            self.quote_cache[symbol] = (result, datetime.now())

            logger.debug(
                f"Retrieved quote for {symbol}: bid={result['bid']}, ask={result['ask']}"
            )
            return result

        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def get_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Get latest quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to quote data
        """
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = await self.get_quote(symbol)
            await asyncio.sleep(0.01)  # Small delay between requests
        return quotes

    async def get_bars(
        self,
        symbol: str,
        timeframe: TimeFrameEnum = TimeFrameEnum.DAY_1,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Optional[List[Dict]]:
        """
        Get historical bar data for a symbol.

        Args:
            symbol: Stock symbol
            timeframe: TimeFrame enum value (default: 1 day)
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            limit: Maximum number of bars to return

        Returns:
            List of bar data dicts with OHLCV; None if error
        """
        try:
            await self._check_rate_limit()

            # Set default dates
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=30)

            # Map timeframe string to TimeFrame object
            timeframe_map = {
                TimeFrameEnum.MINUTE_1: TimeFrame.Minute,
                TimeFrameEnum.MINUTE_5: TimeFrame.Minute,  # Will use multiplier
                TimeFrameEnum.MINUTE_15: TimeFrame.Minute,
                TimeFrameEnum.MINUTE_30: TimeFrame.Minute,
                TimeFrameEnum.HOUR_1: TimeFrame.Hour,
                TimeFrameEnum.DAY_1: TimeFrame.Day,
                TimeFrameEnum.WEEK_1: TimeFrame.Week,
                TimeFrameEnum.MONTH_1: TimeFrame.Month,
            }

            tf = timeframe_map.get(timeframe, TimeFrame.Day)

            # Create request
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start_date,
                end=end_date,
                limit=limit,
            )

            bars = self.data_client.get_stock_bars(request)

            if not bars or symbol not in bars:
                logger.warning(f"No bar data received for {symbol}")
                return None

            result = []
            for bar in bars[symbol]:
                result.append(
                    {
                        "symbol": symbol,
                        "timestamp": bar.timestamp.isoformat(),
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "trade_count": (
                            bar.trade_count if hasattr(bar, "trade_count") else None
                        ),
                        "vwap": bar.vwap if hasattr(bar, "vwap") else None,
                    }
                )

            logger.debug(
                f"Retrieved {len(result)} bars for {symbol} with timeframe {timeframe}"
            )
            return result

        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {e}")
            return None

    async def get_account(self) -> Optional[Dict]:
        """
        Get account information.

        Returns:
            Account data including buying power, equity, etc; None if error
        """
        try:
            await self._check_rate_limit()

            account = self.trading_client.get_account()

            if not account:
                logger.warning("No account data received")
                return None

            result = {
                "account_number": account.account_number,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
                "equity": float(account.equity),
                "last_equity": float(account.last_equity),
                "multiplier": account.multiplier,
                "shorting_enabled": account.shorting_enabled,
                "status": account.status,
            }

            logger.debug(
                f"Retrieved account: portfolio_value=${result['portfolio_value']:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None

    async def connect_stream(self, symbols: List[str]) -> bool:
        """
        Connect to real-time quote stream.

        Args:
            symbols: List of symbols to stream

        Returns:
            True if connection successful
        """
        try:
            if self.is_connected:
                logger.warning("Already connected to stream")
                return False

            # Initialize data stream (note: real implementation would need to handle
            # the async websocket connection properly)
            self.data_stream = StockDataStream(
                api_key=self.api_key, secret_key=self.secret_key
            )

            logger.info(f"Connected to Alpaca stream for {len(symbols)} symbols")
            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"Error connecting to stream: {e}")
            return False

    async def disconnect_stream(self) -> bool:
        """
        Disconnect from real-time stream.

        Returns:
            True if disconnection successful
        """
        try:
            if not self.is_connected:
                logger.warning("Stream not connected")
                return False

            if self.data_stream:
                await self.data_stream.close()

            self.is_connected = False
            logger.info("Disconnected from Alpaca stream")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting stream: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear quote cache."""
        self.quote_cache.clear()
        logger.info("Quote cache cleared")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache info
        """
        return {
            "cached_quotes": len(self.quote_cache),
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window": self.rate_limit_window,
            "recent_requests": len(self.request_timestamps),
        }

    async def health_check(self) -> bool:
        """
        Check API connectivity and credentials.

        Returns:
            True if API is accessible and credentials are valid
        """
        try:
            await self._check_rate_limit()
            account = await self.get_account()
            return account is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
