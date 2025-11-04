# Security Recommendations - Alpaca Integration

## Priority 1: Network Timeout (Before Production)

### Current Issue
```python
# Line 82-90: No timeout parameters
self.trading_client = TradingClient(
    api_key=api_key,
    secret_key=secret_key,
    paper=is_paper,
    url_override=base_url,  # Missing: timeout parameter
)
```

### Recommended Fix
```python
# Add timeout constant at class level
ALPACA_TIMEOUT_SECONDS = 30

# In __init__:
self.trading_client = TradingClient(
    api_key=api_key,
    secret_key=secret_key,
    paper=is_paper,
    url_override=base_url,
    timeout=self.ALPACA_TIMEOUT_SECONDS,
)

# For historical data client (alpaca-py library)
# Check if StockHistoricalDataClient supports timeout parameter
self.data_client = StockHistoricalDataClient(
    api_key=api_key,
    secret_key=secret_key,
    timeout=self.ALPACA_TIMEOUT_SECONDS,
)
```

### Impact
- **Prevents**: Indefinite hanging on network failures
- **Protects**: Against DoS via connection timeout exploitation
- **Improves**: System resilience and user experience

---

## Priority 2: Complete WebSocket Implementation (Before Real-Time Trading)

### Current Issue
Lines 333-361 show incomplete WebSocket implementation:
```python
async def connect_stream(self, symbols: List[str]) -> bool:
    # Line 348-349: Comment acknowledges implementation incomplete
    # "note: real implementation would need to handle the async websocket connection properly"

    self.data_stream = StockDataStream(
        api_key=self.api_key, secret_key=self.secret_key
    )
    # Missing: Symbol subscription
    # Missing: Connection verification
    # Returns True without checking actual connection
```

### Recommended Implementation

Create a new method with proper async lifecycle:

```python
async def connect_stream(self, symbols: List[str]) -> bool:
    """Connect to real-time quote stream with verification."""
    try:
        if self.is_connected:
            logger.warning("Already connected to stream")
            return False

        logger.info(f"Initiating stream connection for {len(symbols)} symbols...")

        self.data_stream = StockDataStream(
            api_key=self.api_key,
            secret_key=self.secret_key
        )

        # Subscribe to quotes
        async def handle_quote(quote):
            """Handle incoming quote data."""
            logger.debug(f"Quote received: {quote.symbol} @ {quote.ask_price}")

        # Register quote handler
        self.data_stream.subscribe_quotes(handle_quote, *symbols)

        # Start connection with timeout
        try:
            await asyncio.wait_for(
                self.data_stream.connect(),
                timeout=30  # 30-second connection timeout
            )
        except asyncio.TimeoutError:
            logger.error("Stream connection timed out")
            return False

        # Verify subscription was successful
        await asyncio.sleep(1)  # Allow time for first quote
        if not self.data_stream._is_connected:
            logger.error("Stream connected but not subscribed")
            return False

        self.is_connected = True
        logger.info(f"Stream successfully connected for symbols: {symbols}")
        return True

    except Exception as e:
        logger.error(f"Failed to connect stream: {e}", exc_info=True)
        self.is_connected = False
        return False


async def disconnect_stream(self) -> bool:
    """Disconnect from real-time stream with graceful shutdown."""
    try:
        if not self.is_connected:
            logger.warning("Stream not connected")
            return False

        if self.data_stream:
            try:
                # Give pending operations 5 seconds to complete
                await asyncio.wait_for(
                    self.data_stream.close(),
                    timeout=5
                )
            except asyncio.TimeoutError:
                logger.warning("Stream close operation timed out")

        self.is_connected = False
        self.data_stream = None
        logger.info("Stream disconnected successfully")
        return True

    except Exception as e:
        logger.error(f"Error disconnecting stream: {e}")
        self.is_connected = False
        return False
```

### Impact
- **Enables**: Real-time market data functionality
- **Prevents**: Silent connection failures
- **Improves**: Data reliability and trading decision quality

---

## Priority 3: Exponential Backoff for Transient Failures

### Current Issue
```python
# Lines 188-190: Fails immediately on any error
except Exception as e:
    logger.error(f"Error getting quote for {symbol}: {e}")
    return None
```

This approach is too aggressive for transient failures (network blips, temporary API throttling).

### Recommended Implementation

Add `tenacity` library to requirements.txt:
```
tenacity>=8.2.0
```

Then apply retry decorator:

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

class AlpacaClient:
    # ... existing code ...

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError,  # Network-related errors
        )),
    )
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote for a symbol with automatic retry."""
        # ... existing implementation ...
```

Backoff schedule:
- Attempt 1: Immediate
- Attempt 2: Wait 2-3 seconds
- Attempt 3: Wait 4-6 seconds
- Attempt 4: Wait 8-30 seconds (capped)

### Configuration Options

```python
# Conservative (fewer retries, less delay)
@retry(
    wait=wait_exponential(multiplier=0.5, min=1, max=10),
    stop=stop_after_attempt(2),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)

# Aggressive (more retries, longer delays)
@retry(
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
)
```

### Impact
- **Reduces**: False failures from temporary network issues
- **Improves**: Success rate for transient failures
- **Prevents**: Unnecessary trading errors

---

## Priority 4: Enhanced Security Testing

Add security-focused tests to `test_alpaca_client.py`:

```python
class TestSecurityAspects:
    """Security-focused test cases."""

    def test_credentials_not_logged(self, caplog):
        """Verify API credentials are never logged."""
        with patch("core.data.alpaca_client.TradingClient"):
            with patch("core.data.alpaca_client.StockHistoricalDataClient"):
                client = AlpacaClient(
                    api_key="test_api_key_12345",
                    secret_key="test_secret_key_67890"
                )

                # Check all logs
                for record in caplog.records:
                    assert "test_api_key_12345" not in record.message
                    assert "test_secret_key_67890" not in record.message

    @pytest.mark.asyncio
    async def test_empty_api_key_raises_error(self):
        """Verify empty API key is rejected."""
        with pytest.raises(ValueError, match="API key and secret key are required"):
            AlpacaClient(api_key="", secret_key="valid_secret")

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        with patch("core.data.alpaca_client.TradingClient"):
            with patch("core.data.alpaca_client.StockHistoricalDataClient"):
                client = AlpacaClient(api_key="test", secret_key="test")

                # Simulate timeout
                client.data_client.get_stock_latest_quote = AsyncMock(
                    side_effect=asyncio.TimeoutError()
                )

                result = await client.get_quote("AAPL")
                assert result is None  # Should return None on timeout
```

---

## Priority 5: Dependency Scanning Setup

Add to CI/CD pipeline:

### Install pip-audit
```bash
pip install pip-audit
```

### Run security audit
```bash
pip-audit
```

### Add to GitHub Actions (.github/workflows/security.yml)
```yaml
name: Security Audit

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r requirements.txt pip-audit

      - name: Run security audit
        run: pip-audit
```

---

## Priority 6: Rate Limiter Improvements

### Current Implementation
Recursive waiting can stack in extreme scenarios.

### Recommended Enhancement

```python
async def _check_rate_limit(self, max_wait_time: float = 60.0) -> bool:
    """
    Check and enforce rate limits with max wait time.

    Args:
        max_wait_time: Maximum seconds to wait (default: 60)

    Returns:
        True if limit check passed, False if exceeded max wait time

    Raises:
        RateLimitError: If rate limit exceeded and max_wait_time exceeded
    """
    import time

    current_time = time.time()

    # Remove old timestamps outside the window
    self.request_timestamps = [
        ts for ts in self.request_timestamps
        if current_time - ts < self.rate_limit_window
    ]

    # Check if we've exceeded the limit
    if len(self.request_timestamps) >= self.rate_limit_requests:
        wait_time = (
            self.request_timestamps[0] + self.rate_limit_window - current_time
        )

        if wait_time > max_wait_time:
            logger.error(
                f"Rate limit wait time {wait_time:.2f}s exceeds max "
                f"{max_wait_time:.2f}s. Raising RateLimitError."
            )
            raise RateLimitError(
                f"Rate limited for {wait_time:.2f}s (max: {max_wait_time}s)"
            )

        logger.warning(
            f"Rate limit approaching: waiting {wait_time:.2f}s"
        )
        await asyncio.sleep(wait_time + 0.1)

    # Record this request
    self.request_timestamps.append(current_time)
```

---

## Monitoring Recommendations

### Logging Points to Monitor
```python
# Security-related events to monitor:
logger.warning(f"Rate limit approaching...")  # Line 131
logger.error(f"Error getting quote for {symbol}...")  # Line 189
logger.error(f"Error getting bars for {symbol}...")  # Line 291
logger.error(f"Error getting account...")  # Line 330
logger.error(f"Error connecting to stream...")  # Line 359
logger.error(f"Error disconnecting stream...")  # Line 382
logger.error(f"Health check failed...")  # Line 416
```

### Alerts to Set Up
1. **Rate Limit Warnings**: Indicates potential API abuse
2. **Connection Errors**: Indicates network issues
3. **Health Check Failures**: Indicates credential or API issues
4. **Credential Errors**: Security breach indicators

---

## Deployment Checklist

Before deploying to production:

- [ ] Add network timeout parameters
- [ ] Complete WebSocket implementation
- [ ] Implement exponential backoff
- [ ] Add security-focused tests
- [ ] Set up dependency scanning
- [ ] Configure monitoring/alerts
- [ ] Review rate limiter edge cases
- [ ] Document API error codes
- [ ] Test with real Alpaca account (paper trading)
- [ ] Conduct penetration testing

---

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Alpaca API Documentation: https://alpaca.markets/docs/
- Python Security Best Practices: https://python.readthedocs.io/en/latest/library/security_warnings.html
- Tenacity Retry Library: https://tenacity.readthedocs.io/
- pip-audit: https://pypa.github.io/pip-audit/

---

*Created by Security Auditor Agent*
*Task 2.1 - Alpaca Markets API Integration*
