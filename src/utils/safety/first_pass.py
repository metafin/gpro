"""First pass feed reduction adjuster.

Reduces feed rate on the first pass of each cut operation to ease
initial tool engagement with the material.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import FeedContext

if TYPE_CHECKING:
    from src.gcode_generator import GenerationSettings


@dataclass
class FirstPassAdjuster:
    """Reduces feed rate on the first pass.

    The first pass of any cutting operation encounters the most resistance
    as the tool initially engages the material. Reducing feed on this pass
    reduces stress on the tool.

    Attributes:
        settings: GenerationSettings containing first_pass_feed_factor
    """
    settings: 'GenerationSettings'

    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        """Apply first pass feed reduction.

        Only reduces feed when pass_num is 0 (first pass) and the
        first_pass_feed_factor is less than 1.0.

        Args:
            feed: Current feed rate
            context: FeedContext with pass_num

        Returns:
            Reduced feed rate on first pass, unchanged otherwise
        """
        if context.pass_num == 0:
            return feed * self.settings.first_pass_feed_factor
        return feed

    def is_enabled(self) -> bool:
        """Check if first pass reduction is enabled.

        Enabled when first_pass_feed_factor is less than 1.0.
        A factor of 1.0 means no reduction.

        Returns:
            True if factor is less than 1.0
        """
        return self.settings.first_pass_feed_factor < 1.0
