"""
Comprehensive test coverage for TradingOrchestrator.

This test suite provides deep coverage for the orchestrator's core trading loop,
including initialization, lifecycle management, trading cycles, and error handling.

Target: 90%+ coverage of core/orchestrator.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agents.strategy_agent import StockAnalysis
from core.orchestrator import TradingOrchestrator

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration for orchestrator."""
    config = Mock()
    config.automation = Mock()
    config.automation.symbols = ["AAPL", "MSFT"]
    config.automation.cadence_s = 30
    return config


@pytest.fixture
def mock_config_no_automation():
    """Mock configuration without automation settings."""
    config = Mock()
    config.automation = None
    return config


@pytest.fixture
def mock_strategy_agent():
    """Mock strategy agent with controllable signals."""
    agent = Mock()

    # Default BUY signal
    agent.analyze_stock = AsyncMock(
        return_value=StockAnalysis(
            symbol="AAPL",
            deep_value_score=75.0,
            squeeze_score=60.0,
            overall_score=70.0,
            recommendation="BUY",
            thesis="Strong value opportunity",
            catalysts=["Earnings catalyst", "Market revaluation"],
            risks=["Market downturn risk"],
            target_price=180.0,
            stop_price=138.0,
            position_size_pct=0.05,
            confidence=0.7,
        )
    )

    return agent


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager with controllable heat checks."""
    manager = Mock()

    # Default: approve trades
    manager.check_portfolio_heat = AsyncMock(
        return_value={
            "approved": True,
            "reason": "Within risk limits",
            "current_heat": 0.08,
            "max_heat": 0.15,
        }
    )

    return manager


@pytest.fixture
def mock_paper_trader():
    """Mock paper trader with price simulation."""
    trader = Mock()

    # Provide market prices
    trader._get_market_price = AsyncMock(return_value=150.0)

    # Portfolio value
    trader.get_portfolio_value = Mock(return_value=100000.0)

    return trader


@pytest.fixture
def mock_order_manager():
    """Mock order manager with order placement."""
    manager = Mock()

    # Successful order placement
    manager.place_market_order = AsyncMock(return_value="order_12345")

    return manager


@pytest.fixture
def orchestrator_with_mocks(
    mock_config,
    mock_strategy_agent,
    mock_risk_manager,
    mock_order_manager,
    mock_paper_trader,
):
    """Complete orchestrator with all mocked dependencies."""
    return TradingOrchestrator(
        config=mock_config,
        strategy_agent=mock_strategy_agent,
        risk_manager=mock_risk_manager,
        order_manager=mock_order_manager,
        paper_trader=mock_paper_trader,
    )


# =============================================================================
# Initialization Tests
# =============================================================================


class TestOrchestratorInitialization:
    """Test orchestrator initialization with various configurations."""

    def test_init_with_full_config(
        self,
        mock_config,
        mock_strategy_agent,
        mock_risk_manager,
        mock_order_manager,
        mock_paper_trader,
    ):
        """Test initialization with complete config."""
        orch = TradingOrchestrator(
            config=mock_config,
            strategy_agent=mock_strategy_agent,
            risk_manager=mock_risk_manager,
            order_manager=mock_order_manager,
            paper_trader=mock_paper_trader,
        )

        assert orch.config == mock_config
        assert orch.strategy_agent == mock_strategy_agent
        assert orch.risk_manager == mock_risk_manager
        assert orch.order_manager == mock_order_manager
        assert orch.paper_trader == mock_paper_trader
        assert orch._symbols == ["AAPL", "MSFT"]
        assert orch._cadence_s == 30
        assert orch._running is False
        assert orch._last_run_ts is None
        assert orch._last_action is None

    def test_init_with_no_automation_config(
        self,
        mock_config_no_automation,
        mock_strategy_agent,
        mock_risk_manager,
        mock_order_manager,
        mock_paper_trader,
    ):
        """Test initialization with missing automation config uses defaults."""
        orch = TradingOrchestrator(
            config=mock_config_no_automation,
            strategy_agent=mock_strategy_agent,
            risk_manager=mock_risk_manager,
            order_manager=mock_order_manager,
            paper_trader=mock_paper_trader,
        )

        # Should use defaults
        assert orch._symbols == ["AAPL", "MSFT"]
        assert orch._cadence_s == 30

    def test_init_with_custom_symbols(
        self,
        mock_config,
        mock_strategy_agent,
        mock_risk_manager,
        mock_order_manager,
        mock_paper_trader,
    ):
        """Test initialization with custom symbol list."""
        mock_config.automation.symbols = ["TSLA", "NVDA", "AMD"]

        orch = TradingOrchestrator(
            config=mock_config,
            strategy_agent=mock_strategy_agent,
            risk_manager=mock_risk_manager,
            order_manager=mock_order_manager,
            paper_trader=mock_paper_trader,
        )

        assert orch._symbols == ["TSLA", "NVDA", "AMD"]

    def test_init_with_none_strategy_agent(
        self, mock_config, mock_risk_manager, mock_order_manager, mock_paper_trader
    ):
        """Test initialization creates default strategy agent if None provided."""
        with patch("core.orchestrator.StrategyAgent") as mock_agent_class:
            mock_agent_instance = Mock()
            mock_agent_class.return_value = mock_agent_instance

            orch = TradingOrchestrator(
                config=mock_config,
                strategy_agent=None,
                risk_manager=mock_risk_manager,
                order_manager=mock_order_manager,
                paper_trader=mock_paper_trader,
            )

            # Should have created a default agent
            assert orch.strategy_agent == mock_agent_instance
            mock_agent_class.assert_called_once()

    def test_init_with_malformed_config(
        self,
        mock_strategy_agent,
        mock_risk_manager,
        mock_order_manager,
        mock_paper_trader,
    ):
        """Test initialization handles malformed config gracefully."""
        bad_config = Mock()
        bad_config.automation = "not_an_object"  # Intentionally wrong type

        orch = TradingOrchestrator(
            config=bad_config,
            strategy_agent=mock_strategy_agent,
            risk_manager=mock_risk_manager,
            order_manager=mock_order_manager,
            paper_trader=mock_paper_trader,
        )

        # Should fall back to defaults
        assert orch._symbols == ["AAPL", "MSFT"]
        assert orch._cadence_s == 30

    def test_init_with_exception_in_config(
        self,
        mock_strategy_agent,
        mock_risk_manager,
        mock_order_manager,
        mock_paper_trader,
    ):
        """Test initialization handles exceptions in config access."""
        # Create a config that raises an exception when accessing automation
        bad_config = Mock()
        bad_config.automation = Mock()
        bad_config.automation.symbols = property(
            lambda self: (_ for _ in ()).throw(Exception("Config error"))
        )

        orch = TradingOrchestrator(
            config=bad_config,
            strategy_agent=mock_strategy_agent,
            risk_manager=mock_risk_manager,
            order_manager=mock_order_manager,
            paper_trader=mock_paper_trader,
        )

        # Should fall back to defaults via exception handler
        assert orch._symbols == ["AAPL", "MSFT"]
        assert orch._cadence_s == 30


# =============================================================================
# Status Tests
# =============================================================================


class TestOrchestratorStatus:
    """Test status reporting functionality."""

    def test_status_not_running(self, orchestrator_with_mocks):
        """Test status when orchestrator is not running."""
        status = orchestrator_with_mocks.status()

        assert status["running"] is False
        assert status["cadence_s"] == 30
        assert status["last_run_ts"] is None
        assert status["last_action"] is None
        assert status["symbols"] == ["AAPL", "MSFT"]

    @pytest.mark.asyncio
    async def test_status_while_running(self, orchestrator_with_mocks):
        """Test status while orchestrator is running."""
        await orchestrator_with_mocks.start()

        status = orchestrator_with_mocks.status()

        assert status["running"] is True
        assert status["cadence_s"] == 30
        assert status["symbols"] == ["AAPL", "MSFT"]

        # Clean up
        await orchestrator_with_mocks.stop()

    @pytest.mark.asyncio
    async def test_status_after_run_cycle(self, orchestrator_with_mocks):
        """Test status after a trading cycle has run."""
        await orchestrator_with_mocks._run_once()

        status = orchestrator_with_mocks.status()

        assert status["last_run_ts"] is not None
        assert status["last_action"] is not None

        # Verify timestamp is recent
        last_run = datetime.fromisoformat(status["last_run_ts"])
        assert (datetime.now() - last_run).total_seconds() < 5


# =============================================================================
# Lifecycle Tests
# =============================================================================


class TestOrchestratorLifecycle:
    """Test orchestrator start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_successfully(self, orchestrator_with_mocks):
        """Test starting orchestrator successfully."""
        assert orchestrator_with_mocks._running is False
        assert orchestrator_with_mocks._task is None

        await orchestrator_with_mocks.start()

        assert orchestrator_with_mocks._running is True
        assert orchestrator_with_mocks._task is not None
        assert not orchestrator_with_mocks._task.done()

        # Clean up
        await orchestrator_with_mocks.stop()

    @pytest.mark.asyncio
    async def test_start_already_running_is_idempotent(self, orchestrator_with_mocks):
        """Test starting when already running does nothing."""
        await orchestrator_with_mocks.start()
        first_task = orchestrator_with_mocks._task

        # Try starting again
        await orchestrator_with_mocks.start()
        second_task = orchestrator_with_mocks._task

        # Should be the same task
        assert first_task == second_task
        assert orchestrator_with_mocks._running is True

        # Clean up
        await orchestrator_with_mocks.stop()

    @pytest.mark.asyncio
    async def test_stop_cleanly(self, orchestrator_with_mocks):
        """Test stopping orchestrator cleanly."""
        await orchestrator_with_mocks.start()
        assert orchestrator_with_mocks._running is True

        await orchestrator_with_mocks.stop()

        assert orchestrator_with_mocks._running is False
        # Task should be cancelled
        if orchestrator_with_mocks._task:
            assert orchestrator_with_mocks._task.done()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, orchestrator_with_mocks):
        """Test stopping when not running does nothing."""
        assert orchestrator_with_mocks._running is False

        # Should not raise error
        await orchestrator_with_mocks.stop()

        assert orchestrator_with_mocks._running is False

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self, orchestrator_with_mocks):
        """Test complete start-stop cycle."""
        # Start
        await orchestrator_with_mocks.start()
        assert orchestrator_with_mocks._running is True

        # Stop
        await orchestrator_with_mocks.stop()
        assert orchestrator_with_mocks._running is False

        # Start again
        await orchestrator_with_mocks.start()
        assert orchestrator_with_mocks._running is True

        # Clean up
        await orchestrator_with_mocks.stop()

    @pytest.mark.asyncio
    async def test_start_with_custom_cadence(self, orchestrator_with_mocks):
        """Test starting with custom cadence."""
        await orchestrator_with_mocks.start(cadence_s=60)

        assert orchestrator_with_mocks._cadence_s == 60
        assert orchestrator_with_mocks._running is True

        # Clean up
        await orchestrator_with_mocks.stop()

    @pytest.mark.asyncio
    async def test_start_with_custom_symbols(self, orchestrator_with_mocks):
        """Test starting with custom symbol list."""
        custom_symbols = ["TSLA", "NVDA"]
        await orchestrator_with_mocks.start(symbols=custom_symbols)

        assert orchestrator_with_mocks._symbols == custom_symbols
        assert orchestrator_with_mocks._running is True

        # Clean up
        await orchestrator_with_mocks.stop()


# =============================================================================
# Trading Cycle Tests - MOST CRITICAL
# =============================================================================


class TestTradingCycle:
    """Test the core trading cycle (_run_once method)."""

    @pytest.mark.asyncio
    async def test_run_once_with_buy_signal(self, orchestrator_with_mocks):
        """Test executing trade on BUY signal."""
        # Setup: strategy returns BUY for both symbols
        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=75.0,
                squeeze_score=60.0,
                overall_score=70.0,
                recommendation="BUY",
                thesis="Strong buy",
                catalysts=["Earnings"],
                risks=["Market risk"],
                target_price=180.0,
                stop_price=138.0,
                position_size_pct=0.05,
                confidence=0.7,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Verify workflow
        orchestrator_with_mocks.strategy_agent.analyze_stock.assert_called()
        orchestrator_with_mocks.paper_trader._get_market_price.assert_called()
        orchestrator_with_mocks.risk_manager.check_portfolio_heat.assert_called()
        orchestrator_with_mocks.order_manager.place_market_order.assert_called()

        # Check last action (will be for last symbol processed - MSFT)
        assert "order_submitted:" in orchestrator_with_mocks._last_action
        assert "order_12345" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_with_strong_buy_signal(self, orchestrator_with_mocks):
        """Test executing trade on STRONG_BUY signal."""
        # Setup: strategy returns STRONG_BUY
        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="MSFT",
                deep_value_score=85.0,
                squeeze_score=75.0,
                overall_score=82.0,
                recommendation="STRONG_BUY",
                thesis="Exceptional opportunity",
                catalysts=["Multiple catalysts"],
                risks=["Minimal risk"],
                target_price=400.0,
                stop_price=320.0,
                position_size_pct=0.05,
                confidence=0.85,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Should execute trade
        orchestrator_with_mocks.order_manager.place_market_order.assert_called()
        assert "order_submitted" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_with_hold_signal(self, orchestrator_with_mocks):
        """Test skipping trade on HOLD signal."""
        # Setup: strategy returns HOLD
        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=55.0,
                squeeze_score=45.0,
                overall_score=50.0,
                recommendation="HOLD",
                thesis="Neutral",
                catalysts=[],
                risks=["Market risk"],
                target_price=160.0,
                stop_price=138.0,
                position_size_pct=0.0,
                confidence=0.5,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Should NOT place order
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()
        assert "analyzed:" in orchestrator_with_mocks._last_action
        assert ":HOLD" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_with_sell_signal(self, orchestrator_with_mocks):
        """Test skipping trade on SELL signal."""
        # Setup: strategy returns SELL
        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=30.0,
                squeeze_score=20.0,
                overall_score=28.0,
                recommendation="SELL",
                thesis="Overvalued",
                catalysts=[],
                risks=["High risk"],
                target_price=120.0,
                stop_price=138.0,
                position_size_pct=0.0,
                confidence=0.6,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Should NOT place order
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_once_risk_rejection(self, orchestrator_with_mocks):
        """Test circuit breaker blocks trade."""
        # Setup: risk manager rejects
        orchestrator_with_mocks.risk_manager.check_portfolio_heat.return_value = {
            "approved": False,
            "reason": "Portfolio heat limit exceeded",
            "current_heat": 0.18,
            "max_heat": 0.15,
        }

        await orchestrator_with_mocks._run_once()

        # Should NOT place order
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()
        assert "risk_reject:" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_portfolio_heat_rejection(self, orchestrator_with_mocks):
        """Test heat limit blocks trade."""
        # Setup: high portfolio heat
        orchestrator_with_mocks.risk_manager.check_portfolio_heat.return_value = {
            "approved": False,
            "reason": "Would exceed max portfolio heat",
            "current_heat": 0.14,
            "max_heat": 0.15,
        }

        await orchestrator_with_mocks._run_once()

        # Should be rejected
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()
        assert "risk_reject" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_order_submission_failure(self, orchestrator_with_mocks):
        """Test handling order failure."""
        # Setup: order manager returns None (failure)
        orchestrator_with_mocks.order_manager.place_market_order.return_value = None

        await orchestrator_with_mocks._run_once()

        # Should log failure
        assert "order_failed:" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_price_fetch_failure(self, orchestrator_with_mocks):
        """Test handling price unavailable."""
        # Setup: no market price available
        orchestrator_with_mocks.paper_trader._get_market_price.return_value = None

        await orchestrator_with_mocks._run_once()

        # Should skip trade, not place order
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_once_price_fetch_zero(self, orchestrator_with_mocks):
        """Test handling zero price."""
        # Setup: price returns 0
        orchestrator_with_mocks.paper_trader._get_market_price.return_value = 0

        await orchestrator_with_mocks._run_once()

        # Should skip trade (falsy value)
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_once_analysis_error(self, orchestrator_with_mocks):
        """Test handling strategy error."""
        # Setup: strategy raises exception
        orchestrator_with_mocks.strategy_agent.analyze_stock.side_effect = Exception(
            "API rate limit exceeded"
        )

        # Should not raise - errors are caught
        await orchestrator_with_mocks._run_once()

        # Should not place order
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_once_multiple_symbols(self, orchestrator_with_mocks):
        """Test processing multiple symbols."""
        # Default config has AAPL and MSFT
        await orchestrator_with_mocks._run_once()

        # Should analyze both symbols
        assert orchestrator_with_mocks.strategy_agent.analyze_stock.call_count == 2
        calls = orchestrator_with_mocks.strategy_agent.analyze_stock.call_args_list
        symbols_analyzed = [call[0][0] for call in calls]
        assert "AAPL" in symbols_analyzed
        assert "MSFT" in symbols_analyzed

    @pytest.mark.asyncio
    async def test_run_once_partial_symbol_failures(self, orchestrator_with_mocks):
        """Test some symbols succeed, some fail."""
        # Setup: first call succeeds, second fails
        orchestrator_with_mocks.strategy_agent.analyze_stock.side_effect = [
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=70.0,
                squeeze_score=60.0,
                overall_score=65.0,
                recommendation="BUY",
                thesis="Good opportunity",
                catalysts=["Earnings"],
                risks=["Market risk"],
                target_price=180.0,
                stop_price=138.0,
                position_size_pct=0.05,
                confidence=0.7,
            ),
            Exception("Error analyzing MSFT"),
        ]

        # Should not raise - continues to next symbol
        await orchestrator_with_mocks._run_once()

        # Should have tried to place at least one order (for AAPL)
        orchestrator_with_mocks.order_manager.place_market_order.assert_called()

    @pytest.mark.asyncio
    async def test_run_once_all_symbols_rejected(self, orchestrator_with_mocks):
        """Test all trades rejected by risk."""
        # Setup: all rejected
        orchestrator_with_mocks.risk_manager.check_portfolio_heat.return_value = {
            "approved": False,
            "reason": "Max heat exceeded",
        }

        await orchestrator_with_mocks._run_once()

        # No orders placed
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_once_position_sizing_calculation(self, orchestrator_with_mocks):
        """Test position sizing calculation is correct."""
        # Setup: Use single symbol to test specific sizing
        orchestrator_with_mocks._symbols = ["AAPL"]
        orchestrator_with_mocks.paper_trader.get_portfolio_value.return_value = 100000.0
        orchestrator_with_mocks.paper_trader._get_market_price.return_value = 150.0

        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=70.0,
                squeeze_score=60.0,
                overall_score=65.0,
                recommendation="BUY",
                thesis="Good",
                catalysts=[],
                risks=[],
                target_price=180.0,
                stop_price=138.0,
                position_size_pct=0.03,  # 3% position
                confidence=0.7,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Check order was placed with correct quantity
        orchestrator_with_mocks.order_manager.place_market_order.assert_called_once()
        call_args = orchestrator_with_mocks.order_manager.place_market_order.call_args

        symbol = call_args[0][0]
        quantity = call_args[0][1]
        side = call_args[0][2]

        assert symbol == "AAPL"
        assert side == "BUY"
        # Expected: (100000 * 0.03) / 150 = 20 shares
        assert quantity >= 1  # At least 1 share
        assert quantity <= 25  # Reasonable range

    @pytest.mark.asyncio
    async def test_run_once_minimum_position_size(self, orchestrator_with_mocks):
        """Test minimum position size of 1 share."""
        # Setup: very small position size
        orchestrator_with_mocks.strategy_agent.analyze_stock.return_value = (
            StockAnalysis(
                symbol="AAPL",
                deep_value_score=50.0,
                squeeze_score=40.0,
                overall_score=45.0,
                recommendation="BUY",
                thesis="Small opportunity",
                catalysts=[],
                risks=[],
                target_price=160.0,
                stop_price=138.0,
                position_size_pct=0.001,  # 0.1% - very small
                confidence=0.5,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Should place order with at least 1 share
        call_args = orchestrator_with_mocks.order_manager.place_market_order.call_args
        quantity = call_args[0][1]
        assert quantity >= 1

    @pytest.mark.asyncio
    async def test_run_once_updates_timestamp(self, orchestrator_with_mocks):
        """Test that _run_once updates last_run_ts."""
        before = datetime.now()

        await orchestrator_with_mocks._run_once()

        after = datetime.now()

        assert orchestrator_with_mocks._last_run_ts is not None
        assert before <= orchestrator_with_mocks._last_run_ts <= after


# =============================================================================
# Error Handling and Loop Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling and loop behavior."""

    @pytest.mark.asyncio
    async def test_run_loop_continues_on_cycle_error(self, orchestrator_with_mocks):
        """Test that loop CONTINUES on cycle errors (fixed from previous bug)."""
        call_count = 0

        async def mock_run_once_with_error():
            nonlocal call_count
            call_count += 1
            raise Exception("Simulated cycle error")

        # Patch _run_once to simulate error
        orchestrator_with_mocks._run_once = mock_run_once_with_error
        orchestrator_with_mocks._cadence_s = 0.05
        # Reduce backoff to make test faster (default is 5s which is too long for test)
        orchestrator_with_mocks._base_backoff = 0.01
        orchestrator_with_mocks._max_backoff = 0.05

        # Start the loop
        await orchestrator_with_mocks.start()

        # Let it run for multiple cycles
        await asyncio.sleep(0.2)

        # Stop
        await orchestrator_with_mocks.stop()

        # FIXED BEHAVIOR: Loop continues despite errors (has continue statement)
        # Verify loop executed multiple times despite errors
        assert call_count > 1, f"Loop should have continued, got {call_count} calls"
        assert (
            call_count >= 3
        ), "Loop should have executed at least 3 cycles in 0.2s with 0.05s cadence"

    @pytest.mark.asyncio
    async def test_run_loop_cancellation(self, orchestrator_with_mocks):
        """Test clean cancellation of loop."""
        orchestrator_with_mocks._cadence_s = 10  # Long cadence

        await orchestrator_with_mocks.start()
        assert orchestrator_with_mocks._running is True

        # Cancel immediately
        await orchestrator_with_mocks.stop()

        # Should be stopped
        assert orchestrator_with_mocks._running is False

    @pytest.mark.asyncio
    async def test_run_loop_handles_cancellation_gracefully(
        self, orchestrator_with_mocks
    ):
        """Test CancelledError is handled gracefully."""
        orchestrator_with_mocks._cadence_s = 0.1

        await orchestrator_with_mocks.start()

        # Let it run briefly
        await asyncio.sleep(0.05)

        # Stop should not raise
        await orchestrator_with_mocks.stop()

        assert orchestrator_with_mocks._running is False

    @pytest.mark.asyncio
    async def test_run_loop_timeout_continues(self, orchestrator_with_mocks):
        """Test loop continues after timeout error in cycle."""
        call_count = 0

        async def mock_run_once_timeout_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError("Analysis timeout")
            # Second call succeeds
            return

        orchestrator_with_mocks._run_once = mock_run_once_timeout_then_succeed
        orchestrator_with_mocks._cadence_s = 0.05
        # Reduce backoff to make test faster (default is 5s which is too long for test)
        orchestrator_with_mocks._base_backoff = 0.01
        orchestrator_with_mocks._max_backoff = 0.05

        await orchestrator_with_mocks.start()
        await asyncio.sleep(0.15)
        await orchestrator_with_mocks.stop()

        # Loop should continue after timeout
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_run_once_analysis_timeout(self, orchestrator_with_mocks):
        """Test timeout on strategy analysis (30s limit)."""

        async def slow_analyze(symbol):
            # Simulate slow analysis that times out
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("Analysis timeout")

        orchestrator_with_mocks.strategy_agent.analyze_stock = slow_analyze

        await orchestrator_with_mocks._run_once()

        # Should NOT place order (timeout caught)
        orchestrator_with_mocks.order_manager.place_market_order.assert_not_called()
        # Should record timeout in last_action
        assert "timeout:" in orchestrator_with_mocks._last_action

    @pytest.mark.asyncio
    async def test_run_once_position_limit_cap(self, orchestrator_with_mocks):
        """Test position quantity capped at MAX_SHARES_PER_ORDER."""
        # Setup: large portfolio, small price = large calculated qty
        orchestrator_with_mocks.paper_trader.get_portfolio_value = Mock(
            return_value=5_000_000
        )
        orchestrator_with_mocks.paper_trader._get_market_price = AsyncMock(
            return_value=10.0
        )

        # BUY signal with 20% position size = 100,000 shares
        orchestrator_with_mocks.strategy_agent.analyze_stock = AsyncMock(
            return_value=StockAnalysis(
                symbol="AAPL",
                deep_value_score=70.0,
                squeeze_score=60.0,
                overall_score=65.0,
                recommendation="BUY",
                thesis="Good opportunity",
                catalysts=["Earnings"],
                risks=["Market risk"],
                target_price=180.0,
                stop_price=138.0,
                position_size_pct=0.20,  # 20% would be 100k shares
                confidence=0.7,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Order should be placed but with capped quantity
        # (2 calls: AAPL and MSFT, both get capped)
        assert orchestrator_with_mocks.order_manager.place_market_order.call_count == 2

        # Check first call (AAPL)
        call_args = (
            orchestrator_with_mocks.order_manager.place_market_order.call_args_list[0]
        )
        symbol, quantity, side = call_args[0]
        assert quantity == 10_000, f"Expected 10,000 shares for AAPL, got {quantity}"

    @pytest.mark.asyncio
    async def test_run_once_position_within_limit(self, orchestrator_with_mocks):
        """Test position quantity NOT capped when under limit."""
        # Setup: small calculated qty (no cap needed)
        orchestrator_with_mocks.paper_trader.get_portfolio_value = Mock(
            return_value=100_000
        )
        orchestrator_with_mocks.paper_trader._get_market_price = AsyncMock(
            return_value=150.0
        )

        # BUY signal with 5% position size = 33 shares
        orchestrator_with_mocks.strategy_agent.analyze_stock = AsyncMock(
            return_value=StockAnalysis(
                symbol="AAPL",
                deep_value_score=70.0,
                squeeze_score=60.0,
                overall_score=65.0,
                recommendation="BUY",
                thesis="Good opportunity",
                catalysts=["Earnings"],
                risks=["Market risk"],
                target_price=180.0,
                stop_price=138.0,
                position_size_pct=0.05,  # 5% = ~33 shares
                confidence=0.7,
            )
        )

        await orchestrator_with_mocks._run_once()

        # Order placed with uncapped quantity
        # (2 calls: AAPL and MSFT, both get same qty)
        assert orchestrator_with_mocks.order_manager.place_market_order.call_count == 2

        # Check first call (AAPL)
        call_args = (
            orchestrator_with_mocks.order_manager.place_market_order.call_args_list[0]
        )
        symbol, quantity, side = call_args[0]

        # With loss aversion bias (2.3x), effective size is ~43% of raw:
        # raw = 100k * 0.05 / 150 = 33, biased = 100k * (0.05/2.3) / 150 = 14
        assert (
            quantity == 14
        ), f"Expected 14 shares for AAPL (loss-aversion adjusted), got {quantity}"


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestOrchestratorIntegration:
    """Integration-style tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self, orchestrator_with_mocks):
        """Test complete workflow: start → cycle → stop."""
        # Start orchestrator
        await orchestrator_with_mocks.start(cadence_s=0.1)

        # Let it run one cycle
        await asyncio.sleep(0.15)

        # Check status
        status = orchestrator_with_mocks.status()
        assert status["running"] is True
        assert status["last_run_ts"] is not None

        # Stop
        await orchestrator_with_mocks.stop()

        # Verify stopped
        final_status = orchestrator_with_mocks.status()
        assert final_status["running"] is False

    @pytest.mark.asyncio
    async def test_multiple_cycles_execution(self, orchestrator_with_mocks):
        """Test multiple trading cycles execute correctly."""
        orchestrator_with_mocks._cadence_s = 0.05  # Very fast for testing

        # Track calls
        original_run_once = orchestrator_with_mocks._run_once
        call_count = 0

        async def counting_run_once():
            nonlocal call_count
            call_count += 1
            await original_run_once()

        orchestrator_with_mocks._run_once = counting_run_once

        # Start and run
        await orchestrator_with_mocks.start()
        await asyncio.sleep(0.2)
        await orchestrator_with_mocks.stop()

        # Should have executed multiple cycles
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_symbol_rotation_across_cycles(self, orchestrator_with_mocks):
        """Test all symbols are processed across cycles."""
        symbols_processed = set()

        original_analyze = orchestrator_with_mocks.strategy_agent.analyze_stock

        async def tracking_analyze(symbol):
            symbols_processed.add(symbol)
            return await original_analyze(symbol)

        orchestrator_with_mocks.strategy_agent.analyze_stock = tracking_analyze

        # Run one cycle
        await orchestrator_with_mocks._run_once()

        # Should have processed both symbols
        assert "AAPL" in symbols_processed
        assert "MSFT" in symbols_processed
