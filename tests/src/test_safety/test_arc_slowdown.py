"""Tests for arc slowdown feed adjuster."""
import pytest
from dataclasses import dataclass

from src.utils.safety import FeedContext, ArcSlowdownAdjuster


@dataclass
class MockSettings:
    """Mock GenerationSettings for testing."""
    arc_slowdown_enabled: bool = True
    arc_feed_factor: float = 0.8


class TestArcSlowdownAdjuster:
    """Tests for ArcSlowdownAdjuster."""

    def test_adjust_feed_on_arc(self):
        """Arc moves should have reduced feed."""
        settings = MockSettings(arc_slowdown_enabled=True, arc_feed_factor=0.8)
        adjuster = ArcSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, is_arc=True)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 80.0  # 100 * 0.8

    def test_adjust_feed_straight_line(self):
        """Straight line moves should keep original feed."""
        settings = MockSettings(arc_slowdown_enabled=True, arc_feed_factor=0.8)
        adjuster = ArcSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, is_arc=False)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 100.0  # No reduction

    def test_is_enabled_when_setting_true(self):
        """Enabled when arc_slowdown_enabled is True."""
        settings = MockSettings(arc_slowdown_enabled=True)
        adjuster = ArcSlowdownAdjuster(settings)

        assert adjuster.is_enabled() is True

    def test_is_disabled_when_setting_false(self):
        """Disabled when arc_slowdown_enabled is False."""
        settings = MockSettings(arc_slowdown_enabled=False)
        adjuster = ArcSlowdownAdjuster(settings)

        assert adjuster.is_enabled() is False

    def test_aggressive_factor(self):
        """Test with more aggressive arc feed reduction."""
        settings = MockSettings(arc_slowdown_enabled=True, arc_feed_factor=0.5)
        adjuster = ArcSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, is_arc=True)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 50.0

    def test_minimal_factor(self):
        """Test with minimal arc feed reduction."""
        settings = MockSettings(arc_slowdown_enabled=True, arc_feed_factor=0.9)
        adjuster = ArcSlowdownAdjuster(settings)
        context = FeedContext(base_feed=45.0, pass_num=0, is_arc=True)

        result = adjuster.adjust_feed(45.0, context)

        assert result == pytest.approx(40.5)

    def test_default_for_non_arc(self):
        """Non-arc moves don't get reduced even with is_arc explicitly False."""
        settings = MockSettings(arc_slowdown_enabled=True, arc_feed_factor=0.5)
        adjuster = ArcSlowdownAdjuster(settings)
        context = FeedContext(base_feed=100.0, pass_num=0, is_arc=False)

        result = adjuster.adjust_feed(100.0, context)

        assert result == 100.0
