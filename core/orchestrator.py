"""
Trading Orchestrator - runs automated paper-mode cycles

Coordinates: screen → analyze → risk-check → execute → monitor
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agents.strategy_agent import StrategyAgent

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Minimal orchestrator to run autonomous cycles in paper mode.
    """

    def __init__(
        self,
        config,
        strategy_agent: Optional[StrategyAgent],
        risk_manager,
        order_manager,
        paper_trader,
    ):
        self.config = config
        self.strategy_agent = strategy_agent or StrategyAgent()
        self.risk_manager = risk_manager
        self.order_manager = order_manager
        self.paper_trader = paper_trader

        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._cadence_s: int = 30
        self._last_run_ts: Optional[datetime] = None
        self._last_action: Optional[str] = None
        self._symbols: List[str] = []

        # Defaults if automation config missing
        try:
            automation = getattr(self.config, "automation", None)
            self._symbols = (
                getattr(automation, "symbols", ["AAPL", "MSFT"])
                if automation
                else ["AAPL", "MSFT"]
            )
            self._cadence_s = (
                int(getattr(automation, "cadence_s", 30)) if automation else 30
            )
        except Exception:
            self._symbols = ["AAPL", "MSFT"]
            self._cadence_s = 30

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "cadence_s": self._cadence_s,
            "last_run_ts": self._last_run_ts.isoformat() if self._last_run_ts else None,
            "last_action": self._last_action,
            "symbols": self._symbols,
        }

    async def start(
        self, cadence_s: Optional[int] = None, symbols: Optional[List[str]] = None
    ):
        if self._running:
            return
        if cadence_s:
            self._cadence_s = cadence_s
        if symbols:
            self._symbols = symbols
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"TradingOrchestrator started (cadence={self._cadence_s}s, symbols={self._symbols})"
        )

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TradingOrchestrator stopped")

    async def _run_loop(self):
        try:
            while self._running:
                await self._run_once()
                await asyncio.sleep(self._cadence_s)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Orchestrator loop error: {e}")

    async def _run_once(self):
        self._last_run_ts = datetime.now()
        self._last_action = "cycle_start"

        for symbol in self._symbols:
            try:
                # Analyze
                analysis = await self.strategy_agent.analyze_stock(symbol)
                self._last_action = f"analyzed:{symbol}:{analysis.recommendation}"

                if analysis.recommendation not in ("BUY", "STRONG_BUY"):
                    continue

                # Get current simulated price
                current_price = await self.paper_trader._get_market_price(symbol)
                if not current_price:
                    continue

                # Risk check (portfolio heat)
                # Use a small default size for smoke (e.g., 1 share) respecting position size
                desired_pct = max(analysis.position_size_pct, 0.005)
                portfolio_value = self.paper_trader.get_portfolio_value()
                quantity = max(1, int((portfolio_value * desired_pct) / current_price))

                heat_check = await self.risk_manager.check_portfolio_heat(
                    symbol, quantity, "BUY", current_price
                )
                if not heat_check.get("approved"):
                    self._last_action = f"risk_reject:{symbol}"
                    continue

                # Execute market buy in paper
                order_id = await self.order_manager.place_market_order(
                    symbol, quantity, "BUY"
                )
                if order_id:
                    self._last_action = f"order_submitted:{symbol}:{order_id}"
                else:
                    self._last_action = f"order_failed:{symbol}"

            except Exception as e:
                logger.error(f"Cycle error for {symbol}: {e}")
