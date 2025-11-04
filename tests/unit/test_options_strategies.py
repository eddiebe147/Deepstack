"""
Comprehensive tests for options trading strategies.

Tests cover:
- Iron Condor strategy
- Bull Call Spread
- Bear Put Spread
- Greeks calculation
- P&L modeling
- Auto-close logic
- Edge cases
"""

from datetime import datetime, timedelta

import pytest

from core.strategies.options import (
    BearPutSpread,
    BullCallSpread,
    IronCondorStrategy,
    OptionLeg,
    OptionsPosition,
    calculate_black_scholes_greeks,
    calculate_position_greeks,
    model_pnl_scenarios,
)
from core.strategies.options.pnl_modeling import (
    calculate_pnl,
    calculate_pnl_at_expiration,
    calculate_roi,
    find_breakeven_points,
    get_risk_reward_ratio,
)

# ============================================================================
# Base Classes Tests
# ============================================================================


class TestOptionLeg:
    """Test OptionLeg data model."""

    def test_create_valid_option_leg(self):
        """Test creating a valid option leg."""
        expiration = datetime.now() + timedelta(days=45)
        leg = OptionLeg(
            symbol="AAPL",
            strike=150.0,
            expiration=expiration,
            option_type="call",
            action="buy",
            quantity=1,
            premium=5.0,
        )

        assert leg.symbol == "AAPL"
        assert leg.strike == 150.0
        assert leg.option_type == "call"
        assert leg.action == "buy"
        assert leg.quantity == 1
        assert leg.premium == 5.0

    def test_invalid_option_type(self):
        """Test that invalid option type raises error."""
        expiration = datetime.now() + timedelta(days=45)
        with pytest.raises(ValueError, match="option_type must be"):
            OptionLeg(
                symbol="AAPL",
                strike=150.0,
                expiration=expiration,
                option_type="invalid",
                action="buy",
                quantity=1,
                premium=5.0,
            )

    def test_invalid_action(self):
        """Test that invalid action raises error."""
        expiration = datetime.now() + timedelta(days=45)
        with pytest.raises(ValueError, match="action must be"):
            OptionLeg(
                symbol="AAPL",
                strike=150.0,
                expiration=expiration,
                option_type="call",
                action="hold",
                quantity=1,
                premium=5.0,
            )

    def test_negative_strike(self):
        """Test that negative strike raises error."""
        expiration = datetime.now() + timedelta(days=45)
        with pytest.raises(ValueError, match="strike must be positive"):
            OptionLeg(
                symbol="AAPL",
                strike=-150.0,
                expiration=expiration,
                option_type="call",
                action="buy",
                quantity=1,
                premium=5.0,
            )

    def test_contract_multiplier(self):
        """Test contract multiplier (should be 100)."""
        expiration = datetime.now() + timedelta(days=45)
        leg = OptionLeg(
            symbol="AAPL",
            strike=150.0,
            expiration=expiration,
            option_type="call",
            action="buy",
            quantity=2,
            premium=5.0,
        )

        assert leg.contract_multiplier() == 100

    def test_total_premium(self):
        """Test total premium calculation."""
        expiration = datetime.now() + timedelta(days=45)
        leg = OptionLeg(
            symbol="AAPL",
            strike=150.0,
            expiration=expiration,
            option_type="call",
            action="buy",
            quantity=2,
            premium=5.0,
        )

        # 5.0 * 2 * 100 = 1000
        assert leg.total_premium() == 1000.0

    def test_to_dict(self):
        """Test converting leg to dictionary."""
        expiration = datetime.now() + timedelta(days=45)
        leg = OptionLeg(
            symbol="AAPL",
            strike=150.0,
            expiration=expiration,
            option_type="call",
            action="buy",
            quantity=1,
            premium=5.0,
        )

        leg_dict = leg.to_dict()
        assert leg_dict["symbol"] == "AAPL"
        assert leg_dict["strike"] == 150.0
        assert leg_dict["option_type"] == "call"


class TestOptionsPosition:
    """Test OptionsPosition data model."""

    def test_create_valid_position(self):
        """Test creating a valid options position."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [
            OptionLeg("AAPL", 150.0, expiration, "call", "buy", 1, 5.0),
            OptionLeg("AAPL", 155.0, expiration, "call", "sell", 1, 2.0),
        ]

        position = OptionsPosition(
            strategy_name="Bull Call Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=300.0,
            max_profit=200.0,
            max_loss=300.0,
            breakeven_points=[153.0],
        )

        assert position.strategy_name == "Bull Call Spread"
        assert len(position.legs) == 2
        assert position.symbol == "AAPL"
        assert position.expiration == expiration

    def test_empty_legs_raises_error(self):
        """Test that empty legs list raises error."""
        with pytest.raises(ValueError, match="at least one leg"):
            OptionsPosition(
                strategy_name="Test",
                legs=[],
                entry_date=datetime.now(),
                entry_cost=0.0,
                max_profit=0.0,
                max_loss=0.0,
                breakeven_points=[],
            )

    def test_mismatched_symbols_raises_error(self):
        """Test that different symbols raise error."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [
            OptionLeg("AAPL", 150.0, expiration, "call", "buy", 1, 5.0),
            OptionLeg("MSFT", 155.0, expiration, "call", "sell", 1, 2.0),
        ]

        with pytest.raises(ValueError, match="same symbol"):
            OptionsPosition(
                strategy_name="Test",
                legs=legs,
                entry_date=datetime.now(),
                entry_cost=0.0,
                max_profit=0.0,
                max_loss=0.0,
                breakeven_points=[],
            )

    def test_days_to_expiration(self):
        """Test days to expiration calculation."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [OptionLeg("AAPL", 150.0, expiration, "call", "buy", 1, 5.0)]

        position = OptionsPosition(
            strategy_name="Test",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=0.0,
            max_profit=0.0,
            max_loss=0.0,
            breakeven_points=[],
        )

        dte = position.days_to_expiration()
        assert 44 <= dte <= 45  # Allow for timing

    def test_is_credit_spread(self):
        """Test credit spread detection."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [OptionLeg("AAPL", 150.0, expiration, "call", "buy", 1, 5.0)]

        # Credit spread (negative cost)
        credit_position = OptionsPosition(
            strategy_name="Credit Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=-400.0,
            max_profit=400.0,
            max_loss=100.0,
            breakeven_points=[],
        )

        assert credit_position.is_credit_spread()
        assert credit_position.net_credit_received() == 400.0
        assert credit_position.net_debit_paid() == 0.0

        # Debit spread (positive cost)
        debit_position = OptionsPosition(
            strategy_name="Debit Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=300.0,
            max_profit=200.0,
            max_loss=300.0,
            breakeven_points=[],
        )

        assert not debit_position.is_credit_spread()
        assert debit_position.net_credit_received() == 0.0
        assert debit_position.net_debit_paid() == 300.0


# ============================================================================
# Greeks Calculation Tests
# ============================================================================


class TestGreeksCalculation:
    """Test Black-Scholes Greeks calculations."""

    def test_calculate_call_greeks(self):
        """Test Greeks calculation for call option."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.30,
            risk_free_rate=0.05,
            option_type="call",
        )

        # ATM call should have delta around 0.5
        assert 0.4 < greeks["delta"] < 0.6
        assert greeks["gamma"] > 0
        assert greeks["theta"] < 0  # Time decay is negative
        assert greeks["vega"] > 0
        assert greeks["price"] > 0

    def test_calculate_put_greeks(self):
        """Test Greeks calculation for put option."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.30,
            risk_free_rate=0.05,
            option_type="put",
        )

        # ATM put should have delta around -0.5
        assert -0.6 < greeks["delta"] < -0.4
        assert greeks["gamma"] > 0
        assert greeks["theta"] < 0
        assert greeks["vega"] > 0
        assert greeks["price"] > 0

    def test_itm_call_delta(self):
        """Test that ITM call has higher delta."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=110.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.30,
            option_type="call",
        )

        # ITM call should have delta > 0.5
        assert greeks["delta"] > 0.5

    def test_otm_call_delta(self):
        """Test that OTM call has lower delta."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=90.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.30,
            option_type="call",
        )

        # OTM call should have delta < 0.5
        assert greeks["delta"] < 0.5

    def test_expiration_day_greeks(self):
        """Test Greeks at expiration (0 DTE)."""
        # ITM call at expiration
        greeks = calculate_black_scholes_greeks(
            underlying_price=110.0,
            strike=100.0,
            days_to_expiration=0,
            volatility=0.30,
            option_type="call",
        )

        # Should have intrinsic value
        assert greeks["price"] == 10.0
        assert greeks["delta"] == 1.0
        assert greeks["gamma"] == 0.0
        assert greeks["theta"] == 0.0
        assert greeks["vega"] == 0.0

    def test_expiration_otm_call(self):
        """Test OTM call at expiration."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=90.0,
            strike=100.0,
            days_to_expiration=0,
            volatility=0.30,
            option_type="call",
        )

        assert greeks["price"] == 0.0
        assert greeks["delta"] == 0.0

    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        with pytest.raises(ValueError):
            calculate_black_scholes_greeks(
                underlying_price=-100.0,
                strike=100.0,
                days_to_expiration=45,
                volatility=0.30,
                option_type="call",
            )

        with pytest.raises(ValueError):
            calculate_black_scholes_greeks(
                underlying_price=100.0,
                strike=100.0,
                days_to_expiration=45,
                volatility=0.30,
                option_type="invalid",
            )

    def test_position_greeks(self):
        """Test calculating total position Greeks."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [
            OptionLeg("AAPL", 100.0, expiration, "call", "buy", 1, 5.0),
            OptionLeg("AAPL", 105.0, expiration, "call", "sell", 1, 2.0),
        ]

        position = OptionsPosition(
            strategy_name="Bull Call Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=300.0,
            max_profit=200.0,
            max_loss=300.0,
            breakeven_points=[103.0],
        )

        greeks = calculate_position_greeks(
            position=position,
            underlying_price=100.0,
            days_to_expiration=45,
            volatility=0.30,
        )

        # Bull call spread should have positive delta (bullish)
        assert greeks.delta > 0
        # But lower than a naked call (we sold the upside)
        assert greeks.delta < 1.0


# ============================================================================
# Iron Condor Tests
# ============================================================================


class TestIronCondorStrategy:
    """Test Iron Condor strategy."""

    def test_create_iron_condor(self):
        """Test creating an Iron Condor position."""
        strategy = IronCondorStrategy(
            wing_width=5.0,
            range_width_pct=0.05,
            profit_target_pct=0.50,
            loss_limit_pct=0.50,
        )

        position = strategy.create_position(
            symbol="SPY",
            underlying_price=400.0,
            expiration_days=45,
            contracts=1,
            volatility=0.20,
        )

        # Should have 4 legs
        assert len(position.legs) == 4

        # Check leg types and actions
        assert position.legs[0].option_type == "put"
        assert position.legs[0].action == "sell"
        assert position.legs[1].option_type == "put"
        assert position.legs[1].action == "buy"
        assert position.legs[2].option_type == "call"
        assert position.legs[2].action == "sell"
        assert position.legs[3].option_type == "call"
        assert position.legs[3].action == "buy"

        # Verify strike relationships
        # Put spread: sell > buy (lower strikes)
        assert position.legs[0].strike > position.legs[1].strike
        # Call spread: sell < buy (higher strikes)
        assert position.legs[2].strike < position.legs[3].strike

        # Verify wing width
        put_width = position.legs[0].strike - position.legs[1].strike
        call_width = position.legs[3].strike - position.legs[2].strike
        assert abs(put_width - 5.0) < 0.01
        assert abs(call_width - 5.0) < 0.01

        # Should be a credit spread
        assert position.is_credit_spread()
        assert position.max_profit > 0
        assert position.max_loss > 0

    def test_iron_condor_symmetry(self):
        """Test that Iron Condor is symmetric around price."""
        strategy = IronCondorStrategy(wing_width=5.0, range_width_pct=0.05)

        position = strategy.create_position(
            symbol="SPY",
            underlying_price=400.0,
            expiration_days=45,
            contracts=1,
            volatility=0.20,
        )

        # Short strikes should be equidistant from current price
        short_put = position.legs[0].strike
        short_call = position.legs[2].strike
        center = (short_put + short_call) / 2

        # Center should be close to current price
        assert abs(center - 400.0) < 1.0

    def test_iron_condor_max_profit_loss(self):
        """Test Iron Condor max profit and loss calculations."""
        strategy = IronCondorStrategy(wing_width=5.0)

        position = strategy.create_position(
            symbol="SPY", underlying_price=400.0, expiration_days=45, contracts=1
        )

        # Max loss = wing width - credit received
        expected_max_loss = (5.0 * 100) - position.net_credit_received()
        assert abs(position.max_loss - expected_max_loss) < 1.0

        # Max profit = credit received
        assert abs(position.max_profit - position.net_credit_received()) < 0.01

    def test_iron_condor_pnl_calculation(self):
        """Test P&L calculation for Iron Condor."""
        strategy = IronCondorStrategy()

        position = strategy.create_position(
            symbol="SPY", underlying_price=400.0, expiration_days=45, contracts=1
        )

        # At entry price, P&L should be less than max profit
        pnl = strategy.calculate_pnl(
            position=position,
            current_price=400.0,
            days_to_expiration=45,
            volatility=0.20,
        )

        # Should be less than max profit (haven't captured full time decay yet)
        assert pnl < position.max_profit
        # Should be greater than max loss (not breached strikes)
        assert pnl > -position.max_loss

    def test_iron_condor_profit_target(self):
        """Test Iron Condor profit target logic."""
        strategy = IronCondorStrategy(profit_target_pct=0.50)

        position = strategy.create_position(
            symbol="SPY", underlying_price=400.0, expiration_days=45, contracts=1
        )

        # Should close at 50% of max profit
        profit_target = position.max_profit * 0.50
        should_close = strategy.should_close(
            position=position, current_pnl=profit_target + 1, days_to_expiration=30
        )

        assert should_close

    def test_iron_condor_loss_limit(self):
        """Test Iron Condor loss limit logic."""
        strategy = IronCondorStrategy(loss_limit_pct=0.50)

        position = strategy.create_position(
            symbol="SPY", underlying_price=400.0, expiration_days=45, contracts=1
        )

        # Should close at 50% of max loss
        loss_limit = -abs(position.max_loss * 0.50)
        should_close = strategy.should_close(
            position=position, current_pnl=loss_limit - 1, days_to_expiration=30
        )

        assert should_close

    def test_iron_condor_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        with pytest.raises(ValueError):
            IronCondorStrategy(wing_width=-5.0)

        with pytest.raises(ValueError):
            IronCondorStrategy(range_width_pct=1.5)

        with pytest.raises(ValueError):
            IronCondorStrategy(profit_target_pct=1.5)


# ============================================================================
# Vertical Spreads Tests
# ============================================================================


class TestBullCallSpread:
    """Test Bull Call Spread strategy."""

    def test_create_bull_call_spread(self):
        """Test creating a Bull Call Spread."""
        strategy = BullCallSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL",
            underlying_price=150.0,
            expiration_days=45,
            contracts=1,
            volatility=0.30,
        )

        # Should have 2 legs
        assert len(position.legs) == 2

        # Both should be calls
        assert position.legs[0].option_type == "call"
        assert position.legs[1].option_type == "call"

        # Long lower strike, short higher strike
        assert position.legs[0].action == "buy"
        assert position.legs[1].action == "sell"
        assert position.legs[0].strike < position.legs[1].strike

        # Should be a debit spread
        assert not position.is_credit_spread()
        assert position.net_debit_paid() > 0

    def test_bull_call_spread_max_profit_loss(self):
        """Test Bull Call Spread max profit/loss calculations."""
        strategy = BullCallSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Max profit = strike width - debit paid
        expected_max_profit = (5.0 * 100) - position.net_debit_paid()
        assert abs(position.max_profit - expected_max_profit) < 1.0

        # Max loss = debit paid
        assert abs(position.max_loss - position.net_debit_paid()) < 0.01

    def test_bull_call_spread_breakeven(self):
        """Test Bull Call Spread breakeven calculation."""
        strategy = BullCallSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Breakeven = long strike + debit per share
        long_strike = position.legs[0].strike
        debit_per_share = position.net_debit_paid() / 100
        expected_breakeven = long_strike + debit_per_share

        assert len(position.breakeven_points) == 1
        assert abs(position.breakeven_points[0] - expected_breakeven) < 0.01

    def test_bull_call_spread_profit_target(self):
        """Test Bull Call Spread profit target."""
        strategy = BullCallSpread(profit_target_pct=0.70)

        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        profit_target = position.max_profit * 0.70
        should_close = strategy.should_close(
            position=position, current_pnl=profit_target + 1, days_to_expiration=30
        )

        assert should_close


class TestBearPutSpread:
    """Test Bear Put Spread strategy."""

    def test_create_bear_put_spread(self):
        """Test creating a Bear Put Spread."""
        strategy = BearPutSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL",
            underlying_price=150.0,
            expiration_days=45,
            contracts=1,
            volatility=0.30,
        )

        # Should have 2 legs
        assert len(position.legs) == 2

        # Both should be puts
        assert position.legs[0].option_type == "put"
        assert position.legs[1].option_type == "put"

        # Long higher strike, short lower strike
        assert position.legs[0].action == "buy"
        assert position.legs[1].action == "sell"
        assert position.legs[0].strike > position.legs[1].strike

        # Should be a debit spread
        assert not position.is_credit_spread()
        assert position.net_debit_paid() > 0

    def test_bear_put_spread_max_profit_loss(self):
        """Test Bear Put Spread max profit/loss calculations."""
        strategy = BearPutSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Max profit = strike width - debit paid
        expected_max_profit = (5.0 * 100) - position.net_debit_paid()
        assert abs(position.max_profit - expected_max_profit) < 1.0

        # Max loss = debit paid
        assert abs(position.max_loss - position.net_debit_paid()) < 0.01

    def test_bear_put_spread_breakeven(self):
        """Test Bear Put Spread breakeven calculation."""
        strategy = BearPutSpread(strike_width=5.0)

        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Breakeven = long strike - debit per share
        long_strike = position.legs[0].strike
        debit_per_share = position.net_debit_paid() / 100
        expected_breakeven = long_strike - debit_per_share

        assert len(position.breakeven_points) == 1
        assert abs(position.breakeven_points[0] - expected_breakeven) < 0.01


# ============================================================================
# P&L Modeling Tests
# ============================================================================


class TestPnLModeling:
    """Test P&L scenario modeling."""

    def test_model_pnl_scenarios(self):
        """Test P&L modeling across price range."""
        strategy = BullCallSpread(strike_width=5.0)
        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        scenarios = model_pnl_scenarios(
            position=position, days_to_expiration=45, volatility=0.30, num_points=20
        )

        # Should have 20 price points
        assert len(scenarios) == 20

        # All should have P&L values
        for price, pnl in scenarios.items():
            assert isinstance(price, float)
            assert isinstance(pnl, (int, float))

    def test_pnl_at_expiration(self):
        """Test P&L calculation at expiration."""
        strategy = BullCallSpread(strike_width=5.0)
        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        scenarios = calculate_pnl_at_expiration(position=position, num_points=10)

        # Should have 10 price points
        assert len(scenarios) == 10

        # Find max profit scenario
        max_pnl = max(scenarios.values())
        # At expiration, max profit should match position.max_profit
        assert abs(max_pnl - position.max_profit) < 1.0

    def test_find_breakeven_points(self):
        """Test finding breakeven points."""
        strategy = BullCallSpread(strike_width=5.0)
        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        breakevens = find_breakeven_points(position)

        # Bull call spread should have 1 breakeven
        assert len(breakevens) == 1

        # Should match the position's breakeven
        assert abs(breakevens[0] - position.breakeven_points[0]) < 0.5

    def test_calculate_roi(self):
        """Test ROI calculation."""
        # Credit spread
        expiration = datetime.now() + timedelta(days=45)
        legs = [OptionLeg("SPY", 400.0, expiration, "put", "sell", 1, 2.0)]
        credit_position = OptionsPosition(
            strategy_name="Credit Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=-400.0,
            max_profit=400.0,
            max_loss=100.0,
            breakeven_points=[],
        )

        roi = calculate_roi(credit_position, 50.0)
        # ROI = 50 / 100 = 0.50 (50%)
        assert abs(roi - 0.50) < 0.01

        # Debit spread
        debit_position = OptionsPosition(
            strategy_name="Debit Spread",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=300.0,
            max_profit=200.0,
            max_loss=300.0,
            breakeven_points=[],
        )

        roi = calculate_roi(debit_position, 60.0)
        # ROI = 60 / 300 = 0.20 (20%)
        assert abs(roi - 0.20) < 0.01

    def test_risk_reward_ratio(self):
        """Test risk/reward ratio calculation."""
        expiration = datetime.now() + timedelta(days=45)
        legs = [OptionLeg("SPY", 400.0, expiration, "call", "buy", 1, 5.0)]

        position = OptionsPosition(
            strategy_name="Test",
            legs=legs,
            entry_date=datetime.now(),
            entry_cost=300.0,
            max_profit=200.0,
            max_loss=300.0,
            breakeven_points=[],
        )

        ratio = get_risk_reward_ratio(position)
        # 200 / 300 = 0.667
        assert abs(ratio - 0.667) < 0.01


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_iron_condor_full_lifecycle(self):
        """Test complete Iron Condor lifecycle."""
        strategy = IronCondorStrategy(
            wing_width=5.0, range_width_pct=0.05, profit_target_pct=0.50
        )

        # Create position
        position = strategy.create_position(
            symbol="SPY",
            underlying_price=400.0,
            expiration_days=45,
            contracts=2,
            volatility=0.20,
        )

        assert len(position.legs) == 4
        assert position.is_credit_spread()

        # Calculate Greeks
        greeks = calculate_position_greeks(
            position=position,
            underlying_price=400.0,
            days_to_expiration=45,
            volatility=0.20,
        )

        # Iron Condor should be delta neutral (close to 0)
        assert abs(greeks.delta) < 0.5
        # Theta magnitude should be reasonable (iron condor benefits from time decay)
        # Note: When we SELL options, positive theta means we benefit from time decay
        assert abs(greeks.theta) > 0

        # Model P&L scenarios
        scenarios = model_pnl_scenarios(
            position=position, days_to_expiration=45, volatility=0.20, num_points=50
        )

        assert len(scenarios) == 50

        # Test profit target
        current_pnl = position.max_profit * 0.60
        should_close = strategy.should_close(
            position=position, current_pnl=current_pnl, days_to_expiration=30
        )

        assert should_close  # Should close at 60% (target is 50%)

    def test_vertical_spread_comparison(self):
        """Compare Bull Call and Bear Put spreads."""
        bull_strategy = BullCallSpread(strike_width=5.0)
        bear_strategy = BearPutSpread(strike_width=5.0)

        bull_position = bull_strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        bear_position = bear_strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Both should be debit spreads
        assert not bull_position.is_credit_spread()
        assert not bear_position.is_credit_spread()

        # Bull should have positive delta
        bull_greeks = calculate_position_greeks(bull_position, 150.0, 45, 0.30)
        assert bull_greeks.delta > 0

        # Bear should have negative delta
        bear_greeks = calculate_position_greeks(bear_position, 150.0, 45, 0.30)
        assert bear_greeks.delta < 0


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_deep_itm_option(self):
        """Test deep ITM option Greeks."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=150.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.30,
            option_type="call",
        )

        # Deep ITM call should have delta close to 1
        assert greeks["delta"] > 0.9

    def test_deep_otm_option(self):
        """Test deep OTM option Greeks."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=150.0,
            days_to_expiration=45,
            volatility=0.30,
            option_type="call",
        )

        # Deep OTM call should have delta close to 0
        assert greeks["delta"] < 0.1

    def test_high_volatility_impact(self):
        """Test impact of high volatility on option price."""
        low_vol = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.10,
            option_type="call",
        )

        high_vol = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=100.0,
            days_to_expiration=45,
            volatility=0.50,
            option_type="call",
        )

        # Higher volatility should increase option price
        assert high_vol["price"] > low_vol["price"]
        # And increase vega
        assert high_vol["vega"] > low_vol["vega"]

    def test_multi_contract_position(self):
        """Test position with multiple contracts."""
        strategy = IronCondorStrategy()
        position = strategy.create_position(
            symbol="SPY",
            underlying_price=400.0,
            expiration_days=45,
            contracts=10,  # 10 contracts
        )

        # Max profit/loss should scale with contracts
        assert position.max_profit > 1000
        assert position.max_loss > 100

    def test_very_short_dte(self):
        """Test options with very short time to expiration."""
        greeks = calculate_black_scholes_greeks(
            underlying_price=100.0,
            strike=100.0,
            days_to_expiration=1,
            volatility=0.30,
            option_type="call",
        )

        # Very short DTE should have high theta (time decay)
        assert greeks["theta"] < -0.1

    def test_position_at_expiration(self):
        """Test position value at expiration."""
        strategy = BullCallSpread(strike_width=5.0)
        position = strategy.create_position(
            symbol="AAPL", underlying_price=150.0, expiration_days=45, contracts=1
        )

        # Calculate P&L at expiration with stock above short strike
        pnl = calculate_pnl(
            position=position,
            current_price=160.0,  # Above both strikes
            days_to_expiration=0,
            volatility=0.30,
        )

        # Should be at max profit
        assert abs(pnl - position.max_profit) < 1.0
