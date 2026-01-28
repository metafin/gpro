"""Tests for corner slowdown feed adjuster."""
import pytest
from dataclasses import dataclass

from src.utils.safety import FeedContext, CornerSlowdownAdjuster


@dataclass
class MockSettings:
    """Mock GenerationSettings for testing."""
    corner_slowdown_enabled: bool = True
    corner_feed_factor: float = 0.5


class TestCornerSlowdownAdjuster:
    """Tests for CornerSlowdownAdjuster."""

    def test_adjust_feed_at_corner(self):
        """Corner points should have reduced feed."""
        settings = MockSettings(corner_slowdown_enabled=True, corner_feed_factor=0.5)
        adjuster = CornerSlowdownAdjuster(settings)
        # corner_factor=0.5 represents a moderate corner
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.5)

        result = adjuster.adjust_feed(100.0, context)

        # 100 * 0.5 (global factor) * 0.5 (severity) = 25
        assert result == 25.0

    def test_adjust_feed_not_a_corner(self):
        """Non-corner points should keep original feed."""
        settings = MockSettings(corner_slowdown_enabled=True, corner_feed_factor=0.5)
        adjuster = CornerSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=1.0)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 100.0  # No reduction

    def test_adjust_feed_sharp_corner(self):
        """Sharp corners should have more aggressive reduction."""
        settings = MockSettings(corner_slowdown_enabled=True, corner_feed_factor=0.5)
        adjuster = CornerSlowdownAdjuster(settings)
        # corner_factor=0.3 represents a very sharp corner
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.3)

        result = adjuster.adjust_feed(100.0, context)

        # 100 * 0.5 * 0.3 = 15
        assert result == 15.0

    def test_adjust_feed_mild_corner(self):
        """Mild corners should have less aggressive reduction."""
        settings = MockSettings(corner_slowdown_enabled=True, corner_feed_factor=0.5)
        adjuster = CornerSlowdownAdjuster(settings)
        # corner_factor=0.75 represents a mild corner
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.75)

        result = adjuster.adjust_feed(100.0, context)

        # 100 * 0.5 * 0.75 = 37.5
        assert result == pytest.approx(37.5)

    def test_is_enabled_when_setting_true(self):
        """Enabled when corner_slowdown_enabled is True."""
        settings = MockSettings(corner_slowdown_enabled=True)
        adjuster = CornerSlowdownAdjuster(settings)

        assert adjuster.is_enabled() is True

    def test_is_disabled_when_setting_false(self):
        """Disabled when corner_slowdown_enabled is False."""
        settings = MockSettings(corner_slowdown_enabled=False)
        adjuster = CornerSlowdownAdjuster(settings)

        assert adjuster.is_enabled() is False

    def test_different_global_factor(self):
        """Test with different global corner feed factor."""
        settings = MockSettings(corner_slowdown_enabled=True, corner_feed_factor=0.8)
        adjuster = CornerSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.5)

        result = adjuster.adjust_feed(100.0, context)

        # 100 * 0.8 * 0.5 = 40
        assert result == 40.0
