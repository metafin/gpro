"""Base classes and types for safety feed adjustments.

This module defines the core protocol and coordinator for feed rate
safety features. Each safety feature implements the FeedAdjuster protocol
and is registered with the SafetyCoordinator.
"""
from dataclasses import dataclass, field
from typing import Protocol, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.gcode_generator import GenerationSettings


@dataclass
class FeedContext:
    """Context for feed rate adjustment decisions.

    This dataclass carries all information a feed adjuster might need
    to make its adjustment decision. It's passed through the chain of
    adjusters, allowing each to consider relevant factors.

    Attributes:
        base_feed: The original feed rate before any adjustments
        pass_num: Zero-indexed pass number (0 = first pass)
        is_arc: True if this move is an arc (G02/G03)
        corner_factor: Pre-calculated corner severity factor (1.0 = not a corner)
    """
    base_feed: float
    pass_num: int
    is_arc: bool = False
    corner_factor: float = 1.0


class FeedAdjuster(Protocol):
    """Protocol for feed rate adjustment safety features.

    Each safety feature (first pass reduction, corner slowdown, arc slowdown)
    implements this protocol. The coordinator chains them together.

    Methods:
        adjust_feed: Given a feed rate and context, return adjusted feed
        is_enabled: Check if this adjuster should be active
    """

    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        """Adjust the feed rate based on safety context.

        Args:
            feed: Current feed rate (may already be adjusted by prior adjusters)
            context: FeedContext with information for the adjustment decision

        Returns:
            Adjusted feed rate (may be unchanged if not applicable)
        """
        ...

    def is_enabled(self) -> bool:
        """Check if this adjuster is enabled based on settings.

        Returns:
            True if this adjuster should apply its adjustment
        """
        ...


@dataclass
class SafetyCoordinator:
    """Coordinates all safety feed adjusters in a chain.

    The coordinator maintains a list of feed adjusters and applies them
    in sequence. Only enabled adjusters are applied. The order matters:
    typically first-pass reduction is applied first, then corner slowdown,
    then arc slowdown.

    Example:
        coordinator = SafetyCoordinator(settings)
        context = FeedContext(base_feed=45.0, pass_num=0, is_arc=True)
        adjusted_feed = coordinator.get_adjusted_feed(45.0, context)
    """
    adjusters: List[FeedAdjuster] = field(default_factory=list)

    def register(self, adjuster: FeedAdjuster) -> None:
        """Register a feed adjuster with the coordinator.

        Args:
            adjuster: FeedAdjuster implementation to add to the chain
        """
        self.adjusters.append(adjuster)

    def get_adjusted_feed(self, base_feed: float, context: FeedContext) -> float:
        """Apply all enabled adjusters to get the final feed rate.

        Args:
            base_feed: Starting feed rate before adjustments
            context: FeedContext with information for adjustment decisions

        Returns:
            Final adjusted feed rate after all applicable adjusters
        """
        feed = base_feed
        for adjuster in self.adjusters:
            if adjuster.is_enabled():
                feed = adjuster.adjust_feed(feed, context)
        return feed


def create_safety_coordinator(settings: 'GenerationSettings') -> SafetyCoordinator:
    """Factory function to create a fully-configured SafetyCoordinator.

    Creates and registers all safety adjusters based on the provided settings.
    This is the main entry point for gcode_generator to get a coordinator.

    Args:
        settings: GenerationSettings with safety configuration

    Returns:
        SafetyCoordinator with all adjusters registered
    """
    # Import here to avoid circular imports
    from .first_pass import FirstPassAdjuster
    from .corner_slowdown import CornerSlowdownAdjuster
    from .arc_slowdown import ArcSlowdownAdjuster

    coordinator = SafetyCoordinator()

    # Register adjusters in order of application
    coordinator.register(FirstPassAdjuster(settings))
    coordinator.register(CornerSlowdownAdjuster(settings))
    coordinator.register(ArcSlowdownAdjuster(settings))

    return coordinator
