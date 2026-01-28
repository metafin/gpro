"""Shared dataclasses for G-code generation modules."""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Point:
    """A 2D coordinate point."""
    x: float
    y: float


@dataclass
class GCodeParams:
    """G-code generation parameters for a specific material/tool combination."""
    spindle_speed: int
    feed_rate: float       # inches/min
    plunge_rate: float     # inches/min
    material_depth: float  # inches (thickness or wall_thickness)

    # Drill-specific
    pecking_depth: Optional[float] = None  # inches per peck

    # End mill-specific
    pass_depth: Optional[float] = None     # inches per pass


@dataclass
class CircleCut:
    """A circular cut operation."""
    center: Point
    diameter: float


@dataclass
class HexCut:
    """A hexagonal cut operation."""
    center: Point
    flat_to_flat: float


@dataclass
class LineCutPoint:
    """A point in a line cut path."""
    x: float
    y: float
    line_type: str  # 'start', 'straight', 'arc'
    arc_center_x: Optional[float] = None
    arc_center_y: Optional[float] = None
    arc_direction: Optional[str] = None  # 'cw', 'ccw', or None for auto-detect


@dataclass
class LineCut:
    """A line cut operation (path of connected segments)."""
    points: List[LineCutPoint]
