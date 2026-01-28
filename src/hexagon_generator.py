"""Hexagon vertex calculation utilities.

Generates hexagon vertices for G-code toolpaths with proper orientation
and tool compensation.
"""
import math
from typing import List, Tuple


def calculate_hexagon_vertices(
    center_x: float,
    center_y: float,
    flat_to_flat: float
) -> List[Tuple[float, float]]:
    """
    Calculate hexagon vertices given center and flat-to-flat distance.

    Hexagon is oriented with flats parallel to X-axis (point-up orientation).

    Vertex order starts at top point and goes clockwise:
    - v0: top (12 o'clock)
    - v1: upper right (2 o'clock)
    - v2: lower right (4 o'clock)
    - v3: bottom (6 o'clock)
    - v4: lower left (8 o'clock)
    - v5: upper left (10 o'clock)

    Args:
        center_x: X coordinate of hexagon center
        center_y: Y coordinate of hexagon center
        flat_to_flat: Distance between parallel flat sides (wrench size)

    Returns:
        List of 6 (x, y) vertex tuples in clockwise order from top
    """
    # Apothem is distance from center to middle of flat side
    apothem = flat_to_flat / 2

    # Circumradius is distance from center to vertex
    # For regular hexagon: circumradius = apothem / cos(30°) = apothem / (√3/2)
    circumradius = flat_to_flat / math.sqrt(3)

    # Generate vertices starting at top (90°), going clockwise
    # Clockwise means decreasing angles in standard math coordinates
    vertices = []
    for i in range(6):
        angle = math.pi / 2 - i * math.pi / 3  # 90°, 30°, -30°, -90°, -150°, -210°
        x = center_x + circumradius * math.cos(angle)
        y = center_y + circumradius * math.sin(angle)
        vertices.append((x, y))

    return vertices


def calculate_compensated_vertices(
    center_x: float,
    center_y: float,
    flat_to_flat: float,
    tool_diameter: float,
    compensation: str = 'interior'
) -> List[Tuple[float, float]]:
    """
    Calculate hexagon vertices with tool radius compensation.

    Each vertex is offset along the angle bisector based on compensation type.

    Note: This is a re-export from tool_compensation for backward compatibility.
    The canonical implementation is in src/utils/tool_compensation.py.

    Args:
        center_x: X coordinate of hexagon center
        center_y: Y coordinate of hexagon center
        flat_to_flat: Distance between parallel flat sides (wrench size)
        tool_diameter: Diameter of the cutting tool
        compensation: "none", "interior", or "exterior"
            - "interior" (default): Tool cuts inside, resulting hex = flat_to_flat
            - "exterior": Tool cuts outside, cutting out a hex of flat_to_flat
            - "none": Tool center follows the hex vertices

    Returns:
        List of 6 compensated (x, y) vertex tuples in clockwise order from top
    """
    # Lazy import to avoid circular dependency
    from .utils.tool_compensation import calculate_hexagon_compensated_vertices
    return calculate_hexagon_compensated_vertices(
        center_x, center_y, flat_to_flat, tool_diameter, compensation
    )


def get_hexagon_start_position(
    vertices: List[Tuple[float, float]]
) -> Tuple[float, float]:
    """
    Get the starting position for hexagon cutting.

    Returns the first vertex (top) for positioning before cutting.

    Args:
        vertices: List of hexagon vertex coordinates

    Returns:
        (x, y) tuple of the starting vertex
    """
    if not vertices:
        return (0, 0)
    return vertices[0]


def calculate_hexagon_bounds(
    center_x: float,
    center_y: float,
    flat_to_flat: float
) -> Tuple[float, float, float, float]:
    """
    Calculate the bounding box of a hexagon.

    Args:
        center_x: X coordinate of hexagon center
        center_y: Y coordinate of hexagon center
        flat_to_flat: Distance between parallel flat sides

    Returns:
        Tuple of (min_x, min_y, max_x, max_y)
    """
    apothem = flat_to_flat / 2
    circumradius = flat_to_flat / math.sqrt(3)

    # For point-up orientation:
    # - X extent is ±apothem (distance to flat sides)
    # - Y extent is ±circumradius (distance to points)
    min_x = center_x - apothem
    max_x = center_x + apothem
    min_y = center_y - circumradius
    max_y = center_y + circumradius

    return (min_x, min_y, max_x, max_y)
