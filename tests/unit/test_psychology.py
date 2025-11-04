"""
Comprehensive tests for Psychology Module components.

Tests cover:
    - DrawdownMonitor: Drawdown tracking, position size reduction, circuit breaker
    - EmotionalFirewall: Pattern detection, trade blocking, cooldown periods
    - TradingTimeOut: Consecutive losses, exponential backoff, override mechanism
    - RecoveryProtocol: Phased recovery, advancement requirements, demotion logic

Test Coverage Target: 80%+
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from core.psychology import (
    DrawdownMonitor,
    EmotionalFirewall,
    RecoveryProtocol,
    TradingTimeOut,
)
from core.psychology.emotional_firewall import EmotionalPattern
from core.psychology.recovery_protocol import RecoveryPhase
from core.psychology.trading_timeout import TimeOutReason

# ============================================================================
# DrawdownMonitor Tests
# ============================================================================


class TestDrawdownMonitor:
    """Test suite for DrawdownMonitor class."""

    def test_initialization(self):
        """Test basic initialization."""
        monitor = DrawdownMonitor(initial_capital=100000)

        assert monitor.initial_capital == 100000
        assert monitor.peak_value == 100000
        assert monitor.current_drawdown == 0.0
        assert monitor.position_size_multiplier == 1.0
        assert not monitor.circuit_breaker_active

    def test_initialization_invalid_capital(self):
        """Test initialization with invalid capital."""
        with pytest.raises(ValueError):
            DrawdownMonitor(initial_capital=-1000)

        with pytest.raises(ValueError):
            DrawdownMonitor(initial_capital=0)

    def test_no_drawdown(self):
        """Test status when portfolio is at peak."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=100000)

        assert status["current_drawdown"] == 0.0
        assert status["position_size_multiplier"] == 1.0
        assert not status["circuit_breaker"]

    def test_new_peak(self):
        """Test updating to new peak value."""
        monitor = DrawdownMonitor(initial_capital=100000)

        # Update to new high
        status = monitor.update(current_value=110000)

        assert status["peak_value"] == 110000
        assert status["current_drawdown"] == 0.0
        assert status["position_size_multiplier"] == 1.0

    def test_small_drawdown(self):
        """Test small drawdown (< 5%)."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=96000)  # 4% drawdown

        assert abs(status["current_drawdown"] - 0.04) < 0.001
        assert status["position_size_multiplier"] == 1.0  # Still full size

    def test_moderate_drawdown_5_percent(self):
        """Test 5-10% drawdown triggers 75% sizing."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=92000)  # 8% drawdown

        assert abs(status["current_drawdown"] - 0.08) < 0.001
        assert status["position_size_multiplier"] == 0.75

    def test_significant_drawdown_10_percent(self):
        """Test 10-15% drawdown triggers 50% sizing."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=88000)  # 12% drawdown

        assert abs(status["current_drawdown"] - 0.12) < 0.001
        assert status["position_size_multiplier"] == 0.50

    def test_severe_drawdown_15_percent(self):
        """Test 15-20% drawdown triggers 25% sizing."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=83000)  # 17% drawdown

        assert abs(status["current_drawdown"] - 0.17) < 0.001
        assert status["position_size_multiplier"] == 0.25

    def test_circuit_breaker_activation(self):
        """Test circuit breaker at 20% drawdown."""
        monitor = DrawdownMonitor(initial_capital=100000)
        status = monitor.update(current_value=79000)  # 21% drawdown

        assert status["circuit_breaker"]
        assert status["position_size_multiplier"] == 0.0
        assert not monitor.is_trading_allowed()

    def test_circuit_breaker_disabled(self):
        """Test that circuit breaker can be disabled."""
        monitor = DrawdownMonitor(initial_capital=100000, enable_circuit_breaker=False)
        status = monitor.update(current_value=75000)  # 25% drawdown

        assert not status["circuit_breaker"]
        assert status["position_size_multiplier"] == 0.25  # Still uses 15-20% level

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        monitor = DrawdownMonitor(initial_capital=100000)
        monitor.update(current_value=79000)  # Trip breaker

        # Invalid confirmation code
        assert not monitor.reset_circuit_breaker("WRONG_CODE")
        assert monitor.circuit_breaker_active

        # Valid confirmation code
        assert monitor.reset_circuit_breaker("RESET_TRADING")
        assert not monitor.circuit_breaker_active

    def test_recovery_tracking(self):
        """Test entry into and exit from recovery mode."""
        monitor = DrawdownMonitor(initial_capital=100000)

        # Create drawdown
        monitor.update(current_value=92000)  # 8% drawdown
        assert monitor.in_recovery

        # Recover to new peak
        monitor.update(current_value=101000)
        assert not monitor.in_recovery

    def test_max_drawdown_tracking(self):
        """Test tracking of maximum drawdown."""
        monitor = DrawdownMonitor(initial_capital=100000)

        monitor.update(current_value=95000)  # 5% drawdown
        assert monitor.max_drawdown == 0.05

        monitor.update(current_value=88000)  # 12% drawdown
        assert monitor.max_drawdown == 0.12

        monitor.update(current_value=90000)  # 10% drawdown (recovering)
        assert monitor.max_drawdown == 0.12  # Max unchanged

    def test_threshold_breach_tracking(self):
        """Test tracking of threshold breaches."""
        monitor = DrawdownMonitor(initial_capital=100000, enable_logging=False)

        # Breach 5% threshold
        monitor.update(current_value=92000)
        assert monitor.threshold_breaches[0.10] == 1

        # Breach 10% threshold
        monitor.update(current_value=88000)
        assert monitor.threshold_breaches[0.10] == 1

        # Recover and breach again
        monitor.update(current_value=100000)  # Back to peak
        monitor.update(current_value=92000)  # Breach again
        assert monitor.threshold_breaches[0.10] >= 1

    def test_get_max_position_size(self):
        """Test position size calculation with drawdown adjustment."""
        monitor = DrawdownMonitor(initial_capital=100000)

        # No drawdown
        assert monitor.get_max_position_size(10000) == 10000

        # 8% drawdown (75% sizing)
        monitor.update(current_value=92000)
        assert monitor.get_max_position_size(10000) == 7500

        # 12% drawdown (50% sizing)
        monitor.update(current_value=88000)
        assert monitor.get_max_position_size(10000) == 5000

    def test_statistics(self):
        """Test comprehensive statistics."""
        monitor = DrawdownMonitor(initial_capital=100000)

        monitor.update(current_value=92000)
        monitor.update(current_value=88000)
        monitor.update(current_value=85000)

        stats = monitor.get_statistics()

        assert stats["initial_capital"] == 100000
        assert stats["current_value"] == 85000
        assert stats["max_drawdown"] == 0.15
        assert stats["total_updates"] == 3


# ============================================================================
# EmotionalFirewall Tests
# ============================================================================


class TestEmotionalFirewall:
    """Test suite for EmotionalFirewall class."""

    def test_initialization(self):
        """Test basic initialization."""
        firewall = EmotionalFirewall()

        assert firewall.enable_all_checks
        assert firewall.current_streak_count == 0
        assert firewall.total_trades == 0
        assert firewall.blocked_trades == 0

    def test_no_blocking_when_disabled(self):
        """Test that no blocking occurs when checks are disabled."""
        firewall = EmotionalFirewall(enable_all_checks=False)

        result = firewall.should_block_trade("AAPL")
        assert not result["blocked"]

    def test_record_trade_win(self):
        """Test recording a winning trade."""
        firewall = EmotionalFirewall()

        firewall.record_trade("AAPL", profit_loss=500)

        assert firewall.total_trades == 1
        assert firewall.current_streak_type == "win"
        assert firewall.current_streak_count == 1

    def test_record_trade_loss(self):
        """Test recording a losing trade."""
        firewall = EmotionalFirewall()

        firewall.record_trade("AAPL", profit_loss=-500)

        assert firewall.total_trades == 1
        assert firewall.current_streak_type == "loss"
        assert firewall.current_streak_count == 1

    def test_win_streak_detection(self):
        """Test detection of win streaks."""
        firewall = EmotionalFirewall()

        # Record 5 consecutive wins
        for i in range(5):
            firewall.record_trade(f"STOCK{i}", profit_loss=100)

        result = firewall.should_block_trade("NEXT")
        assert result["blocked"]
        assert EmotionalPattern.WIN_STREAK.value in result["patterns_detected"]

    def test_loss_streak_detection(self):
        """Test detection of loss streaks."""
        firewall = EmotionalFirewall()

        # Record 5 consecutive losses
        for i in range(5):
            firewall.record_trade(f"STOCK{i}", profit_loss=-100)

        result = firewall.should_block_trade("NEXT")
        assert result["blocked"]
        assert EmotionalPattern.LOSS_STREAK.value in result["patterns_detected"]

    def test_streak_reset_on_opposite_outcome(self):
        """Test that streak resets when outcome changes."""
        firewall = EmotionalFirewall()

        # Win streak
        for i in range(3):
            firewall.record_trade(f"STOCK{i}", profit_loss=100)

        assert firewall.current_streak_count == 3
        assert firewall.current_streak_type == "win"

        # Loss breaks streak
        firewall.record_trade("LOSER", profit_loss=-100)

        assert firewall.current_streak_count == 1
        assert firewall.current_streak_type == "loss"

    def test_revenge_trading_detection(self):
        """Test detection of revenge trading after loss."""
        firewall = EmotionalFirewall()

        # Record a loss
        firewall.record_trade("LOSER", profit_loss=-1000)

        # Try to trade immediately (should be blocked)
        result = firewall.should_block_trade("REVENGE")
        assert result["blocked"]
        assert EmotionalPattern.REVENGE_TRADING.value in result["patterns_detected"]

    def test_revenge_trading_window_expires(self):
        """Test that revenge window expires after 30 minutes."""
        firewall = EmotionalFirewall()

        # Record a loss
        loss_time = datetime.now(firewall.timezone)
        firewall.record_trade("LOSER", profit_loss=-1000, timestamp=loss_time)

        # Try to trade 35 minutes later (should be allowed)
        trade_time = loss_time + timedelta(minutes=35)
        result = firewall.should_block_trade("SAFE", timestamp=trade_time)
        assert not result["blocked"]

    def test_hourly_overtrading_detection(self):
        """Test detection of too many trades per hour."""
        firewall = EmotionalFirewall()

        base_time = datetime.now(firewall.timezone)

        # Record 3 trades in one hour
        for i in range(3):
            trade_time = base_time + timedelta(minutes=i * 10)
            firewall.record_trade(f"STOCK{i}", profit_loss=100, timestamp=trade_time)

        # 4th trade in same hour should be blocked
        result = firewall.should_block_trade(
            "OVERTRADE", timestamp=base_time + timedelta(minutes=45)
        )
        assert result["blocked"]
        assert EmotionalPattern.OVERTRADING.value in result["patterns_detected"]

    def test_daily_overtrading_detection(self):
        """Test detection of too many trades per day."""
        firewall = EmotionalFirewall()

        base_time = datetime.now(firewall.timezone).replace(hour=9, minute=0)

        # Record 10 trades throughout the day
        for i in range(10):
            trade_time = base_time + timedelta(hours=i)
            firewall.record_trade(f"STOCK{i}", profit_loss=100, timestamp=trade_time)

        # 11th trade should be blocked
        result = firewall.should_block_trade(
            "OVERTRADE", timestamp=base_time + timedelta(hours=10)
        )
        assert result["blocked"]

    @patch("core.psychology.emotional_firewall.datetime")
    def test_weekend_trading_detection(self, mock_datetime):
        """Test detection of weekend trading."""
        firewall = EmotionalFirewall()

        # Saturday
        saturday = datetime(2025, 1, 4, 10, 0, tzinfo=firewall.timezone)  # Saturday
        mock_datetime.now.return_value = saturday

        result = firewall.should_block_trade("WEEKEND", timestamp=saturday)
        assert result["blocked"]
        assert EmotionalPattern.WEEKEND.value in result["patterns_detected"]

    def test_late_night_trading_detection(self):
        """Test detection of late night trading."""
        firewall = EmotionalFirewall()

        # 9 PM (after 8 PM cutoff)
        late_time = datetime.now(firewall.timezone).replace(hour=21, minute=0)

        result = firewall.should_block_trade("LATE", timestamp=late_time)
        assert result["blocked"]
        assert EmotionalPattern.LATE_NIGHT.value in result["patterns_detected"]

    def test_position_size_increase_after_loss(self):
        """Test detection of position size increase after loss."""
        firewall = EmotionalFirewall()

        # Record trades with normal sizing
        firewall.record_trade("STOCK1", profit_loss=100, position_size=5000)
        firewall.record_trade("STOCK2", profit_loss=-200, position_size=5000)
        firewall.record_trade("STOCK3", profit_loss=150, position_size=5000)

        # Try to trade with significantly larger size after recent loss
        result = firewall.should_block_trade("BIG", position_size=8000)
        assert result["blocked"]
        assert (
            EmotionalPattern.SIZE_INCREASE_AFTER_LOSS.value
            in result["patterns_detected"]
        )

    def test_cooldown_activation(self):
        """Test that cooldown is set after blocking."""
        firewall = EmotionalFirewall()

        # Trigger loss streak
        for i in range(5):
            firewall.record_trade(f"LOSS{i}", profit_loss=-100)

        # Block trade and set cooldown
        result = firewall.should_block_trade("NEXT")
        assert result["blocked"]
        assert result["cooldown_expires"] is not None

        # Try to trade again immediately (should be blocked by cooldown)
        result2 = firewall.should_block_trade("NEXT2")
        assert result2["blocked"]
        assert "Active cooldown" in result2["reasons"][0]

    def test_cooldown_override(self):
        """Test manual cooldown override."""
        firewall = EmotionalFirewall()

        # Set cooldown
        firewall.cooldown_expires_at = datetime.now(firewall.timezone) + timedelta(
            hours=1
        )
        firewall.cooldown_reason = "Test cooldown"

        # Invalid code
        assert not firewall.override_cooldown("WRONG")
        assert firewall.cooldown_expires_at is not None

        # Valid code
        assert firewall.override_cooldown("OVERRIDE_COOLDOWN")
        assert firewall.cooldown_expires_at is None

    def test_statistics(self):
        """Test comprehensive statistics."""
        firewall = EmotionalFirewall()

        # Record some trades
        firewall.record_trade("WIN1", profit_loss=100)
        firewall.record_trade("WIN2", profit_loss=200)
        firewall.record_trade("LOSS1", profit_loss=-150)

        # Trigger some blocks
        for i in range(5):
            firewall.record_trade(f"LOSS{i}", profit_loss=-100)

        firewall.should_block_trade("BLOCKED")

        stats = firewall.get_statistics()

        assert stats["total_trades"] > 0
        assert stats["blocked_trades"] > 0
        assert "current_streak" in stats
        assert "blocks_by_pattern" in stats

    def test_reset_streak(self):
        """Test manual streak reset."""
        firewall = EmotionalFirewall()

        # Build up a streak
        for i in range(3):
            firewall.record_trade(f"WIN{i}", profit_loss=100)

        assert firewall.current_streak_count == 3

        # Reset
        firewall.reset_streak()

        assert firewall.current_streak_count == 0
        assert firewall.current_streak_type is None

    def test_clear_history(self):
        """Test clearing trade history."""
        firewall = EmotionalFirewall()

        # Record trades
        for i in range(5):
            firewall.record_trade(f"TRADE{i}", profit_loss=100)

        # Clear
        firewall.clear_history()

        assert firewall.total_trades == 0
        assert len(firewall.trade_history) == 0
        assert len(firewall.recent_trades) == 0


# ============================================================================
# TradingTimeOut Tests
# ============================================================================


class TestTradingTimeOut:
    """Test suite for TradingTimeOut class."""

    def test_initialization(self):
        """Test basic initialization."""
        timeout = TradingTimeOut(portfolio_value=100000)

        assert timeout.portfolio_value == 100000
        assert timeout.consecutive_losses == 0
        assert not timeout.in_timeout

    def test_record_single_loss(self):
        """Test recording a single loss."""
        timeout = TradingTimeOut(consecutive_loss_limit=3, portfolio_value=100000)

        status = timeout.record_loss("AAPL", loss_amount=500)

        assert timeout.consecutive_losses == 1
        assert not status["in_timeout"]

    def test_consecutive_loss_timeout(self):
        """Test timeout after consecutive losses."""
        timeout = TradingTimeOut(consecutive_loss_limit=3, portfolio_value=100000)

        # Record 3 consecutive losses
        for i in range(3):
            status = timeout.record_loss(f"STOCK{i}", loss_amount=500)

        assert status["in_timeout"]
        assert status["reason"] == TimeOutReason.CONSECUTIVE_LOSSES.value

    def test_win_resets_consecutive_losses(self):
        """Test that a win resets consecutive loss counter."""
        timeout = TradingTimeOut(consecutive_loss_limit=3, portfolio_value=100000)

        # Record 2 losses
        timeout.record_loss("LOSS1", loss_amount=500)
        timeout.record_loss("LOSS2", loss_amount=500)
        assert timeout.consecutive_losses == 2

        # Record a win
        timeout.record_win("WIN", profit_amount=1000)
        assert timeout.consecutive_losses == 0

    def test_daily_loss_limit_timeout(self):
        """Test timeout when daily loss limit exceeded."""
        timeout = TradingTimeOut(
            consecutive_loss_limit=10,  # High limit so it doesn't trigger
            daily_loss_limit_pct=0.02,
            portfolio_value=100000,
        )

        # Lose 2.5% in one day
        status = timeout.record_loss("BIG_LOSS", loss_amount=2500)

        assert status["in_timeout"]
        assert status["reason"] == TimeOutReason.DAILY_LOSS_LIMIT.value

    def test_exponential_backoff(self):
        """Test exponential backoff on repeated timeouts."""
        timeout = TradingTimeOut(
            consecutive_loss_limit=2, portfolio_value=100000, enable_logging=False
        )

        # First timeout (should be 60 minutes)
        timeout.record_loss("LOSS1", 500)
        timeout.record_loss("LOSS2", 500)
        assert timeout.get_next_timeout_duration() == 240  # Next would be 4 hours

        # Clear timeout
        timeout.override_timeout("OVERRIDE_TIMEOUT")
        timeout.consecutive_losses = 0

        # Second timeout (should be 240 minutes)
        timeout.record_loss("LOSS3", 500)
        timeout.record_loss("LOSS4", 500)
        assert timeout.get_next_timeout_duration() == 1440  # Next would be 24 hours

    def test_timeout_expiration(self):
        """Test that timeout automatically expires."""
        timeout = TradingTimeOut(portfolio_value=100000)

        # Set timeout that expired 1 minute ago
        past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        timeout.in_timeout = True
        timeout.timeout_expires_at = past_time

        # Check timeout (should auto-clear)
        status = timeout.check_timeout()
        assert not status["in_timeout"]

    def test_manual_timeout(self):
        """Test manually setting a timeout."""
        timeout = TradingTimeOut(portfolio_value=100000)

        timeout.manual_timeout(duration_minutes=120, reason="Manual halt for review")

        assert timeout.in_timeout
        assert timeout.timeout_reason == TimeOutReason.MANUAL

    def test_timeout_override(self):
        """Test manual timeout override."""
        timeout = TradingTimeOut(consecutive_loss_limit=2, portfolio_value=100000)

        # Trigger timeout
        timeout.record_loss("LOSS1", 500)
        timeout.record_loss("LOSS2", 500)
        assert timeout.in_timeout

        # Invalid code
        assert not timeout.override_timeout("WRONG")
        assert timeout.in_timeout

        # Valid code
        assert timeout.override_timeout("OVERRIDE_TIMEOUT")
        assert not timeout.in_timeout

    def test_daily_reset(self):
        """Test that daily tracking resets at midnight."""
        timeout = TradingTimeOut(portfolio_value=100000)

        # Record loss
        timeout.daily_loss_amount = 1000

        # Force daily reset
        timeout.daily_reset_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        status = timeout.check_timeout()

        # Should have reset
        assert status["daily_loss_amount"] == 0

    def test_time_remaining_calculation(self):
        """Test time remaining calculation."""
        timeout = TradingTimeOut(consecutive_loss_limit=2, portfolio_value=100000)

        # Trigger timeout
        timeout.record_loss("LOSS1", 500)
        timeout.record_loss("LOSS2", 500)

        status = timeout.check_timeout()
        assert status["time_remaining"] is not None
        assert status["time_remaining"]["total_minutes"] > 0

    def test_reset_trigger_count(self):
        """Test resetting timeout trigger count."""
        timeout = TradingTimeOut(portfolio_value=100000)

        timeout.timeout_trigger_count = 5

        # Invalid code
        assert not timeout.reset_trigger_count("WRONG")
        assert timeout.timeout_trigger_count == 5

        # Valid code
        assert timeout.reset_trigger_count("RESET_TRIGGERS")
        assert timeout.timeout_trigger_count == 0

    def test_statistics(self):
        """Test comprehensive statistics."""
        timeout = TradingTimeOut(consecutive_loss_limit=2, portfolio_value=100000)

        # Record some losses and trigger timeout
        timeout.record_loss("LOSS1", 500)
        timeout.record_loss("LOSS2", 500)

        stats = timeout.get_statistics()

        assert stats["total_losses_recorded"] == 2
        assert stats["total_timeouts_triggered"] == 1
        assert "timeouts_by_reason" in stats

    def test_update_portfolio_value(self):
        """Test updating portfolio value."""
        timeout = TradingTimeOut(portfolio_value=100000)

        timeout.update_portfolio_value(120000)
        assert timeout.portfolio_value == 120000


# ============================================================================
# RecoveryProtocol Tests
# ============================================================================


class TestRecoveryProtocol:
    """Test suite for RecoveryProtocol class."""

    def test_initialization(self):
        """Test basic initialization."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        assert protocol.entry_drawdown == 0.15
        assert protocol.initial_portfolio_value == 85000
        assert protocol.current_phase == RecoveryPhase.PHASE_1_CONSERVATIVE
        assert not protocol.recovery_completed

    def test_initialization_invalid_drawdown(self):
        """Test initialization with invalid drawdown."""
        with pytest.raises(ValueError):
            RecoveryProtocol(entry_drawdown=-0.1, portfolio_value=100000)

        with pytest.raises(ValueError):
            RecoveryProtocol(entry_drawdown=1.5, portfolio_value=100000)

    def test_phase_1_position_sizing(self):
        """Test 50% position sizing in Phase 1."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        assert protocol.get_position_size_multiplier() == 0.50

    def test_record_profitable_trade(self):
        """Test recording a profitable trade."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        status = protocol.record_trade(profit_loss=1000, symbol="AAPL")

        assert len(protocol.phase_trades) == 1
        assert protocol.phase_profit_loss == 1000
        assert protocol.consecutive_losses == 0

    def test_record_losing_trade(self):
        """Test recording a losing trade."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        status = protocol.record_trade(profit_loss=-500, symbol="AAPL")

        assert len(protocol.phase_trades) == 1
        assert protocol.phase_profit_loss == -500
        assert protocol.consecutive_losses == 1

    def test_cannot_advance_without_requirements(self):
        """Test that advancement is blocked without meeting requirements."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        # Record only 1 profitable trade (need 5)
        protocol.record_trade(profit_loss=1000)

        check = protocol.can_advance_phase()
        assert not check["can_advance"]
        assert len(check["blocking_reasons"]) > 0

    def test_advance_phase_with_requirements(self):
        """Test successful phase advancement."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15, portfolio_value=85000, enable_logging=False
        )

        # Phase 1 requires: 5 trades, 3% profit, 60% win rate
        # Record 5 winning trades totaling > 3% profit
        for i in range(5):
            protocol.record_trade(profit_loss=550, symbol=f"STOCK{i}")

        # Check if can advance
        check = protocol.can_advance_phase()
        assert check["can_advance"]

        # Advance
        success = protocol.advance_phase()
        assert success
        assert protocol.current_phase == RecoveryPhase.PHASE_2_CAUTIOUS

    def test_phase_2_position_sizing(self):
        """Test 75% position sizing in Phase 2."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15,
            portfolio_value=85000,
            starting_phase=RecoveryPhase.PHASE_2_CAUTIOUS,
        )

        assert protocol.get_position_size_multiplier() == 0.75

    def test_phase_3_position_sizing(self):
        """Test 100% position sizing in Phase 3 (full recovery)."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15,
            portfolio_value=85000,
            starting_phase=RecoveryPhase.PHASE_3_FULL_RECOVERY,
        )

        assert protocol.get_position_size_multiplier() == 1.00

    def test_full_recovery_completion(self):
        """Test completing full recovery."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15,
            portfolio_value=85000,
            starting_phase=RecoveryPhase.PHASE_2_CAUTIOUS,
            enable_logging=False,
        )

        # Meet Phase 2 requirements and advance to Phase 3
        for i in range(4):
            protocol.record_trade(profit_loss=500, symbol=f"STOCK{i}")

        protocol.advance_phase()

        assert protocol.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY
        assert protocol.recovery_completed

    def test_demotion_on_excessive_losses(self):
        """Test demotion to earlier phase on poor performance."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15,
            portfolio_value=85000,
            starting_phase=RecoveryPhase.PHASE_2_CAUTIOUS,
            enable_logging=False,
        )

        # Record excessive consecutive losses
        for i in range(5):
            protocol.record_trade(profit_loss=-500, symbol=f"LOSS{i}")

        # Should be demoted to Phase 1
        assert protocol.current_phase == RecoveryPhase.PHASE_1_CONSERVATIVE

    def test_no_demotion_from_phase_1(self):
        """Test that Phase 1 is the floor (no demotion below it)."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15, portfolio_value=85000, enable_logging=False
        )

        initial_phase = protocol.current_phase

        # Record many losses
        for i in range(10):
            protocol.record_trade(profit_loss=-500, symbol=f"LOSS{i}")

        # Should still be in Phase 1
        assert protocol.current_phase == initial_phase

    def test_cannot_advance_from_phase_3(self):
        """Test that Phase 3 is the ceiling (no advancement beyond it)."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15,
            portfolio_value=85000,
            starting_phase=RecoveryPhase.PHASE_3_FULL_RECOVERY,
        )

        check = protocol.can_advance_phase()
        assert not check["can_advance"]
        assert check["reason"] == "Already at full recovery"

    def test_win_rate_requirement(self):
        """Test that win rate must meet threshold."""
        protocol = RecoveryProtocol(
            entry_drawdown=0.15, portfolio_value=85000, enable_logging=False
        )

        # Record 5 trades but only 2 wins (40% win rate, need 60%)
        protocol.record_trade(profit_loss=1000)
        protocol.record_trade(profit_loss=-500)
        protocol.record_trade(profit_loss=-500)
        protocol.record_trade(profit_loss=1000)
        protocol.record_trade(profit_loss=-500)

        check = protocol.can_advance_phase()
        assert not check["can_advance"]
        assert not check["requirements_met"]["win_rate"]

    def test_get_status(self):
        """Test comprehensive status reporting."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        protocol.record_trade(profit_loss=500)
        protocol.record_trade(profit_loss=700)

        status = protocol.get_status()

        assert status["in_recovery"]
        assert status["current_phase"] == RecoveryPhase.PHASE_1_CONSERVATIVE.value
        assert status["position_size_multiplier"] == 0.50
        assert status["phase_trades_count"] == 2
        assert "advancement_check" in status

    def test_get_statistics(self):
        """Test comprehensive statistics."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        protocol.record_trade(profit_loss=500)
        protocol.record_trade(profit_loss=700)

        stats = protocol.get_statistics()

        assert stats["entry_drawdown"] == 0.15
        assert stats["total_trades"] == 2
        assert "phase_history" in stats
        assert "current_phase_status" in stats

    def test_force_phase_advance(self):
        """Test forcing phase advancement."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        initial_phase = protocol.current_phase

        # Invalid code
        assert not protocol.force_phase_advance("WRONG")
        assert protocol.current_phase == initial_phase

        # Valid code
        assert protocol.force_phase_advance("FORCE_ADVANCE")
        assert protocol.current_phase == RecoveryPhase.PHASE_2_CAUTIOUS

    def test_get_max_position_size(self):
        """Test position size calculation with recovery adjustment."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        # Phase 1: 50% sizing
        assert protocol.get_max_position_size(10000) == 5000

        # Advance to Phase 2: 75% sizing
        protocol.current_phase = RecoveryPhase.PHASE_2_CAUTIOUS
        assert protocol.get_max_position_size(10000) == 7500

        # Advance to Phase 3: 100% sizing
        protocol.current_phase = RecoveryPhase.PHASE_3_FULL_RECOVERY
        assert protocol.get_max_position_size(10000) == 10000

    def test_is_in_recovery(self):
        """Test recovery status check."""
        protocol = RecoveryProtocol(entry_drawdown=0.15, portfolio_value=85000)

        assert protocol.is_in_recovery()

        # Complete recovery
        protocol.recovery_completed = True
        assert not protocol.is_in_recovery()


# ============================================================================
# Integration Tests
# ============================================================================


class TestPsychologyIntegration:
    """Integration tests for Psychology Module components working together."""

    def test_drawdown_triggers_recovery(self):
        """Test that drawdown naturally leads into recovery protocol."""
        # Start with drawdown monitor
        monitor = DrawdownMonitor(initial_capital=100000)
        monitor.update(current_value=85000)  # 15% drawdown

        # This should trigger entry into recovery
        protocol = RecoveryProtocol(
            entry_drawdown=monitor.current_drawdown,
            portfolio_value=monitor.current_value,
        )

        assert protocol.is_in_recovery()
        assert protocol.get_position_size_multiplier() == 0.50

    def test_timeout_with_firewall(self):
        """Test timeout and firewall working together."""
        timeout = TradingTimeOut(consecutive_loss_limit=3, portfolio_value=100000)
        firewall = EmotionalFirewall()

        # Record 3 consecutive losses (triggers both systems)
        for i in range(3):
            timeout.record_loss(f"LOSS{i}", 500)
            firewall.record_trade(f"LOSS{i}", profit_loss=-500)

        # Both should block trading
        assert timeout.is_in_timeout()

        firewall_result = firewall.should_block_trade("NEXT")
        assert firewall_result["blocked"]

    def test_full_loss_recovery_workflow(self):
        """Test complete workflow from loss to recovery."""
        portfolio_value = 100000

        # 1. Drawdown occurs
        monitor = DrawdownMonitor(initial_capital=portfolio_value)
        monitor.update(88000)  # 12% drawdown

        # 2. Enter recovery protocol
        protocol = RecoveryProtocol(
            entry_drawdown=monitor.current_drawdown, portfolio_value=88000
        )

        # 3. Record some profitable trades with reduced sizing
        for i in range(6):
            profit = 600
            protocol.record_trade(profit_loss=profit)
            monitor.update(monitor.current_value + profit)

        # 4. Should be able to advance phase
        assert protocol.can_advance_phase()["can_advance"]

        # 5. Continue recovery until full recovery
        protocol.advance_phase()
        assert protocol.current_phase == RecoveryPhase.PHASE_2_CAUTIOUS

        # 6. More profitable trades
        for i in range(4):
            profit = 500
            protocol.record_trade(profit_loss=profit)
            monitor.update(monitor.current_value + profit)

        # 7. Advance to full recovery
        protocol.advance_phase()
        assert protocol.current_phase == RecoveryPhase.PHASE_3_FULL_RECOVERY
        assert protocol.recovery_completed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core.psychology", "--cov-report=term-missing"])
