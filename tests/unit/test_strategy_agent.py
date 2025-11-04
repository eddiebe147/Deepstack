"""
Unit tests for StrategyAgent - Deep Value and Squeeze Detection

Tests core functionality of strategy analysis including:
- Deep value scoring
- Squeeze score calculation
- Position sizing
"""

import sys
from pathlib import Path
from unittest.mock import patch


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.agents.strategy_agent import StrategyAgent


class TestSqueezeScoring:
    """Test squeeze score calculation."""

    def test_calculate_squeeze_score_high_squeeze(self, mock_config):
        """Test squeeze score calculation with high squeeze potential."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # High squeeze parameters
            score = agent._calculate_squeeze_score(
                short_interest=0.50,  # 50% short interest
                days_to_cover=9.0,  # 9 days to cover
                borrow_cost=0.18,  # 18% borrow cost
                float_available=0.10,  # 10% float available
            )

            # Should be high score (>80 = Extreme)
            assert score >= 80.0
            assert score <= 100.0

    def test_calculate_squeeze_score_low_squeeze(self, mock_config):
        """Test squeeze score calculation with low squeeze potential."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # Low squeeze parameters
            score = agent._calculate_squeeze_score(
                short_interest=0.05,  # 5% short interest
                days_to_cover=1.5,  # 1.5 days to cover
                borrow_cost=0.01,  # 1% borrow cost
                float_available=0.40,  # 40% float available
            )

            # Should be low score (<40 = Low)
            assert score < 40.0
            assert score >= 0.0

    def test_calculate_squeeze_score_moderate_squeeze(self, mock_config):
        """Test squeeze score calculation with moderate squeeze potential."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # Moderate squeeze parameters
            score = agent._calculate_squeeze_score(
                short_interest=0.25,  # 25% short interest
                days_to_cover=5.0,  # 5 days to cover
                borrow_cost=0.08,  # 8% borrow cost
                float_available=0.20,  # 20% float available
            )

            # Should be moderate score (40-60 = Moderate)
            assert 40.0 <= score < 60.0


class TestDeepValueScoring:
    """Test deep value score calculation."""

    def test_calculate_deep_value_score_high_value(
        self, mock_config, sample_fundamentals_high_value
    ):
        """Test deep value scoring with excellent fundamentals."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            score = agent._calculate_deep_value_score(sample_fundamentals_high_value)

            # Should be high score (>70)
            assert score >= 70.0
            assert score <= 100.0

    def test_calculate_deep_value_score_low_value(
        self, mock_config, sample_fundamentals_low_value
    ):
        """Test deep value scoring with poor fundamentals."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            score = agent._calculate_deep_value_score(sample_fundamentals_low_value)

            # Should be low score (<50)
            assert score < 50.0
            assert score >= 0.0

    def test_calculate_deep_value_score_pe_ratio_impact(self, mock_config):
        """Test that P/E ratio properly impacts deep value score."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # Low P/E should score higher
            low_pe_fundamentals = {
                "pe_ratio": 8.0,
                "pb_ratio": 1.0,
                "roe": 0.15,
                "fcf_yield": 0.06,
                "debt_equity": 0.5,
                "current_ratio": 1.5,
            }

            # High P/E should score lower
            high_pe_fundamentals = {
                "pe_ratio": 25.0,
                "pb_ratio": 1.0,
                "roe": 0.15,
                "fcf_yield": 0.06,
                "debt_equity": 0.5,
                "current_ratio": 1.5,
            }

            low_pe_score = agent._calculate_deep_value_score(low_pe_fundamentals)
            high_pe_score = agent._calculate_deep_value_score(high_pe_fundamentals)

            assert low_pe_score > high_pe_score

    def test_calculate_deep_value_score_roe_impact(self, mock_config):
        """Test that ROE properly impacts deep value score."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # High ROE should score higher
            high_roe_fundamentals = {
                "pe_ratio": 15.0,
                "pb_ratio": 1.5,
                "roe": 0.25,  # 25% ROE
                "fcf_yield": 0.06,
                "debt_equity": 0.5,
                "current_ratio": 1.5,
            }

            # Low ROE should score lower
            low_roe_fundamentals = {
                "pe_ratio": 15.0,
                "pb_ratio": 1.5,
                "roe": 0.08,  # 8% ROE
                "fcf_yield": 0.06,
                "debt_equity": 0.5,
                "current_ratio": 1.5,
            }

            high_roe_score = agent._calculate_deep_value_score(high_roe_fundamentals)
            low_roe_score = agent._calculate_deep_value_score(low_roe_fundamentals)

            assert high_roe_score > low_roe_score


class TestPositionSizing:
    """Test position sizing calculations."""

    def test_calculate_position_size_high_scores(self, mock_config):
        """Test position sizing with high overall and squeeze scores."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            position_size = agent._calculate_position_size(
                overall_score=85.0, squeeze_score=75.0
            )

            # Should be close to max (5%)
            assert position_size > 0.0
            assert position_size <= 0.05  # Hard limit

    def test_calculate_position_size_low_scores(self, mock_config):
        """Test position sizing with low scores."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            position_size = agent._calculate_position_size(
                overall_score=30.0, squeeze_score=20.0
            )

            # Should be small
            assert position_size > 0.0
            assert position_size < 0.01  # Less than 1%

    def test_calculate_position_size_never_exceeds_max(self, mock_config):
        """Test that position size never exceeds hard limit."""
        with patch("core.agents.strategy_agent.get_config", return_value=mock_config):
            agent = StrategyAgent()

            # Even with perfect scores
            position_size = agent._calculate_position_size(
                overall_score=100.0, squeeze_score=100.0
            )

            # Should never exceed 5%
            assert position_size <= 0.05
