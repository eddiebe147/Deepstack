"""
Unit tests for AlpacaClient - Alpaca Markets API integration

Tests core functionality including:
- Quote retrieval with caching
- Historical bar data
- Rate limiting
- Account information
- Error handling
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data.alpaca_client import AlpacaClient, TimeFrameEnum


class TestAlpacaClientInitialization:
    """Test AlpacaClient initialization and configuration."""

    def test_init_with_valid_credentials(self):
        """Test successful initialization with valid credentials."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            assert client.api_key == "test_key"
            assert client.secret_key == "test_secret"
            assert client.base_url == "https://paper-api.alpaca.markets"
            assert client.is_connected is False
            assert len(client.quote_cache) == 0

    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(
                api_key="test_key",
                secret_key="test_secret",
                base_url="https://api.alpaca.markets",
            )

            assert client.base_url == "https://api.alpaca.markets"

    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="API key and secret key are required"):
            AlpacaClient(api_key="", secret_key="test_secret")

    def test_init_missing_secret_key(self):
        """Test initialization fails without secret key."""
        with pytest.raises(ValueError, match="API key and secret key are required"):
            AlpacaClient(api_key="test_key", secret_key="")

    def test_init_with_custom_rate_limits(self):
        """Test initialization with custom rate limits."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(
                api_key="test_key",
                secret_key="test_secret",
                rate_limit_requests=100,
                rate_limit_window=30,
            )

            assert client.rate_limit_requests == 100
            assert client.rate_limit_window == 30


class TestQuoteRetrieval:
    """Test quote retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_quote_success(self):
        """Test successful quote retrieval."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            # Mock quote data
            mock_quote = MagicMock()
            mock_quote.bid_price = 150.25
            mock_quote.ask_price = 150.35
            mock_quote.bid_size = 100
            mock_quote.ask_size = 200

            mock_data_client.return_value.get_stock_latest_quote.return_value = {
                "AAPL": mock_quote
            }
            client.data_client = mock_data_client.return_value

            result = await client.get_quote("AAPL")

            assert result is not None
            assert result["symbol"] == "AAPL"
            assert result["bid"] == 150.25
            assert result["ask"] == 150.35
            assert result["bid_volume"] == 100
            assert result["ask_volume"] == 200

    @pytest.mark.asyncio
    async def test_get_quote_caching(self):
        """Test quote caching functionality."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            # Mock quote data
            mock_quote = MagicMock()
            mock_quote.bid_price = 150.25
            mock_quote.ask_price = 150.35
            mock_quote.bid_size = 100
            mock_quote.ask_size = 200

            mock_data_client.return_value.get_stock_latest_quote.return_value = {
                "AAPL": mock_quote
            }
            client.data_client = mock_data_client.return_value

            # First call should fetch from API
            result1 = await client.get_quote("AAPL")
            api_calls_1 = client.data_client.get_stock_latest_quote.call_count

            # Second call should use cache
            result2 = await client.get_quote("AAPL")
            api_calls_2 = client.data_client.get_stock_latest_quote.call_count

            assert result1 == result2
            assert api_calls_2 == api_calls_1  # No additional API call

    @pytest.mark.asyncio
    async def test_get_quote_cache_expiration(self):
        """Test quote cache expiration."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")
            client.cache_ttl = 1  # 1 second TTL

            # Mock quote data
            mock_quote = MagicMock()
            mock_quote.bid_price = 150.25
            mock_quote.ask_price = 150.35
            mock_quote.bid_size = 100
            mock_quote.ask_size = 200

            mock_data_client.return_value.get_stock_latest_quote.return_value = {
                "AAPL": mock_quote
            }
            client.data_client = mock_data_client.return_value

            # First call
            await client.get_quote("AAPL")

            # Wait for cache to expire
            await asyncio.sleep(1.1)

            # Second call should fetch from API again
            await client.get_quote("AAPL")

            # Should have made 2 API calls
            assert client.data_client.get_stock_latest_quote.call_count == 2

    @pytest.mark.asyncio
    async def test_get_quote_api_error(self):
        """Test quote retrieval with API error."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            mock_data_client.return_value.get_stock_latest_quote.side_effect = (
                Exception("API Error")
            )
            client.data_client = mock_data_client.return_value

            result = await client.get_quote("AAPL")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_quotes_multiple_symbols(self):
        """Test quote retrieval for multiple symbols."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            # Mock quote data
            mock_quote = MagicMock()
            mock_quote.bid_price = 150.25
            mock_quote.ask_price = 150.35
            mock_quote.bid_size = 100
            mock_quote.ask_size = 200

            def side_effect(request):
                symbol = request.symbol_or_symbols
                return {symbol: mock_quote}

            mock_data_client.return_value.get_stock_latest_quote.side_effect = (
                side_effect
            )
            client.data_client = mock_data_client.return_value

            result = await client.get_quotes(["AAPL", "GOOGL", "MSFT"])

            assert len(result) == 3
            assert all(v is not None for v in result.values())


class TestBarData:
    """Test historical bar data retrieval."""

    @pytest.mark.asyncio
    async def test_get_bars_success(self):
        """Test successful bar data retrieval."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            # Mock bar data
            mock_bar = MagicMock()
            mock_bar.timestamp = datetime(2024, 1, 1, 10, 0)
            mock_bar.open = 150.0
            mock_bar.high = 152.0
            mock_bar.low = 149.0
            mock_bar.close = 151.0
            mock_bar.volume = 1000000
            mock_bar.trade_count = 5000
            mock_bar.vwap = 150.5

            mock_data_client.return_value.get_stock_bars.return_value = {
                "AAPL": [mock_bar]
            }
            client.data_client = mock_data_client.return_value

            result = await client.get_bars("AAPL", TimeFrameEnum.DAY_1)

            assert result is not None
            assert len(result) == 1
            assert result[0]["symbol"] == "AAPL"
            assert result[0]["open"] == 150.0
            assert result[0]["close"] == 151.0
            assert result[0]["volume"] == 1000000

    @pytest.mark.asyncio
    async def test_get_bars_with_custom_dates(self):
        """Test bar data with custom date range."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            mock_bar = MagicMock()
            mock_bar.timestamp = datetime(2024, 1, 1)
            mock_bar.open = 150.0
            mock_bar.high = 152.0
            mock_bar.low = 149.0
            mock_bar.close = 151.0
            mock_bar.volume = 1000000

            mock_data_client.return_value.get_stock_bars.return_value = {
                "AAPL": [mock_bar]
            }
            client.data_client = mock_data_client.return_value

            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 31)

            result = await client.get_bars(
                "AAPL",
                TimeFrameEnum.DAY_1,
                start_date=start,
                end_date=end,
                limit=30,
            )

            assert result is not None
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_bars_multiple_timeframes(self):
        """Test bar data with different timeframes."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            mock_bar = MagicMock()
            mock_bar.timestamp = datetime(2024, 1, 1)
            mock_bar.open = 150.0
            mock_bar.high = 152.0
            mock_bar.low = 149.0
            mock_bar.close = 151.0
            mock_bar.volume = 100000

            mock_data_client.return_value.get_stock_bars.return_value = {
                "AAPL": [mock_bar]
            }
            client.data_client = mock_data_client.return_value

            for timeframe in [
                TimeFrameEnum.MINUTE_1,
                TimeFrameEnum.MINUTE_5,
                TimeFrameEnum.HOUR_1,
                TimeFrameEnum.DAY_1,
                TimeFrameEnum.WEEK_1,
            ]:
                result = await client.get_bars("AAPL", timeframe)
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_bars_api_error(self):
        """Test bar retrieval with API error."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch(
                "core.data.alpaca_client.StockHistoricalDataClient"
            ) as mock_data_client,
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            mock_data_client.return_value.get_stock_bars.side_effect = Exception(
                "API Error"
            )
            client.data_client = mock_data_client.return_value

            result = await client.get_bars("AAPL")

            assert result is None


class TestAccountInfo:
    """Test account information retrieval."""

    @pytest.mark.asyncio
    async def test_get_account_success(self):
        """Test successful account retrieval."""
        with (
            patch("core.data.alpaca_client.TradingClient") as mock_trading,
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            # Mock account data
            mock_account = MagicMock()
            mock_account.account_number = "PA12345"
            mock_account.buying_power = "50000.00"
            mock_account.cash = "25000.00"
            mock_account.portfolio_value = "100000.00"
            mock_account.long_market_value = "75000.00"
            mock_account.short_market_value = "0.00"
            mock_account.equity = "100000.00"
            mock_account.last_equity = "100000.00"
            mock_account.multiplier = "1"
            mock_account.shorting_enabled = True
            mock_account.status = "ACTIVE"

            mock_trading.return_value.get_account.return_value = mock_account

            client = AlpacaClient(api_key="test_key", secret_key="test_secret")
            client.trading_client = mock_trading.return_value

            result = await client.get_account()

            assert result is not None
            assert result["account_number"] == "PA12345"
            assert result["buying_power"] == 50000.0
            assert result["cash"] == 25000.0
            assert result["portfolio_value"] == 100000.0
            assert result["shorting_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_account_api_error(self):
        """Test account retrieval with API error."""
        with (
            patch("core.data.alpaca_client.TradingClient") as mock_trading,
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            mock_trading.return_value.get_account.side_effect = Exception("API Error")

            client = AlpacaClient(api_key="test_key", secret_key="test_secret")
            client.trading_client = mock_trading.return_value

            result = await client.get_account()

            assert result is None


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test that rate limiting is enforced."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(
                api_key="test_key",
                secret_key="test_secret",
                rate_limit_requests=2,
                rate_limit_window=2,
            )

            # Record timestamps for rate limiting check
            await client._check_rate_limit()  # Request 1
            await client._check_rate_limit()  # Request 2

            # Both should succeed without delay
            assert len(client.request_timestamps) == 2

    @pytest.mark.asyncio
    async def test_rate_limit_window_expiration(self):
        """Test that old requests are removed from rate limit tracking."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(
                api_key="test_key",
                secret_key="test_secret",
                rate_limit_window=1,
            )

            await client._check_rate_limit()

            # Wait for window to expire
            await asyncio.sleep(1.1)

            await client._check_rate_limit()

            # Old timestamp should be removed
            assert all(
                ts > (datetime.now().timestamp() - 1)
                for ts in client.request_timestamps
            )


class TestCache:
    """Test caching functionality."""

    def test_clear_cache(self):
        """Test cache clearing."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            # Add some cached data
            client.quote_cache["AAPL"] = ({"symbol": "AAPL"}, datetime.now())
            client.quote_cache["GOOGL"] = ({"symbol": "GOOGL"}, datetime.now())

            assert len(client.quote_cache) == 2

            client.clear_cache()

            assert len(client.quote_cache) == 0

    def test_get_cache_stats(self):
        """Test cache statistics."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            stats = client.get_cache_stats()

            assert "cached_quotes" in stats
            assert "rate_limit_requests" in stats
            assert "rate_limit_window" in stats
            assert "recent_requests" in stats


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with (
            patch("core.data.alpaca_client.TradingClient") as mock_trading,
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            mock_account = MagicMock()
            mock_account.account_number = "PA12345"
            mock_account.buying_power = "50000.00"
            mock_account.cash = "25000.00"
            mock_account.portfolio_value = "100000.00"
            mock_account.long_market_value = "75000.00"
            mock_account.short_market_value = "0.00"
            mock_account.equity = "100000.00"
            mock_account.last_equity = "100000.00"
            mock_account.multiplier = "1"
            mock_account.shorting_enabled = True
            mock_account.status = "ACTIVE"

            mock_trading.return_value.get_account.return_value = mock_account

            client = AlpacaClient(api_key="test_key", secret_key="test_secret")
            client.trading_client = mock_trading.return_value

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with API failure."""
        with (
            patch("core.data.alpaca_client.TradingClient") as mock_trading,
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
        ):
            mock_trading.return_value.get_account.side_effect = Exception("API Error")

            client = AlpacaClient(api_key="test_key", secret_key="test_secret")
            client.trading_client = mock_trading.return_value

            result = await client.health_check()

            assert result is False


class TestStreamConnection:
    """Test real-time stream connection."""

    @pytest.mark.asyncio
    async def test_connect_stream_success(self):
        """Test successful stream connection."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
            patch("core.data.alpaca_client.StockDataStream"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            result = await client.connect_stream(["AAPL", "GOOGL"])

            assert result is True
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect_stream_success(self):
        """Test successful stream disconnection."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
            patch("core.data.alpaca_client.StockDataStream"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            await client.connect_stream(["AAPL"])

            # Mock the close method to be awaitable
            if client.data_stream:
                client.data_stream.close = AsyncMock()

            result = await client.disconnect_stream()

            assert result is True
            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_stream_already_connected(self):
        """Test connection when already connected."""
        with (
            patch("core.data.alpaca_client.TradingClient"),
            patch("core.data.alpaca_client.StockHistoricalDataClient"),
            patch("core.data.alpaca_client.StockDataStream"),
        ):
            client = AlpacaClient(api_key="test_key", secret_key="test_secret")

            await client.connect_stream(["AAPL"])
            result = await client.connect_stream(["GOOGL"])

            assert result is False
