"""Tube void detection and filtering utilities.

For tube stock, operations falling entirely within the hollow center should be skipped.
"""
from typing import List, Tuple, Dict, Any, Optional


def calculate_void_bounds(
    outer_width: float,
    outer_height: float,
    wall_thickness: float
) -> Tuple[float, float, float, float]:
    """
    Calculate the void (hollow) region bounds for tube stock.

    Args:
        outer_width: Tube outer width (inches)
        outer_height: Tube outer height (inches)
        wall_thickness: Tube wall thickness (inches)

    Returns:
        Tuple of (void_x_min, void_y_min, void_x_max, void_y_max)
    """
    void_x_min = wall_thickness
    void_y_min = wall_thickness
    void_x_max = outer_width - wall_thickness
    void_y_max = outer_height - wall_thickness

    return (void_x_min, void_y_min, void_x_max, void_y_max)


def point_in_void(
    x: float,
    y: float,
    void_bounds: Tuple[float, float, float, float],
    tool_radius: float = 0
) -> bool:
    """
    Check if a point (with tool radius) falls entirely within the tube void.

    Args:
        x: Point X coordinate
        y: Point Y coordinate
        void_bounds: Tuple of (void_x_min, void_y_min, void_x_max, void_y_max)
        tool_radius: Tool radius for compensation (optional)

    Returns:
        True if point is entirely within the void
    """
    void_x_min, void_y_min, void_x_max, void_y_max = void_bounds

    # Point with tool radius must be entirely inside void
    return (
        x - tool_radius > void_x_min and
        x + tool_radius < void_x_max and
        y - tool_radius > void_y_min and
        y + tool_radius < void_y_max
    )


def circle_in_void(
    center_x: float,
    center_y: float,
    diameter: float,
    void_bounds: Tuple[float, float, float, float],
    tool_diameter: float = 0
) -> bool:
    """
    Check if a circular cut falls entirely within the tube void.

    Args:
        center_x: Circle center X
        center_y: Circle center Y
        diameter: Circle diameter
        void_bounds: Tuple of (void_x_min, void_y_min, void_x_max, void_y_max)
        tool_diameter: Tool diameter for compensation

    Returns:
        True if circle is entirely within the void
    """
    # The actual cut radius (outer edge of the cut)
    cut_outer_radius = diameter / 2

    return point_in_void(
        center_x, center_y,
        void_bounds,
        tool_radius=cut_outer_radius
    )


def hexagon_in_void(
    center_x: float,
    center_y: float,
    flat_to_flat: float,
    void_bounds: Tuple[float, float, float, float],
    tool_diameter: float = 0
) -> bool:
    """
    Check if a hexagonal cut falls entirely within the tube void.

    Args:
        center_x: Hexagon center X
        center_y: Hexagon center Y
        flat_to_flat: Hexagon flat-to-flat distance
        void_bounds: Tuple of (void_x_min, void_y_min, void_x_max, void_y_max)
        tool_diameter: Tool diameter for compensation

    Returns:
        True if hexagon is entirely within the void
    """
    import math

    # For a point-up hexagon, circumradius extends further than apothem
    circumradius = flat_to_flat / math.sqrt(3)

    return point_in_void(
        center_x, center_y,
        void_bounds,
        tool_radius=circumradius
    )


def filter_drill_points(
    points: List[Tuple[float, float]],
    void_bounds: Tuple[float, float, float, float],
    tool_diameter: float
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Filter drill points, separating those in void from those on material.

    Args:
        points: List of (x, y) drill point coordinates
        void_bounds: Void region bounds
        tool_diameter: Drill diameter

    Returns:
        Tuple of (valid_points, skipped_points)
    """
    valid = []
    skipped = []
    tool_radius = tool_diameter / 2

    for point in points:
        x, y = point
        if point_in_void(x, y, void_bounds, tool_radius):
            skipped.append(point)
        else:
            valid.append(point)

    return valid, skipped


def filter_circular_cuts(
    cuts: List[Dict[str, float]],
    void_bounds: Tuple[float, float, float, float],
    tool_diameter: float
) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    """
    Filter circular cuts, separating those in void from those on material.

    Args:
        cuts: List of circular cut dicts with center_x, center_y, diameter
        void_bounds: Void region bounds
        tool_diameter: End mill diameter

    Returns:
        Tuple of (valid_cuts, skipped_cuts)
    """
    valid = []
    skipped = []

    for cut in cuts:
        if circle_in_void(
            cut['center_x'], cut['center_y'],
            cut['diameter'],
            void_bounds,
            tool_diameter
        ):
            skipped.append(cut)
        else:
            valid.append(cut)

    return valid, skipped


def filter_hexagonal_cuts(
    cuts: List[Dict[str, float]],
    void_bounds: Tuple[float, float, float, float],
    tool_diameter: float
) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    """
    Filter hexagonal cuts, separating those in void from those on material.

    Args:
        cuts: List of hexagonal cut dicts with center_x, center_y, flat_to_flat
        void_bounds: Void region bounds
        tool_diameter: End mill diameter

    Returns:
        Tuple of (valid_cuts, skipped_cuts)
    """
    valid = []
    skipped = []

    for cut in cuts:
        if hexagon_in_void(
            cut['center_x'], cut['center_y'],
            cut['flat_to_flat'],
            void_bounds,
            tool_diameter
        ):
            skipped.append(cut)
        else:
            valid.append(cut)

    return valid, skipped


def filter_operations_for_tube(
    expanded_ops: Dict[str, List],
    material,
    drill_diameter: Optional[float] = None,
    end_mill_diameter: Optional[float] = None
) -> Dict[str, Any]:
    """
    Filter all expanded operations for tube material, removing void operations.

    Args:
        expanded_ops: Dict with drill_points, circular_cuts, hexagonal_cuts, line_cuts
        material: Material object with outer_width, outer_height, wall_thickness
        drill_diameter: Drill tool diameter (for drill operations)
        end_mill_diameter: End mill diameter (for cut operations)

    Returns:
        Dict with filtered operations and skipped counts
    """
    if material.form != 'tube':
        return {
            **expanded_ops,
            'skipped_drill_points': [],
            'skipped_circular_cuts': [],
            'skipped_hexagonal_cuts': []
        }

    void_bounds = calculate_void_bounds(
        material.outer_width,
        material.outer_height,
        material.wall_thickness
    )

    result = {
        'line_cuts': expanded_ops.get('line_cuts', []),  # Line cuts not filtered
        'skipped_drill_points': [],
        'skipped_circular_cuts': [],
        'skipped_hexagonal_cuts': []
    }

    # Filter drill points
    if drill_diameter:
        valid_drills, skipped_drills = filter_drill_points(
            expanded_ops.get('drill_points', []),
            void_bounds,
            drill_diameter
        )
        result['drill_points'] = valid_drills
        result['skipped_drill_points'] = skipped_drills
    else:
        result['drill_points'] = expanded_ops.get('drill_points', [])

    # Filter circular cuts
    if end_mill_diameter:
        valid_circles, skipped_circles = filter_circular_cuts(
            expanded_ops.get('circular_cuts', []),
            void_bounds,
            end_mill_diameter
        )
        result['circular_cuts'] = valid_circles
        result['skipped_circular_cuts'] = skipped_circles

        valid_hexes, skipped_hexes = filter_hexagonal_cuts(
            expanded_ops.get('hexagonal_cuts', []),
            void_bounds,
            end_mill_diameter
        )
        result['hexagonal_cuts'] = valid_hexes
        result['skipped_hexagonal_cuts'] = skipped_hexes
    else:
        result['circular_cuts'] = expanded_ops.get('circular_cuts', [])
        result['hexagonal_cuts'] = expanded_ops.get('hexagonal_cuts', [])

    return result
