"""Tool compensation utilities for offset calculations."""
import math
from typing import List, Tuple, Dict, Optional

from ..hexagon_generator import calculate_hexagon_vertices


def get_compensation_offset(tool_diameter: float, compensation: str) -> float:
    """
    Get the radial offset for tool compensation.

    This is the core abstraction for applying compensation to any shape.
    The offset is added to the feature radius to get the toolpath radius.

    Args:
        tool_diameter: Tool diameter (inches)
        compensation: "none", "interior", or "exterior"

    Returns:
        Offset amount:
        - 0 for 'none' (tool center follows the path)
        - -tool_radius for 'interior' (shrink path, cut inside)
        - +tool_radius for 'exterior' (expand path, cut outside)
    """
    tool_radius = tool_diameter / 2
    if compensation == 'interior':
        return -tool_radius
    elif compensation == 'exterior':
        return tool_radius
    return 0.0


def calculate_cut_radius(
    feature_diameter: float,
    tool_diameter: float,
    compensation: str = 'interior'
) -> float:
    """
    Calculate the radius for circular cuts with tool compensation.

    Args:
        feature_diameter: Desired hole/feature diameter (inches)
        tool_diameter: Tool diameter (inches)
        compensation: "none", "interior", or "exterior"
            - "interior" (default): Tool cuts inside, resulting hole = feature_diameter
            - "exterior": Tool cuts outside, cutting out a disk of feature_diameter
            - "none": Tool center follows the feature_diameter circle

    Returns:
        Radius for the toolpath center (inches)
    """
    feature_radius = feature_diameter / 2
    offset = get_compensation_offset(tool_diameter, compensation)
    return feature_radius + offset


def offset_point_inward(
    point: Tuple[float, float],
    center: Tuple[float, float],
    offset_distance: float
) -> Tuple[float, float]:
    """
    Offset a point toward a center by a given distance.

    Args:
        point: (x, y) coordinates of the point to offset
        center: (x, y) coordinates of the center point
        offset_distance: Distance to move toward center (inches)

    Returns:
        New (x, y) coordinates after offset
    """
    px, py = point
    cx, cy = center

    # Vector from point to center
    dx = cx - px
    dy = cy - py

    # Distance from point to center
    distance = math.sqrt(dx * dx + dy * dy)

    if distance == 0:
        return point

    # Normalize and apply offset
    unit_x = dx / distance
    unit_y = dy / distance

    new_x = px + unit_x * offset_distance
    new_y = py + unit_y * offset_distance

    return (new_x, new_y)


def calculate_hexagon_compensated_vertices(
    center_x: float,
    center_y: float,
    flat_to_flat: float,
    tool_diameter: float,
    compensation: str = 'interior'
) -> List[Tuple[float, float]]:
    """
    Calculate hexagon vertices with tool radius compensation.

    Each vertex is offset along the angle bisector based on compensation type.

    Args:
        center_x: X coordinate of center
        center_y: Y coordinate of center
        flat_to_flat: Distance between parallel flat sides (inches)
        tool_diameter: Tool diameter (inches)
        compensation: "none", "interior", or "exterior"
            - "interior" (default): Tool cuts inside, resulting hex = flat_to_flat
            - "exterior": Tool cuts outside, cutting out a hex of flat_to_flat
            - "none": Tool center follows the hex vertices

    Returns:
        List of 6 compensated (x, y) vertex tuples
    """
    # Get uncompensated vertices first
    vertices = calculate_hexagon_vertices(center_x, center_y, flat_to_flat)

    if compensation == 'none':
        return vertices

    # For a regular hexagon, the offset along the angle bisector
    # is tool_radius / sin(60°) = tool_radius * 2 / sqrt(3)
    tool_radius = tool_diameter / 2
    base_offset = tool_radius * 2 / math.sqrt(3)

    # Interior: offset inward (positive offset_distance moves toward center)
    # Exterior: offset outward (negative offset_distance moves away from center)
    if compensation == 'interior':
        offset_distance = base_offset
    else:  # exterior
        offset_distance = -base_offset

    # Offset each vertex toward/away from center
    center = (center_x, center_y)
    compensated = []
    for vertex in vertices:
        comp_vertex = offset_point_inward(vertex, center, offset_distance)
        compensated.append(comp_vertex)

    return compensated


def calculate_line_normal(
    p1: Tuple[float, float],
    p2: Tuple[float, float]
) -> Tuple[float, float]:
    """
    Calculate the unit normal vector perpendicular to a line segment.

    The normal points to the left of the direction from p1 to p2.

    Args:
        p1: Start point (x, y)
        p2: End point (x, y)

    Returns:
        Unit normal vector (nx, ny)
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return (0.0, 0.0)

    # Perpendicular vector (rotate 90 degrees CCW)
    # (-dy, dx) points left of the direction vector
    nx = -dy / length
    ny = dx / length

    return (nx, ny)


def offset_line_segment(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    offset: float
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Offset a line segment perpendicular to its direction.

    Positive offset moves the segment to the left of the direction.
    Negative offset moves it to the right.

    Args:
        p1: Start point (x, y)
        p2: End point (x, y)
        offset: Distance to offset (positive = left, negative = right)

    Returns:
        Tuple of (new_p1, new_p2) offset points
    """
    nx, ny = calculate_line_normal(p1, p2)

    new_p1 = (p1[0] + nx * offset, p1[1] + ny * offset)
    new_p2 = (p2[0] + nx * offset, p2[1] + ny * offset)

    return (new_p1, new_p2)


def calculate_line_intersection(
    l1_p1: Tuple[float, float],
    l1_p2: Tuple[float, float],
    l2_p1: Tuple[float, float],
    l2_p2: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
    """
    Calculate the intersection point of two infinite lines.

    Each line is defined by two points.

    Args:
        l1_p1, l1_p2: Two points on line 1
        l2_p1, l2_p2: Two points on line 2

    Returns:
        Intersection point (x, y) or None if lines are parallel
    """
    x1, y1 = l1_p1
    x2, y2 = l1_p2
    x3, y3 = l2_p1
    x4, y4 = l2_p2

    # Line 1: (x2-x1)*y - (y2-y1)*x = (x2-x1)*y1 - (y2-y1)*x1
    # Line 2: (x4-x3)*y - (y4-y3)*x = (x4-x3)*y3 - (y4-y3)*x3

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denom) < 1e-10:
        # Lines are parallel
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom

    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)

    return (ix, iy)


def calculate_line_circle_intersection(
    line_p1: Tuple[float, float],
    line_p2: Tuple[float, float],
    center: Tuple[float, float],
    radius: float,
    prefer_near: Tuple[float, float]
) -> Optional[Tuple[float, float]]:
    """
    Find intersection between a line and a circle, preferring point nearest to prefer_near.

    Args:
        line_p1, line_p2: Two points defining the line
        center: Circle center (cx, cy)
        radius: Circle radius
        prefer_near: When two intersections exist, return the one closest to this point

    Returns:
        Intersection point (x, y) or None if no intersection
    """
    dx = line_p2[0] - line_p1[0]
    dy = line_p2[1] - line_p1[1]

    # Vector from circle center to line start
    ax = line_p1[0] - center[0]
    ay = line_p1[1] - center[1]

    # Quadratic coefficients: A*t^2 + B*t + C = 0
    A = dx * dx + dy * dy
    B = 2 * (ax * dx + ay * dy)
    C = ax * ax + ay * ay - radius * radius

    if abs(A) < 1e-10:
        return None  # Degenerate line (zero length)

    discriminant = B * B - 4 * A * C

    if discriminant < 0:
        return None  # No intersection

    sqrt_disc = math.sqrt(discriminant)
    t1 = (-B - sqrt_disc) / (2 * A)
    t2 = (-B + sqrt_disc) / (2 * A)

    # Calculate both intersection points
    p1 = (line_p1[0] + t1 * dx, line_p1[1] + t1 * dy)
    p2 = (line_p1[0] + t2 * dx, line_p1[1] + t2 * dy)

    # Return the one closest to prefer_near
    dist1 = (p1[0] - prefer_near[0])**2 + (p1[1] - prefer_near[1])**2
    dist2 = (p2[0] - prefer_near[0])**2 + (p2[1] - prefer_near[1])**2

    return p1 if dist1 <= dist2 else p2


def offset_arc_segment(
    start: Dict,
    end: Dict,
    offset: float,
    is_exterior: bool
) -> Dict:
    """
    Offset an arc segment by adjusting its radius.

    For exterior compensation, the arc radius increases.
    For interior compensation, the arc radius decreases.

    Args:
        start: Start point dict with x, y
        end: End point dict with x, y, arc_center_x, arc_center_y
        offset: Tool radius (always positive)
        is_exterior: True for exterior compensation, False for interior

    Returns:
        Modified end point dict with adjusted coordinates and center

    Raises:
        ValueError: If interior compensation would make arc radius negative
    """
    center_x = end.get('arc_center_x', 0)
    center_y = end.get('arc_center_y', 0)

    # Calculate original radius from start point to center
    dx_start = start['x'] - center_x
    dy_start = start['y'] - center_y
    original_radius = math.sqrt(dx_start * dx_start + dy_start * dy_start)

    # Determine new radius based on compensation type
    if is_exterior:
        new_radius = original_radius + offset
    else:
        new_radius = original_radius - offset
        if new_radius <= 0:
            raise ValueError(
                f"Arc radius ({original_radius:.4f}) is too small for interior "
                f"compensation with tool radius {offset:.4f}"
            )

    # Scale factor for adjusting points
    if original_radius > 0:
        scale = new_radius / original_radius
    else:
        scale = 1.0

    # Offset start point (relative to center)
    new_start_x = center_x + dx_start * scale
    new_start_y = center_y + dy_start * scale

    # Offset end point (relative to center)
    dx_end = end['x'] - center_x
    dy_end = end['y'] - center_y
    new_end_x = center_x + dx_end * scale
    new_end_y = center_y + dy_end * scale

    # Create new end point dict
    new_end = dict(end)
    new_end['x'] = new_end_x
    new_end['y'] = new_end_y
    # Center stays the same - arc just has different radius

    return new_end, (new_start_x, new_start_y)


def _is_path_closed(path: List[Dict], tolerance: float = 0.0001) -> bool:
    """
    Check if a path is closed (first and last points are the same).

    Args:
        path: List of point dicts with x, y
        tolerance: Maximum distance to consider points equal

    Returns:
        True if path is closed
    """
    if len(path) < 2:
        return False

    first = path[0]
    last = path[-1]
    dx = abs(first['x'] - last['x'])
    dy = abs(first['y'] - last['y'])
    return dx < tolerance and dy < tolerance


def calculate_path_winding(path: List[Dict]) -> float:
    """
    Calculate the winding number (signed area) of a path.

    Positive = counter-clockwise, Negative = clockwise.

    Args:
        path: List of point dicts with x, y

    Returns:
        Signed area (positive = CCW, negative = CW)
    """
    if len(path) < 3:
        return 0.0

    area = 0.0
    n = len(path)

    for i in range(n):
        j = (i + 1) % n
        area += path[i]['x'] * path[j]['y']
        area -= path[j]['x'] * path[i]['y']

    return area / 2.0


def compensate_line_path(
    path: List[Dict],
    tool_diameter: float,
    compensation_type: str
) -> List[Dict]:
    """
    Apply tool compensation to a line path.

    For exterior compensation, the tool path expands outward (material stays inside).
    For interior compensation, the tool path shrinks inward (material stays outside).

    Closed paths are auto-detected by checking if first and last points match.

    Args:
        path: List of point dicts with x, y, and optional line_type, arc_center_x/y
        tool_diameter: Diameter of the cutting tool
        compensation_type: "none", "interior", or "exterior"

    Returns:
        New path with compensated coordinates
    """
    if compensation_type == 'none' or not path or len(path) < 2:
        return path

    tool_radius = tool_diameter / 2.0

    # Auto-detect if path is closed (first and last points at same location)
    closed = _is_path_closed(path)

    # Store closing segment data from original last point before reducing path length
    # This preserves arc/line_type info that would otherwise be lost
    closing_segment_data = path[-1] if closed and len(path) > 1 else None

    # Determine offset direction based on path winding and compensation type
    # Normal points LEFT of walking direction
    # For CCW path: LEFT = inside, RIGHT = outside
    # For CW path: LEFT = outside, RIGHT = inside
    winding = calculate_path_winding(path)

    # Determine offset: positive = left of direction, negative = right
    if compensation_type == 'exterior':
        # Exterior: expand outward (tool outside the path)
        # CCW (positive winding): outside is RIGHT = negative offset
        # CW (negative winding): outside is LEFT = positive offset
        offset = -tool_radius if winding >= 0 else tool_radius
    else:  # interior
        # Interior: shrink inward (tool inside the path)
        # CCW (positive winding): inside is LEFT = positive offset
        # CW (negative winding): inside is RIGHT = negative offset
        offset = tool_radius if winding >= 0 else -tool_radius

    # Process the path - for closed paths, don't process the duplicate closing point
    n = len(path) - 1 if closed else len(path)
    compensated_path = []

    # Build list of offset segments
    offset_segments = []

    for i in range(n - 1 if not closed else n):
        j = (i + 1) % n
        p1 = (path[i]['x'], path[i]['y'])
        p2 = (path[j]['x'], path[j]['y'])

        # For closing segment of closed path, use original last point's segment data
        # This preserves arc info that would be lost when j wraps to 0
        if closed and j == 0 and closing_segment_data:
            segment_source = closing_segment_data
        else:
            segment_source = path[j]

        line_type = segment_source.get('line_type', 'straight')

        if line_type == 'arc':
            # For arcs, we need to adjust radius instead of parallel offset
            arc_center = (segment_source.get('arc_center_x', 0), segment_source.get('arc_center_y', 0))

            # Determine which side of the chord the arc bulges to by sampling
            # a point on the arc (the midpoint angularly)
            arc_dir = segment_source.get('arc_direction', '').lower()

            # Calculate angles from center to start and end
            start_angle = math.atan2(p1[1] - arc_center[1], p1[0] - arc_center[0])
            end_angle = math.atan2(p2[1] - arc_center[1], p2[0] - arc_center[0])

            # Calculate mid angle based on arc direction
            if arc_dir == 'cw':
                # CW: angles decrease, so mid is between start and end going backwards
                if start_angle < end_angle:
                    start_angle += 2 * math.pi
                mid_angle = (start_angle + end_angle) / 2
            else:
                # CCW: angles increase, so mid is between start and end going forwards
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                mid_angle = (start_angle + end_angle) / 2

            # Sample point on the arc at mid angle
            radius = math.sqrt((p1[0] - arc_center[0])**2 + (p1[1] - arc_center[1])**2)
            arc_mid_x = arc_center[0] + radius * math.cos(mid_angle)
            arc_mid_y = arc_center[1] + radius * math.sin(mid_angle)

            # Check which side of the chord (p1 to p2) this arc point is on
            # using cross product of chord direction and vector to arc point
            chord_dx = p2[0] - p1[0]
            chord_dy = p2[1] - p1[1]
            to_arc_dx = arc_mid_x - p1[0]
            to_arc_dy = arc_mid_y - p1[1]

            cross = chord_dx * to_arc_dy - chord_dy * to_arc_dx
            arc_bulges_left = cross > 0  # Positive cross = arc point is left of chord

            # Determine radius change based on where arc bulges vs where we want to offset
            want_offset_left = offset > 0

            if arc_bulges_left == want_offset_left:
                # Arc bulges toward the offset direction - INCREASE radius to push further
                radius_change = abs(tool_radius)
            else:
                # Arc bulges away from offset direction - DECREASE radius
                radius_change = -abs(tool_radius)

            # Calculate new arc points - scale each endpoint independently
            dx1 = p1[0] - arc_center[0]
            dy1 = p1[1] - arc_center[1]
            dx2 = p2[0] - arc_center[0]
            dy2 = p2[1] - arc_center[1]

            # Calculate radius for each endpoint independently
            radius1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
            radius2 = math.sqrt(dx2 * dx2 + dy2 * dy2)

            new_radius1 = radius1 + radius_change
            new_radius2 = radius2 + radius_change

            if new_radius1 <= 0 or new_radius2 <= 0:
                min_radius = min(radius1, radius2)
                raise ValueError(
                    f"Arc radius ({min_radius:.4f}) is too small for "
                    f"{compensation_type} compensation with tool radius {tool_radius:.4f}"
                )

            scale1 = new_radius1 / radius1 if radius1 > 0 else 1.0
            scale2 = new_radius2 / radius2 if radius2 > 0 else 1.0

            new_p1 = (arc_center[0] + dx1 * scale1, arc_center[1] + dy1 * scale1)
            new_p2 = (arc_center[0] + dx2 * scale2, arc_center[1] + dy2 * scale2)

            offset_segments.append({
                'type': 'arc',
                'start': new_p1,
                'end': new_p2,
                'center': arc_center,
                'original_index': j,
                'segment_source': segment_source
            })
        else:
            # Straight segment - parallel offset
            new_p1, new_p2 = offset_line_segment(p1, p2, offset)
            offset_segments.append({
                'type': 'straight',
                'start': new_p1,
                'end': new_p2,
                'original_index': j,
                'segment_source': segment_source
            })

    # Now find intersections between adjacent offset segments
    if not offset_segments:
        return path

    for i in range(len(offset_segments)):
        seg = offset_segments[i]
        # Use segment_source for point data (preserves arc info for closing segments)
        original_point = seg['segment_source']

        if i == 0:
            # First point - use start of first segment
            if closed:
                # Find intersection with last segment
                prev_seg = offset_segments[-1]
                if seg['type'] == 'straight' and prev_seg['type'] == 'straight':
                    intersection = calculate_line_intersection(
                        prev_seg['start'], prev_seg['end'],
                        seg['start'], seg['end']
                    )
                    if intersection:
                        first_point = intersection
                    else:
                        first_point = seg['start']
                elif prev_seg['type'] == 'arc' and seg['type'] == 'straight':
                    # Last segment is arc, first is straight
                    arc_center = prev_seg['center']
                    dx = prev_seg['end'][0] - arc_center[0]
                    dy = prev_seg['end'][1] - arc_center[1]
                    arc_radius = math.sqrt(dx * dx + dy * dy)
                    intersection = calculate_line_circle_intersection(
                        seg['start'], seg['end'],
                        arc_center, arc_radius,
                        seg['start']
                    )
                    if intersection:
                        first_point = intersection
                    else:
                        first_point = seg['start']
                elif prev_seg['type'] == 'straight' and seg['type'] == 'arc':
                    # Last segment is straight, first is arc
                    arc_center = seg['center']
                    dx = seg['start'][0] - arc_center[0]
                    dy = seg['start'][1] - arc_center[1]
                    arc_radius = math.sqrt(dx * dx + dy * dy)
                    intersection = calculate_line_circle_intersection(
                        prev_seg['start'], prev_seg['end'],
                        arc_center, arc_radius,
                        seg['start']
                    )
                    if intersection:
                        first_point = intersection
                    else:
                        first_point = seg['start']
                else:
                    # Arc to arc - use segment start for now
                    first_point = seg['start']
            else:
                first_point = seg['start']

            new_point = dict(path[0])  # Copy original first point
            new_point['x'] = first_point[0]
            new_point['y'] = first_point[1]
            compensated_path.append(new_point)

        # Handle the end of this segment / start of next
        if i < len(offset_segments) - 1 or closed:
            next_i = (i + 1) % len(offset_segments)
            next_seg = offset_segments[next_i]

            if seg['type'] == 'straight' and next_seg['type'] == 'straight':
                intersection = calculate_line_intersection(
                    seg['start'], seg['end'],
                    next_seg['start'], next_seg['end']
                )
                if intersection:
                    corner_point = intersection
                else:
                    corner_point = seg['end']
            elif seg['type'] == 'arc' and next_seg['type'] == 'straight':
                # Arc to straight: find where straight line intersects the arc circle
                arc_center = seg['center']
                # Use radius at arc end
                dx = seg['end'][0] - arc_center[0]
                dy = seg['end'][1] - arc_center[1]
                arc_radius = math.sqrt(dx * dx + dy * dy)
                intersection = calculate_line_circle_intersection(
                    next_seg['start'], next_seg['end'],
                    arc_center, arc_radius,
                    seg['end']  # Prefer point near arc end
                )
                if intersection:
                    corner_point = intersection
                else:
                    corner_point = seg['end']
            elif seg['type'] == 'straight' and next_seg['type'] == 'arc':
                # Straight to arc: find where straight line intersects the arc circle
                arc_center = next_seg['center']
                # Use radius at arc start
                dx = next_seg['start'][0] - arc_center[0]
                dy = next_seg['start'][1] - arc_center[1]
                arc_radius = math.sqrt(dx * dx + dy * dy)
                intersection = calculate_line_circle_intersection(
                    seg['start'], seg['end'],
                    arc_center, arc_radius,
                    next_seg['start']  # Prefer point near arc start
                )
                if intersection:
                    corner_point = intersection
                else:
                    corner_point = next_seg['start']
            else:
                # Arc to arc - insert a straight line segment between the two arcs
                # This ensures each arc starts/ends on its own compensated circle

                # First, add end point of arc 1 (on arc 1's circle)
                arc1_end_point = dict(original_point)
                arc1_end_point['x'] = seg['end'][0]
                arc1_end_point['y'] = seg['end'][1]
                compensated_path.append(arc1_end_point)

                # Then add start point of arc 2 as a straight line (on arc 2's circle)
                # This creates a short connecting line between the two arcs
                arc2_start_point = {
                    'x': next_seg['start'][0],
                    'y': next_seg['start'][1],
                    'line_type': 'straight'
                }
                compensated_path.append(arc2_start_point)

                # Skip the normal corner point addition below
                continue

            new_point = dict(original_point)
            new_point['x'] = corner_point[0]
            new_point['y'] = corner_point[1]

            if seg['type'] == 'arc':
                # Keep arc center unchanged
                pass

            compensated_path.append(new_point)
        else:
            # Open path, last point
            new_point = dict(original_point)
            new_point['x'] = seg['end'][0]
            new_point['y'] = seg['end'][1]
            compensated_path.append(new_point)

    return compensated_path
