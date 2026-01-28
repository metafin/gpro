"""Coordinate and parameter validation utilities."""
import math
from typing import List, Tuple, Dict, Optional


def validate_bounds(
    x: float,
    y: float,
    max_x: float,
    max_y: float
) -> bool:
    """
    Check if a point is within machine bounds.

    Args:
        x: X coordinate
        y: Y coordinate
        max_x: Maximum X travel
        max_y: Maximum Y travel

    Returns:
        True if point is within bounds
    """
    return 0 <= x <= max_x and 0 <= y <= max_y


def validate_all_points(
    points: List[Tuple[float, float]],
    max_x: float,
    max_y: float
) -> List[str]:
    """
    Validate all points are within machine bounds.

    Args:
        points: List of (x, y) coordinate tuples
        max_x: Maximum X travel
        max_y: Maximum Y travel

    Returns:
        List of error messages for out-of-bounds points (empty if all valid)
    """
    errors = []
    for x, y in points:
        if x < 0:
            errors.append(f"Point ({x}, {y}) has negative X coordinate")
        elif x > max_x:
            errors.append(f"Point ({x}, {y}) exceeds max X ({max_x})")

        if y < 0:
            errors.append(f"Point ({y}, {y}) has negative Y coordinate")
        elif y > max_y:
            errors.append(f"Point ({x}, {y}) exceeds max Y ({max_y})")

    return errors


def validate_tool_in_standards(
    tool_type: str,
    size: float,
    gcode_standards: Dict
) -> bool:
    """
    Check if G-code parameters exist for a tool type and size.

    Args:
        tool_type: Tool type ('drill', 'end_mill_1flute', 'end_mill_2flute')
        size: Tool diameter
        gcode_standards: Material's gcode_standards dict

    Returns:
        True if parameters exist for this tool
    """
    if not gcode_standards:
        return False

    tool_standards = gcode_standards.get(tool_type, {})
    size_key = str(size)

    return size_key in tool_standards


def validate_circle_bounds(
    center_x: float,
    center_y: float,
    diameter: float,
    max_x: float,
    max_y: float
) -> List[str]:
    """
    Validate a circle is within machine bounds.

    Args:
        center_x: Circle center X
        center_y: Circle center Y
        diameter: Circle diameter
        max_x: Maximum X travel
        max_y: Maximum Y travel

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    radius = diameter / 2

    if center_x - radius < 0:
        errors.append(f"Circle at ({center_x}, {center_y}) extends past X=0")
    if center_x + radius > max_x:
        errors.append(f"Circle at ({center_x}, {center_y}) extends past X={max_x}")
    if center_y - radius < 0:
        errors.append(f"Circle at ({center_x}, {center_y}) extends past Y=0")
    if center_y + radius > max_y:
        errors.append(f"Circle at ({center_x}, {center_y}) extends past Y={max_y}")

    return errors


def validate_hexagon_bounds(
    center_x: float,
    center_y: float,
    flat_to_flat: float,
    max_x: float,
    max_y: float
) -> List[str]:
    """
    Validate a hexagon is within machine bounds.

    For a point-up hexagon, the circumradius extends further in Y than X.

    Args:
        center_x: Hexagon center X
        center_y: Hexagon center Y
        flat_to_flat: Distance between parallel flats
        max_x: Maximum X travel
        max_y: Maximum Y travel

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    apothem = flat_to_flat / 2
    circumradius = flat_to_flat / math.sqrt(3)

    # X extent is the apothem (distance to flat)
    if center_x - apothem < 0:
        errors.append(f"Hexagon at ({center_x}, {center_y}) extends past X=0")
    if center_x + apothem > max_x:
        errors.append(f"Hexagon at ({center_x}, {center_y}) extends past X={max_x}")

    # Y extent is the circumradius (distance to vertex)
    if center_y - circumradius < 0:
        errors.append(f"Hexagon at ({center_x}, {center_y}) extends past Y=0")
    if center_y + circumradius > max_y:
        errors.append(f"Hexagon at ({center_x}, {center_y}) extends past Y={max_y}")

    return errors


def validate_arc_geometry(
    path: List[Dict],
    tolerance: float = 0.001
) -> List[str]:
    """
    Validate arc geometry in a line path.

    Checks that arc endpoints are equidistant from the arc center.
    Invalid arcs will cause discontinuities in tool-compensated paths.

    Args:
        path: List of point dicts with x, y, and optional arc properties
        tolerance: Maximum allowed difference in radii (inches)

    Returns:
        List of warning messages for invalid arcs (empty if all valid)
    """
    warnings = []

    for i, point in enumerate(path):
        if point.get('line_type') != 'arc':
            continue

        # Get arc center
        center_x = point.get('arc_center_x')
        center_y = point.get('arc_center_y')

        if center_x is None or center_y is None:
            warnings.append(f"Arc at point {i} is missing center coordinates")
            continue

        # Get start point (previous point in path)
        if i == 0:
            warnings.append(f"Arc at point {i}: arc cannot be the first point in path")
            continue

        start = path[i - 1]
        start_x = start.get('x', 0)
        start_y = start.get('y', 0)

        # Get end point (current point)
        end_x = point.get('x', 0)
        end_y = point.get('y', 0)

        # Calculate radii
        start_radius = math.sqrt(
            (start_x - center_x) ** 2 + (start_y - center_y) ** 2
        )
        end_radius = math.sqrt(
            (end_x - center_x) ** 2 + (end_y - center_y) ** 2
        )

        # Check if radii match
        radius_diff = abs(start_radius - end_radius)
        if radius_diff > tolerance:
            warnings.append(
                f"Arc from ({start_x}, {start_y}) to ({end_x}, {end_y}) has invalid geometry: "
                f"start is {start_radius:.4f}\" from center ({center_x}, {center_y}), "
                f"but end is {end_radius:.4f}\" from center. "
                f"Difference of {radius_diff:.4f}\" exceeds tolerance of {tolerance}\". "
                f"This will cause discontinuities in tool-compensated paths."
            )

    return warnings


def validate_stepdown(
    pass_depth: float,
    tool_diameter: float,
    max_stepdown_factor: float = 0.5
) -> Tuple[List[str], List[str]]:
    """
    Validate stepdown (pass depth) against tool diameter.

    Aggressive stepdowns can break end mills. This function checks:
    - ERROR if pass_depth > tool_diameter (blocks generation)
    - WARNING if pass_depth > tool_diameter * max_stepdown_factor

    Args:
        pass_depth: Depth per pass (inches)
        tool_diameter: End mill diameter (inches)
        max_stepdown_factor: Maximum safe ratio of pass_depth to tool_diameter

    Returns:
        Tuple of (errors, warnings) lists
    """
    errors = []
    warnings = []

    if pass_depth <= 0 or tool_diameter <= 0:
        return errors, warnings

    ratio = pass_depth / tool_diameter

    if ratio > 1.0:
        errors.append(
            f"Pass depth ({pass_depth:.4f}\") exceeds tool diameter ({tool_diameter:.4f}\"). "
            f"This will almost certainly break the end mill. Reduce pass depth."
        )
    elif ratio > max_stepdown_factor:
        warnings.append(
            f"Pass depth ({pass_depth:.4f}\") is {ratio * 100:.0f}% of tool diameter ({tool_diameter:.4f}\"). "
            f"Recommended maximum is {max_stepdown_factor * 100:.0f}%. "
            f"Consider reducing pass depth to avoid tool breakage."
        )

    return errors, warnings


def validate_feed_rates(
    feed_rate: float,
    plunge_rate: float
) -> List[str]:
    """
    Validate feed rate and plunge rate relationship.

    Plunge rate typically should not exceed feed rate.

    Args:
        feed_rate: Cutting feed rate (in/min)
        plunge_rate: Plunge feed rate (in/min)

    Returns:
        List of warning messages
    """
    warnings = []

    if plunge_rate > feed_rate:
        warnings.append(
            f"Plunge rate ({plunge_rate} in/min) exceeds feed rate ({feed_rate} in/min). "
            f"Verify this is intentional for your material and tool."
        )

    return warnings
