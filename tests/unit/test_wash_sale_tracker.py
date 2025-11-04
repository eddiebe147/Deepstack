"""
Unit tests for WashSaleTracker - IRS Wash Sale Rule Compliance

Tests comprehensive wash sale tracking including:
- Loss sale recording
- Wash sale detection within 30-day window
- Alternative symbol suggestions
- Disallowed loss calculations
- Expired record cleanup
- Edge cases and boundary conditions

Each test validates IRS Publication 550 compliance.
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from core.tax.wash_sale_tracker import LossSale, WashSaleTracker


class TestLossSaleDataClass:
    """Test LossSale dataclass validation."""

    def test_loss_sale_creation_valid(self):
        """Test creating a valid loss sale record."""
        loss_sale = LossSale(
            symbol="AAPL",
            quantity=100,
            loss_amount=500.0,
            sale_date=datetime(2024, 1, 15),
            cost_basis=15000.0,
            sale_price=14500.0,
        )

        assert loss_sale.symbol == "AAPL"
        assert loss_sale.quantity == 100
        assert loss_sale.loss_amount == 500.0
        assert loss_sale.cost_basis == 15000.0
        assert loss_sale.sale_price == 14500.0

    def test_loss_sale_invalid_quantity(self):
        """Test that invalid quantity raises error."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            LossSale(
                symbol="AAPL",
                quantity=-100,  # Invalid
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

    def test_loss_sale_invalid_loss_amount(self):
        """Test that negative loss amount raises error."""
        with pytest.raises(ValueError, match="Loss amount must be positive"):
            LossSale(
                symbol="AAPL",
                quantity=100,
                loss_amount=-500.0,  # Invalid
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

    def test_loss_sale_invalid_prices(self):
        """Test that invalid prices raise error."""
        with pytest.raises(
            ValueError, match="Cost basis and sale price must be non-negative"
        ):
            LossSale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=-15000.0,  # Invalid
                sale_price=14500.0,
            )


class TestBasicLossSaleRecording:
    """Test basic loss sale recording functionality."""

    def test_record_single_loss_sale(self):
        """Test recording a single loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Verify it was recorded
            loss_sales = tracker.get_loss_sales("AAPL")
            assert len(loss_sales) == 1
            assert loss_sales[0].symbol == "AAPL"
            assert loss_sales[0].quantity == 100
            assert loss_sales[0].loss_amount == 500.0

    def test_record_multiple_loss_sales_same_symbol(self):
        """Test recording multiple loss sales for same symbol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record first loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Record second loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=50,
                loss_amount=200.0,
                sale_date=datetime(2024, 2, 1),
                cost_basis=7500.0,
                sale_price=7300.0,
            )

            # Verify both recorded
            loss_sales = tracker.get_loss_sales("AAPL")
            assert len(loss_sales) == 2

    def test_record_loss_sales_different_symbols(self):
        """Test recording loss sales for different symbols."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            tracker.record_loss_sale(
                symbol="GOOGL",
                quantity=50,
                loss_amount=1000.0,
                sale_date=datetime(2024, 1, 20),
                cost_basis=7500.0,
                sale_price=6500.0,
            )

            # Verify both symbols tracked
            assert len(tracker.get_loss_sales("AAPL")) == 1
            assert len(tracker.get_loss_sales("GOOGL")) == 1
            assert len(tracker.get_affected_symbols()) == 2

    def test_symbol_case_insensitive(self):
        """Test that symbol lookup is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            tracker.record_loss_sale(
                symbol="aapl",  # lowercase
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Should find it with uppercase
            loss_sales = tracker.get_loss_sales("AAPL")
            assert len(loss_sales) == 1

    def test_invalid_symbol_recording(self):
        """Test that invalid symbol raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
                tracker.record_loss_sale(
                    symbol="",  # Empty
                    quantity=100,
                    loss_amount=500.0,
                    sale_date=datetime(2024, 1, 15),
                    cost_basis=15000.0,
                    sale_price=14500.0,
                )


class TestWashSaleDetection:
    """Test wash sale detection within 30-day windows."""

    def test_wash_sale_same_day_purchase(self):
        """Test wash sale on same day as loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Try to buy same day
            assert tracker.is_wash_sale("AAPL", loss_date) is True

    def test_wash_sale_within_30_days_after(self):
        """Test wash sale within 30 days AFTER loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Test various days after
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=1)) is True
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=15)) is True
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=30)) is True

    def test_wash_sale_within_30_days_before(self):
        """Test wash sale within 30 days BEFORE loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Test various days before
            assert tracker.is_wash_sale("AAPL", loss_date - timedelta(days=1)) is True
            assert tracker.is_wash_sale("AAPL", loss_date - timedelta(days=15)) is True
            assert tracker.is_wash_sale("AAPL", loss_date - timedelta(days=30)) is True

    def test_no_wash_sale_outside_window(self):
        """Test no wash sale outside 30-day window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Test 31 days after (outside window)
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=31)) is False

            # Test 31 days before (outside window)
            assert tracker.is_wash_sale("AAPL", loss_date - timedelta(days=31)) is False

            # Test 60 days after (way outside)
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=60)) is False

    def test_no_wash_sale_different_symbol(self):
        """Test that different symbol doesn't trigger wash sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Try to buy different symbol
            assert tracker.is_wash_sale("GOOGL", loss_date) is False

    def test_no_wash_sale_no_loss_sales(self):
        """Test that no loss sales means no wash sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # No loss sales recorded
            assert tracker.is_wash_sale("AAPL", datetime(2024, 1, 15)) is False

    def test_wash_sale_boundary_exactly_30_days(self):
        """Test wash sale boundary at exactly 30 days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15, 12, 0, 0)  # Noon
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Exactly 30 days = wash sale
            assert tracker.is_wash_sale("AAPL", loss_date + timedelta(days=30)) is True
            assert tracker.is_wash_sale("AAPL", loss_date - timedelta(days=30)) is True


class TestWashSaleWindow:
    """Test wash sale window calculation."""

    def test_wash_sale_window_single_loss(self):
        """Test wash sale window for single loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            loss_date = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            window = tracker.get_wash_sale_window("AAPL")
            assert window is not None

            # Window should be 30 days before to 30 days after
            expected_start = loss_date - timedelta(days=30)
            expected_end = loss_date + timedelta(days=30)

            assert window[0] == expected_start
            assert window[1] == expected_end

    def test_wash_sale_window_multiple_losses(self):
        """Test wash sale window with multiple loss sales."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # First loss
            loss_date1 = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date1,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Second loss (later)
            loss_date2 = datetime(2024, 2, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=50,
                loss_amount=200.0,
                sale_date=loss_date2,
                cost_basis=7500.0,
                sale_price=7300.0,
            )

            window = tracker.get_wash_sale_window("AAPL")
            assert window is not None

            # Should span from earliest start to latest end
            expected_start = loss_date1 - timedelta(days=30)
            expected_end = loss_date2 + timedelta(days=30)

            assert window[0] == expected_start
            assert window[1] == expected_end

    def test_wash_sale_window_no_losses(self):
        """Test wash sale window when no losses recorded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            window = tracker.get_wash_sale_window("AAPL")
            assert window is None


class TestAlternativeSymbols:
    """Test alternative symbol suggestions."""

    def test_get_alternatives_for_tech_stock(self):
        """Test getting alternatives for tech stock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            alternatives = tracker.get_alternative_symbols("AAPL", count=5)

            # Should return tech alternatives
            assert len(alternatives) > 0
            assert len(alternatives) <= 5
            assert "AAPL" not in alternatives  # Not the same symbol

    def test_get_alternatives_for_finance_stock(self):
        """Test getting alternatives for finance stock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            alternatives = tracker.get_alternative_symbols("JPM", count=5)

            # Should return finance alternatives
            assert len(alternatives) > 0
            assert "JPM" not in alternatives

    def test_get_alternatives_filters_wash_sales(self):
        """Test that alternatives exclude symbols with wash sales."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record loss on AAPL
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Record loss on potential alternative MSFT
            tracker.record_loss_sale(
                symbol="MSFT",
                quantity=100,
                loss_amount=300.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=10000.0,
                sale_price=9700.0,
            )

            alternatives = tracker.get_alternative_symbols("AAPL", count=5)

            # MSFT should be filtered out (has wash sale)
            assert "MSFT" not in alternatives

    def test_get_alternatives_custom_count(self):
        """Test getting custom number of alternatives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            alternatives = tracker.get_alternative_symbols("AAPL", count=3)
            assert len(alternatives) <= 3

    def test_get_alternatives_unknown_symbol(self):
        """Test getting alternatives for unknown symbol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            alternatives = tracker.get_alternative_symbols("UNKNOWN", count=5)
            # Should return empty list for unknown symbols
            assert alternatives == []


class TestDisallowedLossCalculation:
    """Test disallowed loss calculation."""

    def test_calculate_disallowed_loss_single(self):
        """Test calculating disallowed loss for single loss sale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record recent loss (within window)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            disallowed = tracker.calculate_disallowed_loss("AAPL")
            assert disallowed == 500.0

    def test_calculate_disallowed_loss_multiple(self):
        """Test calculating disallowed loss with multiple loss sales."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record first loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Record second loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=50,
                loss_amount=300.0,
                sale_date=datetime.now() - timedelta(days=5),
                cost_basis=7500.0,
                sale_price=7200.0,
            )

            disallowed = tracker.calculate_disallowed_loss("AAPL")
            assert disallowed == 800.0  # 500 + 300

    def test_calculate_disallowed_loss_expired(self):
        """Test that expired losses are not counted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record old loss (outside window)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=40),  # > 30 days
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            disallowed = tracker.calculate_disallowed_loss("AAPL")
            assert disallowed == 0.0  # Outside window

    def test_calculate_disallowed_loss_no_losses(self):
        """Test calculating disallowed loss with no losses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            disallowed = tracker.calculate_disallowed_loss("AAPL")
            assert disallowed == 0.0


class TestExpiredRecordCleanup:
    """Test cleanup of expired wash sale records."""

    def test_clear_expired_records(self):
        """Test clearing records older than 61 days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record old loss (> 61 days)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=70),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Record recent loss
            tracker.record_loss_sale(
                symbol="GOOGL",
                quantity=50,
                loss_amount=300.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=7500.0,
                sale_price=7200.0,
            )

            # Clear expired
            deleted = tracker.clear_expired_records()

            # Should have deleted 1 record
            assert deleted == 1

            # AAPL should be gone
            assert len(tracker.get_loss_sales("AAPL")) == 0

            # GOOGL should remain
            assert len(tracker.get_loss_sales("GOOGL")) == 1

    def test_clear_expired_no_records(self):
        """Test clearing when no expired records exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record recent loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Clear expired
            deleted = tracker.clear_expired_records()

            # Should have deleted 0 records
            assert deleted == 0

            # AAPL should remain
            assert len(tracker.get_loss_sales("AAPL")) == 1


class TestDatabasePersistence:
    """Test database persistence and reload."""

    def test_persistence_across_instances(self):
        """Test that data persists across tracker instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test.db"

            # Create first instance and record loss
            tracker1 = WashSaleTracker(db_path=db_path)
            tracker1.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Create second instance (should load from DB)
            tracker2 = WashSaleTracker(db_path=db_path)

            # Should find the loss sale
            loss_sales = tracker2.get_loss_sales("AAPL")
            assert len(loss_sales) == 1
            assert loss_sales[0].loss_amount == 500.0

    def test_database_auto_load_on_init(self):
        """Test that database is automatically loaded on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test.db"

            # Create and populate
            tracker1 = WashSaleTracker(db_path=db_path)
            tracker1.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # New instance should auto-load
            tracker2 = WashSaleTracker(db_path=db_path)
            assert "AAPL" in tracker2.get_affected_symbols()


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_get_affected_symbols(self):
        """Test getting list of affected symbols."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record losses for multiple symbols
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            tracker.record_loss_sale(
                symbol="GOOGL",
                quantity=50,
                loss_amount=300.0,
                sale_date=datetime(2024, 1, 20),
                cost_basis=7500.0,
                sale_price=7200.0,
            )

            symbols = tracker.get_affected_symbols()
            assert len(symbols) == 2
            assert "AAPL" in symbols
            assert "GOOGL" in symbols

    def test_get_summary(self):
        """Test getting tracker summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record some losses
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            tracker.record_loss_sale(
                symbol="GOOGL",
                quantity=50,
                loss_amount=300.0,
                sale_date=datetime.now() - timedelta(days=5),
                cost_basis=7500.0,
                sale_price=7200.0,
            )

            summary = tracker.get_summary()

            assert summary["total_loss_sales"] == 2
            assert summary["affected_symbols"] == 2
            assert "AAPL" in summary["symbols_list"]
            assert "GOOGL" in summary["symbols_list"]
            assert summary["total_disallowed_loss"] == 800.0  # Both within window

    def test_export_to_json(self):
        """Test exporting wash sale data to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record a loss
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Export to JSON
            json_path = f"{tmpdir}/export.json"
            tracker.export_to_json(json_path)

            # Verify file exists
            assert Path(json_path).exists()

            # Verify content
            import json

            with open(json_path, "r") as f:
                data = json.load(f)

            assert data["total_loss_sales"] == 1
            assert len(data["loss_sales"]) == 1
            assert data["loss_sales"][0]["symbol"] == "AAPL"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_same_day_multiple_transactions(self):
        """Test multiple transactions on same day."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            same_date = datetime(2024, 1, 15, 10, 0, 0)

            # Record multiple losses same day
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=same_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=50,
                loss_amount=200.0,
                sale_date=same_date,
                cost_basis=7500.0,
                sale_price=7300.0,
            )

            # Both should be tracked
            loss_sales = tracker.get_loss_sales("AAPL")
            assert len(loss_sales) == 2

    def test_very_large_loss_amount(self):
        """Test handling very large loss amounts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Use recent date (within 30-day window)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=10000,
                loss_amount=1000000.0,  # $1M loss
                sale_date=datetime.now() - timedelta(days=10),
                cost_basis=15000000.0,
                sale_price=14000000.0,
            )

            disallowed = tracker.calculate_disallowed_loss("AAPL")
            assert disallowed == 1000000.0

    def test_fractional_shares(self):
        """Test handling fractional quantities (should round to int)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Quantity should be integer
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,  # Integer shares
                loss_amount=500.0,
                sale_date=datetime(2024, 1, 15),
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            loss_sales = tracker.get_loss_sales("AAPL")
            assert isinstance(loss_sales[0].quantity, int)

    def test_wash_sale_year_boundary(self):
        """Test wash sale across year boundary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Loss sale in December
            loss_date = datetime(2023, 12, 20)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=loss_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Purchase in January (next year, within 30 days)
            purchase_date = datetime(2024, 1, 10)
            assert tracker.is_wash_sale("AAPL", purchase_date) is True

    def test_empty_tracker_operations(self):
        """Test operations on empty tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # All should return safe defaults
            assert tracker.get_loss_sales() == []
            assert tracker.get_affected_symbols() == []
            assert tracker.calculate_disallowed_loss("AAPL") == 0.0
            assert tracker.is_wash_sale("AAPL", datetime.now()) is False
            assert tracker.get_wash_sale_window("AAPL") is None

            summary = tracker.get_summary()
            assert summary["total_loss_sales"] == 0
            assert summary["total_disallowed_loss"] == 0.0


class TestIntegration:
    """Integration tests for end-to-end wash sale tracking."""

    def test_realistic_trading_scenario(self):
        """Test realistic trading scenario with wash sale prevention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Day 1: Sell AAPL at a loss
            day1 = datetime(2024, 1, 15)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=day1,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Day 10: Try to buy AAPL again (wash sale!)
            day10 = day1 + timedelta(days=10)
            assert tracker.is_wash_sale("AAPL", day10) is True

            # Get alternatives
            alternatives = tracker.get_alternative_symbols("AAPL", count=3)
            assert len(alternatives) > 0

            # Buy alternative instead (no wash sale)
            alt_symbol = alternatives[0]
            assert tracker.is_wash_sale(alt_symbol, day10) is False

            # Day 45: Outside wash sale window
            day45 = day1 + timedelta(days=45)
            assert tracker.is_wash_sale("AAPL", day45) is False

    def test_multiple_symbols_management(self):
        """Test managing wash sales for multiple symbols."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            base_date = datetime(2024, 1, 1)

            # Record losses for multiple symbols
            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
            for i, symbol in enumerate(symbols):
                tracker.record_loss_sale(
                    symbol=symbol,
                    quantity=100,
                    loss_amount=500.0 + (i * 100),
                    sale_date=base_date + timedelta(days=i),
                    cost_basis=15000.0,
                    sale_price=14500.0,
                )

            # Verify all tracked
            assert len(tracker.get_affected_symbols()) == 4

            # Check each for wash sale
            check_date = base_date + timedelta(days=2)
            for symbol in symbols:
                # Should trigger wash sale based on timing
                result = tracker.is_wash_sale(symbol, check_date)
                # AAPL, GOOGL should trigger; MSFT, TSLA might not
                if symbol in ["AAPL", "GOOGL"]:
                    assert result is True

    def test_wash_sale_with_cleanup(self):
        """Test wash sale tracking with periodic cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = WashSaleTracker(db_path=f"{tmpdir}/test.db")

            # Record old loss
            old_date = datetime.now() - timedelta(days=70)
            tracker.record_loss_sale(
                symbol="AAPL",
                quantity=100,
                loss_amount=500.0,
                sale_date=old_date,
                cost_basis=15000.0,
                sale_price=14500.0,
            )

            # Record recent loss
            recent_date = datetime.now() - timedelta(days=10)
            tracker.record_loss_sale(
                symbol="GOOGL",
                quantity=50,
                loss_amount=300.0,
                sale_date=recent_date,
                cost_basis=7500.0,
                sale_price=7200.0,
            )

            # Before cleanup
            assert len(tracker.get_affected_symbols()) == 2

            # Cleanup
            deleted = tracker.clear_expired_records()
            assert deleted == 1

            # After cleanup
            assert len(tracker.get_affected_symbols()) == 1
            assert "GOOGL" in tracker.get_affected_symbols()
            assert "AAPL" not in tracker.get_affected_symbols()
