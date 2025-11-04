"""
Comprehensive tests for Stop Loss Manager.

Tests all stop types, never-downgrade rule, 100% coverage validation,
and integration with position sizing.
"""

import pytest

from core.risk.stop_loss_manager import StopLossManager


class TestStopLossManagerInit:
    """Test stop loss manager initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        manager = StopLossManager(account_balance=100000)

        assert manager.account_balance == 100000
        assert manager.max_risk_per_trade == 0.02
        assert manager.default_stop_pct == 0.02
        assert manager.default_atr_multiplier == 2.0
        assert manager.default_trailing_pct == 0.05
        assert len(manager.active_stops) == 0

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        manager = StopLossManager(
            account_balance=50000,
            max_risk_per_trade=0.01,
            default_stop_pct=0.015,
            default_atr_multiplier=1.5,
            default_trailing_pct=0.03,
        )

        assert manager.account_balance == 50000
        assert manager.max_risk_per_trade == 0.01
        assert manager.default_stop_pct == 0.015
        assert manager.default_atr_multiplier == 1.5
        assert manager.default_trailing_pct == 0.03

    def test_init_invalid_balance(self):
        """Test initialization fails with invalid balance."""
        with pytest.raises(ValueError, match="Account balance must be positive"):
            StopLossManager(account_balance=-1000)

        with pytest.raises(ValueError, match="Account balance must be positive"):
            StopLossManager(account_balance=0)

    def test_init_invalid_risk_params(self):
        """Test initialization fails with invalid risk parameters."""
        with pytest.raises(ValueError, match="max_risk_per_trade"):
            StopLossManager(account_balance=100000, max_risk_per_trade=0)

        with pytest.raises(ValueError, match="max_risk_per_trade"):
            StopLossManager(account_balance=100000, max_risk_per_trade=0.15)

        with pytest.raises(ValueError, match="default_stop_pct"):
            StopLossManager(account_balance=100000, default_stop_pct=0)

        with pytest.raises(ValueError, match="default_stop_pct"):
            StopLossManager(account_balance=100000, default_stop_pct=1.5)


class TestFixedPercentageStops:
    """Test fixed percentage stop calculations."""

    def test_fixed_pct_long_stop(self):
        """Test fixed % stop for long position."""
        manager = StopLossManager(account_balance=100000, default_stop_pct=0.02)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=10000.0,
            position_side="long",
            stop_type="fixed_pct",
        )

        assert result["stop_price"] == 147.0  # 150 * (1 - 0.02)
        assert result["stop_type"] == "fixed_pct"
        assert result["position_side"] == "long"
        assert result["risk_amount"] == pytest.approx(200.0, abs=1.0)  # ~2% of $10k
        assert result["stop_distance"] == 0.02

    def test_fixed_pct_short_stop(self):
        """Test fixed % stop for short position."""
        manager = StopLossManager(account_balance=100000, default_stop_pct=0.02)

        result = manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="fixed_pct",
        )

        assert result["stop_price"] == 204.0  # 200 * (1 + 0.02)
        assert result["stop_type"] == "fixed_pct"
        assert result["position_side"] == "short"
        assert result["risk_amount"] == pytest.approx(200.0, abs=1.0)

    def test_fixed_pct_custom_percentage(self):
        """Test fixed % stop with custom percentage."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=5000.0,
            stop_type="fixed_pct",
            stop_pct=0.05,  # 5% stop
        )

        assert result["stop_price"] == 95.0  # 100 * (1 - 0.05)
        assert result["stop_distance"] == 0.05

    def test_stop_stores_in_active_stops(self):
        """Test that calculated stops are stored in active_stops."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )

        assert "AAPL" in manager.active_stops
        assert manager.active_stops["AAPL"]["stop_price"] == 147.0
        assert manager.active_stops["AAPL"]["entry_price"] == 150.0


class TestATRBasedStops:
    """Test ATR-based stop calculations."""

    def test_atr_based_long_stop(self):
        """Test ATR-based stop for long position."""
        manager = StopLossManager(account_balance=100000, default_atr_multiplier=2.0)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=10000.0,
            position_side="long",
            stop_type="atr_based",
            atr=3.0,
            atr_multiplier=2.0,
        )

        assert result["stop_price"] == 144.0  # 150 - (3.0 * 2.0)
        assert result["stop_type"] == "atr_based"
        assert "ATR-based" in result["rationale"]

    def test_atr_based_short_stop(self):
        """Test ATR-based stop for short position."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="atr_based",
            atr=5.0,
            atr_multiplier=2.5,
        )

        assert result["stop_price"] == 212.5  # 200 + (5.0 * 2.5)
        assert result["stop_type"] == "atr_based"

    def test_atr_based_different_multipliers(self):
        """Test ATR-based stops with different multipliers."""
        manager = StopLossManager(account_balance=100000)

        # 1.5x ATR
        result1 = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=5000.0,
            stop_type="atr_based",
            atr=2.0,
            atr_multiplier=1.5,
        )
        assert result1["stop_price"] == 97.0  # 100 - (2.0 * 1.5)

        # 3.0x ATR
        result2 = manager.calculate_stop_loss(
            symbol="GOOGL",
            entry_price=100.0,
            position_size=5000.0,
            stop_type="atr_based",
            atr=2.0,
            atr_multiplier=3.0,
        )
        assert result2["stop_price"] == 94.0  # 100 - (2.0 * 3.0)

    def test_atr_based_requires_atr_value(self):
        """Test that ATR-based stops require ATR value."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="ATR value required"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=150.0,
                position_size=10000.0,
                stop_type="atr_based",
                # Missing atr parameter
            )

    def test_atr_based_rejects_invalid_atr(self):
        """Test that ATR-based stops reject invalid ATR values."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="ATR value required"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=150.0,
                position_size=10000.0,
                stop_type="atr_based",
                atr=0,
            )

        with pytest.raises(ValueError, match="ATR value required"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=150.0,
                position_size=10000.0,
                stop_type="atr_based",
                atr=-1.0,
            )


class TestTrailingStops:
    """Test trailing stop functionality."""

    def test_trailing_stop_initialization(self):
        """Test trailing stop is initialized correctly."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=10000.0,
            stop_type="trailing",
        )

        assert result["stop_price"] == 142.5  # 150 * (1 - 0.05)
        assert result["stop_type"] == "trailing"
        assert "Trailing stop" in result["rationale"]

    def test_trailing_stop_moves_up_long(self):
        """Test trailing stop moves up with price for longs."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # Initial stop
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="trailing",
        )
        initial_stop = manager.active_stops["AAPL"]["stop_price"]
        assert initial_stop == 95.0  # 100 * (1 - 0.05)

        # Price moves up to 110
        update1 = manager.update_trailing_stop(symbol="AAPL", current_price=110.0)
        assert update1["stop_price"] == 104.5  # 110 * (1 - 0.05)
        assert update1["stop_moved"] is True
        assert update1["highest_price"] == 110.0

        # Price moves up to 120
        update2 = manager.update_trailing_stop(symbol="AAPL", current_price=120.0)
        assert update2["stop_price"] == 114.0  # 120 * (1 - 0.05)
        assert update2["stop_moved"] is True
        assert update2["highest_price"] == 120.0

    def test_trailing_stop_never_downgrades_long(self):
        """Test trailing stop never moves down for longs (never-downgrade rule)."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # Initial stop at $100
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="trailing",
        )

        # Price moves up to 120, stop moves to 114
        manager.update_trailing_stop(symbol="AAPL", current_price=120.0)
        assert manager.active_stops["AAPL"]["stop_price"] == 114.0

        # Price drops to 110 (below high of 120)
        # Stop should NOT move down (never-downgrade)
        update = manager.update_trailing_stop(symbol="AAPL", current_price=110.0)
        assert update["stop_price"] == 114.0  # Unchanged
        assert update["stop_moved"] is False
        assert "never-downgrade" in update["rationale"]

    def test_trailing_stop_moves_down_short(self):
        """Test trailing stop moves down with price for shorts."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # Initial stop for short
        manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="trailing",
        )
        initial_stop = manager.active_stops["TSLA"]["stop_price"]
        assert initial_stop == 210.0  # 200 * (1 + 0.05)

        # Price moves down to 180 (favorable for short)
        update1 = manager.update_trailing_stop(symbol="TSLA", current_price=180.0)
        assert update1["stop_price"] == 189.0  # 180 * (1 + 0.05)
        assert update1["stop_moved"] is True
        assert update1["lowest_price"] == 180.0

    def test_trailing_stop_never_downgrades_short(self):
        """Test trailing stop never moves up for shorts (never-downgrade rule)."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # Initial stop for short at $200
        manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="trailing",
        )

        # Price moves down to 180, stop moves to 189
        manager.update_trailing_stop(symbol="TSLA", current_price=180.0)
        assert manager.active_stops["TSLA"]["stop_price"] == 189.0

        # Price moves back up to 190 (unfavorable for short)
        # Stop should NOT move up (never-downgrade for shorts)
        update = manager.update_trailing_stop(symbol="TSLA", current_price=190.0)
        assert update["stop_price"] == 189.0  # Unchanged
        assert update["stop_moved"] is False

    def test_trailing_stop_locks_profits(self):
        """Test trailing stop locks in profits."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # Entry at 100
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="trailing",
        )

        # Price moves to 150 (50% gain)
        update = manager.update_trailing_stop(symbol="AAPL", current_price=150.0)
        new_stop = update["stop_price"]
        assert new_stop == 142.5  # 150 * (1 - 0.05)

        # Profit locked = new_stop - entry = 142.5 - 100 = 42.5
        assert update["profit_locked"] == 42.5


class TestStopNeverDowngrades:
    """Test never-downgrade rule validation."""

    def test_validate_no_downgrade_long(self):
        """Test validation allows stop to move up for longs."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["AAPL"]["stop_price"]  # 98

        # Moving stop up is allowed
        is_valid = manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=99.0)
        assert is_valid is True

    def test_validate_detects_downgrade_long(self):
        """Test validation detects downgrade for longs."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["AAPL"]["stop_price"]  # 98

        # Moving stop down is NOT allowed (downgrade)
        is_valid = manager.validate_stop_never_downgrades(symbol="AAPL", new_stop=97.0)
        assert is_valid is False

    def test_validate_no_downgrade_short(self):
        """Test validation allows stop to move down for shorts."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["TSLA"]["stop_price"]  # 204

        # Moving stop down is allowed for shorts
        is_valid = manager.validate_stop_never_downgrades(symbol="TSLA", new_stop=203.0)
        assert is_valid is True

    def test_validate_detects_downgrade_short(self):
        """Test validation detects downgrade for shorts."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["TSLA"]["stop_price"]  # 204

        # Moving stop up is NOT allowed for shorts (downgrade)
        is_valid = manager.validate_stop_never_downgrades(symbol="TSLA", new_stop=205.0)
        assert is_valid is False

    def test_validate_no_existing_stop(self):
        """Test validation passes if no existing stop (can't downgrade)."""
        manager = StopLossManager(account_balance=100000)

        is_valid = manager.validate_stop_never_downgrades(
            symbol="NEW_SYMBOL", new_stop=100.0
        )
        assert is_valid is True


class TestStopCoverage:
    """Test 100% stop loss coverage validation."""

    def test_100pct_coverage_all_positions_have_stops(self):
        """Test 100% coverage when all positions have stops."""
        manager = StopLossManager(account_balance=100000)

        # Create stops for all positions
        symbols = ["AAPL", "GOOGL", "TSLA"]
        for symbol in symbols:
            manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=100.0,
                position_size=5000.0,
                stop_type="fixed_pct",
            )

        # Validate coverage
        coverage = manager.validate_100pct_coverage(symbols)
        assert coverage["total_positions"] == 3
        assert coverage["positions_with_stops"] == 3
        assert coverage["coverage_pct"] == 1.0
        assert coverage["has_100pct_coverage"] is True
        assert len(coverage["missing_stops"]) == 0

    def test_coverage_detects_missing_stops(self):
        """Test coverage detection when some positions lack stops."""
        manager = StopLossManager(account_balance=100000)

        # Only create stops for 2 out of 3 positions
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=5000.0,
            stop_type="fixed_pct",
        )
        manager.calculate_stop_loss(
            symbol="GOOGL",
            entry_price=100.0,
            position_size=5000.0,
            stop_type="fixed_pct",
        )

        # Validate coverage (TSLA missing)
        symbols = ["AAPL", "GOOGL", "TSLA"]
        coverage = manager.validate_100pct_coverage(symbols)
        assert coverage["total_positions"] == 3
        assert coverage["positions_with_stops"] == 2
        assert coverage["coverage_pct"] == pytest.approx(0.667, abs=0.01)
        assert coverage["has_100pct_coverage"] is False
        assert "TSLA" in coverage["missing_stops"]

    def test_coverage_empty_portfolio(self):
        """Test coverage with no positions (edge case)."""
        manager = StopLossManager(account_balance=100000)

        coverage = manager.validate_100pct_coverage([])
        assert coverage["total_positions"] == 0
        assert coverage["coverage_pct"] == 1.0
        assert coverage["has_100pct_coverage"] is True


class TestRiskCalculation:
    """Test risk amount and percentage calculations."""

    def test_risk_calculation_long(self):
        """Test risk calculation for long position."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
            stop_pct=0.02,
        )

        # Entry: $100, Stop: $98, Position: $10,000
        # Shares: 100, Risk per share: $2, Total risk: $200
        assert result["risk_amount"] == pytest.approx(200.0, abs=1.0)
        assert result["risk_pct"] == pytest.approx(0.02, abs=0.001)
        assert result["account_risk_pct"] == pytest.approx(
            0.002, abs=0.0001
        )  # $200/$100k

    def test_risk_exceeds_max_account_risk(self):
        """Test that stops exceeding max account risk are rejected."""
        manager = StopLossManager(account_balance=100000, max_risk_per_trade=0.02)

        # This should fail: 10% stop on $30k position = $3k risk = 3% of account
        with pytest.raises(ValueError, match="exceeds max account risk"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=30000.0,
                stop_type="fixed_pct",
                stop_pct=0.10,  # 10% stop
            )

    def test_high_risk_warning(self):
        """Test warning when approaching max account risk."""
        manager = StopLossManager(account_balance=100000, max_risk_per_trade=0.02)

        # Risk close to max (1.8% of account)
        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=30000.0,
            stop_type="fixed_pct",
            stop_pct=0.06,  # 6% stop, $1,800 risk
        )

        assert result["account_risk_pct"] == pytest.approx(0.018, abs=0.001)
        assert len(result["warnings"]) > 0
        assert "High account risk" in result["warnings"][0]

    def test_shares_calculation(self):
        """Test number of shares is calculated correctly."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=15000.0,
            stop_type="fixed_pct",
        )

        assert result["shares"] == 100  # $15,000 / $150 = 100 shares


class TestEmergencyStops:
    """Test emergency stop update functionality."""

    def test_emergency_stop_update(self):
        """Test emergency stop update in market crash scenario."""
        manager = StopLossManager(account_balance=100000)

        # Initial stop
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["AAPL"]["stop_price"]  # 98

        # Emergency update (e.g., market crash)
        result = manager.emergency_stop_update(
            symbol="AAPL", emergency_stop_price=95.0, reason="Market circuit breaker"
        )

        assert result["stop_price"] == 95.0
        assert result["old_stop_price"] == old_stop
        assert "Market circuit breaker" in result["reason"]
        assert manager.active_stops["AAPL"]["stop_price"] == 95.0

    def test_emergency_stop_violates_never_downgrade(self):
        """Test emergency stop that violates never-downgrade rule."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )

        # Emergency stop BELOW old stop (violates never-downgrade)
        result = manager.emergency_stop_update(
            symbol="AAPL", emergency_stop_price=95.0, reason="Flash crash"
        )

        assert result["violated_never_downgrade"] is True
        assert "WARNING" in result["warning"]

    def test_emergency_stop_no_violation(self):
        """Test emergency stop that doesn't violate never-downgrade."""
        manager = StopLossManager(account_balance=100000)

        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )
        old_stop = manager.active_stops["AAPL"]["stop_price"]  # 98

        # Emergency stop ABOVE old stop (doesn't violate)
        result = manager.emergency_stop_update(
            symbol="AAPL", emergency_stop_price=99.0, reason="Tighten risk"
        )

        assert result["violated_never_downgrade"] is False
        assert result["warning"] == ""

    def test_emergency_stop_no_active_stop(self):
        """Test emergency stop fails if no active stop exists."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="No active stop"):
            manager.emergency_stop_update(
                symbol="AAPL", emergency_stop_price=95.0, reason="Emergency"
            )


class TestInputValidation:
    """Test input validation for stop calculations."""

    def test_invalid_symbol(self):
        """Test empty symbol is rejected."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            manager.calculate_stop_loss(
                symbol="",
                entry_price=100.0,
                position_size=10000.0,
                stop_type="fixed_pct",
            )

    def test_invalid_entry_price(self):
        """Test invalid entry prices are rejected."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="Entry price must be positive"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=0,
                position_size=10000.0,
                stop_type="fixed_pct",
            )

        with pytest.raises(ValueError, match="Entry price must be positive"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=-100.0,
                position_size=10000.0,
                stop_type="fixed_pct",
            )

    def test_invalid_position_size(self):
        """Test invalid position sizes are rejected."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="Position size must be positive"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=0,
                stop_type="fixed_pct",
            )

    def test_invalid_position_side(self):
        """Test invalid position sides are rejected."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="Invalid position_side"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=10000.0,
                position_side="sideways",
                stop_type="fixed_pct",
            )

    def test_invalid_stop_type(self):
        """Test invalid stop types are rejected."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="Invalid stop_type"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=10000.0,
                stop_type="magic_stop",
            )

    def test_stop_too_tight(self):
        """Test stops that are too tight are rejected."""
        manager = StopLossManager(
            account_balance=100000, min_stop_distance=0.005  # 0.5% min
        )

        with pytest.raises(ValueError, match="Stop too tight"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=10000.0,
                stop_type="fixed_pct",
                stop_pct=0.001,  # 0.1% stop (too tight)
            )

    def test_stop_too_wide(self):
        """Test stops that are too wide are rejected."""
        manager = StopLossManager(
            account_balance=100000, max_stop_distance=0.10  # 10% max
        )

        with pytest.raises(ValueError, match="Stop too wide"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=10000.0,
                stop_type="fixed_pct",
                stop_pct=0.15,  # 15% stop (too wide)
            )

    def test_long_stop_above_entry(self):
        """Test that stop above entry is rejected for longs."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="must be below entry"):
            manager.calculate_stop_loss(
                symbol="AAPL",
                entry_price=100.0,
                position_size=10000.0,
                position_side="long",
                custom_stop_price=105.0,  # Above entry
            )

    def test_short_stop_below_entry(self):
        """Test that stop below entry is rejected for shorts."""
        manager = StopLossManager(account_balance=100000)

        with pytest.raises(ValueError, match="must be above entry"):
            manager.calculate_stop_loss(
                symbol="TSLA",
                entry_price=200.0,
                position_size=10000.0,
                position_side="short",
                custom_stop_price=195.0,  # Below entry
            )


class TestHelperMethods:
    """Test helper methods and utilities."""

    def test_get_active_stop(self):
        """Test getting active stop for a symbol."""
        manager = StopLossManager(account_balance=100000)

        # No stop initially
        assert manager.get_active_stop("AAPL") is None

        # Create stop
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )

        # Get active stop
        stop = manager.get_active_stop("AAPL")
        assert stop is not None
        assert stop["stop_price"] == 98.0
        assert stop["entry_price"] == 100.0

    def test_remove_stop(self):
        """Test removing a stop when position is closed."""
        manager = StopLossManager(account_balance=100000)

        # Create stop
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )
        assert "AAPL" in manager.active_stops

        # Remove stop
        removed = manager.remove_stop("AAPL")
        assert removed is True
        assert "AAPL" not in manager.active_stops

        # Try removing again
        removed_again = manager.remove_stop("AAPL")
        assert removed_again is False

    def test_get_all_stops(self):
        """Test getting all active stops."""
        manager = StopLossManager(account_balance=100000)

        # Create multiple stops
        for symbol in ["AAPL", "GOOGL", "TSLA"]:
            manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=100.0,
                position_size=5000.0,
                stop_type="fixed_pct",
            )

        all_stops = manager.get_all_stops()
        assert len(all_stops) == 3
        assert "AAPL" in all_stops
        assert "GOOGL" in all_stops
        assert "TSLA" in all_stops

    def test_update_account_balance(self):
        """Test updating account balance."""
        manager = StopLossManager(account_balance=100000)

        manager.update_account_balance(150000)
        assert manager.account_balance == 150000

        with pytest.raises(ValueError, match="Account balance must be positive"):
            manager.update_account_balance(0)


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""

    def test_complete_trade_lifecycle(self):
        """Test complete trade lifecycle with stop management."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # 1. Enter position with trailing stop
        entry = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            stop_type="trailing",
        )
        assert entry["stop_price"] == 95.0

        # 2. Price moves up, update trailing stop
        update1 = manager.update_trailing_stop(symbol="AAPL", current_price=110.0)
        assert update1["stop_price"] == 104.5
        assert update1["stop_moved"] is True

        # 3. Price continues up
        update2 = manager.update_trailing_stop(symbol="AAPL", current_price=120.0)
        assert update2["stop_price"] == 114.0
        assert update2["profit_locked"] == 14.0  # 114 - 100

        # 4. Price pulls back (stop doesn't downgrade)
        update3 = manager.update_trailing_stop(symbol="AAPL", current_price=115.0)
        assert update3["stop_price"] == 114.0  # Unchanged
        assert update3["stop_moved"] is False

        # 5. Close position
        manager.remove_stop("AAPL")
        assert manager.get_active_stop("AAPL") is None

    def test_multiple_positions_coverage(self):
        """Test managing stops for multiple positions."""
        manager = StopLossManager(account_balance=100000)

        # Create positions with different stop types
        manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            position_size=10000.0,
            stop_type="fixed_pct",
        )

        manager.calculate_stop_loss(
            symbol="GOOGL",
            entry_price=100.0,
            position_size=8000.0,
            stop_type="atr_based",
            atr=2.5,
        )

        manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=12000.0,
            stop_type="trailing",
        )

        # Validate 100% coverage
        symbols = ["AAPL", "GOOGL", "TSLA"]
        coverage = manager.validate_100pct_coverage(symbols)
        assert coverage["has_100pct_coverage"] is True

        # Get all stops
        all_stops = manager.get_all_stops()
        assert len(all_stops) == 3

    def test_short_position_complete_cycle(self):
        """Test complete short position cycle."""
        manager = StopLossManager(account_balance=100000, default_trailing_pct=0.05)

        # 1. Enter short with trailing stop
        entry = manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            stop_type="trailing",
        )
        assert entry["stop_price"] == 210.0  # 200 * (1 + 0.05)

        # 2. Price moves down (favorable), update trailing stop
        update1 = manager.update_trailing_stop(symbol="TSLA", current_price=180.0)
        assert update1["stop_price"] == 189.0  # 180 * (1 + 0.05)
        assert update1["stop_moved"] is True

        # 3. Price continues down
        update2 = manager.update_trailing_stop(symbol="TSLA", current_price=160.0)
        assert update2["stop_price"] == 168.0  # 160 * (1 + 0.05)
        assert update2["profit_locked"] == 32.0  # 200 - 168

        # 4. Validate never-downgrade
        is_valid = manager.validate_stop_never_downgrades(symbol="TSLA", new_stop=170.0)
        assert is_valid is False  # Would move up (bad for short)


class TestCustomStops:
    """Test custom stop price functionality."""

    def test_custom_stop_long(self):
        """Test custom stop price for long position."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="AAPL",
            entry_price=100.0,
            position_size=10000.0,
            position_side="long",
            custom_stop_price=95.0,
        )

        assert result["stop_price"] == 95.0
        assert result["stop_type"] == "custom"
        assert "Custom stop" in result["rationale"]

    def test_custom_stop_short(self):
        """Test custom stop price for short position."""
        manager = StopLossManager(account_balance=100000)

        result = manager.calculate_stop_loss(
            symbol="TSLA",
            entry_price=200.0,
            position_size=10000.0,
            position_side="short",
            custom_stop_price=210.0,
        )

        assert result["stop_price"] == 210.0
        assert result["stop_type"] == "custom"
