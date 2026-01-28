"""Tests for safety coordinator."""
import pytest
from dataclasses import dataclass

from src.utils.safety import (
    FeedContext,
    SafetyCoordinator,
    create_safety_coordinator,
    FirstPassAdjuster,
    CornerSlowdownAdjuster,
    ArcSlowdownAdjuster
)


@dataclass
class MockSettings:
    """Mock GenerationSettings for testing."""
    first_pass_feed_factor: float = 0.7
    corner_slowdown_enabled: bool = True
    corner_feed_factor: float = 0.5
    arc_slowdown_enabled: bool = True
    arc_feed_factor: float = 0.8


class TestSafetyCoordinator:
    """Tests for SafetyCoordinator."""

    def test_register_adjuster(self):
        """Can register adjusters."""
        coordinator = SafetyCoordinator()
        settings = MockSettings()
        adjuster = FirstPassAdjuster(settings)

        coordinator.register(adjuster)

        assert len(coordinator.adjusters) == 1

    def test_get_adjusted_feed_single_adjuster(self):
        """Single adjuster applies its reduction."""
        coordinator = SafetyCoordinator()
        settings = MockSettings(first_pass_feed_factor=0.7)
        coordinator.register(FirstPassAdjuster(settings))
        context = FeedContext(base_feed=100.0, pass_num=0)

        result = coordinator.get_adjusted_feed(100.0, context)

        assert result == 70.0

    def test_get_adjusted_feed_multiple_adjusters(self):
        """Multiple adjusters apply sequentially."""
        coordinator = SafetyCoordinator()
        settings = MockSettings(
            first_pass_feed_factor=0.7,
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5
        )
        coordinator.register(FirstPassAdjuster(settings))
        coordinator.register(CornerSlowdownAdjuster(settings))

        # First pass at a corner with 0.5 severity
        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.5)

        result = coordinator.get_adjusted_feed(100.0, context)

        # First pass: 100 * 0.7 = 70
        # Corner: 70 * 0.5 * 0.5 = 17.5
        assert result == pytest.approx(17.5)

    def test_get_adjusted_feed_disabled_adjuster_skipped(self):
        """Disabled adjusters don't apply their reduction."""
        coordinator = SafetyCoordinator()
        settings = MockSettings(
            first_pass_feed_factor=1.0,  # Disabled (factor is 1.0)
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5
        )
        coordinator.register(FirstPassAdjuster(settings))
        coordinator.register(CornerSlowdownAdjuster(settings))

        context = FeedContext(base_feed=100.0, pass_num=0, corner_factor=0.5)

        result = coordinator.get_adjusted_feed(100.0, context)

        # First pass disabled (factor=1.0), not applied
        # Corner: 100 * 0.5 * 0.5 = 25
        assert result == 25.0

    def test_all_adjusters_combined(self):
        """All three adjusters work together."""
        coordinator = SafetyCoordinator()
        settings = MockSettings(
            first_pass_feed_factor=0.7,
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5,
            arc_slowdown_enabled=True,
            arc_feed_factor=0.8
        )
        coordinator.register(FirstPassAdjuster(settings))
        coordinator.register(CornerSlowdownAdjuster(settings))
        coordinator.register(ArcSlowdownAdjuster(settings))

        # First pass, at a corner, on an arc
        context = FeedContext(
            base_feed=100.0,
            pass_num=0,
            is_arc=True,
            corner_factor=0.5
        )

        result = coordinator.get_adjusted_feed(100.0, context)

        # First pass: 100 * 0.7 = 70
        # Corner: 70 * 0.5 * 0.5 = 17.5
        # Arc: 17.5 * 0.8 = 14
        assert result == pytest.approx(14.0)

    def test_no_adjustments_when_all_disabled(self):
        """No reduction when all adjusters are disabled."""
        coordinator = SafetyCoordinator()
        settings = MockSettings(
            first_pass_feed_factor=1.0,  # Disabled
            corner_slowdown_enabled=False,  # Disabled
            arc_slowdown_enabled=False  # Disabled
        )
        coordinator.register(FirstPassAdjuster(settings))
        coordinator.register(CornerSlowdownAdjuster(settings))
        coordinator.register(ArcSlowdownAdjuster(settings))

        context = FeedContext(
            base_feed=100.0,
            pass_num=0,
            is_arc=True,
            corner_factor=0.5
        )

        result = coordinator.get_adjusted_feed(100.0, context)

        assert result == 100.0


class TestCreateSafetyCoordinator:
    """Tests for create_safety_coordinator factory function."""

    def test_creates_coordinator_with_all_adjusters(self):
        """Factory creates coordinator with all three adjusters."""
        settings = MockSettings()
        coordinator = create_safety_coordinator(settings)

        assert len(coordinator.adjusters) == 3

    def test_first_adjuster_is_first_pass(self):
        """First adjuster is FirstPassAdjuster."""
        settings = MockSettings()
        coordinator = create_safety_coordinator(settings)

        assert isinstance(coordinator.adjusters[0], FirstPassAdjuster)

    def test_second_adjuster_is_corner(self):
        """Second adjuster is CornerSlowdownAdjuster."""
        settings = MockSettings()
        coordinator = create_safety_coordinator(settings)

        assert isinstance(coordinator.adjusters[1], CornerSlowdownAdjuster)

    def test_third_adjuster_is_arc(self):
        """Third adjuster is ArcSlowdownAdjuster."""
        settings = MockSettings()
        coordinator = create_safety_coordinator(settings)

        assert isinstance(coordinator.adjusters[2], ArcSlowdownAdjuster)

    def test_coordinator_applies_all_enabled(self):
        """Created coordinator applies all enabled adjusters."""
        settings = MockSettings(
            first_pass_feed_factor=0.7,
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5,
            arc_slowdown_enabled=True,
            arc_feed_factor=0.8
        )
        coordinator = create_safety_coordinator(settings)

        context = FeedContext(
            base_feed=100.0,
            pass_num=0,
            is_arc=True,
            corner_factor=0.5
        )

        result = coordinator.get_adjusted_feed(100.0, context)

        # Same calculation as above
        assert result == pytest.approx(14.0)


class TestFeedContext:
    """Tests for FeedContext dataclass."""

    def test_default_values(self):
        """FeedContext has correct defaults."""
        context = FeedContext(base_feed=100.0, pass_num=0)

        assert context.base_feed == 100.0
        assert context.pass_num == 0
        assert context.is_arc is False
        assert context.corner_factor == 1.0

    def test_all_values_set(self):
        """All FeedContext values can be set."""
        context = FeedContext(
            base_feed=45.0,
            pass_num=2,
            is_arc=True,
            corner_factor=0.5
        )

        assert context.base_feed == 45.0
        assert context.pass_num == 2
        assert context.is_arc is True
        assert context.corner_factor == 0.5
