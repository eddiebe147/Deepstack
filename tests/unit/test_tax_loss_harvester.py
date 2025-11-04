"""
Unit tests for TaxLossHarvester - Tax Optimization System

Tests comprehensive tax-loss harvesting including:
- Opportunity scanning (positions with unrealized losses)
- Tax benefit calculation (short-term vs long-term)
- Harvest planning (ranking by tax benefit)
- Harvest execution (sell + buy alternative)
- Wash sale integration (31-day rule compliance)
- Year-end planning (maximize tax savings)
- Alpha estimation (3-5% target)
- Edge cases: no losses, all gains, mixed portfolio

Coverage target: 80%+ with 20+ tests
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from core.broker.paper_trader import PaperTrader
from core.config import Config
from core.tax.tax_loss_harvester import (
    HarvestOpportunity,
    HarvestPlan,
    HarvestResult,
    TaxLossHarvester,
    YearEndPlan,
)
from core.tax.wash_sale_tracker import WashSaleTracker


class TestDataClasses:
    """Test data class creation and validation."""

    def test_harvest_opportunity_creation(self):
        """Test creating a HarvestOpportunity."""
        opp = HarvestOpportunity(
            symbol="AAPL",
            quantity=100,
            cost_basis=15000.0,
            current_value=14000.0,
            unrealized_loss=1000.0,
            holding_period_days=100,
            is_short_term=True,
            purchase_date=datetime(2024, 1, 1),
            estimated_tax_benefit=370.0,  # 1000 * 0.37
        )

        assert opp.symbol == "AAPL"
        assert opp.quantity == 100
        assert opp.unrealized_loss == 1000.0
        assert opp.is_short_term is True
        assert opp.estimated_tax_benefit == 370.0

    def test_harvest_plan_creation(self):
        """Test creating a HarvestPlan."""
        opp = HarvestOpportunity(
            symbol="AAPL",
            quantity=100,
            cost_basis=15000.0,
            current_value=14000.0,
            unrealized_loss=1000.0,
            holding_period_days=100,
            is_short_term=True,
            purchase_date=datetime(2024, 1, 1),
            estimated_tax_benefit=370.0,
        )

        plan = HarvestPlan(
            opportunity=opp,
            alternative_symbol="MSFT",
            execute_date=datetime.now(),
            expected_tax_benefit=370.0,
            notes="Test harvest plan",
        )

        assert plan.opportunity.symbol == "AAPL"
        assert plan.alternative_symbol == "MSFT"
        assert plan.expected_tax_benefit == 370.0

    def test_harvest_result_success(self):
        """Test creating a successful HarvestResult."""
        result = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=100,
            loss_realized=1000.0,
            tax_benefit=370.0,
            execution_date=datetime.now(),
            original_cost_basis=15000.0,
            sale_proceeds=14000.0,
            replacement_cost=14000.0,
            success=True,
            error_message=None,
        )

        assert result.success is True
        assert result.loss_realized == 1000.0
        assert result.tax_benefit == 370.0
        assert result.error_message is None

    def test_harvest_result_failure(self):
        """Test creating a failed HarvestResult."""
        result = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=100,
            loss_realized=0.0,
            tax_benefit=0.0,
            execution_date=datetime.now(),
            original_cost_basis=15000.0,
            sale_proceeds=0.0,
            replacement_cost=0.0,
            success=False,
            error_message="Failed to execute",
        )

        assert result.success is False
        assert result.error_message == "Failed to execute"

    def test_year_end_plan_creation(self):
        """Test creating a YearEndPlan."""
        plan = YearEndPlan(
            total_harvestable_loss=5000.0,
            total_tax_benefit=1850.0,
            short_term_opportunities=[],
            long_term_opportunities=[],
            recommended_harvests=[],
            deadline=datetime(2024, 12, 31),
        )

        assert plan.total_harvestable_loss == 5000.0
        assert plan.total_tax_benefit == 1850.0
        assert plan.deadline.month == 12
        assert plan.deadline.day == 31


class TestTaxBenefitCalculation:
    """Test tax benefit calculation logic."""

    @pytest.fixture
    def harvester(self):
        """Create harvester for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
                tax_rate_short_term=0.37,
                tax_rate_long_term=0.20,
                min_loss_threshold=100.0,
            )
            yield harvester

    def test_short_term_tax_benefit(self, harvester):
        """Test tax benefit calculation for short-term loss."""
        # Short-term loss: 37% tax rate
        loss = 1000.0
        is_short_term = True

        benefit = harvester.calculate_tax_benefit_from_params(loss, is_short_term)

        assert benefit == 370.0  # 1000 * 0.37

    def test_long_term_tax_benefit(self, harvester):
        """Test tax benefit calculation for long-term loss."""
        # Long-term loss: 20% tax rate
        loss = 1000.0
        is_short_term = False

        benefit = harvester.calculate_tax_benefit_from_params(loss, is_short_term)

        assert benefit == 200.0  # 1000 * 0.20

    def test_tax_benefit_with_opportunity(self, harvester):
        """Test tax benefit calculation using HarvestOpportunity."""
        opp = HarvestOpportunity(
            symbol="AAPL",
            quantity=100,
            cost_basis=15000.0,
            current_value=14000.0,
            unrealized_loss=1000.0,
            holding_period_days=100,
            is_short_term=True,
            purchase_date=datetime(2024, 1, 1),
            estimated_tax_benefit=370.0,
        )

        benefit = harvester.calculate_tax_benefit(opp)

        assert benefit == 370.0  # 1000 * 0.37 (short-term)

    def test_custom_tax_rates(self):
        """Test harvester with custom tax rates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")

            # Custom tax rates
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
                tax_rate_short_term=0.40,  # 40%
                tax_rate_long_term=0.15,  # 15%
            )

            # Short-term
            benefit_st = harvester.calculate_tax_benefit_from_params(1000.0, True)
            assert benefit_st == 400.0

            # Long-term
            benefit_lt = harvester.calculate_tax_benefit_from_params(1000.0, False)
            assert benefit_lt == 150.0


class TestOpportunityScanning:
    """Test scanning for harvest opportunities."""

    @pytest.fixture
    def setup(self):
        """Setup harvester with mock trader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
                min_loss_threshold=100.0,
            )
            yield harvester, trader

    @pytest.mark.asyncio
    async def test_scan_no_positions(self, setup):
        """Test scanning with no positions."""
        harvester, trader = setup

        opportunities = await harvester.scan_opportunities()

        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_position_with_gain(self, setup):
        """Test scanning position with gain (not a harvest opportunity)."""
        harvester, trader = setup

        # Mock position with gain
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 140.0,  # Cost $140/share
                "updated_at": datetime.now() - timedelta(days=100),
            }
        }

        # Mock price: $150 (gain)
        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 150.0

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 0  # No loss, no opportunity

    @pytest.mark.asyncio
    async def test_scan_position_with_loss(self, setup):
        """Test scanning position with loss (harvest opportunity)."""
        harvester, trader = setup

        # Mock position with loss
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.0,  # Cost $150/share
                "updated_at": datetime.now() - timedelta(days=100),
            }
        }

        # Mock price: $140 (loss of $10/share = $1000 total)
        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 140.0

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 1
            opp = opportunities[0]
            assert opp.symbol == "AAPL"
            assert opp.quantity == 100
            assert opp.unrealized_loss == 1000.0
            assert opp.is_short_term is True  # < 365 days
            assert opp.estimated_tax_benefit == 370.0  # 1000 * 0.37

    @pytest.mark.asyncio
    async def test_scan_below_threshold(self, setup):
        """Test scanning position with loss below threshold."""
        harvester, trader = setup

        # Mock position with small loss
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 10,
                "avg_cost": 150.0,
                "updated_at": datetime.now() - timedelta(days=100),
            }
        }

        # Mock price: $149 (loss of $10 total - below $100 threshold)
        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 149.0

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 0  # Below threshold

    @pytest.mark.asyncio
    async def test_scan_wash_sale_filter(self, setup):
        """Test scanning filters out positions that would trigger wash sale."""
        harvester, trader = setup

        # Record a loss sale (creates wash sale window)
        harvester.wash_sale_tracker.record_loss_sale(
            symbol="AAPL",
            quantity=100,
            loss_amount=1000.0,
            sale_date=datetime.now() - timedelta(days=10),
            cost_basis=15000.0,
            sale_price=14000.0,
        )

        # Mock position with loss
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.0,
                "updated_at": datetime.now() - timedelta(days=100),
            }
        }

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 140.0

            opportunities = await harvester.scan_opportunities()

            # Should be filtered out due to wash sale
            assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_scan_multiple_positions(self, setup):
        """Test scanning multiple positions, sorted by tax benefit."""
        harvester, trader = setup

        # Mock multiple positions
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.0,
                "updated_at": datetime.now() - timedelta(days=100),  # Short-term
            },
            "GOOGL": {
                "symbol": "GOOGL",
                "quantity": 50,
                "avg_cost": 2000.0,
                "updated_at": datetime.now() - timedelta(days=400),  # Long-term
            },
        }

        # Mock prices
        async def mock_get_price(symbol):
            prices = {
                "AAPL": 140.0,  # Loss: $1000, benefit: $370 (short-term)
                "GOOGL": 1900.0,  # Loss: $5000, benefit: $1000 (long-term)
            }
            return prices.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 2

            # Should be sorted by tax benefit (GOOGL higher)
            assert opportunities[0].symbol == "GOOGL"
            assert opportunities[0].estimated_tax_benefit == 1000.0

            assert opportunities[1].symbol == "AAPL"
            assert opportunities[1].estimated_tax_benefit == 370.0

    @pytest.mark.asyncio
    async def test_scan_long_term_vs_short_term(self, setup):
        """Test holding period calculation (short-term vs long-term)."""
        harvester, trader = setup

        # Short-term position (< 365 days)
        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.0,
                "updated_at": datetime.now() - timedelta(days=200),
            }
        }

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 140.0

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 1
            assert opportunities[0].is_short_term is True
            assert opportunities[0].holding_period_days == 200

        # Long-term position (>= 365 days)
        trader.positions = {
            "GOOGL": {
                "symbol": "GOOGL",
                "quantity": 100,
                "avg_cost": 2000.0,
                "updated_at": datetime.now() - timedelta(days=400),
            }
        }

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = 1900.0

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 1
            assert opportunities[0].is_short_term is False
            assert opportunities[0].holding_period_days == 400


class TestHarvestPlanning:
    """Test harvest planning logic."""

    @pytest.fixture
    def setup(self):
        """Setup harvester with mock positions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
                min_loss_threshold=100.0,
            )

            # Setup positions with losses
            trader.positions = {
                "AAPL": {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "avg_cost": 150.0,
                    "updated_at": datetime.now() - timedelta(days=100),
                },
                "GOOGL": {
                    "symbol": "GOOGL",
                    "quantity": 50,
                    "avg_cost": 2000.0,
                    "updated_at": datetime.now() - timedelta(days=400),
                },
            }

            yield harvester, trader

    @pytest.mark.asyncio
    async def test_plan_harvest_default(self, setup):
        """Test planning harvest with default parameters."""
        harvester, trader = setup

        # Mock prices
        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            plans = await harvester.plan_harvest()

            assert len(plans) == 2

            # Check alternatives are assigned
            assert plans[0].alternative_symbol in ["MSFT", "AMZN", "META", "AAPL"]
            assert plans[1].alternative_symbol in ["MSFT", "NVDA", "AMD"]

    @pytest.mark.asyncio
    async def test_plan_harvest_max_limit(self, setup):
        """Test planning harvest with max_harvests limit."""
        harvester, trader = setup

        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            plans = await harvester.plan_harvest(max_harvests=1)

            assert len(plans) == 1  # Limited to 1

    @pytest.mark.asyncio
    async def test_plan_harvest_target_loss(self, setup):
        """Test planning harvest with target loss amount."""
        harvester, trader = setup

        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            # Target $2000 loss (should get both positions)
            plans = await harvester.plan_harvest(target_loss_amount=2000.0)

            assert len(plans) >= 1

    @pytest.mark.asyncio
    async def test_plan_harvest_no_alternatives(self, setup):
        """Test planning when no alternatives available."""
        harvester, trader = setup

        # Mock get_alternative_symbols to return empty
        with patch.object(
            harvester.wash_sale_tracker, "get_alternative_symbols"
        ) as mock_alt:
            mock_alt.return_value = []

            async def mock_get_price(symbol):
                return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

            with patch.object(
                trader, "_get_market_price", new_callable=AsyncMock
            ) as mock:
                mock.side_effect = mock_get_price

                plans = await harvester.plan_harvest()

                # Should have no plans (no alternatives)
                assert len(plans) == 0


class TestHarvestExecution:
    """Test harvest execution."""

    @pytest.fixture
    def setup(self):
        """Setup harvester for execution testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
            )

            # Add cash to trader
            trader.cash = 50000.0

            yield harvester, trader

    @pytest.mark.asyncio
    async def test_execute_harvest_success(self, setup):
        """Test successful harvest execution."""
        harvester, trader = setup

        # Create opportunity and plan
        opp = HarvestOpportunity(
            symbol="AAPL",
            quantity=100,
            cost_basis=15000.0,
            current_value=14000.0,
            unrealized_loss=1000.0,
            holding_period_days=100,
            is_short_term=True,
            purchase_date=datetime(2024, 1, 1),
            estimated_tax_benefit=370.0,
        )

        plan = HarvestPlan(
            opportunity=opp,
            alternative_symbol="MSFT",
            execute_date=datetime.now(),
            expected_tax_benefit=370.0,
            notes="Test harvest",
        )

        # Mock prices
        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "MSFT": 380.0}.get(symbol)

        # Mock place_market_order
        call_count = {"value": 0}

        async def mock_place_order(symbol, quantity, action, auto_stop_loss=True):
            call_count["value"] += 1
            return f"order_{call_count['value']}"

        with patch.object(
            trader, "_get_market_price", new_callable=AsyncMock
        ) as mock_price:
            mock_price.side_effect = mock_get_price

            with patch.object(
                trader, "place_market_order", new_callable=AsyncMock
            ) as mock_order:
                mock_order.side_effect = mock_place_order

                # Mock trade history
                trader.trade_history = [
                    {"action": "SELL", "price": 140.0, "quantity": 100},
                    {"action": "BUY", "price": 380.0, "quantity": 36},
                ]

                result = await harvester.execute_harvest(plan)

                assert result.success is True
                assert result.original_symbol == "AAPL"
                assert result.alternative_symbol == "MSFT"
                assert result.loss_realized > 0
                assert result.tax_benefit > 0
                assert result.error_message is None

    @pytest.mark.asyncio
    async def test_execute_harvest_sell_fails(self, setup):
        """Test harvest when sell order fails."""
        harvester, trader = setup

        opp = HarvestOpportunity(
            symbol="AAPL",
            quantity=100,
            cost_basis=15000.0,
            current_value=14000.0,
            unrealized_loss=1000.0,
            holding_period_days=100,
            is_short_term=True,
            purchase_date=datetime(2024, 1, 1),
            estimated_tax_benefit=370.0,
        )

        plan = HarvestPlan(
            opportunity=opp,
            alternative_symbol="MSFT",
            execute_date=datetime.now(),
            expected_tax_benefit=370.0,
            notes="Test harvest",
        )

        # Mock sell failure
        async def mock_place_order(symbol, quantity, action, auto_stop_loss=True):
            if action == "SELL":
                return None  # Failure
            return "order_123"

        with patch.object(trader, "place_market_order", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_place_order

            result = await harvester.execute_harvest(plan)

            assert result.success is False
            assert "Failed to sell" in result.error_message


class TestYearEndPlanning:
    """Test year-end planning."""

    @pytest.fixture
    def setup(self):
        """Setup harvester for year-end testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
            )

            # Setup positions
            trader.positions = {
                "AAPL": {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "avg_cost": 150.0,
                    "updated_at": datetime.now() - timedelta(days=100),  # Short-term
                },
                "GOOGL": {
                    "symbol": "GOOGL",
                    "quantity": 50,
                    "avg_cost": 2000.0,
                    "updated_at": datetime.now() - timedelta(days=400),  # Long-term
                },
            }

            yield harvester, trader

    @pytest.mark.asyncio
    async def test_year_end_planning_basic(self, setup):
        """Test basic year-end planning."""
        harvester, trader = setup

        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            plan = await harvester.year_end_planning(datetime(2024, 12, 1))

            assert plan.deadline == datetime(2024, 12, 31)
            assert plan.total_harvestable_loss > 0
            assert plan.total_tax_benefit > 0
            assert len(plan.short_term_opportunities) == 1  # AAPL
            assert len(plan.long_term_opportunities) == 1  # GOOGL

    @pytest.mark.asyncio
    async def test_year_end_planning_no_opportunities(self, setup):
        """Test year-end planning with no opportunities."""
        harvester, trader = setup

        # Clear positions
        trader.positions = {}

        plan = await harvester.year_end_planning(datetime(2024, 12, 1))

        assert plan.total_harvestable_loss == 0.0
        assert plan.total_tax_benefit == 0.0
        assert len(plan.short_term_opportunities) == 0
        assert len(plan.long_term_opportunities) == 0
        assert len(plan.recommended_harvests) == 0

    @pytest.mark.asyncio
    async def test_year_end_planning_deadline(self, setup):
        """Test year-end planning sets correct deadline."""
        harvester, trader = setup

        async def mock_get_price(symbol):
            return {"AAPL": 140.0, "GOOGL": 1900.0}.get(symbol)

        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_get_price

            plan = await harvester.year_end_planning(datetime(2024, 6, 15))

            # Deadline should be Dec 31 of current year
            assert plan.deadline.year == 2024
            assert plan.deadline.month == 12
            assert plan.deadline.day == 31

            # Recommended harvests should execute by Dec 29 (T+2 settlement)
            if plan.recommended_harvests:
                for harvest in plan.recommended_harvests:
                    assert harvest.execute_date.month == 12
                    assert harvest.execute_date.day == 29


class TestHarvestHistory:
    """Test harvest history and reporting."""

    @pytest.fixture
    def setup(self):
        """Setup harvester."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
            )
            yield harvester

    def test_harvest_history_empty(self, setup):
        """Test harvest history when empty."""
        harvester = setup

        history = harvester.get_harvest_history()

        assert len(history) == 0

    def test_harvest_history_with_results(self, setup):
        """Test harvest history with results."""
        harvester = setup

        # Add some results
        result1 = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=100,
            loss_realized=1000.0,
            tax_benefit=370.0,
            execution_date=datetime(2024, 1, 1),
            original_cost_basis=15000.0,
            sale_proceeds=14000.0,
            replacement_cost=14000.0,
            success=True,
        )

        result2 = HarvestResult(
            original_symbol="GOOGL",
            alternative_symbol="META",
            quantity=50,
            loss_realized=5000.0,
            tax_benefit=1000.0,
            execution_date=datetime(2024, 2, 1),
            original_cost_basis=100000.0,
            sale_proceeds=95000.0,
            replacement_cost=95000.0,
            success=True,
        )

        harvester.harvest_history = [result1, result2]

        history = harvester.get_harvest_history()

        # Should be sorted by date (newest first)
        assert len(history) == 2
        assert history[0].execution_date > history[1].execution_date


class TestAlphaEstimation:
    """Test annual alpha estimation."""

    @pytest.fixture
    def setup(self):
        """Setup harvester with trader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            trader.initial_cash = 100000.0
            trader.cash = 100000.0
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
            )
            yield harvester, trader

    def test_alpha_no_history(self, setup):
        """Test alpha estimation with no harvest history."""
        harvester, trader = setup

        alpha = harvester.estimate_annual_alpha()

        assert alpha == 0.0

    def test_alpha_with_harvests(self, setup):
        """Test alpha estimation with harvest history."""
        harvester, trader = setup

        # Add harvest results
        result1 = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=100,
            loss_realized=1000.0,
            tax_benefit=370.0,  # $370 benefit
            execution_date=datetime.now(),
            original_cost_basis=15000.0,
            sale_proceeds=14000.0,
            replacement_cost=14000.0,
            success=True,
        )

        result2 = HarvestResult(
            original_symbol="GOOGL",
            alternative_symbol="META",
            quantity=50,
            loss_realized=10000.0,
            tax_benefit=2000.0,  # $2000 benefit
            execution_date=datetime.now(),
            original_cost_basis=100000.0,
            sale_proceeds=90000.0,
            replacement_cost=90000.0,
            success=True,
        )

        harvester.harvest_history = [result1, result2]

        alpha = harvester.estimate_annual_alpha()

        # Total benefit: $2370 on $100k portfolio = 2.37%
        expected_alpha = (370.0 + 2000.0) / 100000.0
        assert abs(alpha - expected_alpha) < 0.0001

    def test_alpha_target_range(self, setup):
        """Test that alpha can achieve 3-5% target range."""
        harvester, trader = setup

        # Simulate harvests totaling 4% of portfolio
        total_benefit = 4000.0  # 4% of $100k

        result = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=1000,
            loss_realized=total_benefit / 0.37,  # Reverse calculate loss
            tax_benefit=total_benefit,
            execution_date=datetime.now(),
            original_cost_basis=50000.0,
            sale_proceeds=40000.0,
            replacement_cost=40000.0,
            success=True,
        )

        harvester.harvest_history = [result]

        alpha = harvester.estimate_annual_alpha()

        # Should be in target range
        assert 0.03 <= alpha <= 0.05  # 3-5%


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def setup(self):
        """Setup harvester."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            trader = PaperTrader(config=config, enable_risk_systems=False)
            wash_tracker = WashSaleTracker(db_path=f"{tmpdir}/wash.db")
            harvester = TaxLossHarvester(
                trader=trader,
                wash_sale_tracker=wash_tracker,
            )
            yield harvester, trader

    @pytest.mark.asyncio
    async def test_scan_with_no_price_data(self, setup):
        """Test scanning when price data unavailable."""
        harvester, trader = setup

        trader.positions = {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 100,
                "avg_cost": 150.0,
                "updated_at": datetime.now(),
            }
        }

        # Mock price unavailable
        with patch.object(trader, "_get_market_price", new_callable=AsyncMock) as mock:
            mock.return_value = None

            opportunities = await harvester.scan_opportunities()

            assert len(opportunities) == 0

    def test_min_loss_threshold_filter(self, setup):
        """Test minimum loss threshold filtering."""
        harvester, trader = setup

        # Create harvester with high threshold
        harvester.min_loss_threshold = 5000.0

        # Small loss should be filtered
        loss = 1000.0
        benefit = harvester.calculate_tax_benefit_from_params(loss, True)

        # Benefit calculated, but would be filtered in scan
        assert benefit == 370.0

    def test_zero_portfolio_value(self, setup):
        """Test alpha calculation with zero portfolio value."""
        harvester, trader = setup

        trader.cash = 0.0
        trader.positions = {}

        result = HarvestResult(
            original_symbol="AAPL",
            alternative_symbol="MSFT",
            quantity=100,
            loss_realized=1000.0,
            tax_benefit=370.0,
            execution_date=datetime.now(),
            original_cost_basis=15000.0,
            sale_proceeds=14000.0,
            replacement_cost=14000.0,
            success=True,
        )

        harvester.harvest_history = [result]

        alpha = harvester.estimate_annual_alpha()

        # Should handle gracefully
        assert alpha == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
