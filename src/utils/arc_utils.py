"""Arc direction and offset calculation utilities."""
from typing import Tuple, Optional


def calculate_arc_direction(
    current: Tuple[float, float],
    destination: Tuple[float, float],
    center: Tuple[float, float],
    direction_hint: Optional[str] = None
) -> str:
    """
    Determine arc direction (G02 CW or G03 CCW) using cross product.

    Args:
        current: Current position (x, y)
        destination: Destination position (x, y)
        center: Arc center (x, y)
        direction_hint: Optional explicit direction ('cw' or 'ccw').
                       If provided, overrides the automatic calculation.
                       Useful for semicircles where cross product is 0.

    Returns:
        "G02" for clockwise, "G03" for counter-clockwise
    """
    # If explicit direction is provided, use it
    if direction_hint:
        hint_lower = direction_hint.lower()
        if hint_lower == 'cw':
            return "G02"
        elif hint_lower == 'ccw':
            return "G03"

    cx, cy = current
    dx, dy = destination
    ax, ay = center

    # Vector from center to current
    vec_to_current_x = cx - ax
    vec_to_current_y = cy - ay

    # Vector from center to destination
    vec_to_dest_x = dx - ax
    vec_to_dest_y = dy - ay

    # Cross product (2D): determines if destination is CW or CCW from current
    # Positive cross product = CCW rotation, Negative = CW rotation
    cross = vec_to_current_x * vec_to_dest_y - vec_to_current_y * vec_to_dest_x

    if cross > 0:
        return "G03"  # Counter-clockwise
    else:
        return "G02"  # Clockwise


def calculate_ij_offsets(
    current: Tuple[float, float],
    center: Tuple[float, float]
) -> Tuple[float, float]:
    """
    Calculate I, J offsets for arc commands.

    I and J are the offsets from the current position to the arc center.

    Args:
        current: Current position (x, y)
        center: Arc center (x, y)

    Returns:
        Tuple of (I, J) offsets
    """
    cx, cy = current
    ax, ay = center

    i = ax - cx
    j = ay - cy

    return (i, j)
