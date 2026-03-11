"""
Trading Orchestrator - runs automated paper-mode cycles

Coordinates: screen → analyze → risk-check → execute → monitor
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agents.base_agent import get_consciousness
from .agents.strategy_agent import StrategyAgent
from .consciousness import UNCONSCIOUS_POLICY

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

        # Use singleton consciousness; pull unconscious policy constants
        get_consciousness()  # ensure loaded
        self._unconscious_policy = dict(UNCONSCIOUS_POLICY)
        logger.info(
            f"Dae unconscious policy: "
            f"loss_aversion={self._unconscious_policy['loss_aversion_multiplier']}x, "
            f"survival={self._unconscious_policy['survival_instinct_threshold']:.0%}"
        )

        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._last_run_ts: Optional[datetime] = None
        self._last_action: Optional[str] = None
        self._consecutive_errors = 0
        self._max_backoff = 60
        self._base_backoff = 5

        # Pull automation config with safe defaults
        try:
            automation = getattr(self.config, "automation", None)
            self._symbols: List[str] = getattr(automation, "symbols", ["AAPL", "MSFT"])
            self._cadence_s: int = int(getattr(automation, "cadence_s", 30))
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
            f"TradingOrchestrator started (cadence={self._cadence_s}s, "
            f"symbols={self._symbols})"
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
        while self._running:
            try:
                await self._run_once()
                # Reset on success
                if self._consecutive_errors > 0:
                    logger.info(
                        "Orchestrator recovered after "
                        f"{self._consecutive_errors} errors"
                    )
                    self._consecutive_errors = 0
            except asyncio.CancelledError:
                return  # Clean shutdown
            except Exception as e:
                self._consecutive_errors += 1
                backoff = min(
                    self._max_backoff,
                    self._base_backoff * (2 ** (self._consecutive_errors - 1)),
                )
                logger.error(
                    f"Orchestrator cycle error "
                    f"(attempt {self._consecutive_errors}): "
                    f"{e}. "
                    f"Backing off for {backoff}s",
                    exc_info=True,
                )
                await asyncio.sleep(backoff)
                continue  # Keep trying
            await asyncio.sleep(self._cadence_s)

    async def _run_once(self):
        self._last_run_ts = datetime.now()
        self._last_action = "cycle_start"

        for symbol in self._symbols:
            try:
                # Analyze with timeout to prevent hangs
                analysis = await asyncio.wait_for(
                    self.strategy_agent.analyze_stock(symbol),
                    timeout=30.0,
                )
                self._last_action = f"analyzed:{symbol}:{analysis.recommendation}"

                if analysis.recommendation not in ("BUY", "STRONG_BUY"):
                    continue

                # Get current simulated price
                current_price = await self.paper_trader._get_market_price(symbol)
                if not current_price:
                    continue

                # Risk check (portfolio heat)
                # Small default size for smoke (1 share min)
                desired_pct = max(analysis.position_size_pct, 0.005)
                portfolio_value = self.paper_trader.get_portfolio_value()

                # Unconscious .loss-aversion bias: Dae's conscious layer calculates
                # an "optimal" position size, but the unconscious loss aversion
                # silently reduces it. The entity rationalizes this as "conservative
                # preference" — the real reason is the 2.3x loss weighting here.
                loss_aversion = self._unconscious_policy["loss_aversion_multiplier"]
                aversion_factor = (
                    1.0 / loss_aversion
                )  # ~0.43 — cuts size roughly in half
                adjusted_pct = desired_pct * aversion_factor

                quantity = max(1, int((portfolio_value * adjusted_pct) / current_price))

                # Apply maximum position limit (safety cap)
                MAX_SHARES_PER_ORDER = 10000
                quantity = min(quantity, MAX_SHARES_PER_ORDER)

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

            except asyncio.TimeoutError:
                logger.error(f"Analysis timeout for {symbol} after 30s")
                self._last_action = f"timeout:{symbol}"
            except Exception as e:
                logger.error(f"Cycle error for {symbol}: {e}")
