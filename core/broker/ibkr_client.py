"""
IBKR Client - Interactive Brokers integration for DeepStack Trading System

Provides a clean wrapper around ib_insync for paper trading and live trading operations.
Handles connection management, order placement, position tracking, and market data.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ib_insync import (
    IB,
    BarDataList,
    Contract,
    LimitOrder,
    MarketOrder,
    Stock,
    StopOrder,
    Ticker,
)
from ib_insync.contract import ContractDetails
from ib_insync.order import OrderStatus

from ..config import Config

logger = logging.getLogger(__name__)


class IBKRClient:
    """
    Interactive Brokers client wrapper for DeepStack trading operations.

    Handles:
    - Connection management (paper/live trading)
    - Order placement and management
    - Position tracking
    - Market data streaming
    - Account information
    """

    def __init__(self, config: Config):
        """
        Initialize IBKR client.

        Args:
            config: DeepStack configuration object
        """
        self.config = config
        self.ib = IB()
        self.connected = False
        self.account_id = None

        # Connection settings
        self.host = config.ibkr_host or "127.0.0.1"
        self.port = config.ibkr_port or 7497
        self.client_id = config.ibkr_client_id or 1
        self.readonly = config.trading.mode == "paper"

        # Market data subscriptions
        self.subscriptions: Dict[str, Ticker] = {}

        # Callbacks
        self.ib.connectedEvent += self._on_connected
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.errorEvent += self._on_error

        logger.info(
            f"IBKR Client initialized for {'paper' if self.readonly else 'live'} trading"
        )

    async def connect(self) -> bool:
        """
        Connect to IBKR TWS/Gateway.

        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(
                f"Connecting to IBKR at {self.host}:{self.port} (client_id={self.client_id})"
            )

            # Connect to IBKR
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                readonly=self.readonly,
                timeout=30,
            )

            # Wait for connection confirmation
            await asyncio.sleep(2)

            if self.ib.isConnected():
                self.connected = True
                self.account_id = await self._get_account_id()
                logger.info(
                    f"Successfully connected to IBKR - Account: {self.account_id}"
                )
                return True
            else:
                logger.error("Failed to connect to IBKR")
                return False

        except Exception as e:
            logger.error(f"Error connecting to IBKR: {e}")
            return False

    async def disconnect(self):
        """Disconnect from IBKR."""
        if self.connected:
            logger.info("Disconnecting from IBKR")
            self.ib.disconnect()
            self.connected = False
            self.account_id = None

    async def _get_account_id(self) -> Optional[str]:
        """Get the primary account ID."""
        try:
            accounts = await self.ib.managedAccounts()
            if accounts:
                return accounts[0]
        except Exception as e:
            logger.error(f"Error getting account ID: {e}")
        return None

    def _on_connected(self):
        """Handle connection established."""
        logger.info("IBKR connection established")

    def _on_disconnected(self):
        """Handle disconnection."""
        logger.warning("IBKR connection lost")
        self.connected = False

    def _on_error(
        self,
        reqId: int,
        errorCode: int,
        errorString: str,
        contract: Optional[Contract] = None,
    ):
        """Handle IBKR errors."""
        logger.error(f"IBKR Error [{errorCode}]: {errorString}")

    # Account Information Methods

    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary information.

        Returns:
            Dict containing account values (cash, buying power, etc.)
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            account_values = await self.ib.accountSummaryAsync()

            summary = {}
            for av in account_values:
                if av.account == self.account_id:
                    summary[av.tag] = av.value

            return summary

        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}

    async def get_buying_power(self) -> float:
        """
        Get available buying power.

        Returns:
            float: Buying power in dollars
        """
        summary = await self.get_account_summary()
        return float(summary.get("BuyingPower", 0))

    async def get_cash_balance(self) -> float:
        """
        Get cash balance.

        Returns:
            float: Cash balance in dollars
        """
        summary = await self.get_account_summary()
        return float(summary.get("TotalCashValue", 0))

    # Position Methods

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions.

        Returns:
            List of position dictionaries
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            positions = await self.ib.positionsAsync()

            result = []
            for pos in positions:
                if pos.account == self.account_id:
                    result.append(
                        {
                            "symbol": pos.contract.symbol,
                            "position": pos.position,
                            "avg_cost": pos.avgCost,
                            "market_value": pos.marketValue,
                            "unrealized_pnl": pos.unrealizedPNL,
                            "realized_pnl": pos.realizedPNL,
                        }
                    )

            return result

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Position dictionary or None
        """
        positions = await self.get_positions()
        for pos in positions:
            if pos["symbol"] == symbol:
                return pos
        return None

    # Market Data Methods

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Quote dictionary with bid/ask/last
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            contract = Stock(symbol, "SMART", "USD")
            await self.ib.qualifyContractsAsync(contract)

            ticker = self.ib.reqMktData(contract, "", False, False)

            # Wait for data
            await asyncio.sleep(2)

            if ticker.last:
                return {
                    "symbol": symbol,
                    "bid": ticker.bid,
                    "ask": ticker.ask,
                    "last": ticker.last,
                    "volume": ticker.volume,
                    "timestamp": datetime.now(),
                }

        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")

        return None

    async def subscribe_market_data(self, symbols: List[str]) -> Dict[str, Ticker]:
        """
        Subscribe to real-time market data for symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dict of symbol -> Ticker objects
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        subscriptions = {}

        for symbol in symbols:
            try:
                contract = Stock(symbol, "SMART", "USD")
                await self.ib.qualifyContractsAsync(contract)

                ticker = self.ib.reqMktData(contract, "", False, False)
                subscriptions[symbol] = ticker

            except Exception as e:
                logger.error(f"Error subscribing to {symbol}: {e}")

        self.subscriptions.update(subscriptions)
        return subscriptions

    async def unsubscribe_market_data(self, symbols: Optional[List[str]] = None):
        """
        Unsubscribe from market data.

        Args:
            symbols: Specific symbols to unsubscribe, or None for all
        """
        if symbols is None:
            symbols = list(self.subscriptions.keys())

        for symbol in symbols:
            if symbol in self.subscriptions:
                self.ib.cancelMktData(self.subscriptions[symbol])
                del self.subscriptions[symbol]

    # Order Methods

    async def place_market_order(
        self, symbol: str, quantity: int, action: str
    ) -> Optional[str]:
        """
        Place a market order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'

        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(symbol, quantity, action, "MKT")

    async def place_limit_order(
        self, symbol: str, quantity: int, action: str, limit_price: float
    ) -> Optional[str]:
        """
        Place a limit order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            limit_price: Limit price

        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(symbol, quantity, action, "LMT", limit_price)

    async def place_stop_order(
        self, symbol: str, quantity: int, action: str, stop_price: float
    ) -> Optional[str]:
        """
        Place a stop order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            stop_price: Stop price

        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(
            symbol, quantity, action, "STP", stop_price=stop_price
        )

    async def _place_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Optional[str]:
        """
        Internal method to place orders.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            order_type: Order type ('MKT', 'LMT', 'STP')
            limit_price: Limit price (for LMT orders)
            stop_price: Stop price (for STP orders)

        Returns:
            Order ID if successful, None otherwise
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            # Create contract
            contract = Stock(symbol, "SMART", "USD")
            await self.ib.qualifyContractsAsync(contract)

            # Create order
            if order_type == "MKT":
                order = MarketOrder(action, quantity)
            elif order_type == "LMT":
                order = LimitOrder(action, quantity, limit_price)
            elif order_type == "STP":
                order = StopOrder(action, quantity, stop_price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Place order
            trade = self.ib.placeOrder(contract, order)

            # Wait for order confirmation
            await asyncio.sleep(1)

            if trade.orderStatus.status == OrderStatus.Submitted:
                logger.info(
                    f"Order placed: {action} {quantity} {symbol} at {order_type}"
                )
                return str(trade.order.orderId)
            else:
                logger.error(f"Order failed: {trade.orderStatus.status}")
                return None

        except Exception as e:
            logger.error(f"Error placing {order_type} order for {symbol}: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if successful
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            # Find the order
            orders = self.ib.openOrders()
            for order in orders:
                if str(order.orderId) == order_id:
                    self.ib.cancelOrder(order)
                    logger.info(f"Order cancelled: {order_id}")
                    return True

            logger.warning(f"Order not found: {order_id}")
            return False

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    # Historical Data Methods

    async def get_historical_data(
        self, symbol: str, duration: str = "1 D", bar_size: str = "1 min"
    ) -> Optional[BarDataList]:
        """
        Get historical data for symbol.

        Args:
            symbol: Stock symbol
            duration: Duration string (e.g., '1 D', '1 W', '1 M')
            bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour')

        Returns:
            BarDataList with historical bars
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            contract = Stock(symbol, "SMART", "USD")
            await self.ib.qualifyContractsAsync(contract)

            bars = await self.ib.reqHistoricalDataAsync(
                contract=contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )

            return bars

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None

    # Utility Methods

    async def get_contract_details(self, symbol: str) -> Optional[ContractDetails]:
        """
        Get contract details for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            ContractDetails object
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR")

        try:
            contract = Stock(symbol, "SMART", "USD")
            details = await self.ib.reqContractDetailsAsync(contract)

            if details:
                return details[0]
            return None

        except Exception as e:
            logger.error(f"Error getting contract details for {symbol}: {e}")
            return None

    def is_market_open(self) -> bool:
        """
        Check if market is currently open.

        Returns:
            bool: True if market is open
        """
        now = datetime.now()

        # US stock market hours (ET): 9:30 AM - 4:00 PM
        # Simplified check - doesn't account for holidays
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close

    # Context Manager Support

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
