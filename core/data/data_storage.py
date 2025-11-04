"""
Data Storage - Persistent data management for DeepStack

Handles database operations, file storage, and data persistence for
trading data, configurations, and analytics.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..config import Config

logger = logging.getLogger(__name__)


class DataStorage:
    """
    Data storage manager for DeepStack.

    Handles:
    - SQLite database for trading data
    - JSON configuration storage
    - CSV export for analytics
    - Data backup and recovery
    """

    def __init__(self, config: Config):
        """
        Initialize data storage.

        Args:
            config: DeepStack configuration
        """
        self.config = config
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

        # Database paths
        self.main_db = self.data_dir / "deepstack.db"
        self.paper_trading_db = self.data_dir / "paper_trading.db"
        self.analytics_db = self.data_dir / "analytics.db"

        # Initialize databases
        self._init_databases()

        logger.info("DataStorage initialized")

    def _init_databases(self):
        """Initialize all databases."""
        self._init_main_database()
        self._init_paper_trading_database()
        self._init_analytics_database()

    def _init_main_database(self):
        """Initialize main application database."""
        try:
            with sqlite3.connect(self.main_db) as conn:
                # System configuration and state
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS system_config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP
                    )
                """
                )

                # Trading sessions
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trading_sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        mode TEXT,
                        status TEXT,
                        notes TEXT
                    )
                """
                )

                # API keys and credentials (encrypted)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS credentials (
                        provider TEXT PRIMARY KEY,
                        api_key_encrypted TEXT,
                        updated_at TIMESTAMP
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing main database: {e}")

    def _init_paper_trading_database(self):
        """Initialize paper trading database."""
        try:
            with sqlite3.connect(self.paper_trading_db) as conn:
                # Positions
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS positions (
                        symbol TEXT PRIMARY KEY,
                        quantity INTEGER,
                        avg_cost REAL,
                        market_value REAL,
                        unrealized_pnl REAL,
                        realized_pnl REAL,
                        updated_at TIMESTAMP
                    )
                """
                )

                # Orders
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        symbol TEXT,
                        action TEXT,
                        quantity INTEGER,
                        order_type TEXT,
                        limit_price REAL,
                        stop_price REAL,
                        status TEXT,
                        filled_quantity INTEGER DEFAULT 0,
                        filled_avg_price REAL,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """
                )

                # Trades
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        symbol TEXT,
                        action TEXT,
                        quantity INTEGER,
                        price REAL,
                        slippage REAL,
                        timestamp TIMESTAMP,
                        order_id TEXT,
                        strategy TEXT,
                        notes TEXT
                    )
                """
                )

                # Daily P&L
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_pnl (
                        date DATE PRIMARY KEY,
                        pnl REAL,
                        trades_count INTEGER,
                        win_rate REAL,
                        updated_at TIMESTAMP
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing paper trading database: {e}")

    def _init_analytics_database(self):
        """Initialize analytics database."""
        try:
            with sqlite3.connect(self.analytics_db) as conn:
                # Performance metrics
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        metric_name TEXT,
                        value REAL,
                        period TEXT,
                        calculated_at TIMESTAMP,
                        PRIMARY KEY (metric_name, period)
                    )
                """
                )

                # Strategy performance
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        strategy_name TEXT,
                        date DATE,
                        pnl REAL,
                        trades_count INTEGER,
                        win_rate REAL,
                        avg_trade REAL,
                        max_drawdown REAL,
                        sharpe_ratio REAL,
                        PRIMARY KEY (strategy_name, date)
                    )
                """
                )

                # Risk metrics
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS risk_metrics (
                        metric_name TEXT,
                        value REAL,
                        timestamp TIMESTAMP,
                        PRIMARY KEY (metric_name, timestamp)
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing analytics database: {e}")

    # Configuration Storage Methods

    def save_config_value(self, key: str, value: str):
        """
        Save configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        try:
            with sqlite3.connect(self.main_db) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, ?)
                """,
                    (key, value, datetime.now()),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving config value {key}: {e}")

    def get_config_value(self, key: str) -> Optional[str]:
        """
        Get configuration value.

        Args:
            key: Configuration key

        Returns:
            Configuration value or None
        """
        try:
            with sqlite3.connect(self.main_db) as conn:
                cursor = conn.execute(
                    "SELECT value FROM system_config WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                return row[0] if row else None

        except Exception as e:
            logger.error(f"Error getting config value {key}: {e}")
            return None

    # Paper Trading Storage Methods

    def save_position(
        self,
        symbol: str,
        quantity: int,
        avg_cost: float,
        market_value: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ):
        """
        Save position data.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            avg_cost: Average cost per share
            market_value: Current market value
            unrealized_pnl: Unrealized P&L
            realized_pnl: Realized P&L
        """
        try:
            with sqlite3.connect(self.paper_trading_db) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO positions
                    (symbol, quantity, avg_cost, market_value, unrealized_pnl, realized_pnl, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        symbol,
                        quantity,
                        avg_cost,
                        market_value,
                        unrealized_pnl,
                        realized_pnl,
                        datetime.now(),
                    ),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving position for {symbol}: {e}")

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all positions.

        Returns:
            List of position dictionaries
        """
        try:
            with sqlite3.connect(self.paper_trading_db) as conn:
                cursor = conn.execute("SELECT * FROM positions")
                rows = cursor.fetchall()

                positions = []
                for row in rows:
                    positions.append(
                        {
                            "symbol": row[0],
                            "quantity": row[1],
                            "avg_cost": row[2],
                            "market_value": row[3],
                            "unrealized_pnl": row[4],
                            "realized_pnl": row[5],
                            "updated_at": row[6],
                        }
                    )

                return positions

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def save_trade(
        self,
        trade_id: str,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        slippage: float,
        order_id: str,
        strategy: str = "",
        notes: str = "",
    ):
        """
        Save trade data.

        Args:
            trade_id: Unique trade identifier
            symbol: Stock symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            price: Execution price
            slippage: Price slippage
            order_id: Related order ID
            strategy: Strategy used
            notes: Additional notes
        """
        try:
            with sqlite3.connect(self.paper_trading_db) as conn:
                conn.execute(
                    """
                    INSERT INTO trades
                    (trade_id, symbol, action, quantity, price, slippage, timestamp, order_id, strategy, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        trade_id,
                        symbol,
                        action,
                        quantity,
                        price,
                        slippage,
                        datetime.now(),
                        order_id,
                        strategy,
                        notes,
                    ),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving trade {trade_id}: {e}")

    def get_trades(
        self, limit: int = 100, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades.

        Args:
            limit: Maximum number of trades to return
            symbol: Optional symbol filter

        Returns:
            List of trade dictionaries
        """
        try:
            with sqlite3.connect(self.paper_trading_db) as conn:
                if symbol:
                    cursor = conn.execute(
                        "SELECT * FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                        (symbol, limit),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)
                    )

                rows = cursor.fetchall()

                trades = []
                for row in rows:
                    trades.append(
                        {
                            "trade_id": row[0],
                            "symbol": row[1],
                            "action": row[2],
                            "quantity": row[3],
                            "price": row[4],
                            "slippage": row[5],
                            "timestamp": row[6],
                            "order_id": row[7],
                            "strategy": row[8],
                            "notes": row[9],
                        }
                    )

                return trades

        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []

    # Analytics Storage Methods

    def save_performance_metric(self, metric_name: str, value: float, period: str):
        """
        Save performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            period: Time period (e.g., 'daily', 'weekly', 'monthly')
        """
        try:
            with sqlite3.connect(self.analytics_db) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO performance_metrics
                    (metric_name, value, period, calculated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (metric_name, value, period, datetime.now()),
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving performance metric {metric_name}: {e}")

    def get_performance_metrics(self, period: str) -> Dict[str, float]:
        """
        Get performance metrics for period.

        Args:
            period: Time period

        Returns:
            Dictionary of metric names to values
        """
        try:
            with sqlite3.connect(self.analytics_db) as conn:
                cursor = conn.execute(
                    "SELECT metric_name, value FROM performance_metrics WHERE period = ?",
                    (period,),
                )
                rows = cursor.fetchall()

                return {row[0]: row[1] for row in rows}

        except Exception as e:
            logger.error(f"Error getting performance metrics for {period}: {e}")
            return {}

    # Export Methods

    def export_trades_to_csv(
        self,
        filepath: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Export trades to CSV file.

        Args:
            filepath: Output CSV file path
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        try:
            trades = self.get_trades(limit=10000)  # Get all trades

            if not trades:
                logger.warning("No trades to export")
                return

            df = pd.DataFrame(trades)

            # Filter by date if specified
            if start_date:
                df = df[df["timestamp"] >= start_date]
            if end_date:
                df = df[df["timestamp"] <= end_date]

            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(df)} trades to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {e}")

    def export_positions_to_csv(self, filepath: str):
        """
        Export positions to CSV file.

        Args:
            filepath: Output CSV file path
        """
        try:
            positions = self.get_positions()

            if not positions:
                logger.warning("No positions to export")
                return

            df = pd.DataFrame(positions)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(df)} positions to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting positions to CSV: {e}")

    # Backup and Recovery

    def backup_databases(self, backup_dir: str):
        """
        Backup all databases to directory.

        Args:
            backup_dir: Backup directory path
        """
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Copy database files
            import shutil

            for db_file in [self.main_db, self.paper_trading_db, self.analytics_db]:
                if db_file.exists():
                    backup_file = backup_path / f"{db_file.stem}_{timestamp}.db"
                    shutil.copy2(db_file, backup_file)

            logger.info(f"Databases backed up to {backup_dir}")

        except Exception as e:
            logger.error(f"Error backing up databases: {e}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage information
        """
        try:
            total_size = 0
            file_count = 0

            for db_file in [self.main_db, self.paper_trading_db, self.analytics_db]:
                if db_file.exists():
                    total_size += db_file.stat().st_size
                    file_count += 1

            return {
                "total_size_bytes": total_size,
                "file_count": file_count,
                "data_directory": str(self.data_dir),
                "databases": {
                    "main": str(self.main_db),
                    "paper_trading": str(self.paper_trading_db),
                    "analytics": str(self.analytics_db),
                },
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                "total_size_bytes": 0,
                "file_count": 0,
                "data_directory": str(self.data_dir),
            }
