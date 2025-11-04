"""
Order Manager - Handles order placement and management for DeepStack

Manages the lifecycle of orders from creation to execution, with risk checks
and position size validation built in.
"""

import logging
from typing import Any, Dict, List, Optional

from ..config import Config
from ..risk.portfolio_risk import PortfolioRisk
from .ibkr_client import IBKRClient
from .paper_trader import PaperTrader

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Manages order placement and lifecycle for DeepStack trading.

    Features:
    - Pre-trade risk validation
    - Position size limits
    - Order status tracking
    - Automatic bracket order creation
    """

    def __init__(
        self,
        config: Config,
        ibkr_client: Optional[IBKRClient] = None,
        paper_trader: Optional[PaperTrader] = None,
        risk_manager: Optional[PortfolioRisk] = None,
    ):
        """
        Initialize order manager.

        Args:
            config: DeepStack configuration
            ibkr_client: IBKR client for live trading
            paper_trader: Paper trader for paper trading
            risk_manager: Portfolio risk manager
        """
        self.config = config
        self.ibkr = ibkr_client
        self.paper = paper_trader
        self.risk = risk_manager

        self.active_orders: Dict[str, Dict[str, Any]] = {}

        logger.info("Order Manager initialized")

    async def place_market_order(
        self, symbol: str, quantity: int, action: str, validate_risk: bool = True
    ) -> Optional[str]:
        """
        Place a market order with risk validation.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            validate_risk: Whether to validate risk limits

        Returns:
            Order ID if successful, None otherwise
        """
        # Pre-trade validation
        if validate_risk and not await self._validate_order(symbol, quantity, action):
            logger.warning(f"Order validation failed: {action} {quantity} {symbol}")
            return None

        # Place order based on trading mode
        if self.config.trading.mode == "live" and self.ibkr:
            return await self.ibkr.place_market_order(symbol, quantity, action)
        elif self.config.trading.mode == "paper" and self.paper:
            return await self.paper.place_market_order(symbol, quantity, action)
        else:
            logger.error("No valid trading client available")
            return None

    async def place_limit_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        limit_price: float,
        validate_risk: bool = True,
    ) -> Optional[str]:
        """
        Place a limit order with risk validation.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            limit_price: Limit price
            validate_risk: Whether to validate risk limits

        Returns:
            Order ID if successful, None otherwise
        """
        # Pre-trade validation
        if validate_risk and not await self._validate_order(
            symbol, quantity, action, limit_price
        ):
            logger.warning(
                f"Limit order validation failed: {action} {quantity} {symbol} @ ${limit_price}"
            )
            return None

        # Place order based on trading mode
        if self.config.trading.mode == "live" and self.ibkr:
            return await self.ibkr.place_limit_order(
                symbol, quantity, action, limit_price
            )
        elif self.config.trading.mode == "paper" and self.paper:
            return await self.paper.place_limit_order(
                symbol, quantity, action, limit_price
            )
        else:
            logger.error("No valid trading client available")
            return None

    async def place_stop_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        stop_price: float,
        validate_risk: bool = True,
    ) -> Optional[str]:
        """
        Place a stop order with risk validation.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            stop_price: Stop price
            validate_risk: Whether to validate risk limits

        Returns:
            Order ID if successful, None otherwise
        """
        # For stop orders, we mainly validate that we're not creating invalid stops
        if validate_risk and not await self._validate_stop_order(
            symbol, quantity, action, stop_price
        ):
            logger.warning(
                f"Stop order validation failed: {action} {quantity} {symbol} stop @ ${stop_price}"
            )
            return None

        # Place order based on trading mode
        if self.config.trading.mode == "live" and self.ibkr:
            return await self.ibkr.place_stop_order(
                symbol, quantity, action, stop_price
            )
        elif self.config.trading.mode == "paper" and self.paper:
            return await self.paper.place_stop_order(
                symbol, quantity, action, stop_price
            )
        else:
            logger.error("No valid trading client available")
            return None

    async def place_bracket_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        entry_price: float,
        stop_price: float,
        target_price: Optional[float] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Place a bracket order (entry + stop + optional target).

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            entry_price: Entry price (limit order)
            stop_price: Stop loss price
            target_price: Optional profit target price

        Returns:
            Dict with order IDs if successful, None otherwise
        """
        # Validate bracket order
        if not await self._validate_bracket_order(
            symbol, quantity, action, entry_price, stop_price, target_price
        ):
            logger.warning(
                f"Bracket order validation failed: {action} {quantity} {symbol}"
            )
            return None

        # For now, implement as separate orders
        # In production, this would use IBKR's bracket order functionality
        order_ids = {}

        try:
            # Place entry order
            if action == "BUY":
                entry_order_id = await self.place_limit_order(
                    symbol, quantity, "BUY", entry_price
                )
            else:
                entry_order_id = await self.place_limit_order(
                    symbol, quantity, "SELL", entry_price
                )

            if entry_order_id:
                order_ids["entry"] = entry_order_id

                # Place stop order (would be attached in real bracket order)
                stop_order_id = await self.place_stop_order(
                    symbol, quantity, "SELL" if action == "BUY" else "BUY", stop_price
                )
                if stop_order_id:
                    order_ids["stop"] = stop_order_id

                # Place target order if specified
                if target_price:
                    target_order_id = await self.place_limit_order(
                        symbol,
                        quantity,
                        "SELL" if action == "BUY" else "BUY",
                        target_price,
                    )
                    if target_order_id:
                        order_ids["target"] = target_order_id

                logger.info(
                    f"Bracket order placed: {action} {quantity} {symbol} "
                    f"entry@${entry_price} stop@${stop_price}"
                    f"{f' target@${target_price}' if target_price else ''}"
                )
                return order_ids
            else:
                logger.error("Failed to place entry order for bracket")
                return None

        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if successful
        """
        try:
            if self.config.trading.mode == "live" and self.ibkr:
                return await self.ibkr.cancel_order(order_id)
            elif self.config.trading.mode == "paper" and self.paper:
                return await self.paper.cancel_order(order_id)
            else:
                logger.error("No valid trading client available")
                return False
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all orders, optionally for specific symbol.

        Args:
            symbol: Optional symbol to cancel orders for

        Returns:
            Number of orders cancelled
        """
        # This would query open orders and cancel them
        # For now, return 0 as we don't have order tracking implemented yet
        logger.warning("cancel_all_orders not fully implemented")
        return 0

    # Risk Validation Methods

    async def _validate_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        limit_price: Optional[float] = None,
    ) -> bool:
        """
        Validate order against risk limits.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            limit_price: Optional limit price

        Returns:
            bool: True if order passes validation
        """
        try:
            # Get current price for position sizing
            current_price = limit_price
            if not current_price:
                if self.ibkr and self.ibkr.connected:
                    quote = await self.ibkr.get_quote(symbol)
                    current_price = quote.get("last") if quote else None
                elif self.paper:
                    current_price = await self.paper._get_market_price(symbol)

            if not current_price:
                logger.error(f"Could not get price for {symbol}")
                return False

            # Check position size limits
            position_value = quantity * current_price
            max_position_pct = self.config.max_position_size

            # For buys, check if this exceeds position limits
            if action == "BUY":
                portfolio_value = await self._get_portfolio_value()
                if portfolio_value > 0:
                    position_pct = position_value / portfolio_value
                    if position_pct > max_position_pct:
                        logger.warning(
                            f"Position size {position_pct:.1%} exceeds limit {max_position_pct:.1%}"
                        )
                        return False

                # Check concentration limits
                existing_position = await self._get_position(symbol)
                if existing_position:
                    existing_value = (
                        existing_position["quantity"] * existing_position["avg_cost"]
                    )
                    total_value = existing_value + position_value
                    concentration_pct = total_value / portfolio_value
                    max_concentration = self.config.max_concentration or 0.25
                    if concentration_pct > max_concentration:
                        logger.warning(
                            f"Concentration {concentration_pct:.1%} exceeds limit {max_concentration:.1%}"
                        )
                        return False

            # Check portfolio heat if risk manager available
            if self.risk:
                heat_check = await self.risk.check_portfolio_heat(
                    symbol, quantity, action, current_price
                )
                if not heat_check["approved"]:
                    logger.warning(
                        f"Portfolio heat check failed: {heat_check['reason']}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False

    async def _validate_stop_order(
        self, symbol: str, quantity: int, action: str, stop_price: float
    ) -> bool:
        """
        Validate stop order logic.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            stop_price: Stop price

        Returns:
            bool: True if valid
        """
        # For stop orders, mainly check that we have a position to sell
        if action == "SELL":
            position = await self._get_position(symbol)
            if not position or position["quantity"] < quantity:
                logger.warning(f"Insufficient position for stop order: {symbol}")
                return False

        # Additional validation could check stop distance, etc.
        return True

    async def _validate_bracket_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        entry_price: float,
        stop_price: float,
        target_price: Optional[float] = None,
    ) -> bool:
        """
        Validate bracket order logic.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            action: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_price: Stop price
            target_price: Optional target price

        Returns:
            bool: True if valid
        """
        # Validate entry vs stop makes sense
        if action == "BUY":
            if stop_price >= entry_price:
                logger.warning("Stop price must be below entry price for buy orders")
                return False
            if target_price and target_price <= entry_price:
                logger.warning("Target price must be above entry price for buy orders")
                return False
        else:  # SELL
            if stop_price <= entry_price:
                logger.warning("Stop price must be above entry price for sell orders")
                return False
            if target_price and target_price >= entry_price:
                logger.warning("Target price must be below entry price for sell orders")
                return False

        # Validate risk/reward ratio
        risk = abs(entry_price - stop_price)
        if target_price:
            reward = abs(target_price - entry_price)
            rr_ratio = reward / risk
            min_rr_ratio = 2.0  # Require at least 2:1 reward to risk
            if rr_ratio < min_rr_ratio:
                logger.warning(
                    f"Risk/reward ratio {rr_ratio:.1f} below minimum {min_rr_ratio}"
                )
                return False

        return True

    # Helper Methods

    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        if self.config.trading.mode == "live" and self.ibkr:
            summary = await self.ibkr.get_account_summary()
            return float(summary.get("NetLiquidation", 0))
        elif self.config.trading.mode == "paper" and self.paper:
            return self.paper.get_portfolio_value()
        return 0

    async def _get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position for symbol."""
        if self.config.trading.mode == "live" and self.ibkr:
            return await self.ibkr.get_position(symbol)
        elif self.config.trading.mode == "paper" and self.paper:
            return self.paper.get_position(symbol)
        return None

    # Order Status Methods

    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an order.

        Args:
            order_id: Order ID

        Returns:
            Order status dictionary or None
        """
        # This would query the broker for order status
        # For now, return basic status
        logger.warning("get_order_status not fully implemented")
        return {"order_id": order_id, "status": "UNKNOWN"}

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        Get all open orders.

        Returns:
            List of open order dictionaries
        """
        # This would query open orders from broker
        logger.warning("get_open_orders not fully implemented")
        return []

    # Utility Methods

    def calculate_position_size(
        self, symbol: str, entry_price: float, stop_price: float, risk_pct: float = 0.02
    ) -> int:
        """
        Calculate position size based on risk management rules.

        Args:
            symbol: Stock symbol
            entry_price: Entry price
            stop_price: Stop loss price
            risk_pct: Risk percentage (default 2%)

        Returns:
            Number of shares to trade
        """
        risk_amount = self._get_portfolio_value() * risk_pct
        risk_per_share = abs(entry_price - stop_price)

        if risk_per_share == 0:
            return 0

        shares = int(risk_amount / risk_per_share)

        # Apply maximum position limits
        max_position_value = self._get_portfolio_value() * self.config.max_position_size
        max_shares_by_value = int(max_position_value / entry_price)

        return min(shares, max_shares_by_value)
