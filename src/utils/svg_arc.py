"""
SVG Arc Calculation Module

Converts CNC arc specifications to SVG arc parameters.

CNC Arc Definition (what the user specifies):
    - Start point (from path)
    - End point (from path)
    - Center point (arc_center_x, arc_center_y)
    - Direction: CW or CCW

That's it. These 4 things uniquely define an arc.

SVG Arc Definition (what SVG needs):
    A rx ry x-rotation large-arc-flag sweep-flag x y

SVG uses radius + flags instead of a center point, so we must convert.
The large_arc_flag is NOT user input - it's calculated from the angular span.

Coordinate Systems and Y-Inversion:
    - CNC: Y-up (standard math coordinates)
    - SVG: Y-down (screen coordinates)
    - When we convert CNC to SVG, we flip Y: svg_y = height - cnc_y

This Y flip in the COORDINATES (not the direction) means:
    - A CCW arc in CNC, when drawn with flipped Y coords, needs sweep=0 to look correct
    - A CW arc in CNC, when drawn with flipped Y coords, needs sweep=1 to look correct

The key insight: we flip the Y coordinates of all points, but we DON'T flip the
direction interpretation. The sweep_flag tells SVG which way to curve, and since
our points are already Y-flipped, we use sweep=0 for CCW and sweep=1 for CW.
"""

import math
from typing import Tuple, Optional


def calculate_arc_angular_span(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    center_x: float, center_y: float,
    clockwise: bool
) -> float:
    """
    Calculate the angular span of an arc in degrees.

    Args:
        start_x, start_y: Arc start point
        end_x, end_y: Arc end point
        center_x, center_y: Arc center
        clockwise: True for CW, False for CCW (in the coordinate system of the points)

    Returns:
        Angular span in degrees (always positive, 0-360)
    """
    # Calculate angles from center to start and end points
    start_angle = math.atan2(start_y - center_y, start_x - center_x)
    end_angle = math.atan2(end_y - center_y, end_x - center_x)

    # Calculate the angular difference
    if clockwise:
        # CW: subtract end from start (going backwards in angle)
        span = start_angle - end_angle
    else:
        # CCW: subtract start from end (going forwards in angle)
        span = end_angle - start_angle

    # Normalize to 0-360 range
    span_degrees = math.degrees(span)
    if span_degrees <= 0:
        span_degrees += 360

    return span_degrees


def calculate_svg_arc_flags(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    center_x: float, center_y: float,
    arc_direction: Optional[str] = None
) -> Tuple[int, int]:
    """
    Calculate SVG arc flags from CNC arc parameters.

    The user only specifies center + direction. The large_arc_flag is
    calculated automatically based on the angular span of the arc.

    Args:
        start_x, start_y: Arc start point (CNC coordinates)
        end_x, end_y: Arc end point (CNC coordinates)
        center_x, center_y: Arc center (CNC coordinates)
        arc_direction: 'cw', 'ccw', or None/'' for auto-detect (short path)

    Returns:
        Tuple of (large_arc_flag, sweep_flag) for SVG arc command
    """
    arc_dir = (arc_direction or '').lower()

    # Determine the CNC direction
    if arc_dir == 'ccw':
        cw_in_cnc = False
    elif arc_dir == 'cw':
        cw_in_cnc = True
    else:
        # Auto-detect: choose the shorter path
        # Calculate which direction gives the shorter arc
        ccw_span = calculate_arc_angular_span(
            start_x, start_y, end_x, end_y, center_x, center_y, clockwise=False
        )
        cw_span = calculate_arc_angular_span(
            start_x, start_y, end_x, end_y, center_x, center_y, clockwise=True
        )
        cw_in_cnc = cw_span < ccw_span

    # Calculate the angular span for the chosen direction
    span = calculate_arc_angular_span(
        start_x, start_y, end_x, end_y, center_x, center_y, clockwise=cw_in_cnc
    )

    # SVG sweep_flag: accounts for Y-axis inversion between CNC and SVG
    # In SVG's Y-down space, sweep=0 draws CCW on screen, sweep=1 draws CW on screen
    # But our Y is flipped in the conversion, so:
    # CCW in CNC (Y-up) = CCW visually on screen = sweep_flag 0
    # CW in CNC (Y-up) = CW visually on screen = sweep_flag 1
    sweep_flag = 1 if cw_in_cnc else 0

    # large_arc_flag: 1 if arc > 180°, 0 if arc <= 180°
    # This is purely geometric - derived from center + direction
    large_arc_flag = 1 if span > 180 else 0

    return large_arc_flag, sweep_flag


def calculate_arc_radius(
    point_x: float, point_y: float,
    center_x: float, center_y: float
) -> float:
    """Calculate the radius of an arc from a point to its center."""
    return math.sqrt((point_x - center_x) ** 2 + (point_y - center_y) ** 2)


def cnc_to_svg_coords(
    x: float, y: float,
    height: float,
    scale: float = 1.0,
    padding: float = 0.0
) -> Tuple[float, float]:
    """
    Convert CNC coordinates to SVG coordinates.

    Args:
        x, y: CNC coordinates (Y-up)
        height: The height of the CNC workspace
        scale: Scale factor for the conversion
        padding: Padding to add to the coordinates

    Returns:
        Tuple of (svg_x, svg_y) in SVG coordinates (Y-down)
    """
    svg_x = padding + x * scale
    svg_y = padding + (height - y) * scale
    return svg_x, svg_y


def generate_svg_arc_command(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    center_x: float, center_y: float,
    arc_direction: Optional[str] = None,
    height: float = 0.0,
    scale: float = 1.0,
    padding: float = 0.0
) -> str:
    """
    Generate a complete SVG arc path command from CNC arc parameters.

    Args:
        start_x, start_y: Arc start point in CNC coordinates
        end_x, end_y: Arc end point in CNC coordinates
        center_x, center_y: Arc center in CNC coordinates
        arc_direction: 'cw', 'ccw', or None for auto-detect
        height: CNC workspace height (for Y inversion)
        scale: Scale factor
        padding: Padding offset

    Returns:
        SVG arc command string (e.g., "A 0.25 0.25 0 0 1 100.5 200.3")
    """
    # Convert points to SVG coordinates for radius calculation and endpoint
    svg_start_x, svg_start_y = cnc_to_svg_coords(start_x, start_y, height, scale, padding)
    svg_end_x, svg_end_y = cnc_to_svg_coords(end_x, end_y, height, scale, padding)
    svg_center_x, svg_center_y = cnc_to_svg_coords(center_x, center_y, height, scale, padding)

    # Calculate radius in SVG space
    radius = calculate_arc_radius(svg_start_x, svg_start_y, svg_center_x, svg_center_y)

    # Calculate arc flags using CNC coordinates (handles Y inversion internally)
    large_arc_flag, sweep_flag = calculate_svg_arc_flags(
        start_x, start_y, end_x, end_y, center_x, center_y, arc_direction
    )

    return f"A {radius:.4f} {radius:.4f} 0 {large_arc_flag} {sweep_flag} {svg_end_x:.4f} {svg_end_y:.4f}"
