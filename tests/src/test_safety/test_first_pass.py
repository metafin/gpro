"""Tests for first pass feed reduction adjuster."""
import pytest
from dataclasses import dataclass

from src.utils.safety import FeedContext, FirstPassAdjuster


@dataclass
class MockSettings:
    """Mock GenerationSettings for testing."""
    first_pass_feed_factor: float = 0.7


class TestFirstPassAdjuster:
    """Tests for FirstPassAdjuster."""

    def test_adjust_feed_first_pass(self):
        """First pass should have reduced feed."""
        settings = MockSettings(first_pass_feed_factor=0.7)
        adjuster = FirstPassAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 70.0  # 100 * 0.7

    def test_adjust_feed_second_pass(self):
        """Second pass should keep original feed."""
        settings = MockSettings(first_pass_feed_factor=0.7)
        adjuster = FirstPassAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=1)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 100.0  # No reduction

    def test_adjust_feed_later_pass(self):
        """Later passes should keep original feed."""
        settings = MockSettings(first_pass_feed_factor=0.7)
        adjuster = FirstPassAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=5)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 100.0

    def test_is_enabled_when_factor_less_than_one(self):
        """Enabled when factor is less than 1.0."""
        settings = MockSettings(first_pass_feed_factor=0.7)
        adjuster = FirstPassAdjuster(settings)

        assert adjuster.is_enabled() is True

    def test_is_disabled_when_factor_is_one(self):
        """Disabled when factor is 1.0."""
        settings = MockSettings(first_pass_feed_factor=1.0)
        adjuster = FirstPassAdjuster(settings)

        assert adjuster.is_enabled() is False

    def test_aggressive_factor(self):
        """Test with more aggressive feed reduction."""
        settings = MockSettings(first_pass_feed_factor=0.5)
        adjuster = FirstPassAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 50.0

    def test_minimal_factor(self):
        """Test with minimal feed reduction."""
        settings = MockSettings(first_pass_feed_factor=0.3)
        adjuster = FirstPassAdjuster(settings)
        context = FeedContext(base_feed=45.0, pass_num=0)

        result = adjuster.adjust_feed(45.0, context)

        assert result == pytest.approx(13.5)
