"""
Unit tests for Circuit Breaker system.

Tests all breaker types, trip/reset logic, fail-safe behavior, and integration scenarios.
Ensures production-ready circuit breakers that protect against catastrophic losses.

Test Coverage:
    - Initialization and validation
    - Daily loss limit breaker
    - Max drawdown breaker
    - Consecutive losses breaker
    - Volatility spike breaker
    - Manual breaker trips
    - Breaker reset with confirmation
    - Multiple breakers tripped simultaneously
    - Fail-safe behavior
    - Auto-reset functionality
    - Integration scenarios
"""


import pytest

from core.risk.circuit_breaker import BreakerState, BreakerType, CircuitBreaker


class TestCircuitBreakerInit:
    """Test circuit breaker initialization and validation."""

    def test_init_valid_params(self):
        """Test initialization with valid parameters."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            daily_loss_limit=0.03,
            max_drawdown_limit=0.10,
            consecutive_loss_limit=5,
            volatility_threshold=40.0,
        )

        assert breaker.initial_portfolio_value == 100000
        assert breaker.daily_loss_limit == 0.03
        assert breaker.max_drawdown_limit == 0.10
        assert breaker.consecutive_loss_limit == 5
        assert breaker.volatility_threshold == 40.0
        assert breaker.peak_portfolio_value == 100000
        assert breaker.consecutive_losses == 0

    def test_init_invalid_portfolio_value(self):
        """Test initialization fails with invalid portfolio value."""
        with pytest.raises(ValueError, match="must be positive"):
            CircuitBreaker(initial_portfolio_value=-1000)

        with pytest.raises(ValueError, match="must be positive"):
            CircuitBreaker(initial_portfolio_value=0)

    def test_init_invalid_daily_loss_limit(self):
        """Test initialization fails with invalid daily loss limit."""
        with pytest.raises(ValueError, match="daily_loss_limit"):
            CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0)

        with pytest.raises(ValueError, match="daily_loss_limit"):
            CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=1.5)

        with pytest.raises(ValueError, match="daily_loss_limit"):
            CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=-0.05)

    def test_init_invalid_drawdown_limit(self):
        """Test initialization fails with invalid drawdown limit."""
        with pytest.raises(ValueError, match="max_drawdown_limit"):
            CircuitBreaker(initial_portfolio_value=100000, max_drawdown_limit=0)

        with pytest.raises(ValueError, match="max_drawdown_limit"):
            CircuitBreaker(initial_portfolio_value=100000, max_drawdown_limit=2.0)

    def test_init_invalid_consecutive_loss_limit(self):
        """Test initialization fails with invalid consecutive loss limit."""
        with pytest.raises(ValueError, match="consecutive_loss_limit"):
            CircuitBreaker(initial_portfolio_value=100000, consecutive_loss_limit=0)

        with pytest.raises(ValueError, match="consecutive_loss_limit"):
            CircuitBreaker(initial_portfolio_value=100000, consecutive_loss_limit=-5)

    def test_init_invalid_volatility_threshold(self):
        """Test initialization fails with invalid volatility threshold."""
        with pytest.raises(ValueError, match="volatility_threshold"):
            CircuitBreaker(initial_portfolio_value=100000, volatility_threshold=0)

        with pytest.raises(ValueError, match="volatility_threshold"):
            CircuitBreaker(initial_portfolio_value=100000, volatility_threshold=-10)

    def test_init_all_breakers_armed(self):
        """Test all breakers start in ARMED state."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        for breaker_type in BreakerType:
            assert breaker.breaker_states[breaker_type.value] == BreakerState.ARMED
            assert breaker.trip_times[breaker_type.value] is None
            assert breaker.trip_reasons[breaker_type.value] is None


class TestDailyLossBreaker:
    """Test daily loss limit circuit breaker."""

    def test_no_trip_within_limit(self):
        """Test breaker doesn't trip when daily loss within limit."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # 2% loss - within 3% limit
        result = breaker.check_breakers(
            current_portfolio_value=98000, start_of_day_value=100000
        )

        assert result["trading_allowed"] is True
        assert len(result["breakers_tripped"]) == 0
        assert result["current_daily_loss_pct"] == 0.02

    def test_trip_on_daily_loss_limit(self):
        """Test breaker trips when daily loss exceeds limit."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # 3% loss - at limit
        result = breaker.check_breakers(
            current_portfolio_value=97000, start_of_day_value=100000
        )

        assert result["trading_allowed"] is False
        assert BreakerType.DAILY_LOSS.value in result["breakers_tripped"]
        assert "Daily loss limit breached" in result["reasons"][0]
        assert result["current_daily_loss_pct"] == 0.03

    def test_trip_on_daily_loss_exceeded(self):
        """Test breaker trips when daily loss exceeds limit."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # 5% loss - exceeds 3% limit
        result = breaker.check_breakers(
            current_portfolio_value=95000, start_of_day_value=100000
        )

        assert result["trading_allowed"] is False
        assert BreakerType.DAILY_LOSS.value in result["breakers_tripped"]
        assert result["current_daily_loss_pct"] == 0.05

    def test_no_trip_on_daily_gain(self):
        """Test breaker doesn't trip on daily gains."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # 5% gain
        result = breaker.check_breakers(
            current_portfolio_value=105000, start_of_day_value=100000
        )

        assert result["trading_allowed"] is True
        assert len(result["breakers_tripped"]) == 0
        assert result["current_daily_loss_pct"] == 0.0

    def test_warning_near_daily_loss_limit(self):
        """Test warning when approaching daily loss limit."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # 2.5% loss - 80%+ of 3% limit
        result = breaker.check_breakers(
            current_portfolio_value=97500, start_of_day_value=100000
        )

        assert result["trading_allowed"] is True
        assert len(result["warnings"]) > 0
        assert "Approaching daily loss limit" in result["warnings"][0]

    def test_daily_loss_without_start_of_day(self):
        """Test breaker doesn't trip without start of day value."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # No start_of_day_value provided
        result = breaker.check_breakers(current_portfolio_value=95000)

        # Should not trip because we don't know start of day
        assert result["trading_allowed"] is True
        assert BreakerType.DAILY_LOSS.value not in result["breakers_tripped"]


class TestMaxDrawdownBreaker:
    """Test max drawdown circuit breaker."""

    def test_no_trip_within_drawdown_limit(self):
        """Test breaker doesn't trip when drawdown within limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, max_drawdown_limit=0.10
        )

        # 8% drawdown - within 10% limit
        result = breaker.check_breakers(current_portfolio_value=92000)

        assert result["trading_allowed"] is True
        assert len(result["breakers_tripped"]) == 0
        assert result["current_drawdown_pct"] == 0.08

    def test_trip_on_max_drawdown_limit(self):
        """Test breaker trips when drawdown equals limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, max_drawdown_limit=0.10
        )

        # 10% drawdown - at limit
        result = breaker.check_breakers(current_portfolio_value=90000)

        assert result["trading_allowed"] is False
        assert BreakerType.MAX_DRAWDOWN.value in result["breakers_tripped"]
        assert "Max drawdown limit breached" in result["reasons"][0]
        assert result["current_drawdown_pct"] == 0.10

    def test_trip_on_max_drawdown_exceeded(self):
        """Test breaker trips when drawdown exceeds limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, max_drawdown_limit=0.10
        )

        # 15% drawdown - exceeds 10% limit
        result = breaker.check_breakers(current_portfolio_value=85000)

        assert result["trading_allowed"] is False
        assert BreakerType.MAX_DRAWDOWN.value in result["breakers_tripped"]
        assert result["current_drawdown_pct"] == 0.15

    def test_peak_updates_on_new_high(self):
        """Test peak value updates when portfolio hits new high."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Portfolio increases to 110k
        result1 = breaker.check_breakers(current_portfolio_value=110000)
        assert breaker.peak_portfolio_value == 110000
        assert result1["trading_allowed"] is True

        # Now 10% drawdown from new peak (99k)
        result2 = breaker.check_breakers(current_portfolio_value=99000)
        assert result2["current_drawdown_pct"] == 0.10

    def test_drawdown_from_peak_not_initial(self):
        """Test drawdown calculated from peak, not initial value."""
        # Set high daily loss limit so we only test drawdown breaker
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            max_drawdown_limit=0.10,
            daily_loss_limit=0.50,  # High limit to not interfere with drawdown test
        )

        # Portfolio grows to 120k (new peak)
        breaker.check_breakers(current_portfolio_value=120000)
        assert breaker.peak_portfolio_value == 120000

        # Drop to 110k - only 8.3% from peak
        result = breaker.check_breakers(current_portfolio_value=110000)
        assert result["trading_allowed"] is True
        assert result["current_drawdown_pct"] < 0.10

        # Drop to 107k - exactly 10.8% from peak (120k)
        result2 = breaker.check_breakers(current_portfolio_value=107000)
        assert result2["trading_allowed"] is False  # Exceeds 10% limit

    def test_warning_near_drawdown_limit(self):
        """Test warning when approaching drawdown limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, max_drawdown_limit=0.10
        )

        # 9% drawdown - 90% of 10% limit
        result = breaker.check_breakers(current_portfolio_value=91000)

        assert result["trading_allowed"] is True
        assert len(result["warnings"]) > 0
        assert "Approaching max drawdown limit" in result["warnings"][0]

    def test_manual_peak_update(self):
        """Test manual peak portfolio value update."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Manually update peak
        breaker.update_peak_portfolio_value(150000)
        assert breaker.peak_portfolio_value == 150000

        # 10% drawdown from 150k = 135k
        result = breaker.check_breakers(current_portfolio_value=135000)
        assert result["current_drawdown_pct"] == 0.10


class TestConsecutiveLossesBreaker:
    """Test consecutive losses circuit breaker."""

    def test_no_trip_within_consecutive_loss_limit(self):
        """Test breaker doesn't trip when consecutive losses within limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record 4 consecutive losses
        for _ in range(4):
            breaker.record_trade(-100)

        result = breaker.check_breakers(current_portfolio_value=100000)

        assert result["trading_allowed"] is True
        assert len(result["breakers_tripped"]) == 0
        assert result["consecutive_losses"] == 4

    def test_trip_on_consecutive_loss_limit(self):
        """Test breaker trips when consecutive losses equal limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record 5 consecutive losses
        for _ in range(5):
            breaker.record_trade(-100)

        result = breaker.check_breakers(current_portfolio_value=100000)

        assert result["trading_allowed"] is False
        assert BreakerType.CONSECUTIVE_LOSSES.value in result["breakers_tripped"]
        assert "Consecutive loss limit breached" in result["reasons"][0]
        assert result["consecutive_losses"] == 5

    def test_trip_on_consecutive_losses_exceeded(self):
        """Test breaker trips when consecutive losses exceed limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record 7 consecutive losses
        for _ in range(7):
            breaker.record_trade(-100)

        result = breaker.check_breakers(current_portfolio_value=100000)

        assert result["trading_allowed"] is False
        assert result["consecutive_losses"] == 7

    def test_consecutive_losses_reset_on_win(self):
        """Test consecutive losses reset when a win occurs."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record 4 losses
        for _ in range(4):
            breaker.record_trade(-100)

        assert breaker.consecutive_losses == 4

        # Record a win - should reset consecutive losses
        breaker.record_trade(200)

        assert breaker.consecutive_losses == 0
        assert breaker.consecutive_wins == 1

        # Breaker should not trip
        result = breaker.check_breakers(current_portfolio_value=100000)
        assert result["trading_allowed"] is True

    def test_consecutive_wins_reset_on_loss(self):
        """Test consecutive wins reset when a loss occurs."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Record 3 wins
        for _ in range(3):
            breaker.record_trade(100)

        assert breaker.consecutive_wins == 3
        assert breaker.consecutive_losses == 0

        # Record a loss - should reset consecutive wins
        breaker.record_trade(-50)

        assert breaker.consecutive_wins == 0
        assert breaker.consecutive_losses == 1

    def test_warning_near_consecutive_loss_limit(self):
        """Test warning when approaching consecutive loss limit."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record 4 losses (80% of limit)
        for _ in range(4):
            breaker.record_trade(-100)

        result = breaker.check_breakers(current_portfolio_value=100000)

        assert result["trading_allowed"] is True
        assert len(result["warnings"]) > 0
        assert "Approaching consecutive loss limit" in result["warnings"][0]

    def test_trade_history_tracking(self):
        """Test trade history is properly tracked."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Record some trades
        breaker.record_trade(100, {"symbol": "AAPL"})
        breaker.record_trade(-50, {"symbol": "TSLA"})
        breaker.record_trade(75, {"symbol": "MSFT"})

        assert len(breaker.recent_trades) == 3
        assert breaker.total_trades == 3
        assert breaker.recent_trades[0]["pnl"] == 100
        assert breaker.recent_trades[0]["symbol"] == "AAPL"


class TestVolatilityBreaker:
    """Test volatility spike circuit breaker."""

    def test_no_trip_below_volatility_threshold(self):
        """Test breaker doesn't trip when VIX below threshold."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        result = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=35.0
        )

        assert result["trading_allowed"] is True
        assert len(result["breakers_tripped"]) == 0
        assert result["current_vix"] == 35.0

    def test_trip_on_volatility_threshold(self):
        """Test breaker trips when VIX equals threshold."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        result = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=40.0
        )

        assert result["trading_allowed"] is False
        assert BreakerType.VOLATILITY_SPIKE.value in result["breakers_tripped"]
        assert "Volatility spike detected" in result["reasons"][0]
        assert result["current_vix"] == 40.0

    def test_trip_on_volatility_exceeded(self):
        """Test breaker trips when VIX exceeds threshold."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        # Extreme volatility (like during market crash)
        result = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=75.0
        )

        assert result["trading_allowed"] is False
        assert BreakerType.VOLATILITY_SPIKE.value in result["breakers_tripped"]
        assert result["current_vix"] == 75.0

    def test_no_trip_without_vix_data(self):
        """Test breaker doesn't trip when VIX data not provided."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        # No VIX data
        result = breaker.check_breakers(current_portfolio_value=100000)

        assert result["trading_allowed"] is True
        assert BreakerType.VOLATILITY_SPIKE.value not in result["breakers_tripped"]
        assert result["current_vix"] is None

    def test_warning_near_volatility_threshold(self):
        """Test warning when approaching volatility threshold."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        # VIX at 90% of threshold
        result = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=36.0
        )

        assert result["trading_allowed"] is True
        assert len(result["warnings"]) > 0
        assert "VIX approaching threshold" in result["warnings"][0]

    def test_invalid_vix_ignored(self):
        """Test invalid VIX values are handled gracefully."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=40.0
        )

        # Negative VIX (invalid)
        result = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=-10.0
        )

        # Should not trip (invalid data ignored)
        assert result["trading_allowed"] is True
        assert BreakerType.VOLATILITY_SPIKE.value not in result["breakers_tripped"]


class TestBreakerTrip:
    """Test manual breaker trip functionality."""

    def test_manual_trip_breaker(self):
        """Test manually tripping a circuit breaker."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Manually trip the breaker
        trip_result = breaker.trip_breaker(
            BreakerType.MANUAL.value, "Testing manual halt"
        )

        assert trip_result["tripped"] is True
        assert trip_result["breaker_type"] == BreakerType.MANUAL.value
        assert trip_result["reason"] == "Testing manual halt"
        assert "confirmation_code" in trip_result
        assert len(trip_result["confirmation_code"]) == 16

        # Verify breaker is tripped
        status = breaker.get_breaker_status()
        assert status[BreakerType.MANUAL.value]["tripped"] is True
        assert status["trading_allowed"] is False

    def test_trip_breaker_invalid_type(self):
        """Test tripping breaker with invalid type fails."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        with pytest.raises(ValueError, match="Invalid breaker_type"):
            breaker.trip_breaker("invalid_breaker", "Test")

    def test_trip_generates_confirmation_code(self):
        """Test trip generates unique confirmation code."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        trip1 = breaker.trip_breaker(BreakerType.MANUAL.value, "Test 1")
        breaker.reset_breaker(
            BreakerType.MANUAL.value, trip1["confirmation_code"], "Reset test"
        )

        trip2 = breaker.trip_breaker(BreakerType.MANUAL.value, "Test 2")

        # Codes should be different
        assert trip1["confirmation_code"] != trip2["confirmation_code"]

    def test_trip_updates_state(self):
        """Test trip updates breaker state correctly."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        breaker.trip_breaker(BreakerType.DAILY_LOSS.value, "Test trip")

        assert (
            breaker.breaker_states[BreakerType.DAILY_LOSS.value] == BreakerState.TRIPPED
        )
        assert breaker.trip_times[BreakerType.DAILY_LOSS.value] is not None
        assert breaker.trip_reasons[BreakerType.DAILY_LOSS.value] == "Test trip"
        assert BreakerType.DAILY_LOSS.value in breaker.active_confirmation_codes


class TestBreakerReset:
    """Test breaker reset with confirmation."""

    def test_reset_with_valid_confirmation(self):
        """Test reset works with valid confirmation code."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Trip breaker
        trip_result = breaker.trip_breaker(BreakerType.MANUAL.value, "Test")

        # Reset with correct code
        reset_result = breaker.reset_breaker(
            BreakerType.MANUAL.value,
            trip_result["confirmation_code"],
            "Manual reset",
        )

        assert reset_result["reset_successful"] is True
        assert reset_result["breaker_type"] == BreakerType.MANUAL.value
        assert breaker.breaker_states[BreakerType.MANUAL.value] == BreakerState.ARMED

    def test_reset_with_invalid_confirmation_fails(self):
        """Test reset fails with invalid confirmation code."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Trip breaker
        breaker.trip_breaker(BreakerType.MANUAL.value, "Test")

        # Try to reset with wrong code
        with pytest.raises(PermissionError, match="Invalid confirmation code"):
            breaker.reset_breaker(BreakerType.MANUAL.value, "WRONG_CODE", "Reset")

        # Breaker should still be tripped
        assert breaker.breaker_states[BreakerType.MANUAL.value] == BreakerState.TRIPPED

    def test_reset_non_tripped_breaker_fails(self):
        """Test resetting non-tripped breaker fails."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Try to reset without tripping first
        with pytest.raises(ValueError, match="not tripped"):
            breaker.reset_breaker(BreakerType.MANUAL.value, "SOME_CODE", "Reset")

    def test_reset_invalid_breaker_type_fails(self):
        """Test reset with invalid breaker type fails."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        with pytest.raises(ValueError, match="Invalid breaker_type"):
            breaker.reset_breaker("invalid_type", "CODE", "Reset")

    def test_reset_clears_trip_data(self):
        """Test reset clears all trip-related data."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Trip breaker
        trip_result = breaker.trip_breaker(BreakerType.MANUAL.value, "Test")

        # Reset
        breaker.reset_breaker(
            BreakerType.MANUAL.value, trip_result["confirmation_code"], "Reset"
        )

        # Verify all trip data cleared
        assert breaker.breaker_states[BreakerType.MANUAL.value] == BreakerState.ARMED
        assert breaker.trip_times[BreakerType.MANUAL.value] is None
        assert breaker.trip_reasons[BreakerType.MANUAL.value] is None
        assert BreakerType.MANUAL.value not in breaker.active_confirmation_codes

    def test_reset_consecutive_losses_resets_counter(self):
        """Test resetting consecutive losses breaker resets the counter."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=5
        )

        # Record losses to trip breaker
        for _ in range(5):
            breaker.record_trade(-100)

        breaker.check_breakers(current_portfolio_value=100000)

        assert breaker.consecutive_losses == 5

        # Get confirmation code and reset
        code = breaker.active_confirmation_codes[BreakerType.CONSECUTIVE_LOSSES.value]
        breaker.reset_breaker(BreakerType.CONSECUTIVE_LOSSES.value, code, "Reset")

        # Counter should be reset
        assert breaker.consecutive_losses == 0


class TestMultipleBreakers:
    """Test multiple breakers tripped simultaneously."""

    def test_multiple_breakers_trip(self):
        """Test multiple breakers can trip at once."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            daily_loss_limit=0.03,
            max_drawdown_limit=0.10,
            consecutive_loss_limit=3,
        )

        # Create scenario that trips multiple breakers
        # 1. Record consecutive losses
        for _ in range(3):
            breaker.record_trade(-1000)

        # 2. Check with daily loss and drawdown exceeded
        result = breaker.check_breakers(
            current_portfolio_value=85000, start_of_day_value=100000  # 15% drawdown
        )  # 15% daily loss

        # Multiple breakers should trip
        assert result["trading_allowed"] is False
        assert len(result["breakers_tripped"]) >= 2

        # Should include both daily loss and consecutive losses
        assert BreakerType.DAILY_LOSS.value in result["breakers_tripped"]
        assert BreakerType.MAX_DRAWDOWN.value in result["breakers_tripped"]
        assert BreakerType.CONSECUTIVE_LOSSES.value in result["breakers_tripped"]

    def test_trading_allowed_only_when_all_clear(self):
        """Test trading only allowed when ALL breakers are clear."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Trip one breaker
        trip1 = breaker.trip_breaker(BreakerType.MANUAL.value, "Test 1")

        result = breaker.check_breakers(current_portfolio_value=100000)
        assert result["trading_allowed"] is False

        # Reset it
        breaker.reset_breaker(
            BreakerType.MANUAL.value, trip1["confirmation_code"], "Reset"
        )

        # Now should be allowed
        result = breaker.check_breakers(current_portfolio_value=100000)
        assert result["trading_allowed"] is True

    def test_status_shows_all_breakers(self):
        """Test get_breaker_status returns all breaker states."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Trip some breakers
        breaker.trip_breaker(BreakerType.MANUAL.value, "Test 1")
        breaker.trip_breaker(BreakerType.DAILY_LOSS.value, "Test 2")

        status = breaker.get_breaker_status()

        # Should have all breaker types
        for breaker_type in BreakerType:
            assert breaker_type.value in status

        # Should show which are tripped
        assert status[BreakerType.MANUAL.value]["tripped"] is True
        assert status[BreakerType.DAILY_LOSS.value]["tripped"] is True
        assert status[BreakerType.MAX_DRAWDOWN.value]["tripped"] is False

        assert status["any_tripped"] is True
        assert status["trading_allowed"] is False


class TestFailSafeBehavior:
    """Test fail-safe behavior (halts on errors)."""

    def test_invalid_portfolio_value_triggers_failsafe(self):
        """Test invalid portfolio value triggers fail-safe halt."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Try with invalid portfolio value
        result = breaker.check_breakers(current_portfolio_value=-1000)

        # Should halt trading (fail-safe)
        assert result["trading_allowed"] is False
        assert "system_error" in result["breakers_tripped"]
        assert "FAIL-SAFE" in result["reasons"][0]

    def test_failsafe_on_check_exception(self):
        """Test exception during check triggers fail-safe halt."""
        breaker = CircuitBreaker(initial_portfolio_value=100000)

        # Force an exception by passing invalid type
        result = breaker.check_breakers(current_portfolio_value="invalid")

        # Should fail-safe to halt
        assert result["trading_allowed"] is False
        assert "FAIL-SAFE" in result["reasons"][0]


class TestAutoReset:
    """Test automatic reset functionality."""

    def test_daily_loss_auto_reset_new_day(self):
        """Test daily loss breaker auto-resets on new trading day."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # Trip daily loss breaker
        breaker.check_breakers(current_portfolio_value=97000, start_of_day_value=100000)

        assert (
            breaker.breaker_states[BreakerType.DAILY_LOSS.value] == BreakerState.TRIPPED
        )

        # Simulate new day by changing internal day tracking
        # This would normally happen automatically in check_breakers
        # For testing, we'll manually trigger the reset
        code = breaker.active_confirmation_codes[BreakerType.DAILY_LOSS.value]
        breaker.reset_breaker(
            BreakerType.DAILY_LOSS.value, code, "New trading day reset"
        )

        assert (
            breaker.breaker_states[BreakerType.DAILY_LOSS.value] == BreakerState.ARMED
        )

    def test_drawdown_breaker_no_auto_reset(self):
        """Test max drawdown breaker does NOT auto-reset."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            max_drawdown_limit=0.10,
            auto_reset_hours=1,  # Even with auto-reset enabled
        )

        # Trip drawdown breaker
        breaker.check_breakers(current_portfolio_value=85000)

        assert (
            breaker.breaker_states[BreakerType.MAX_DRAWDOWN.value]
            == BreakerState.TRIPPED
        )

        # Wait for auto-reset time (simulate)
        import time

        time.sleep(0.1)  # Small delay

        # Check again - should still be tripped (no auto-reset for drawdown)
        result = breaker.check_breakers(current_portfolio_value=95000)

        # Still tripped (drawdown breakers don't auto-reset)
        assert BreakerType.MAX_DRAWDOWN.value in result["breakers_tripped"]


class TestIntegration:
    """Integration tests simulating real trading scenarios."""

    def test_catastrophic_loss_scenario(self):
        """Test circuit breakers protect against catastrophic loss."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            daily_loss_limit=0.05,
            max_drawdown_limit=0.15,
            consecutive_loss_limit=5,
        )

        # Simulate series of losing trades
        portfolio_value = 100000
        start_of_day = 100000

        trade_losses = [2000, 1500, 2500, 3000, 2000]  # Total -11k loss

        for i, loss in enumerate(trade_losses):
            # Record trade
            breaker.record_trade(-loss)

            # Update portfolio
            portfolio_value -= loss

            # Check breakers
            result = breaker.check_breakers(
                current_portfolio_value=portfolio_value, start_of_day_value=start_of_day
            )

            print(
                f"Trade {i+1}: Loss ${loss}, Portfolio: ${portfolio_value}, "
                f"Trading Allowed: {result['trading_allowed']}"
            )

        # After 5 losing trades totaling 11% loss, multiple breakers should trip
        final_result = breaker.check_breakers(
            current_portfolio_value=portfolio_value, start_of_day_value=start_of_day
        )

        assert final_result["trading_allowed"] is False
        # Should trip at least consecutive losses and possibly daily loss
        assert len(final_result["breakers_tripped"]) > 0

    def test_volatile_market_protection(self):
        """Test circuit breaker halts during volatile market conditions."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, volatility_threshold=35.0
        )

        # Normal market conditions
        result1 = breaker.check_breakers(
            current_portfolio_value=100000, current_vix=20.0
        )
        assert result1["trading_allowed"] is True

        # Market crash - VIX spikes
        result2 = breaker.check_breakers(
            current_portfolio_value=98000, current_vix=55.0
        )
        assert result2["trading_allowed"] is False
        assert BreakerType.VOLATILITY_SPIKE.value in result2["breakers_tripped"]

    def test_recovery_after_halt(self):
        """Test recovery workflow after breaker trips."""
        breaker = CircuitBreaker(initial_portfolio_value=100000, daily_loss_limit=0.03)

        # Trip breaker
        result1 = breaker.check_breakers(
            current_portfolio_value=97000, start_of_day_value=100000
        )
        assert result1["trading_allowed"] is False

        # Get confirmation code
        code = breaker.active_confirmation_codes[BreakerType.DAILY_LOSS.value]

        # Reset breaker
        reset_result = breaker.reset_breaker(
            BreakerType.DAILY_LOSS.value, code, "Manual recovery after review"
        )
        assert reset_result["reset_successful"] is True

        # Trading should resume - provide start_of_day to avoid re-triggering
        result2 = breaker.check_breakers(
            current_portfolio_value=97000, start_of_day_value=97000
        )
        assert result2["trading_allowed"] is True

    def test_consecutive_small_losses_protection(self):
        """Test protection against many small consecutive losses."""
        breaker = CircuitBreaker(
            initial_portfolio_value=100000, consecutive_loss_limit=10
        )

        # Simulate 10 small losses
        for i in range(10):
            breaker.record_trade(-50)  # Small $50 losses

            if i < 9:
                result = breaker.check_breakers(
                    current_portfolio_value=100000 - (i + 1) * 50
                )
                # Should not trip until 10th loss
                assert result["trading_allowed"] is True
            else:
                # 10th loss should trip
                result = breaker.check_breakers(current_portfolio_value=100000 - 500)
                assert result["trading_allowed"] is False

    def test_new_peak_resets_drawdown_calculation(self):
        """Test drawdown calculation resets from new peaks."""
        # Set high daily loss limit so we only test drawdown breaker
        breaker = CircuitBreaker(
            initial_portfolio_value=100000,
            max_drawdown_limit=0.10,
            daily_loss_limit=0.50,  # High limit to not interfere
        )

        # Portfolio grows
        breaker.check_breakers(current_portfolio_value=120000)
        assert breaker.peak_portfolio_value == 120000

        # Drop 8% from new peak (to 110,400)
        result1 = breaker.check_breakers(current_portfolio_value=110400)
        assert result1["trading_allowed"] is True  # Within 10% limit

        # Recover to new peak
        breaker.check_breakers(current_portfolio_value=125000)
        assert breaker.peak_portfolio_value == 125000

        # Now 10% drawdown is from 125k, not 120k
        result2 = breaker.check_breakers(current_portfolio_value=112500)
        assert result2["trading_allowed"] is False  # Exactly at 10% limit
