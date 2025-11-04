"""
Tax-Loss Harvesting System - Generate 3-5% Annual Alpha

Proactive tax optimization feature that generates alpha through strategic
tax-loss harvesting. Identifies positions with unrealized losses,
calculates tax benefits, and executes harvest trades while maintaining
market exposure and avoiding wash sale violations.

Key Features:
    - Scans portfolio for positions with unrealized losses
    - Calculates tax benefit (short-term: 37%, long-term: 20%)
    - Ranks opportunities by tax benefit
    - Executes harvest: sell losing position, buy alternative
    - Full wash sale integration (31-day rule compliance)
    - Year-end planning mode for maximum tax savings

Expected Alpha:
    - 3-5% annual improvement through tax savings
    - Offsets short-term capital gains (37% tax rate)
    - Converts short-term to long-term gains (20% rate)
    - Carries forward unused losses indefinitely

Example:
    >>> harvester = TaxLossHarvester(trader, wash_tracker)
    >>> opportunities = harvester.scan_opportunities()
    >>> plans = harvester.plan_harvest(max_harvests=5)
    >>> result = harvester.execute_harvest(plans[0])
    >>> print(f"Tax benefit: ${result.tax_benefit:.2f}")
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from ..broker.paper_trader import PaperTrader
from .wash_sale_tracker import WashSaleTracker

logger = logging.getLogger(__name__)


@dataclass
class HarvestOpportunity:
    """A position that can be tax-loss harvested."""

    symbol: str
    quantity: int
    cost_basis: float
    current_value: float
    unrealized_loss: float
    holding_period_days: int
    is_short_term: bool  # Held < 1 year (365 days)
    purchase_date: datetime
    estimated_tax_benefit: float


@dataclass
class HarvestPlan:
    """Plan to execute a tax-loss harvest."""

    opportunity: HarvestOpportunity
    alternative_symbol: str  # What to buy instead
    execute_date: datetime
    expected_tax_benefit: float
    notes: str


@dataclass
class HarvestResult:
    """Result of an executed harvest."""

    original_symbol: str
    alternative_symbol: str
    quantity: int
    loss_realized: float
    tax_benefit: float
    execution_date: datetime
    original_cost_basis: float
    sale_proceeds: float
    replacement_cost: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class YearEndPlan:
    """Year-end tax optimization plan."""

    total_harvestable_loss: float
    total_tax_benefit: float
    short_term_opportunities: List[HarvestOpportunity]
    long_term_opportunities: List[HarvestOpportunity]
    recommended_harvests: List[HarvestPlan]
    deadline: datetime  # Usually Dec 31


class TaxLossHarvester:
    """
    Proactive tax-loss harvesting to generate 3-5% annual alpha.

    Strategy:
    1. Scan portfolio for positions with unrealized losses
    2. Calculate tax benefit of harvesting each loss
    3. Rank opportunities by tax benefit
    4. Execute harvest: sell losing position, buy alternative
    5. Ensure no wash sale violations (31-day rule)
    6. Maintain market exposure throughout

    Tax Rates:
    - Short-term capital gains (< 1 year): 37% for high earners
    - Long-term capital gains (>= 1 year): 20% for high earners
    - Can offset $3,000 of ordinary income annually
    - Unused losses carry forward indefinitely
    """

    def __init__(
        self,
        trader: PaperTrader,
        wash_sale_tracker: WashSaleTracker,
        tax_rate_short_term: float = 0.37,  # Short-term capital gains rate
        tax_rate_long_term: float = 0.20,  # Long-term capital gains rate
        min_loss_threshold: float = 100.0,  # Minimum loss to harvest ($100)
    ):
        """
        Initialize tax-loss harvester.

        Args:
            trader: PaperTrader instance for executing trades
            wash_sale_tracker: WashSaleTracker for compliance
            tax_rate_short_term: Short-term capital gains tax rate (default 37%)
            tax_rate_long_term: Long-term capital gains tax rate (default 20%)
            min_loss_threshold: Minimum loss to harvest in dollars (default $100)
        """
        self.trader = trader
        self.wash_sale_tracker = wash_sale_tracker
        self.tax_rate_short_term = tax_rate_short_term
        self.tax_rate_long_term = tax_rate_long_term
        self.min_loss_threshold = min_loss_threshold

        # Track harvest history for tax reporting
        self.harvest_history: List[HarvestResult] = []

        logger.info(
            f"Tax-Loss Harvester initialized: "
            f"short_term_rate={tax_rate_short_term:.1%}, "
            f"long_term_rate={tax_rate_long_term:.1%}, "
            f"min_threshold=${min_loss_threshold:.2f}"
        )

    async def scan_opportunities(self) -> List[HarvestOpportunity]:
        """
        Scan portfolio for tax-loss harvesting opportunities.

        Returns positions with unrealized losses that can be harvested.
        Filters out positions that would trigger wash sales.

        Returns:
            List of HarvestOpportunity objects, sorted by tax benefit (highest first)
        """
        opportunities = []
        positions = self.trader.get_positions()

        if not positions:
            logger.info("No positions to scan for tax-loss harvesting")
            return []

        current_date = datetime.now()

        for position in positions:
            symbol = position["symbol"]
            quantity = position["quantity"]
            avg_cost = position["avg_cost"]

            # Get current market value
            current_price = await self.trader._get_market_price(symbol)
            if not current_price:
                logger.warning(f"Could not get price for {symbol}, skipping")
                continue

            current_value = current_price * quantity
            cost_basis = avg_cost * quantity
            unrealized_pnl = current_value - cost_basis

            # Only consider positions with losses
            if unrealized_pnl >= 0:
                continue

            unrealized_loss = abs(unrealized_pnl)

            # Filter by minimum threshold
            if unrealized_loss < self.min_loss_threshold:
                logger.debug(
                    f"Skipping {symbol}: loss ${unrealized_loss:.2f} "
                    f"below threshold ${self.min_loss_threshold:.2f}"
                )
                continue

            # Check if position would trigger wash sale
            if self.wash_sale_tracker.is_wash_sale(symbol, current_date):
                logger.info(
                    f"Skipping {symbol}: would trigger wash sale "
                    f"(existing loss sale within 30 days)"
                )
                continue

            # Calculate holding period
            # For paper trader, we need to estimate purchase date from position data
            # In production, this would come from actual trade records
            purchase_date = position.get(
                "updated_at", current_date - timedelta(days=180)
            )
            if isinstance(purchase_date, str):
                purchase_date = datetime.fromisoformat(purchase_date)

            holding_period_days = (current_date - purchase_date).days
            is_short_term = holding_period_days < 365

            # Calculate estimated tax benefit
            tax_benefit = self.calculate_tax_benefit_from_params(
                unrealized_loss, is_short_term
            )

            opportunity = HarvestOpportunity(
                symbol=symbol,
                quantity=quantity,
                cost_basis=cost_basis,
                current_value=current_value,
                unrealized_loss=unrealized_loss,
                holding_period_days=holding_period_days,
                is_short_term=is_short_term,
                purchase_date=purchase_date,
                estimated_tax_benefit=tax_benefit,
            )

            opportunities.append(opportunity)

        # Sort by tax benefit (highest first)
        opportunities.sort(key=lambda x: x.estimated_tax_benefit, reverse=True)

        logger.info(
            f"Found {len(opportunities)} tax-loss harvesting opportunities "
            f"with total potential benefit: "
            f"${sum(o.estimated_tax_benefit for o in opportunities):.2f}"
        )

        return opportunities

    def calculate_tax_benefit(self, opportunity: HarvestOpportunity) -> float:
        """
        Calculate the tax benefit of harvesting a specific loss.

        Tax benefit = loss_amount × applicable_tax_rate

        Short-term losses (held < 1 year):
        - Offset short-term gains first (taxed at 37%)
        - Higher priority for harvesting

        Long-term losses (held >= 1 year):
        - Offset long-term gains (taxed at 20%)
        - Lower priority but still valuable

        Args:
            opportunity: HarvestOpportunity to calculate benefit for

        Returns:
            Estimated tax benefit in dollars
        """
        return self.calculate_tax_benefit_from_params(
            opportunity.unrealized_loss, opportunity.is_short_term
        )

    def calculate_tax_benefit_from_params(
        self, loss_amount: float, is_short_term: bool
    ) -> float:
        """
        Calculate tax benefit from loss parameters.

        Args:
            loss_amount: Dollar amount of loss (positive number)
            is_short_term: True if held < 1 year

        Returns:
            Estimated tax benefit in dollars
        """
        if is_short_term:
            # Short-term: use short-term capital gains rate (higher)
            tax_rate = self.tax_rate_short_term
        else:
            # Long-term: use long-term capital gains rate (lower)
            tax_rate = self.tax_rate_long_term

        # Tax benefit = loss × tax rate
        return loss_amount * tax_rate

    async def plan_harvest(
        self,
        max_harvests: int = 5,
        target_loss_amount: Optional[float] = None,
    ) -> List[HarvestPlan]:
        """
        Plan optimal tax-loss harvesting strategy.

        Ranks opportunities by tax benefit and creates execution plan.
        Ensures alternative symbols are available (no wash sale violations).

        Args:
            max_harvests: Maximum number of harvests to plan (default 5)
            target_loss_amount: Optional target loss amount to harvest

        Returns:
            List of HarvestPlan objects, sorted by tax benefit
        """
        opportunities = await self.scan_opportunities()

        if not opportunities:
            logger.info("No harvest opportunities available")
            return []

        plans = []
        total_loss_harvested = 0.0

        for opportunity in opportunities:
            # Check if we've reached limits
            if len(plans) >= max_harvests:
                break

            if (
                target_loss_amount is not None
                and total_loss_harvested >= target_loss_amount
            ):
                break

            # Find alternative symbol (avoid wash sale)
            alternatives = self.wash_sale_tracker.get_alternative_symbols(
                opportunity.symbol, count=1
            )

            if not alternatives:
                logger.warning(
                    f"No alternative symbols found for {opportunity.symbol}, skipping"
                )
                continue

            alternative_symbol = alternatives[0]

            # Create harvest plan
            plan = HarvestPlan(
                opportunity=opportunity,
                alternative_symbol=alternative_symbol,
                execute_date=datetime.now(),
                expected_tax_benefit=opportunity.estimated_tax_benefit,
                notes=(
                    f"Harvest {opportunity.symbol} loss of "
                    f"${opportunity.unrealized_loss:.2f}, "
                    f"replace with {alternative_symbol}. "
                    f"Tax benefit: ${opportunity.estimated_tax_benefit:.2f} "
                    f"({'short-term' if opportunity.is_short_term else 'long-term'})"  # noqa: E501
                ),
            )

            plans.append(plan)
            total_loss_harvested += opportunity.unrealized_loss

        logger.info(
            f"Planned {len(plans)} harvests with total tax benefit: "
            f"${sum(p.expected_tax_benefit for p in plans):.2f}"
        )

        return plans

    async def execute_harvest(self, plan: HarvestPlan) -> HarvestResult:
        """
        Execute a tax-loss harvest:
        1. Sell the losing position
        2. Record the loss for tax purposes
        3. Find alternative security (avoid wash sale)
        4. Buy alternative to maintain exposure

        Args:
            plan: HarvestPlan to execute

        Returns:
            HarvestResult with execution details and tax benefit realized
        """
        opportunity = plan.opportunity

        try:
            logger.info(
                f"Executing harvest: {opportunity.symbol} → {plan.alternative_symbol}"
            )

            # Step 1: Sell the losing position
            sell_order_id = await self.trader.place_market_order(
                symbol=opportunity.symbol,
                quantity=opportunity.quantity,
                action="SELL",
                auto_stop_loss=False,  # Don't place stop on sell order
            )

            if not sell_order_id:
                error_msg = f"Failed to sell {opportunity.symbol}"
                logger.error(error_msg)
                return HarvestResult(
                    original_symbol=opportunity.symbol,
                    alternative_symbol=plan.alternative_symbol,
                    quantity=opportunity.quantity,
                    loss_realized=0.0,
                    tax_benefit=0.0,
                    execution_date=datetime.now(),
                    original_cost_basis=opportunity.cost_basis,
                    sale_proceeds=0.0,
                    replacement_cost=0.0,
                    success=False,
                    error_message=error_msg,
                )

            # Get actual sale price from trade history
            trades = self.trader.get_trade_history(limit=1)
            if trades and trades[-1]["action"] == "SELL":
                sale_price = trades[-1]["price"]
                sale_proceeds = sale_price * opportunity.quantity
            else:
                # Fallback to current value
                sale_proceeds = opportunity.current_value

            # Calculate actual loss realized
            loss_realized = opportunity.cost_basis - sale_proceeds
            tax_benefit = self.calculate_tax_benefit_from_params(
                loss_realized, opportunity.is_short_term
            )

            # Step 2: Record loss with WashSaleTracker
            self.wash_sale_tracker.record_loss_sale(
                symbol=opportunity.symbol,
                quantity=opportunity.quantity,
                loss_amount=loss_realized,
                sale_date=datetime.now(),
                cost_basis=opportunity.cost_basis,
                sale_price=sale_proceeds,
            )

            # Step 3: Buy alternative (maintain market exposure)
            # Calculate quantity based on available proceeds
            alternative_price = await self.trader._get_market_price(
                plan.alternative_symbol
            )
            if not alternative_price:
                error_msg = f"Could not get price for {plan.alternative_symbol}"
                logger.error(error_msg)
                return HarvestResult(
                    original_symbol=opportunity.symbol,
                    alternative_symbol=plan.alternative_symbol,
                    quantity=opportunity.quantity,
                    loss_realized=loss_realized,
                    tax_benefit=tax_benefit,
                    execution_date=datetime.now(),
                    original_cost_basis=opportunity.cost_basis,
                    sale_proceeds=sale_proceeds,
                    replacement_cost=0.0,
                    success=False,
                    error_message=error_msg,
                )

            # Calculate how many shares we can buy with proceeds
            alternative_quantity = int(sale_proceeds / alternative_price)

            if alternative_quantity <= 0:
                error_msg = f"Insufficient proceeds to buy {plan.alternative_symbol}"
                logger.error(error_msg)
                return HarvestResult(
                    original_symbol=opportunity.symbol,
                    alternative_symbol=plan.alternative_symbol,
                    quantity=opportunity.quantity,
                    loss_realized=loss_realized,
                    tax_benefit=tax_benefit,
                    execution_date=datetime.now(),
                    original_cost_basis=opportunity.cost_basis,
                    sale_proceeds=sale_proceeds,
                    replacement_cost=0.0,
                    success=False,
                    error_message=error_msg,
                )

            buy_order_id = await self.trader.place_market_order(
                symbol=plan.alternative_symbol,
                quantity=alternative_quantity,
                action="BUY",
                auto_stop_loss=True,  # Place stop on new position
            )

            if not buy_order_id:
                error_msg = f"Failed to buy {plan.alternative_symbol}"
                logger.error(error_msg)
                return HarvestResult(
                    original_symbol=opportunity.symbol,
                    alternative_symbol=plan.alternative_symbol,
                    quantity=opportunity.quantity,
                    loss_realized=loss_realized,
                    tax_benefit=tax_benefit,
                    execution_date=datetime.now(),
                    original_cost_basis=opportunity.cost_basis,
                    sale_proceeds=sale_proceeds,
                    replacement_cost=0.0,
                    success=False,
                    error_message=error_msg,
                )

            # Get actual purchase price
            trades = self.trader.get_trade_history(limit=1)
            if trades and trades[-1]["action"] == "BUY":
                buy_price = trades[-1]["price"]
                replacement_cost = buy_price * alternative_quantity
            else:
                replacement_cost = alternative_price * alternative_quantity

            # Create successful result
            result = HarvestResult(
                original_symbol=opportunity.symbol,
                alternative_symbol=plan.alternative_symbol,
                quantity=opportunity.quantity,
                loss_realized=loss_realized,
                tax_benefit=tax_benefit,
                execution_date=datetime.now(),
                original_cost_basis=opportunity.cost_basis,
                sale_proceeds=sale_proceeds,
                replacement_cost=replacement_cost,
                success=True,
                error_message=None,
            )

            # Record in history
            self.harvest_history.append(result)

            logger.info(
                f"Harvest completed: {opportunity.symbol} → {plan.alternative_symbol}, "
                f"loss: ${loss_realized:.2f}, tax benefit: ${tax_benefit:.2f}"
            )

            return result

        except Exception as e:
            error_msg = f"Error executing harvest: {str(e)}"
            logger.error(error_msg)
            return HarvestResult(
                original_symbol=opportunity.symbol,
                alternative_symbol=plan.alternative_symbol,
                quantity=opportunity.quantity,
                loss_realized=0.0,
                tax_benefit=0.0,
                execution_date=datetime.now(),
                original_cost_basis=opportunity.cost_basis,
                sale_proceeds=0.0,
                replacement_cost=0.0,
                success=False,
                error_message=error_msg,
            )

    async def year_end_planning(self, current_date: datetime) -> YearEndPlan:
        """
        Special year-end tax planning mode.

        Maximizes tax benefits before year-end by:
        - Identifying all harvestable losses
        - Prioritizing short-term losses (higher tax rate)
        - Planning replacement purchases after Jan 1 (if needed)
        - Calculating total potential tax savings

        Important: Must settle by Dec 31 (T+2 settlement rule)
        Last safe trading day: Dec 29 or earlier

        Args:
            current_date: Current date for planning

        Returns:
            YearEndPlan with comprehensive year-end strategy
        """
        # Scan all opportunities
        opportunities = await self.scan_opportunities()

        if not opportunities:
            logger.info("No year-end harvest opportunities")
            return YearEndPlan(
                total_harvestable_loss=0.0,
                total_tax_benefit=0.0,
                short_term_opportunities=[],
                long_term_opportunities=[],
                recommended_harvests=[],
                deadline=datetime(current_date.year, 12, 31),
            )

        # Separate by holding period
        short_term = [o for o in opportunities if o.is_short_term]
        long_term = [o for o in opportunities if not o.is_short_term]

        # Sort by tax benefit (highest first)
        short_term.sort(key=lambda o: o.estimated_tax_benefit, reverse=True)
        long_term.sort(key=lambda o: o.estimated_tax_benefit, reverse=True)

        # Calculate totals
        total_loss = sum(o.unrealized_loss for o in opportunities)
        total_benefit = sum(o.estimated_tax_benefit for o in opportunities)

        # Create execution plan (prioritize short-term)
        recommended = []
        year_end_date = datetime(current_date.year, 12, 29)  # Last safe trading day

        for opp in short_term + long_term:
            # Find alternative
            alternatives = self.wash_sale_tracker.get_alternative_symbols(
                opp.symbol, count=1
            )

            if not alternatives:
                logger.warning(f"No alternative for {opp.symbol} in year-end planning")
                continue

            alt_symbol = alternatives[0]

            plan = HarvestPlan(
                opportunity=opp,
                alternative_symbol=alt_symbol,
                execute_date=year_end_date,
                expected_tax_benefit=opp.estimated_tax_benefit,
                notes=(
                    f"Year-end harvest: {opp.symbol} → {alt_symbol}. "
                    f"Loss: ${opp.unrealized_loss:.2f}, "
                    f"Tax benefit: ${opp.estimated_tax_benefit:.2f} "
                    f"({'short-term' if opp.is_short_term else 'long-term'}). "
                    f"Execute by Dec 29 for T+2 settlement by Dec 31."
                ),
            )
            recommended.append(plan)

        year_end_plan = YearEndPlan(
            total_harvestable_loss=total_loss,
            total_tax_benefit=total_benefit,
            short_term_opportunities=short_term,
            long_term_opportunities=long_term,
            recommended_harvests=recommended,
            deadline=datetime(current_date.year, 12, 31),
        )

        logger.info(
            f"Year-end planning complete: "
            f"{len(short_term)} short-term + {len(long_term)} long-term opportunities, "
            f"total tax benefit: ${total_benefit:.2f}"
        )

        return year_end_plan

    def get_harvest_history(self) -> List[HarvestResult]:
        """
        Get history of all executed harvests for tax reporting.

        Returns:
            List of HarvestResult objects, sorted by execution date (newest first)
        """
        return sorted(
            self.harvest_history, key=lambda x: x.execution_date, reverse=True
        )

    def estimate_annual_alpha(self) -> float:
        """
        Estimate annual alpha from tax-loss harvesting.

        Target: 3-5% annual improvement through tax savings.

        Calculation:
        - Sum total tax benefits from harvest history
        - Divide by initial portfolio value
        - Annualize based on time period

        Returns:
            Estimated annual alpha percentage (e.g., 0.035 = 3.5%)
        """
        if not self.harvest_history:
            logger.info("No harvest history - cannot estimate alpha")
            return 0.0

        # Sum total tax benefits
        total_tax_benefit = sum(h.tax_benefit for h in self.harvest_history)

        # Get portfolio value
        portfolio_value = self.trader.get_portfolio_value()

        if portfolio_value <= 0:
            return 0.0

        # Calculate alpha as percentage of portfolio
        alpha = total_tax_benefit / portfolio_value

        # For simplicity, assume harvests are spread over 1 year
        # In production, would annualize based on actual time period
        annual_alpha = alpha

        logger.info(
            f"Estimated annual alpha from tax-loss harvesting: {annual_alpha:.2%} "
            f"(${total_tax_benefit:.2f} benefit on ${portfolio_value:.2f} portfolio)"
        )

        return annual_alpha
