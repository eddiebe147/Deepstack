"""
FastAPI server for DeepStack Trading System

Provides REST/WebSocket API for the CLI interface to communicate with
the trading engine, agents, and market data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .broker.ibkr_client import IBKRClient
from .broker.order_manager import OrderManager
from .broker.paper_trader import PaperTrader
from .config import get_config

logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class QuoteRequest(BaseModel):
    symbol: str


class QuoteResponse(BaseModel):
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    volume: Optional[int]
    timestamp: datetime


class PositionResponse(BaseModel):
    symbol: str
    position: int
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float


class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    action: str  # 'BUY' or 'SELL'
    order_type: str = "MKT"  # 'MKT', 'LMT', 'STP'
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


class OrderResponse(BaseModel):
    order_id: Optional[str]
    status: str
    message: str


class AccountSummaryResponse(BaseModel):
    cash: float
    buying_power: float
    portfolio_value: float
    day_pnl: float
    total_pnl: float


class DeepStackAPIServer:
    """
    FastAPI server for DeepStack trading system.

    Provides endpoints for:
    - Health checks
    - Market data
    - Order placement
    - Position/portfolio queries
    - Real-time updates via WebSocket
    """

    def __init__(self):
        self.config = get_config()
        self.app = FastAPI(title="DeepStack Trading API", version="1.0.0")

        # Initialize components
        self.ibkr_client: Optional[IBKRClient] = None
        self.paper_trader: Optional[PaperTrader] = None
        self.order_manager: Optional[OrderManager] = None

        # WebSocket connections
        self.websocket_connections: List[WebSocket] = []

        self._setup_middleware()
        self._setup_routes()
        self._setup_websocket()

        # Initialize trading components synchronously
        self._initialize_components()

        logger.info("DeepStack API Server initialized")

    def _setup_middleware(self):
        """Setup CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(status="healthy", timestamp=datetime.now())

        @self.app.get("/quote/{symbol}", response_model=QuoteResponse)
        async def get_quote(symbol: str):
            """Get current quote for symbol."""
            try:
                quote = None
                if self.ibkr_client and self.ibkr_client.connected:
                    quote = await self.ibkr_client.get_quote(symbol)
                elif self.paper_trader:
                    price = await self.paper_trader._get_market_price(symbol)
                    if price is not None:
                        # Provide basic quote fields for paper mode
                        quote = {
                            "symbol": symbol,
                            "bid": price - 0.02,
                            "ask": price + 0.02,
                            "last": price,
                            "volume": 0,
                            "timestamp": datetime.now(),
                        }

                if quote:
                    return QuoteResponse(**quote)
                else:
                    raise HTTPException(
                        status_code=404, detail=f"Quote not available for {symbol}"
                    )
            except Exception as e:
                logger.error(f"Error getting quote for {symbol}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/positions", response_model=List[PositionResponse])
        async def get_positions():
            """Get current positions."""
            try:
                positions = []
                if self.config.trading.mode == "live" and self.ibkr_client:
                    ibkr_positions = await self.ibkr_client.get_positions()
                    positions = [PositionResponse(**pos) for pos in ibkr_positions]
                elif self.config.trading.mode == "paper" and self.paper_trader:
                    paper_positions = self.paper_trader.get_positions()
                    positions = [PositionResponse(**pos) for pos in paper_positions]

                return positions
            except Exception as e:
                logger.error(f"Error getting positions: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/account", response_model=AccountSummaryResponse)
        async def get_account_summary():
            """Get account summary."""
            try:
                summary = AccountSummaryResponse(
                    cash=0.0,
                    buying_power=0.0,
                    portfolio_value=0.0,
                    day_pnl=0.0,
                    total_pnl=0.0,
                )

                if self.config.trading.mode == "live" and self.ibkr_client:
                    account_data = await self.ibkr_client.get_account_summary()
                    summary.cash = float(account_data.get("TotalCashValue", 0))
                    summary.buying_power = await self.ibkr_client.get_buying_power()
                elif self.config.trading.mode == "paper" and self.paper_trader:
                    summary.cash = self.paper_trader.cash
                    summary.buying_power = self.paper_trader.get_buying_power()
                    summary.portfolio_value = self.paper_trader.get_portfolio_value()

                return summary
            except Exception as e:
                logger.error(f"Error getting account summary: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/orders", response_model=OrderResponse)
        async def place_order(order: OrderRequest):
            """Place an order."""
            try:
                if not self.order_manager:
                    raise HTTPException(
                        status_code=500, detail="Order manager not initialized"
                    )

                order_id = None

                if order.order_type == "MKT":
                    order_id = await self.order_manager.place_market_order(
                        order.symbol, order.quantity, order.action
                    )
                elif order.order_type == "LMT":
                    if order.limit_price is None:
                        raise HTTPException(
                            status_code=400,
                            detail="Limit price required for limit orders",
                        )
                    order_id = await self.order_manager.place_limit_order(
                        order.symbol, order.quantity, order.action, order.limit_price
                    )
                elif order.order_type == "STP":
                    if order.stop_price is None:
                        raise HTTPException(
                            status_code=400,
                            detail="Stop price required for stop orders",
                        )
                    order_id = await self.order_manager.place_stop_order(
                        order.symbol, order.quantity, order.action, order.stop_price
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported order type: {order.order_type}",
                    )

                if order_id:
                    return OrderResponse(
                        order_id=order_id,
                        status="submitted",
                        message=f"Order {order_id} submitted successfully",
                    )
                else:
                    return OrderResponse(
                        order_id=None,
                        status="failed",
                        message="Order submission failed",
                    )

            except Exception as e:
                logger.error(f"Error placing order: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/orders/{order_id}")
        async def cancel_order(order_id: str):
            """Cancel an order."""
            try:
                if not self.order_manager:
                    raise HTTPException(
                        status_code=500, detail="Order manager not initialized"
                    )

                success = await self.order_manager.cancel_order(order_id)

                if success:
                    return {"status": "cancelled", "order_id": order_id}
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Order {order_id} not found or could not be cancelled",
                    )

            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _setup_websocket(self):
        """Setup WebSocket endpoint for real-time updates."""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                while True:
                    # Keep connection alive and listen for messages
                    data = await websocket.receive_text()

                    # Echo back for now - could handle commands later
                    await websocket.send_text(f"Echo: {data}")

            except WebSocketDisconnect:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

    async def broadcast_update(self, update_type: str, data: Dict[str, Any]):
        """
        Broadcast update to all connected WebSocket clients.

        Args:
            update_type: Type of update (e.g., 'position', 'quote', 'order')
            data: Update data
        """
        message = {
            "type": update_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)

    def _initialize_components(self):
        """Initialize trading components synchronously."""
        try:
            # Initialize IBKR client
            if (
                self.config.trading.mode == "live"
                or self.config.trading.mode == "paper"
            ):
                self.ibkr_client = IBKRClient(self.config)

            # Initialize paper trader
            if self.config.trading.mode == "paper":
                self.paper_trader = PaperTrader(self.config, self.ibkr_client)

            # Initialize order manager
            from ..risk.portfolio_risk import PortfolioRisk

            risk_manager = PortfolioRisk(self.config)
            self.order_manager = OrderManager(
                self.config, self.ibkr_client, self.paper_trader, risk_manager
            )

            logger.info("Trading components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing trading components: {e}")
            # Don't raise - allow server to start even if components fail

    async def initialize_trading_components(self):
        """Initialize trading components (IBKR client, paper trader, etc.)."""
        try:
            # Initialize IBKR client
            if (
                self.config.trading.mode == "live"
                or self.config.trading.mode == "paper"
            ):
                self.ibkr_client = IBKRClient(self.config)
                if self.config.trading.mode == "live":
                    # Only connect for live trading
                    connected = await self.ibkr_client.connect()
                    if not connected:
                        logger.warning("Failed to connect to IBKR for live trading")

            # Initialize paper trader
            if self.config.trading.mode == "paper":
                self.paper_trader = PaperTrader(self.config, self.ibkr_client)

            # Initialize order manager
            from ..risk.portfolio_risk import PortfolioRisk

            risk_manager = PortfolioRisk(self.config)
            self.order_manager = OrderManager(
                self.config, self.ibkr_client, self.paper_trader, risk_manager
            )

            logger.info("Trading components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing trading components: {e}")
            raise

    async def shutdown(self):
        """Shutdown the server and cleanup connections."""
        logger.info("Shutting down DeepStack API Server")

        # Close WebSocket connections
        for websocket in self.websocket_connections:
            try:
                await websocket.close()
            except Exception:
                pass

        # Disconnect IBKR client
        if self.ibkr_client:
            await self.ibkr_client.disconnect()

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app


# Global server instance
_server_instance: Optional[DeepStackAPIServer] = None


def get_server() -> DeepStackAPIServer:
    """Get the global API server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = DeepStackAPIServer()
    return _server_instance


def create_app() -> FastAPI:
    """Create and return FastAPI application."""
    server = get_server()
    return server.get_app()
