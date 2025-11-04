"""
Price Feed - Real-time price streaming for DeepStack

Provides WebSocket-based real-time price updates and price alerting.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)


@dataclass
class PriceUpdate:
    """Real-time price update."""

    symbol: str
    price: float
    timestamp: datetime
    volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None


class PriceFeed:
    """
    Real-time price feed manager.

    Handles WebSocket connections to price providers and distributes
    real-time updates to subscribers.
    """

    def __init__(self):
        """
        Initialize price feed.
        """
        self.subscribers: Dict[str, List[Callable[[PriceUpdate], None]]] = {}
        self.websocket_connections: List[websockets.WebSocketServerProtocol] = []
        self.running = False

        logger.info("PriceFeed initialized")

    def subscribe(self, symbol: str, callback: Callable[[PriceUpdate], None]):
        """
        Subscribe to price updates for a symbol.

        Args:
            symbol: Stock symbol
            callback: Function to call with price updates
        """
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []

        self.subscribers[symbol].append(callback)
        logger.debug(f"Subscribed to {symbol} price updates")

    def unsubscribe(self, symbol: str, callback: Callable[[PriceUpdate], None]):
        """
        Unsubscribe from price updates for a symbol.

        Args:
            symbol: Stock symbol
            callback: Function to remove
        """
        if symbol in self.subscribers:
            try:
                self.subscribers[symbol].remove(callback)
                logger.debug(f"Unsubscribed from {symbol} price updates")
            except ValueError:
                logger.warning(f"Callback not found for {symbol} unsubscribe")

    def publish_update(self, update: PriceUpdate):
        """
        Publish price update to all subscribers.

        Args:
            update: Price update to publish
        """
        if update.symbol in self.subscribers:
            for callback in self.subscribers[update.symbol]:
                try:
                    callback(update)
                except Exception as e:
                    logger.error(
                        f"Error in price update callback for {update.symbol}: {e}"
                    )

    async def start_feed(self, symbols: List[str]):
        """
        Start real-time price feed for symbols.

        Args:
            symbols: List of symbols to monitor
        """
        if self.running:
            logger.warning("Price feed already running")
            return

        self.running = True

        # This would connect to real price feeds (WebSocket APIs)
        # For now, simulate with periodic updates
        asyncio.create_task(self._simulate_price_feed(symbols))

        logger.info(f"Started price feed for {len(symbols)} symbols")

    async def stop_feed(self):
        """Stop the price feed."""
        self.running = False

        # Close WebSocket connections
        for ws in self.websocket_connections:
            try:
                await ws.close()
            except Exception:
                pass

        self.websocket_connections.clear()
        logger.info("Price feed stopped")

    async def _simulate_price_feed(self, symbols: List[str]):
        """Simulate price feed with random updates."""
        import random

        while self.running:
            try:
                # Generate random price updates every 1-3 seconds
                for symbol in symbols:
                    # Simulate price movement (±0.5%)
                    base_price = 100 + random.randint(0, 100)  # Mock base price
                    price_change = random.uniform(-0.005, 0.005)  # ±0.5%
                    new_price = base_price * (1 + price_change)

                    update = PriceUpdate(
                        symbol=symbol,
                        price=new_price,
                        timestamp=datetime.now(),
                        volume=random.randint(1000, 10000),
                    )

                    self.publish_update(update)

                # Wait 1-3 seconds before next update
                await asyncio.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.error(f"Error in price feed simulation: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def connect_websocket(self, websocket: websockets.WebSocketServerProtocol):
        """
        Handle new WebSocket connection for real-time updates.

        Args:
            websocket: WebSocket connection
        """
        self.websocket_connections.append(websocket)

        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "connected",
                        "message": "Connected to DeepStack price feed",
                    }
                )
            )

            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get("type") == "subscribe":
                        symbols = data.get("symbols", [])
                        for symbol in symbols:
                            self.subscribe(
                                symbol,
                                lambda update, ws=websocket: self._send_websocket_update(
                                    ws, update
                                ),
                            )

                        await websocket.send(
                            json.dumps({"type": "subscribed", "symbols": symbols})
                        )

                    elif data.get("type") == "unsubscribe":
                        symbols = data.get("symbols", [])
                        for symbol in symbols:
                            # Remove WebSocket from symbol subscribers
                            if symbol in self.subscribers:
                                self.subscribers[symbol] = [
                                    cb
                                    for cb in self.subscribers[symbol]
                                    if getattr(cb, "_websocket", None) != websocket
                                ]

                        await websocket.send(
                            json.dumps({"type": "unsubscribed", "symbols": symbols})
                        )

                except json.JSONDecodeError:
                    await websocket.send(
                        json.dumps({"type": "error", "message": "Invalid JSON message"})
                    )

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)

    def _send_websocket_update(
        self, websocket: websockets.WebSocketServerProtocol, update: PriceUpdate
    ):
        """Send price update to WebSocket client."""
        try:
            message = {
                "type": "price_update",
                "symbol": update.symbol,
                "price": update.price,
                "timestamp": update.timestamp.isoformat(),
                "volume": update.volume,
                "bid": update.bid,
                "ask": update.ask,
            }

            asyncio.create_task(websocket.send(json.dumps(message)))

        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
