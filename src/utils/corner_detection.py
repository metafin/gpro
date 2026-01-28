"""Corner detection and feed rate reduction utilities.

Implements corner slowdown to reduce stress on end mills when cutting
sharp direction changes. Sharp corners require reduced feed to prevent
tool deflection and improve cut quality.
"""
import math
from typing import List, Tuple, Optional, Dict


def calculate_segment_angle(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float]
) -> float:
    """
    Calculate the angle (in degrees) between two consecutive line segments.

    The angle is measured at p2, between vectors (p1->p2) and (p2->p3).
    Returns the deviation from straight (180° = straight line, 90° = right angle).

    Args:
        p1: Start point of first segment (x, y)
        p2: Shared point (corner location) (x, y)
        p3: End point of second segment (x, y)

    Returns:
        Angle in degrees (0-180). 180 = straight, 90 = right angle, 60 = sharp turn
    """
    # Vector from p1 to p2
    v1x = p2[0] - p1[0]
    v1y = p2[1] - p1[1]

    # Vector from p2 to p3
    v2x = p3[0] - p2[0]
    v2y = p3[1] - p2[1]

    # Calculate magnitudes
    mag1 = math.sqrt(v1x * v1x + v1y * v1y)
    mag2 = math.sqrt(v2x * v2x + v2y * v2y)

    if mag1 < 0.0001 or mag2 < 0.0001:
        return 180.0  # Degenerate case - treat as straight

    # Dot product gives cos(angle)
    dot = v1x * v2x + v1y * v2y
    cos_angle = dot / (mag1 * mag2)

    # Clamp to valid range for acos
    cos_angle = max(-1.0, min(1.0, cos_angle))

    # Convert to degrees
    angle = math.degrees(math.acos(cos_angle))

    return angle


def get_arc_tangent_at_point(
    center: Tuple[float, float],
    point: Tuple[float, float],
    direction: str
) -> Tuple[float, float]:
    """
    Get the tangent direction at a point on an arc.

    The tangent is perpendicular to the radius at that point.
    Direction determines which way the tangent points (CW vs CCW travel).

    Args:
        center: Arc center (x, y)
        point: Point on the arc (x, y)
        direction: 'G02' for CW, 'G03' for CCW

    Returns:
        Unit tangent vector (dx, dy)
    """
    # Radius vector from center to point
    rx = point[0] - center[0]
    ry = point[1] - center[1]

    # Tangent is perpendicular to radius
    # For CCW (G03): tangent = (-ry, rx) (90° counter-clockwise from radius)
    # For CW (G02): tangent = (ry, -rx) (90° clockwise from radius)
    if direction == 'G03':
        tx, ty = -ry, rx
    else:  # G02
        tx, ty = ry, -rx

    # Normalize
    mag = math.sqrt(tx * tx + ty * ty)
    if mag < 0.0001:
        return (1.0, 0.0)  # Default direction

    return (tx / mag, ty / mag)


def calculate_direction_vector(
    p1: Tuple[float, float],
    p2: Tuple[float, float]
) -> Tuple[float, float]:
    """
    Calculate unit direction vector from p1 to p2.

    Args:
        p1: Start point (x, y)
        p2: End point (x, y)

    Returns:
        Unit direction vector (dx, dy)
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    mag = math.sqrt(dx * dx + dy * dy)
    if mag < 0.0001:
        return (1.0, 0.0)  # Default direction

    return (dx / mag, dy / mag)


def angle_between_vectors(
    v1: Tuple[float, float],
    v2: Tuple[float, float]
) -> float:
    """
    Calculate angle between two direction vectors in degrees.

    Args:
        v1: First unit vector (dx, dy)
        v2: Second unit vector (dx, dy)

    Returns:
        Angle in degrees (0-180)
    """
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def identify_corners(
    path: List[Dict],
    angle_threshold: float = 120.0
) -> List[Dict]:
    """
    Identify sharp corners in a line path.

    A corner is where consecutive segments change direction by more than
    the threshold. Returns information about each corner including its
    location and severity.

    Args:
        path: List of path points with 'x', 'y', 'line_type', and optional arc data
        angle_threshold: Maximum angle (degrees) to consider "sharp" (default 120)

    Returns:
        List of corner dicts with: index, x, y, angle, incoming_direction, outgoing_direction
    """
    if len(path) < 3:
        return []

    corners = []

    for i in range(1, len(path) - 1):
        prev_point = path[i - 1]
        curr_point = path[i]
        next_point = path[i + 1]

        p1 = (prev_point.get('x', 0), prev_point.get('y', 0))
        p2 = (curr_point.get('x', 0), curr_point.get('y', 0))
        p3 = (next_point.get('x', 0), next_point.get('y', 0))

        # Get incoming direction
        curr_type = curr_point.get('line_type', 'straight')
        if curr_type == 'arc' and 'arc_center_x' in curr_point:
            # Incoming is an arc - use tangent at endpoint
            center = (curr_point['arc_center_x'], curr_point['arc_center_y'])
            arc_dir = curr_point.get('arc_direction', 'G02')
            if arc_dir.lower() == 'ccw':
                arc_dir = 'G03'
            elif arc_dir.lower() == 'cw':
                arc_dir = 'G02'
            incoming = get_arc_tangent_at_point(center, p2, arc_dir)
        else:
            # Incoming is a line - direction from p1 to p2
            incoming = calculate_direction_vector(p1, p2)

        # Get outgoing direction
        next_type = next_point.get('line_type', 'straight')
        if next_type == 'arc' and 'arc_center_x' in next_point:
            # Outgoing is an arc - use tangent at start point
            center = (next_point['arc_center_x'], next_point['arc_center_y'])
            arc_dir = next_point.get('arc_direction', 'G02')
            if arc_dir.lower() == 'ccw':
                arc_dir = 'G03'
            elif arc_dir.lower() == 'cw':
                arc_dir = 'G02'
            outgoing = get_arc_tangent_at_point(center, p2, arc_dir)
        else:
            # Outgoing is a line - direction from p2 to p3
            outgoing = calculate_direction_vector(p2, p3)

        # Calculate angle between directions
        angle = angle_between_vectors(incoming, outgoing)

        # If angle exceeds threshold, this is a sharp corner
        if angle < angle_threshold:
            corners.append({
                'index': i,
                'x': p2[0],
                'y': p2[1],
                'angle': angle,
                'incoming': incoming,
                'outgoing': outgoing
            })

    return corners


def calculate_corner_feed_factor(angle: float) -> float:
    """
    Calculate feed rate factor based on corner angle.

    Sharper angles require more aggressive feed reduction to prevent
    tool stress and maintain cut quality.

    Angle ranges:
    - 90-120°: Mild corner, 75% feed
    - 60-90°: Moderate corner, 50% feed
    - 30-60°: Sharp corner, 40% feed
    - <30°: Very sharp, 30% feed

    Args:
        angle: Corner angle in degrees (0 = full reversal, 180 = straight)

    Returns:
        Feed rate factor (0.0 to 1.0)
    """
    if angle >= 120:
        return 1.0  # Not a corner, full feed
    elif angle >= 90:
        return 0.75
    elif angle >= 60:
        return 0.50
    elif angle >= 30:
        return 0.40
    else:
        return 0.30


def generate_corner_slowdown_points(
    path: List[Dict],
    angle_threshold: float = 120.0,
    approach_distance: float = 0.05,
    base_feed_factor: float = 0.5
) -> List[Dict]:
    """
    Generate additional path points for corner slowdown.

    Inserts deceleration and acceleration points before and after
    sharp corners to smoothly reduce and restore feed rate.

    Args:
        path: Original path points
        angle_threshold: Angle below which corners need slowdown
        approach_distance: Distance from corner to start/end slowdown
        base_feed_factor: Base corner feed factor (further modified by angle)

    Returns:
        New path with slowdown points inserted (includes 'corner_feed_factor' key)
    """
    if len(path) < 3:
        # Return original path with feed factors of 1.0
        result = []
        for p in path:
            new_p = dict(p)
            new_p['corner_feed_factor'] = 1.0
            result.append(new_p)
        return result

    # Find all corners
    corners = identify_corners(path, angle_threshold)

    if not corners:
        # No corners, return original path with feed factors of 1.0
        result = []
        for p in path:
            new_p = dict(p)
            new_p['corner_feed_factor'] = 1.0
            result.append(new_p)
        return result

    # Create corner index set for quick lookup
    corner_indices = {c['index']: c for c in corners}

    # Build new path with feed factors
    result = []
    for i, point in enumerate(path):
        new_point = dict(point)

        if i in corner_indices:
            # This is a corner point - apply reduced feed
            corner = corner_indices[i]
            angle_factor = calculate_corner_feed_factor(corner['angle'])
            new_point['corner_feed_factor'] = base_feed_factor * angle_factor
        else:
            # Normal point
            new_point['corner_feed_factor'] = 1.0

        result.append(new_point)

    return result


def get_corner_adjusted_feed(
    base_feed: float,
    point: Dict,
    corner_slowdown_enabled: bool = True,
    corner_feed_factor: float = 0.5
) -> float:
    """
    Get the feed rate for a path point, adjusted for corner slowdown.

    Args:
        base_feed: Base cutting feed rate
        point: Path point dict (may contain 'corner_feed_factor')
        corner_slowdown_enabled: Whether corner slowdown is active
        corner_feed_factor: Global corner feed factor from settings

    Returns:
        Adjusted feed rate
    """
    if not corner_slowdown_enabled:
        return base_feed

    point_factor = point.get('corner_feed_factor', 1.0)

    # Apply both the global corner factor and the point-specific factor
    if point_factor < 1.0:
        # This is a corner point
        return base_feed * corner_feed_factor * point_factor
    else:
        return base_feed
