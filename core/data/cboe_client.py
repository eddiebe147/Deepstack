"""
CBOE Options Data Client

Fetches put/call ratio and volume statistics from CBOE's free CSV feeds:
- Total put/call ratio
- Equity put/call ratio
- Index put/call ratio

No API key required - uses publicly available CSV files.
"""

import csv
import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PutCallData:
    """Single day of put/call ratio data from CBOE."""

    date: str
    call_volume: int
    put_volume: int
    total_volume: int
    put_call_ratio: float


# Valid ratio types mapped to their CBOE CSV URLs.
#
# The host and path are hoisted because a URL cannot be wrapped mid-string, and
# the same 68-character prefix was written out three times - so a CBOE path
# change was three edits with two chances to miss one.
_CBOE_RATIOS = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios"

RATIO_URLS: Dict[str, str] = {
    "total": f"{_CBOE_RATIOS}/totalpc.csv",
    "equity": f"{_CBOE_RATIOS}/equitypc.csv",
    "index": f"{_CBOE_RATIOS}/indexpc.csv",
}

VALID_RATIO_TYPES = tuple(RATIO_URLS.keys())


class CBOEClient:
    """
    CBOE options data client for DeepStack Trading System.

    Provides:
    - Current and historical put/call ratios (total, equity, index)
    - PCR percentile ranking vs 252-day history
    - Smart caching with 1-hour TTL
    - Retry logic for transient network errors
    """

    CACHE_TTL = 3600  # 1 hour
    MAX_DATA_AGE_DAYS = 7

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

        # Cache: {ratio_type: (rows, fetched_at)}
        self._cache: Dict[str, Tuple[List[PutCallData], float]] = {}

        self._client: Optional[httpx.AsyncClient] = None

        logger.info("CBOEClient initialized")

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure httpx async client exists."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15, connect=5),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("CBOE client closed")

    def _validate_ratio_type(self, ratio_type: str) -> str:
        """Validate ratio_type is one of: total, equity, index."""
        ratio_type = ratio_type.strip().lower()
        if ratio_type not in VALID_RATIO_TYPES:
            raise ValueError(
                f"Invalid ratio_type '{ratio_type}'. "
                f"Must be one of: {VALID_RATIO_TYPES}"
            )
        return ratio_type

    def _get_cached(self, ratio_type: str) -> Optional[List[PutCallData]]:
        """Return cached data if still fresh, else None."""
        if ratio_type not in self._cache:
            return None

        rows, fetched_at = self._cache[ratio_type]
        if time.time() - fetched_at < self.CACHE_TTL:
            logger.debug(f"Cache hit for CBOE {ratio_type} PCR")
            return rows

        logger.debug(f"Cache expired for CBOE {ratio_type} PCR")
        del self._cache[ratio_type]
        return None

    def _set_cached(self, ratio_type: str, rows: List[PutCallData]) -> None:
        """Store parsed rows in cache."""
        self._cache[ratio_type] = (rows, time.time())

    async def _fetch_csv(self, ratio_type: str) -> List[PutCallData]:
        """
        Fetch and parse a CBOE put/call CSV file with retry logic.

        Returns rows sorted newest-first.
        """
        # Check cache first
        cached = self._get_cached(ratio_type)
        if cached is not None:
            return cached

        url = RATIO_URLS[ratio_type]
        last_error: Optional[Exception] = None

        client = await self._ensure_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()

                rows = self._parse_csv(response.text, ratio_type)
                self._set_cached(ratio_type, rows)
                logger.info(f"Fetched {len(rows)} rows of CBOE {ratio_type} PCR data")
                return rows

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"HTTP {e.response.status_code} fetching CBOE {ratio_type} CSV "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"Network error fetching CBOE {ratio_type} CSV: {e} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                import asyncio

                await asyncio.sleep(min(5 * (2**attempt), 30))

        logger.error(
            f"Failed to fetch CBOE {ratio_type} CSV after "
            f"{self.max_retries} attempts: {last_error}"
        )
        return []

    def _parse_csv(self, text: str, ratio_type: str) -> List[PutCallData]:
        """
        Parse CBOE CSV text into PutCallData rows.

        CBOE CSVs have a header row followed by data rows.
        Columns vary slightly but generally include date, calls, puts, total, P/C ratio.
        """
        rows: List[PutCallData] = []

        reader = csv.reader(io.StringIO(text))

        # CBOE CSVs start with disclaimer/metadata rows before the actual
        # column headers. Skip lines until we find one containing "DATE".
        header = None
        for row in reader:
            normalized_row = [h.strip().upper() for h in row]
            if any("DATE" in col for col in normalized_row):
                header = row
                break

        if header is None:
            logger.warning(f"No header row found in CBOE {ratio_type} CSV")
            return []

        # Normalize headers for matching
        normalized = [h.strip().upper() for h in header]

        # Find column indices - CBOE uses TRADE DATE, CALLS, PUTS, TOTAL, P/C RATIO
        date_idx = self._find_col(normalized, ["TRADE DATE", "DATE"])
        calls_idx = self._find_col(normalized, ["CALLS", "CALL VOLUME", "CALL"])
        puts_idx = self._find_col(normalized, ["PUTS", "PUT VOLUME", "PUT"])
        total_idx = self._find_col(normalized, ["TOTAL", "TOTAL VOLUME"])
        ratio_idx = self._find_col(
            normalized, ["P/C RATIO", "PUT/CALL RATIO", "PC RATIO"]
        )

        if date_idx is None or ratio_idx is None:
            logger.error(
                f"Could not find required columns in CBOE {ratio_type} CSV. "
                f"Headers: {header}"
            )
            return []

        for row in reader:
            try:
                if len(row) <= max(
                    i
                    for i in [date_idx, calls_idx, puts_idx, total_idx, ratio_idx]
                    if i is not None
                ):
                    continue

                date_str = row[date_idx].strip()
                if not date_str:
                    continue

                # Parse date - CBOE uses M/D/YYYY format
                date_val = self._parse_date(date_str)

                pcr = float(row[ratio_idx].strip()) if ratio_idx is not None else 0.0

                call_vol = (
                    self._safe_int(row[calls_idx]) if calls_idx is not None else 0
                )
                put_vol = self._safe_int(row[puts_idx]) if puts_idx is not None else 0
                total_vol = (
                    self._safe_int(row[total_idx])
                    if total_idx is not None
                    else (call_vol + put_vol)
                )

                rows.append(
                    PutCallData(
                        date=date_val,
                        call_volume=call_vol,
                        put_volume=put_vol,
                        total_volume=total_vol,
                        put_call_ratio=pcr,
                    )
                )
            except (ValueError, IndexError) as e:
                # Skip malformed rows silently
                logger.debug(f"Skipping malformed CBOE row: {e}")
                continue

        # Sort newest first
        rows.sort(key=lambda r: r.date, reverse=True)
        return rows

    @staticmethod
    def _find_col(headers: List[str], candidates: List[str]) -> Optional[int]:
        """Find the index of the first matching column header."""
        for i, h in enumerate(headers):
            for candidate in candidates:
                if candidate in h:
                    return i
        return None

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format."""
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Unrecognized date format: {date_str}")

    @staticmethod
    def _safe_int(val: str) -> int:
        """Parse string to int, stripping commas and whitespace."""
        return int(val.strip().replace(",", "")) if val.strip() else 0

    # ── Public API ───────────────────────────────────────────────

    async def get_put_call_ratio(self, ratio_type: str = "total") -> PutCallData:
        """
        Get the most recent put/call ratio.

        Args:
            ratio_type: One of "total", "equity", "index"

        Returns:
            Latest PutCallData row

        Raises:
            ValueError: If ratio_type is invalid or no data available
        """
        ratio_type = self._validate_ratio_type(ratio_type)
        rows = await self._fetch_csv(ratio_type)

        if not rows:
            raise ValueError(f"No CBOE {ratio_type} put/call data available")

        latest = rows[0]
        latest_date = datetime.strptime(latest.date, "%Y-%m-%d")
        age = datetime.now() - latest_date
        if age > timedelta(days=self.MAX_DATA_AGE_DAYS):
            raise ValueError(
                f"Stale CBOE {ratio_type} data: latest row is {latest.date} "
                f"({age.days} days old)"
            )

        return latest

    async def get_historical_pcr(
        self, days: int = 30, ratio_type: str = "total"
    ) -> List[PutCallData]:
        """
        Get historical put/call ratio data.

        Args:
            days: Number of trading days to return (default 30)
            ratio_type: One of "total", "equity", "index"

        Returns:
            List of PutCallData, newest first, up to `days` entries
        """
        ratio_type = self._validate_ratio_type(ratio_type)
        rows = await self._fetch_csv(ratio_type)
        return rows[:days]

    async def get_pcr_percentile(self, ratio_type: str = "total") -> float:
        """
        Calculate where the current PCR sits vs its 252-day history.

        A percentile of 0.90 means the current PCR is higher than 90% of
        the last 252 trading days, indicating elevated put buying (bearish).

        Args:
            ratio_type: One of "total", "equity", "index"

        Returns:
            Percentile as a float between 0.0 and 1.0

        Raises:
            ValueError: If insufficient data
        """
        ratio_type = self._validate_ratio_type(ratio_type)
        rows = await self._fetch_csv(ratio_type)

        if len(rows) < 2:
            raise ValueError(
                f"Insufficient CBOE {ratio_type} data for percentile calculation"
            )

        # Use up to 252 trading days (1 year)
        history = rows[:252]
        current = history[0].put_call_ratio
        count_below = sum(1 for r in history if r.put_call_ratio < current)

        return count_below / len(history)

    def clear_cache(self, ratio_type: Optional[str] = None) -> None:
        """
        Clear cached data.

        Args:
            ratio_type: Specific type to clear, or None for all
        """
        if ratio_type:
            self._cache.pop(ratio_type, None)
            logger.info(f"Cleared CBOE {ratio_type} cache")
        else:
            self._cache.clear()
            logger.info("Cleared all CBOE cache")

    async def health_check(self) -> bool:
        """Check connectivity to CBOE data feeds."""
        try:
            data = await self.get_put_call_ratio("total")
            return data is not None
        except Exception as e:
            logger.error(f"CBOE health check failed: {e}")
            return False
