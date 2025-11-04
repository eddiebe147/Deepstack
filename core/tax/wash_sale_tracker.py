"""
Wash Sale Tracker - IRS Wash Sale Rule Compliance

Tracks and prevents wash sale violations per IRS Publication 550.
A wash sale occurs when you sell a security at a loss and purchase
substantially identical security within 30 days before or after the sale.

The loss deduction is disallowed and added to the cost basis of the new purchase.

Key Features:
    - Tracks all sales at a loss with timestamps
    - Enforces 30-day window before and after loss sales (61-day total)
    - Prevents trades that would trigger wash sales
    - Suggests alternative securities
    - Calculates disallowed losses
    - Auto-cleanup of expired records

IRS Rule Reference:
    - 30 days BEFORE the loss sale
    - The day OF the loss sale
    - 30 days AFTER the loss sale
    - Total window: 61 days

Example:
    >>> tracker = WashSaleTracker()
    >>> # Record a loss sale
    >>> tracker.record_loss_sale(
    ...     symbol="AAPL",
    ...     quantity=100,
    ...     loss_amount=500.0,
    ...     sale_date=datetime(2024, 1, 15),
    ...     cost_basis=15000.0,
    ...     sale_price=14500.0
    ... )
    >>> # Check if repurchase would trigger wash sale
    >>> is_violation = tracker.is_wash_sale("AAPL", datetime(2024, 1, 25))
    >>> # True - within 30 days after loss sale
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LossSale:
    """
    Record of a security sale at a loss.

    Attributes:
        symbol: Stock ticker symbol
        quantity: Number of shares sold
        loss_amount: Dollar amount of loss (positive number)
        sale_date: Date of the loss sale
        cost_basis: Original purchase price (total)
        sale_price: Sale price (total)
    """

    symbol: str
    quantity: int
    loss_amount: float
    sale_date: datetime
    cost_basis: float
    sale_price: float

    def __post_init__(self):
        """Validate loss sale data."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.loss_amount < 0:
            raise ValueError("Loss amount must be positive")
        if self.cost_basis <= 0 or self.sale_price < 0:
            raise ValueError("Cost basis and sale price must be non-negative")


@dataclass
class WashSaleViolation:
    """
    Record of a detected wash sale violation.

    Attributes:
        original_sale: The original loss sale
        repurchase_date: Date of the repurchase
        disallowed_loss: Amount of loss that cannot be deducted
    """

    original_sale: LossSale
    repurchase_date: datetime
    disallowed_loss: float


class WashSaleTracker:
    """
    Tracks and prevents wash sale violations per IRS Publication 550.

    A wash sale occurs when you:
    1. Sell a security at a loss
    2. Purchase substantially identical security within 30 days before or after

    The loss deduction is disallowed and added to the cost basis of the new purchase.

    Implementation Notes:
    - Uses UTC timestamps for consistency
    - "Substantially identical" = same ticker symbol (V1 implementation)
    - 30 days before + 30 days after = 61-day total window
    - Persisted to SQLite database
    - Auto-cleanup of expired records (>61 days old)
    """

    def __init__(self, db_path: str = "data/wash_sales.db"):
        """
        Initialize wash sale tracker.

        Args:
            db_path: Path to SQLite database for persistence
        """
        self.db_path = db_path
        self._init_db()

        # In-memory cache for performance
        self.loss_sales_cache: Dict[str, List[LossSale]] = {}
        self._load_loss_sales()

        logger.info(f"Wash Sale Tracker initialized with db: {db_path}")

    def _init_db(self):
        """Initialize SQLite database for wash sale tracking."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Loss sales table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS loss_sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        loss_amount REAL NOT NULL,
                        sale_date TIMESTAMP NOT NULL,
                        cost_basis REAL NOT NULL,
                        sale_price REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create index separately
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_symbol_date
                    ON loss_sales (symbol, sale_date)
                """
                )

                # Wash sale violations table (for record keeping)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS wash_sale_violations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        loss_sale_id INTEGER NOT NULL,
                        repurchase_date TIMESTAMP NOT NULL,
                        disallowed_loss REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (loss_sale_id) REFERENCES loss_sales (id)
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing wash sale database: {e}")
            raise

    def _load_loss_sales(self):
        """Load loss sales from database into memory cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, quantity, loss_amount, sale_date,
                           cost_basis, sale_price
                    FROM loss_sales
                    ORDER BY sale_date DESC
                """
                )

                rows = cursor.fetchall()
                self.loss_sales_cache.clear()

                for row in rows:
                    symbol = row[0]
                    loss_sale = LossSale(
                        symbol=symbol,
                        quantity=row[1],
                        loss_amount=row[2],
                        sale_date=datetime.fromisoformat(row[3]),
                        cost_basis=row[4],
                        sale_price=row[5],
                    )

                    if symbol not in self.loss_sales_cache:
                        self.loss_sales_cache[symbol] = []
                    self.loss_sales_cache[symbol].append(loss_sale)

                logger.info(
                    f"Loaded {len(rows)} loss sales from database "
                    f"for {len(self.loss_sales_cache)} symbols"
                )

        except Exception as e:
            logger.error(f"Error loading loss sales: {e}")

    def record_loss_sale(
        self,
        symbol: str,
        quantity: int,
        loss_amount: float,
        sale_date: datetime,
        cost_basis: float,
        sale_price: float,
    ) -> None:
        """
        Record a sale at a loss for wash sale tracking.

        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares sold
            loss_amount: Dollar amount of loss (positive number)
            sale_date: Date of the loss sale
            cost_basis: Original purchase price (total)
            sale_price: Sale price (total)

        Raises:
            ValueError: If input validation fails
        """
        # Validate inputs
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        if loss_amount < 0:
            raise ValueError(
                "Loss amount must be positive (losses are positive values)"
            )

        # Create loss sale record
        loss_sale = LossSale(
            symbol=symbol.upper(),
            quantity=quantity,
            loss_amount=loss_amount,
            sale_date=sale_date,
            cost_basis=cost_basis,
            sale_price=sale_price,
        )

        # Save to database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO loss_sales
                    (symbol, quantity, loss_amount, sale_date, cost_basis, sale_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        loss_sale.symbol,
                        loss_sale.quantity,
                        loss_sale.loss_amount,
                        loss_sale.sale_date.isoformat(),
                        loss_sale.cost_basis,
                        loss_sale.sale_price,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Error saving loss sale: {e}")
            raise

        # Update cache (use uppercased symbol)
        symbol_upper = loss_sale.symbol
        if symbol_upper not in self.loss_sales_cache:
            self.loss_sales_cache[symbol_upper] = []
        self.loss_sales_cache[symbol_upper].append(loss_sale)

        logger.info(
            f"Recorded loss sale: {symbol_upper} {quantity} shares, "
            f"loss: ${loss_amount:.2f} on {sale_date.date()}"
        )

    def is_wash_sale(self, symbol: str, purchase_date: datetime) -> bool:
        """
        Check if purchasing this symbol would trigger a wash sale.

        A wash sale is triggered if there's a loss sale of the same symbol
        within 30 days before OR 30 days after the purchase date.

        Args:
            symbol: Stock ticker symbol
            purchase_date: Proposed purchase date

        Returns:
            bool: True if wash sale would be triggered
        """
        symbol = symbol.upper()

        # No loss sales for this symbol
        if symbol not in self.loss_sales_cache:
            return False

        # Check each loss sale for this symbol
        for loss_sale in self.loss_sales_cache[symbol]:
            # Calculate wash sale window
            # 30 days BEFORE the loss sale to 30 days AFTER
            window_start = loss_sale.sale_date - timedelta(days=30)
            window_end = loss_sale.sale_date + timedelta(days=30)

            # Check if purchase date falls within wash sale window
            if window_start <= purchase_date <= window_end:
                logger.warning(
                    f"Wash sale detected for {symbol}: "
                    f"Purchase on {purchase_date.date()} falls within window "
                    f"of loss sale on {loss_sale.sale_date.date()}"
                )
                return True

        return False

    def get_wash_sale_window(self, symbol: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the wash sale window (30 days before/after) for a symbol.

        Returns the EARLIEST start date and LATEST end date across all
        loss sales for this symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Tuple of (window_start, window_end) or None if no loss sales
        """
        symbol = symbol.upper()

        if symbol not in self.loss_sales_cache or not self.loss_sales_cache[symbol]:
            return None

        # Find earliest and latest wash sale windows
        earliest_start = None
        latest_end = None

        for loss_sale in self.loss_sales_cache[symbol]:
            window_start = loss_sale.sale_date - timedelta(days=30)
            window_end = loss_sale.sale_date + timedelta(days=30)

            if earliest_start is None or window_start < earliest_start:
                earliest_start = window_start

            if latest_end is None or window_end > latest_end:
                latest_end = window_end

        return (earliest_start, latest_end)

    def get_alternative_symbols(self, symbol: str, count: int = 5) -> List[str]:
        """
        Suggest alternative securities that don't trigger wash sales.

        V1 Implementation: Returns a simple list of suggested alternatives
        based on sector/similarity. In production, this would query a
        securities database or API for similar stocks.

        Args:
            symbol: Stock ticker symbol to find alternatives for
            count: Number of alternatives to suggest

        Returns:
            List of alternative ticker symbols
        """
        # V1: Simple sector-based alternatives mapping
        # In production, integrate with market data API for:
        # - Same sector/industry
        # - Similar market cap
        # - Similar performance characteristics

        alternatives_map = {
            # Tech
            "AAPL": ["MSFT", "GOOGL", "META", "NVDA", "AMD"],
            "MSFT": ["AAPL", "GOOGL", "AMZN", "META", "ORCL"],
            "GOOGL": ["META", "AMZN", "MSFT", "AAPL", "NFLX"],
            "META": ["GOOGL", "SNAP", "PINS", "TWTR", "NFLX"],
            "NVDA": ["AMD", "INTC", "QCOM", "AVGO", "TSM"],
            "AMD": ["NVDA", "INTC", "QCOM", "MU", "AVGO"],
            # Finance
            "JPM": ["BAC", "WFC", "C", "GS", "MS"],
            "BAC": ["JPM", "WFC", "C", "USB", "PNC"],
            "GS": ["MS", "JPM", "C", "SCHW", "BLK"],
            # Healthcare
            "JNJ": ["PFE", "UNH", "ABBV", "MRK", "LLY"],
            "PFE": ["JNJ", "MRK", "ABBV", "BMY", "LLY"],
            # Energy
            "XOM": ["CVX", "COP", "SLB", "EOG", "MPC"],
            "CVX": ["XOM", "COP", "PSX", "VLO", "MPC"],
            # Consumer
            "AMZN": ["WMT", "TGT", "COST", "HD", "LOW"],
            "WMT": ["TGT", "COST", "AMZN", "KR", "DG"],
            # Automotive
            "TSLA": ["F", "GM", "RIVN", "LCID", "NIO"],
            "F": ["GM", "TSLA", "STLA", "TM", "HMC"],
        }

        symbol = symbol.upper()
        alternatives = alternatives_map.get(symbol, [])

        # Filter out symbols that also have wash sale issues
        safe_alternatives = [
            alt
            for alt in alternatives
            if alt not in self.loss_sales_cache or not self.loss_sales_cache[alt]
        ]

        # Return requested count
        return safe_alternatives[:count]

    def calculate_disallowed_loss(self, symbol: str) -> float:
        """
        Calculate the total disallowed loss for a symbol.

        This is the sum of all loss amounts for sales that are still
        within the wash sale window.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Total disallowed loss amount
        """
        symbol = symbol.upper()

        if symbol not in self.loss_sales_cache:
            return 0.0

        total_disallowed = 0.0
        current_date = datetime.now()

        for loss_sale in self.loss_sales_cache[symbol]:
            # Check if still within wash sale window
            window_end = loss_sale.sale_date + timedelta(days=30)

            if current_date <= window_end:
                # Still within window, loss is disallowed
                total_disallowed += loss_sale.loss_amount

        return total_disallowed

    def clear_expired_records(self) -> int:
        """
        Remove loss records older than 61 days (outside wash sale window).

        The wash sale window is 30 days before + 30 days after = 61 days total.
        Records older than 61 days from today cannot trigger future wash sales.

        Returns:
            Number of records deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM loss_sales
                    WHERE sale_date < datetime('now', '-61 days')
                """
                )
                deleted_count = cursor.rowcount
                conn.commit()

            # Reload cache
            self._load_loss_sales()

            logger.info(f"Cleared {deleted_count} expired wash sale records")
            return deleted_count

        except Exception as e:
            logger.error(f"Error clearing expired records: {e}")
            return 0

    def get_loss_sales(self, symbol: Optional[str] = None) -> List[LossSale]:
        """
        Get all tracked loss sales, optionally filtered by symbol.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            List of LossSale records
        """
        if symbol:
            symbol = symbol.upper()
            return self.loss_sales_cache.get(symbol, [])

        # Return all loss sales
        all_sales = []
        for sales_list in self.loss_sales_cache.values():
            all_sales.extend(sales_list)

        # Sort by date (most recent first)
        return sorted(all_sales, key=lambda x: x.sale_date, reverse=True)

    def get_affected_symbols(self) -> List[str]:
        """
        Get list of symbols with active wash sale restrictions.

        Returns:
            List of ticker symbols
        """
        return sorted(self.loss_sales_cache.keys())

    def export_to_json(self, filepath: str) -> None:
        """
        Export wash sale data to JSON for tax reporting.

        Args:
            filepath: Path to output JSON file
        """
        try:
            data = {
                "export_date": datetime.now().isoformat(),
                "total_loss_sales": sum(
                    len(sales) for sales in self.loss_sales_cache.values()
                ),
                "affected_symbols": self.get_affected_symbols(),
                "loss_sales": [],
            }

            # Add all loss sales
            for sales_list in self.loss_sales_cache.values():
                for sale in sales_list:
                    sale_dict = asdict(sale)
                    sale_dict["sale_date"] = sale.sale_date.isoformat()
                    data["loss_sales"].append(sale_dict)

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported wash sale data to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            raise

    def get_summary(self) -> Dict[str, any]:
        """
        Get summary of wash sale tracker state.

        Returns:
            Dict with summary statistics
        """
        total_loss_sales = sum(len(sales) for sales in self.loss_sales_cache.values())
        total_disallowed = sum(
            self.calculate_disallowed_loss(symbol) for symbol in self.loss_sales_cache
        )

        return {
            "total_loss_sales": total_loss_sales,
            "affected_symbols": len(self.loss_sales_cache),
            "symbols_list": self.get_affected_symbols(),
            "total_disallowed_loss": total_disallowed,
            "oldest_loss_sale": (
                min(
                    sale.sale_date
                    for sales in self.loss_sales_cache.values()
                    for sale in sales
                )
                if total_loss_sales > 0
                else None
            ),
            "newest_loss_sale": (
                max(
                    sale.sale_date
                    for sales in self.loss_sales_cache.values()
                    for sale in sales
                )
                if total_loss_sales > 0
                else None
            ),
        }
