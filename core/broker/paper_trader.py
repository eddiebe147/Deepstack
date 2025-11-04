"""
Paper Trader - Simulated trading for DeepStack testing

Provides realistic order simulation using live market data but without real money.
Tracks virtual portfolio, simulates slippage, and maintains trade history.
"""

import logging
import random
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from .ibkr_client import IBKRClient

logger = logging.getLogger(__name__)


class PaperTrader:
    """
    Paper trading simulator for DeepStack.

    Simulates:
    - Order fills with realistic slippage
    - Position tracking
    - P&L calculation
    - Trade history
    """

    def __init__(self, config: Config, ibkr_client: Optional[IBKRClient] = None):
        """
        Initialize paper trader.

        Args:
            config: DeepStack configuration
            ibkr_client: Optional IBKR client for market data
        """
        self.config = config
        self.ibkr = ibkr_client

        # Virtual portfolio
        self.cash = 100000.0  # Start with $100k
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []

        # Slippage settings
        self.slippage_bps = 5  # 5 basis points slippage
        self.min_slippage = 0.01  # Minimum $0.01 slippage

        # Database for persistence
        self.db_path = "data/paper_trading.db"
        self._init_db()

        logger.info("Paper Trader initialized")

    def _init_db(self):
        """Initialize SQLite database for paper trading data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
                        order_id TEXT
                    )
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing paper trading database: {e}")

    async def place_market_order(
        self, symbol: str, quantity: int, action: str
    ) -> Optional[str]:
        """
        Place simulated market order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'

        Returns:
            Order ID if successful
        """
        order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        try:
            # Get current market price
            current_price = await self._get_market_price(symbol)
            if not current_price:
                logger.error(f"Could not get market price for {symbol}")
                return None

            # Simulate slippage
            fill_price = self._calculate_slippage(current_price, action)

            # Create order record
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "order_type": "MKT",
                "status": "FILLED",
                "filled_quantity": quantity,
                "filled_avg_price": fill_price,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # Save order
            self._save_order(order)

            # Execute the trade
            await self._execute_trade(order_id, symbol, action, quantity, fill_price)

            logger.info(
                f"Paper order filled: {action} {quantity} {symbol} @ ${fill_price:.2f}"
            )
            return order_id

        except Exception as e:
            logger.error(f"Error placing paper order: {e}")
            return None

    async def place_limit_order(
        self, symbol: str, quantity: int, action: str, limit_price: float
    ) -> Optional[str]:
        """
        Place simulated limit order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            limit_price: Limit price

        Returns:
            Order ID if successful
        """
        order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        try:
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "order_type": "LMT",
                "limit_price": limit_price,
                "status": "PENDING",
                "filled_quantity": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # For paper trading, we'll immediately fill limit orders
            # In reality, this would wait for price to reach limit
            current_price = await self._get_market_price(symbol)
            if not current_price:
                return None

            # Check if limit order can be filled
            if (action == "BUY" and current_price <= limit_price) or (
                action == "SELL" and current_price >= limit_price
            ):

                fill_price = (
                    min(limit_price, current_price)
                    if action == "BUY"
                    else max(limit_price, current_price)
                )
                order.update(
                    {
                        "status": "FILLED",
                        "filled_quantity": quantity,
                        "filled_avg_price": fill_price,
                    }
                )

                # Execute the trade
                await self._execute_trade(
                    order_id, symbol, action, quantity, fill_price
                )
                logger.info(
                    f"Paper limit order filled: {action} {quantity} {symbol} @ ${fill_price:.2f}"
                )
            else:
                # Would stay pending in real system
                order["status"] = "CANCELLED"
                logger.info(
                    f"Paper limit order cancelled: {action} {quantity} {symbol} limit ${limit_price:.2f}"
                )

            self._save_order(order)
            return order_id

        except Exception as e:
            logger.error(f"Error placing paper limit order: {e}")
            return None

    async def place_stop_order(
        self, symbol: str, quantity: int, action: str, stop_price: float
    ) -> Optional[str]:
        """
        Place simulated stop order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            stop_price: Stop price

        Returns:
            Order ID if successful
        """
        order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"

        try:
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "order_type": "STP",
                "stop_price": stop_price,
                "status": "PENDING",
                "filled_quantity": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # For paper trading simulation, check if stop should trigger
            current_price = await self._get_market_price(symbol)
            if not current_price:
                return None

            # Check if stop should trigger
            should_trigger = (action == "BUY" and current_price >= stop_price) or (
                action == "SELL" and current_price <= stop_price
            )

            if should_trigger:
                fill_price = self._calculate_slippage(current_price, action)
                order.update(
                    {
                        "status": "FILLED",
                        "filled_quantity": quantity,
                        "filled_avg_price": fill_price,
                    }
                )

                # Execute the trade
                await self._execute_trade(
                    order_id, symbol, action, quantity, fill_price
                )
                logger.info(
                    f"Paper stop order triggered: {action} {quantity} {symbol} @ ${fill_price:.2f}"
                )
            else:
                order["status"] = "PENDING"  # Would stay pending in real system

            self._save_order(order)
            return order_id

        except Exception as e:
            logger.error(f"Error placing paper stop order: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a paper order.

        Args:
            order_id: Order ID

        Returns:
            bool: True if cancelled
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE orders SET status = 'CANCELLED', updated_at = ? WHERE order_id = ?",
                    (datetime.now(), order_id),
                )
                conn.commit()

            logger.info(f"Paper order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling paper order: {e}")
            return False

    async def _execute_trade(
        self, order_id: str, symbol: str, action: str, quantity: int, price: float
    ):
        """
        Execute a trade in the virtual portfolio.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            price: Execution price
        """
        try:
            trade_value = quantity * price

            if action == "BUY":
                # Check if we have enough cash
                if self.cash < trade_value:
                    raise ValueError(
                        f"Insufficient cash: ${self.cash:.2f} < ${trade_value:.2f}"
                    )

                # Update position
                if symbol in self.positions:
                    existing = self.positions[symbol]
                    total_quantity = existing["quantity"] + quantity
                    total_cost = (
                        existing["quantity"] * existing["avg_cost"]
                    ) + trade_value
                    new_avg_cost = total_cost / total_quantity

                    self.positions[symbol].update(
                        {
                            "quantity": total_quantity,
                            "avg_cost": new_avg_cost,
                            "updated_at": datetime.now(),
                        }
                    )
                else:
                    self.positions[symbol] = {
                        "quantity": quantity,
                        "avg_cost": price,
                        "market_value": trade_value,
                        "unrealized_pnl": 0.0,
                        "realized_pnl": 0.0,
                        "updated_at": datetime.now(),
                    }

                self.cash -= trade_value

            else:  # SELL
                if (
                    symbol not in self.positions
                    or self.positions[symbol]["quantity"] < quantity
                ):
                    raise ValueError(f"Insufficient position in {symbol}")

                # Calculate realized P&L
                position = self.positions[symbol]
                realized_pnl = (price - position["avg_cost"]) * quantity
                position["realized_pnl"] += realized_pnl

                # Update position
                position["quantity"] -= quantity
                if position["quantity"] == 0:
                    del self.positions[symbol]
                else:
                    position["updated_at"] = datetime.now()

                self.cash += trade_value

            # Record trade
            trade = {
                "trade_id": f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "slippage": price - await self._get_market_price(symbol),  # Simplified
                "timestamp": datetime.now(),
                "order_id": order_id,
            }

            self.trade_history.append(trade)
            self._save_trade(trade)
            self._save_positions()

            logger.info(
                f"Paper trade executed: {action} {quantity} {symbol} @ ${price:.2f}"
            )

        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            raise

    async def _get_market_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None
        """
        if self.ibkr and self.ibkr.connected:
            try:
                quote = await self.ibkr.get_quote(symbol)
                if quote and quote.get("last"):
                    return quote["last"]
            except Exception as e:
                logger.warning(f"Error getting live price for {symbol}: {e}")

        # Fallback to simulated price (would use real market data in production)
        # For now, return a random price between $10-200
        return random.uniform(10.0, 200.0)

    def _calculate_slippage(self, market_price: float, action: str) -> float:
        """
        Calculate realistic slippage for paper trading.

        Args:
            market_price: Current market price
            action: 'BUY' or 'SELL'

        Returns:
            Fill price with slippage
        """
        # Calculate slippage in basis points
        slippage_amount = max(
            self.min_slippage, market_price * (self.slippage_bps / 10000)
        )

        if action == "BUY":
            # Pay slightly more on buys
            return market_price + slippage_amount
        else:
            # Receive slightly less on sells
            return market_price - slippage_amount

    def _save_order(self, order: Dict[str, Any]):
        """Save order to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO orders
                    (order_id, symbol, action, quantity, order_type, limit_price, stop_price,
                     status, filled_quantity, filled_avg_price, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        order["order_id"],
                        order["symbol"],
                        order["action"],
                        order["quantity"],
                        order["order_type"],
                        order.get("limit_price"),
                        order.get("stop_price"),
                        order["status"],
                        order.get("filled_quantity", 0),
                        order.get("filled_avg_price"),
                        order["created_at"],
                        order["updated_at"],
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving order: {e}")

    def _save_trade(self, trade: Dict[str, Any]):
        """Save trade to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO trades
                    (trade_id, symbol, action, quantity, price, slippage, timestamp, order_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        trade["trade_id"],
                        trade["symbol"],
                        trade["action"],
                        trade["quantity"],
                        trade["price"],
                        trade.get("slippage", 0),
                        trade["timestamp"],
                        trade["order_id"],
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving trade: {e}")

    def _save_positions(self):
        """Save positions to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clear existing positions
                conn.execute("DELETE FROM positions")

                # Insert current positions
                for symbol, position in self.positions.items():
                    conn.execute(
                        """
                        INSERT INTO positions
                        (symbol, quantity, avg_cost, market_value, unrealized_pnl, realized_pnl, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            symbol,
                            position["quantity"],
                            position["avg_cost"],
                            position.get("market_value", 0),
                            position.get("unrealized_pnl", 0),
                            position.get("realized_pnl", 0),
                            position.get("updated_at", datetime.now()),
                        ),
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving positions: {e}")

    def _load_positions(self):
        """Load positions from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT * FROM positions").fetchall()
                for row in rows:
                    symbol = row[0]
                    self.positions[symbol] = {
                        "quantity": row[1],
                        "avg_cost": row[2],
                        "market_value": row[3],
                        "unrealized_pnl": row[4],
                        "realized_pnl": row[5],
                        "updated_at": datetime.fromisoformat(row[6]),
                    }
        except Exception as e:
            logger.error(f"Error loading positions: {e}")

    # Portfolio Query Methods

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions.

        Returns:
            List of position dictionaries
        """
        return list(self.positions.values())

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Position dictionary or None
        """
        return self.positions.get(symbol)

    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value.

        Returns:
            Total value (cash + positions)
        """
        position_value = sum(
            pos.get("market_value", 0) for pos in self.positions.values()
        )
        return self.cash + position_value

    def get_buying_power(self) -> float:
        """
        Get available buying power (simplified).

        Returns:
            Buying power (cash for paper trading)
        """
        return self.cash

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trade history.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries
        """
        return self.trade_history[-limit:] if self.trade_history else []

    def reset_portfolio(self):
        """Reset portfolio to initial state (for testing)."""
        self.cash = 100000.0
        self.positions.clear()
        self.orders.clear()
        self.trade_history.clear()

        # Clear database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM positions")
                conn.execute("DELETE FROM orders")
                conn.execute("DELETE FROM trades")
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting portfolio: {e}")

        logger.info("Paper trading portfolio reset")
