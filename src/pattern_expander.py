"""Pattern expansion utilities for G-code generation.

Expands pattern definitions (linear, grid) into individual coordinates.
"""
from typing import List, Tuple, Dict, Any


def expand_linear_pattern(
    start_x: float,
    start_y: float,
    axis: str,
    spacing: float,
    count: int
) -> List[Tuple[float, float]]:
    """
    Expand a linear pattern into individual points.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        axis: Pattern axis ('x' or 'y')
        spacing: Distance between points
        count: Number of points

    Returns:
        List of (x, y) coordinate tuples
    """
    points = []
    for i in range(count):
        if axis.lower() == 'x':
            points.append((start_x + i * spacing, start_y))
        else:
            points.append((start_x, start_y + i * spacing))
    return points


def expand_grid_pattern(
    start_x: float,
    start_y: float,
    x_spacing: float,
    y_spacing: float,
    x_count: int,
    y_count: int
) -> List[Tuple[float, float]]:
    """
    Expand a grid pattern into individual points.

    Points are generated row by row (Y-major order).

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        x_spacing: Spacing between columns
        y_spacing: Spacing between rows
        x_count: Number of columns
        y_count: Number of rows

    Returns:
        List of (x, y) coordinate tuples
    """
    points = []
    for row in range(y_count):
        for col in range(x_count):
            x = start_x + col * x_spacing
            y = start_y + row * y_spacing
            points.append((x, y))
    return points


def expand_drill_operations(operations: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    """
    Expand all drill operations to individual points.

    Args:
        operations: List of drill operation dicts from project.operations['drill_holes']

    Returns:
        List of (x, y) coordinate tuples for all drill points
    """
    points = []

    for op in operations:
        op_type = op.get('type', 'single')

        if op_type == 'single':
            points.append((op['x'], op['y']))

        elif op_type == 'pattern_linear':
            expanded = expand_linear_pattern(
                op['start_x'], op['start_y'],
                op['axis'], op['spacing'], op['count']
            )
            points.extend(expanded)

        elif op_type == 'pattern_grid':
            expanded = expand_grid_pattern(
                op['start_x'], op['start_y'],
                op['x_spacing'], op['y_spacing'],
                op['x_count'], op['y_count']
            )
            points.extend(expanded)

    return points


def expand_circular_operations(operations: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """
    Expand all circular cut operations.

    Args:
        operations: List of circular cut dicts from project.operations['circular_cuts']

    Returns:
        List of dicts with 'center_x', 'center_y', 'diameter', and lead-in settings
    """
    circles = []

    for op in operations:
        op_type = op.get('type', 'single')

        # Extract lead-in settings that should be preserved when expanding
        lead_in_settings = {
            'lead_in_mode': op.get('lead_in_mode', 'auto'),
            'lead_in_type': op.get('lead_in_type', 'helical'),
            'lead_in_approach_angle': op.get('lead_in_approach_angle', 90)
        }

        if op_type == 'single':
            circles.append({
                'center_x': op['center_x'],
                'center_y': op['center_y'],
                'diameter': op['diameter'],
                'compensation': op.get('compensation', 'interior'),
                **lead_in_settings
            })

        elif op_type == 'pattern_linear':
            centers = expand_linear_pattern(
                op['start_center_x'], op['start_center_y'],
                op['axis'], op['spacing'], op['count']
            )
            for cx, cy in centers:
                circles.append({
                    'center_x': cx,
                    'center_y': cy,
                    'diameter': op['diameter'],
                    'compensation': op.get('compensation', 'interior'),
                    **lead_in_settings
                })

    return circles


def expand_hexagonal_operations(operations: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """
    Expand all hexagonal cut operations.

    Args:
        operations: List of hexagonal cut dicts from project.operations['hexagonal_cuts']

    Returns:
        List of dicts with 'center_x', 'center_y', 'flat_to_flat', and lead-in settings
    """
    hexagons = []

    for op in operations:
        op_type = op.get('type', 'single')

        # Extract lead-in settings that should be preserved when expanding
        lead_in_settings = {
            'lead_in_mode': op.get('lead_in_mode', 'auto'),
            'lead_in_type': op.get('lead_in_type', 'helical'),
            'lead_in_approach_angle': op.get('lead_in_approach_angle', 90)
        }

        if op_type == 'single':
            hexagons.append({
                'center_x': op['center_x'],
                'center_y': op['center_y'],
                'flat_to_flat': op['flat_to_flat'],
                'compensation': op.get('compensation', 'interior'),
                **lead_in_settings
            })

        elif op_type == 'pattern_linear':
            centers = expand_linear_pattern(
                op['start_center_x'], op['start_center_y'],
                op['axis'], op['spacing'], op['count']
            )
            for cx, cy in centers:
                hexagons.append({
                    'center_x': cx,
                    'center_y': cy,
                    'flat_to_flat': op['flat_to_flat'],
                    'compensation': op.get('compensation', 'interior'),
                    **lead_in_settings
                })

    return hexagons


def expand_all_operations(operations: Dict[str, List]) -> Dict[str, List]:
    """
    Expand all operations in a project.

    Args:
        operations: Project operations dict with drill_holes, circular_cuts,
                   hexagonal_cuts, and line_cuts

    Returns:
        Dict with expanded operations:
        - drill_points: List of (x, y) tuples
        - circular_cuts: List of dicts with center_x, center_y, diameter
        - hexagonal_cuts: List of dicts with center_x, center_y, flat_to_flat
        - line_cuts: List of line cut dicts (unchanged)
    """
    return {
        'drill_points': expand_drill_operations(operations.get('drill_holes', [])),
        'circular_cuts': expand_circular_operations(operations.get('circular_cuts', [])),
        'hexagonal_cuts': expand_hexagonal_operations(operations.get('hexagonal_cuts', [])),
        'line_cuts': operations.get('line_cuts', [])  # Line cuts don't need expansion
    }
