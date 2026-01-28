"""Safety features for feed rate adjustments.

This module provides modular, composable safety features for G-code generation.
Each feature is implemented as a FeedAdjuster that can be enabled/disabled
independently.

Safety Features:
- FirstPassAdjuster: Reduces feed on first pass to ease tool engagement
- CornerSlowdownAdjuster: Reduces feed at sharp corners to prevent tool stress
- ArcSlowdownAdjuster: Reduces feed on arcs to account for different dynamics

Usage:
    from src.utils.safety import create_safety_coordinator, FeedContext

    coordinator = create_safety_coordinator(settings)
    context = FeedContext(base_feed=45.0, pass_num=0, is_arc=False, corner_factor=1.0)
    adjusted_feed = coordinator.get_adjusted_feed(45.0, context)
"""
from .base import (
    FeedContext,
    FeedAdjuster,
    SafetyCoordinator,
    create_safety_coordinator,
)
from .first_pass import FirstPassAdjuster
from .corner_slowdown import CornerSlowdownAdjuster
from .arc_slowdown import ArcSlowdownAdjuster

__all__ = [
    'FeedContext',
    'FeedAdjuster',
    'SafetyCoordinator',
    'create_safety_coordinator',
    'FirstPassAdjuster',
    'CornerSlowdownAdjuster',
    'ArcSlowdownAdjuster',
]
