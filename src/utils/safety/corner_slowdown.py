"""Corner slowdown feed adjuster.

Reduces feed rate at sharp corners to prevent tool stress and deflection.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import FeedContext

if TYPE_CHECKING:
    from src.gcode_generator import GenerationSettings


@dataclass
class CornerSlowdownAdjuster:
    """Reduces feed rate at sharp corners.

    Sharp direction changes in toolpaths stress the end mill. This adjuster
    reduces feed at corners based on the corner severity (pre-calculated
    as corner_factor in the FeedContext).

    The final feed at a corner is:
        feed * corner_feed_factor * corner_factor

    Where:
        - corner_feed_factor is the global setting (e.g., 0.5 for 50%)
        - corner_factor is the severity (1.0 = not a corner, lower = sharper)

    Attributes:
        settings: GenerationSettings with corner_slowdown_enabled and corner_feed_factor
    """
    settings: 'GenerationSettings'

    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        """Apply corner feed reduction.

        Only reduces feed when corner_factor is less than 1.0 (indicating
        this point is a corner).

        Args:
            feed: Current feed rate
            context: FeedContext with corner_factor

        Returns:
            Reduced feed rate at corners, unchanged otherwise
        """
        if context.corner_factor < 1.0:
            # Apply both the global corner factor and the point-specific severity
            return feed * self.settings.corner_feed_factor * context.corner_factor
        return feed

    def is_enabled(self) -> bool:
        """Check if corner slowdown is enabled.

        Returns:
            True if corner_slowdown_enabled setting is True
        """
        return self.settings.corner_slowdown_enabled
