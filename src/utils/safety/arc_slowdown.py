"""Arc slowdown feed adjuster.

Reduces feed rate on arc moves (G02/G03) to account for the different
dynamics of curved toolpaths.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import FeedContext

if TYPE_CHECKING:
    from src.gcode_generator import GenerationSettings


@dataclass
class ArcSlowdownAdjuster:
    """Reduces feed rate on arc moves.

    Arcs have different cutting dynamics than straight lines:
    - The tool path is curved, creating varying chip loads
    - On interior cuts, the effective feed at the cutting edge is higher
    - On exterior cuts, the tool may engage more material on one side

    This adjuster applies a simple percentage reduction to all arc moves
    to improve cut quality and reduce tool stress.

    Attributes:
        settings: GenerationSettings with arc_slowdown_enabled and arc_feed_factor
    """
    settings: 'GenerationSettings'

    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        """Apply arc feed reduction.

        Only reduces feed when the move is an arc (context.is_arc is True).

        Args:
            feed: Current feed rate
            context: FeedContext with is_arc flag

        Returns:
            Reduced feed rate on arcs, unchanged otherwise
        """
        if context.is_arc:
            return feed * self.settings.arc_feed_factor
        return feed

    def is_enabled(self) -> bool:
        """Check if arc slowdown is enabled.

        Returns:
            True if arc_slowdown_enabled setting is True
        """
        return self.settings.arc_slowdown_enabled
