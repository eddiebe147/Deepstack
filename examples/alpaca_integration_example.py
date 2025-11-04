"""
Example: Using AlpacaClient for real-time market data in DeepStack

This example demonstrates how to integrate Alpaca Markets API with DeepStack
to fetch real-time quotes, historical bars, and account information.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from core.config import get_config
from core.data.alpaca_client import AlpacaClient, TimeFrameEnum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_quote():
    """Example: Get a quote for a single symbol."""
    config = get_config()

    # Initialize the Alpaca client
    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Get a quote
    quote = await client.get_quote("AAPL")
    if quote:
        logger.info(f"Quote for {quote['symbol']}:")
        logger.info(f"  Bid: ${quote['bid']}")
        logger.info(f"  Ask: ${quote['ask']}")
        logger.info(f"  Bid Volume: {quote['bid_volume']}")
        logger.info(f"  Ask Volume: {quote['ask_volume']}")
    else:
        logger.warning("Failed to get quote")


async def example_multiple_quotes():
    """Example: Get quotes for multiple symbols."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Get quotes for multiple symbols
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    quotes = await client.get_quotes(symbols)

    for symbol, quote in quotes.items():
        if quote:
            logger.info(f"{symbol}: Bid=${quote['bid']}, Ask=${quote['ask']}")
        else:
            logger.warning(f"Failed to get quote for {symbol}")


async def example_historical_bars():
    """Example: Get historical bar data."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Get daily bars for the past 30 days
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()

    bars = await client.get_bars(
        symbol="AAPL",
        timeframe=TimeFrameEnum.DAY_1,
        start_date=start_date,
        end_date=end_date,
        limit=30,
    )

    if bars:
        logger.info(f"Retrieved {len(bars)} bars for AAPL:")
        for bar in bars[:3]:  # Show first 3 bars
            logger.info(
                f"  {bar['timestamp']}: Open=${bar['open']}, "
                f"High=${bar['high']}, Low=${bar['low']}, Close=${bar['close']}"
            )
    else:
        logger.warning("Failed to get bars")


async def example_intraday_bars():
    """Example: Get intraday bar data."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Get 1-minute bars for today
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()

    bars = await client.get_bars(
        symbol="AAPL",
        timeframe=TimeFrameEnum.MINUTE_5,
        start_date=start_date,
        end_date=end_date,
        limit=100,
    )

    if bars:
        logger.info(f"Retrieved {len(bars)} 5-minute bars for AAPL")
        # Analyze the data...
    else:
        logger.warning("Failed to get intraday bars")


async def example_account_info():
    """Example: Get account information."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Get account information
    account = await client.get_account()
    if account:
        logger.info("Account Information:")
        logger.info(f"  Account Number: {account['account_number']}")
        logger.info(f"  Portfolio Value: ${account['portfolio_value']:.2f}")
        logger.info(f"  Cash: ${account['cash']:.2f}")
        logger.info(f"  Buying Power: ${account['buying_power']:.2f}")
        logger.info(f"  Equity: ${account['equity']:.2f}")
    else:
        logger.warning("Failed to get account information")


async def example_health_check():
    """Example: Check API connectivity."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # Perform health check
    is_healthy = await client.health_check()
    if is_healthy:
        logger.info("Alpaca API is accessible and credentials are valid")
    else:
        logger.error("Alpaca API health check failed")


async def example_caching():
    """Example: Demonstrate quote caching."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    # First call - fetches from API
    logger.info("First call to get_quote (fetches from API)...")
    await client.get_quote("AAPL")

    # Second call - uses cache
    logger.info("Second call to get_quote (uses cache)...")
    await client.get_quote("AAPL")

    # Get cache statistics
    stats = client.get_cache_stats()
    logger.info(f"Cache stats: {stats}")

    # Clear cache
    client.clear_cache()
    logger.info("Cache cleared")


async def example_rate_limiting():
    """Example: Demonstrate rate limiting."""
    config = get_config()

    # Create client with tight rate limits for demonstration
    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
        rate_limit_requests=5,  # 5 requests
        rate_limit_window=10,  # per 10 seconds
    )

    logger.info(
        f"Rate limit: {client.rate_limit_requests} requests per {client.rate_limit_window}s"
    )

    # Make several requests - will be rate limited
    for i in range(3):
        logger.info(f"Request {i + 1}...")
        quote = await client.get_quote("AAPL")
        if quote:
            logger.info(f"  Got quote: ${quote['bid']} / ${quote['ask']}")


async def example_multi_timeframe_analysis():
    """Example: Get bars at multiple timeframes for technical analysis."""
    config = get_config()

    client = AlpacaClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        base_url=config.alpaca_base_url,
    )

    symbol = "AAPL"
    timeframes = [
        TimeFrameEnum.MINUTE_5,
        TimeFrameEnum.MINUTE_15,
        TimeFrameEnum.HOUR_1,
        TimeFrameEnum.DAY_1,
    ]

    logger.info(f"Fetching bars for {symbol} at multiple timeframes...")

    for timeframe in timeframes:
        bars = await client.get_bars(symbol, timeframe=timeframe, limit=10)
        if bars:
            logger.info(f"  {timeframe}: {len(bars)} bars retrieved")
        else:
            logger.warning(f"  {timeframe}: Failed to retrieve bars")


async def example_complete_workflow():
    """Example: Complete workflow with error handling."""
    config = get_config()

    try:
        client = AlpacaClient(
            api_key=config.alpaca_api_key,
            secret_key=config.alpaca_secret_key,
            base_url=config.alpaca_base_url,
        )

        logger.info("Starting Alpaca integration workflow...")

        # 1. Health check
        logger.info("1. Checking API connectivity...")
        if not await client.health_check():
            logger.error("API health check failed!")
            return

        # 2. Get account info
        logger.info("2. Fetching account information...")
        account = await client.get_account()
        if account:
            logger.info(f"   Portfolio value: ${account['portfolio_value']:.2f}")

        # 3. Get quotes for multiple symbols
        logger.info("3. Fetching quotes for multiple symbols...")
        symbols = ["AAPL", "GOOGL", "MSFT"]
        quotes = await client.get_quotes(symbols)
        logger.info(f"   Fetched {sum(1 for q in quotes.values() if q)} quotes")

        # 4. Get historical data
        logger.info("4. Fetching historical daily bars...")
        bars = await client.get_bars(
            "AAPL",
            timeframe=TimeFrameEnum.DAY_1,
            start_date=datetime.now() - timedelta(days=30),
            limit=30,
        )
        if bars:
            logger.info(f"   Fetched {len(bars)} daily bars")

        logger.info("Workflow complete!")

    except Exception as e:
        logger.error(f"Error in workflow: {e}", exc_info=True)


async def main():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("AlpacaClient Integration Examples")
    logger.info("=" * 60)

    # Note: Uncomment the examples you want to run
    # Make sure to set ALPACA_API_KEY and ALPACA_SECRET_KEY in your environment

    # await example_basic_quote()
    # await example_multiple_quotes()
    # await example_historical_bars()
    # await example_intraday_bars()
    # await example_account_info()
    # await example_health_check()
    # await example_caching()
    # await example_rate_limiting()
    # await example_multi_timeframe_analysis()
    await example_complete_workflow()


if __name__ == "__main__":
    asyncio.run(main())
