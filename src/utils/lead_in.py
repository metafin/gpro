"""Lead-in utilities for profile cuts.

Implements ramped and helical lead-in strategies to eliminate shock loading
when transitioning from vertical plunge to lateral cut. The tool descends
gradually while moving in X/Y, reducing stress on end mills.

Lead-in types:
- ramp: Linear approach with simultaneous XY and Z movement (for lines)
- helical: Spiral descent using G02/G03 with Z (for circles and hexagons)

Approach angle convention:
- 0°: From top (12 o'clock)
- 90°: From right (3 o'clock) - default, matches original behavior
- 180°: From bottom (6 o'clock)
- 270°: From left (9 o'clock)
"""
import math
from typing import Tuple, List, Optional

from .gcode_format import format_coordinate, generate_rapid_move, generate_linear_move, generate_arc_move


def _user_angle_to_math_angle(user_angle: float) -> float:
    """
    Convert user angle (0=top, 90=right, clockwise) to math angle (radians).

    User angle convention:
    - 0°: Top (12 o'clock position)
    - 90°: Right (3 o'clock position)
    - 180°: Bottom (6 o'clock position)
    - 270°: Left (9 o'clock position)

    Math convention:
    - 0 radians: Right (+X direction)
    - π/2 radians: Up (+Y direction)
    - Counter-clockwise positive

    Args:
        user_angle: Angle in degrees using user convention (0=top, clockwise)

    Returns:
        Angle in radians using math convention (0=right, counter-clockwise)
    """
    # User convention: 0° = top, 90° = right (clockwise)
    # Math convention: 0° = right, 90° = top (counter-clockwise)
    # Convert: math_degrees = 90 - user_angle
    math_degrees = 90 - user_angle
    return math.radians(math_degrees)


def calculate_lead_in_distance(ramp_angle: float, pass_depth: float) -> float:
    """
    Calculate lead-in distance from ramp angle and pass depth.

    The lead-in distance determines how far from the profile start the tool
    begins its ramped descent. A shallower angle (smaller degrees) = longer
    distance = gentler entry.

    Recommended angles:
    - 2-3°: Very gentle, ideal for hard materials or deep cuts
    - 3-5°: Good for aluminum and general use
    - 5-10°: Acceptable for shallow cuts or soft materials

    Args:
        ramp_angle: Entry angle in degrees (2-10° typical)
        pass_depth: Depth of each pass in inches

    Returns:
        Lead-in distance in inches

    Example:
        >>> calculate_lead_in_distance(3.0, 0.1)  # 3° angle, 0.1" pass
        1.91  # inches
    """
    if ramp_angle <= 0 or pass_depth <= 0:
        return 0.25  # Fallback default
    ramp_radians = math.radians(ramp_angle)
    return pass_depth / math.tan(ramp_radians)


def calculate_circle_lead_in_point(
    center_x: float,
    center_y: float,
    cut_radius: float,
    lead_in_distance: float,
    approach_angle: float = 90
) -> Tuple[float, float]:
    """
    Calculate lead-in start point for circle cuts.

    The profile start is on the circle at the specified approach angle.
    Lead-in point is offset radially outward by lead_in_distance.

    Args:
        center_x: Circle center X coordinate
        center_y: Circle center Y coordinate
        cut_radius: Radius of the toolpath (feature radius - tool radius for interior)
        lead_in_distance: Distance from profile start to lead-in point
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position

    Returns:
        (x, y) tuple of lead-in start point
    """
    # Convert user angle to math angle
    math_angle = _user_angle_to_math_angle(approach_angle)

    # Profile start is on circle at the approach angle direction
    # Lead-in is radially outward (further from center) by lead_in_distance
    lead_in_x = center_x + (cut_radius + lead_in_distance) * math.cos(math_angle)
    lead_in_y = center_y + (cut_radius + lead_in_distance) * math.sin(math_angle)
    return (lead_in_x, lead_in_y)


def calculate_hexagon_lead_in_point(
    vertices: List[Tuple[float, float]],
    lead_in_distance: float,
    center: Optional[Tuple[float, float]] = None,
    approach_angle: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate lead-in start point for hexagon cuts.

    When approach_angle is specified, the lead-in point is calculated
    radially from the hexagon center at the specified angle.
    Otherwise (default), extends the line from v0 to v1 backwards.

    Args:
        vertices: List of 6 (x, y) vertex coordinates
        lead_in_distance: Distance from profile start to lead-in point
        center: Hexagon center (x, y) - required when using approach_angle
        approach_angle: Optional direction tool approaches from in degrees
                       (0=top, 90=right). If None, uses edge-direction method.

    Returns:
        (x, y) tuple of lead-in start point
    """
    if len(vertices) < 2:
        return vertices[0] if vertices else (0, 0)

    v0_x, v0_y = vertices[0]

    # If approach_angle is specified and we have center, use radial method
    if approach_angle is not None and center is not None:
        cx, cy = center
        math_angle = _user_angle_to_math_angle(approach_angle)

        # Calculate distance from center to first vertex
        vertex_dist = math.sqrt((v0_x - cx) ** 2 + (v0_y - cy) ** 2)

        # Lead-in point is at approach angle, distance = vertex_dist + lead_in_distance
        lead_in_x = cx + (vertex_dist + lead_in_distance) * math.cos(math_angle)
        lead_in_y = cy + (vertex_dist + lead_in_distance) * math.sin(math_angle)
        return (lead_in_x, lead_in_y)

    # Default: extend the line from v0 to v1 backwards
    v1_x, v1_y = vertices[1]

    # Direction from v0 to v1
    dx = v1_x - v0_x
    dy = v1_y - v0_y
    length = math.sqrt(dx * dx + dy * dy)

    if length < 0.0001:
        return (v0_x, v0_y)

    # Normalize and reverse direction
    dx /= length
    dy /= length

    # Lead-in point is v0 minus direction * distance
    lead_in_x = v0_x - dx * lead_in_distance
    lead_in_y = v0_y - dy * lead_in_distance

    return (lead_in_x, lead_in_y)


def _calculate_path_winding(path: List[dict]) -> float:
    """
    Calculate the winding number (signed area) of a path.

    Positive = counter-clockwise, Negative = clockwise.

    Args:
        path: List of path points with 'x' and 'y' keys

    Returns:
        Signed area (positive = CCW, negative = CW)
    """
    if len(path) < 3:
        return 0.0

    area = 0.0
    n = len(path)

    for i in range(n):
        j = (i + 1) % n
        area += path[i].get('x', 0) * path[j].get('y', 0)
        area -= path[j].get('x', 0) * path[i].get('y', 0)

    return area / 2.0


def calculate_line_lead_in_point(
    path: List[dict],
    lead_in_distance: float,
    compensation: str = 'none',
    approach_angle: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate lead-in start point for line cuts.

    When approach_angle is specified, the tool approaches from that direction
    regardless of path geometry. Otherwise:
    - For 'none' compensation or open paths: extends backward along the path direction.
    - For 'interior' compensation on closed paths: offsets perpendicular toward the
      interior (waste side) so the lead-in scar is on the scrap material.
    - For 'exterior' compensation on closed paths: offsets perpendicular toward the
      exterior (waste side).

    Args:
        path: List of path points with 'x' and 'y' keys
        lead_in_distance: Distance from profile start to lead-in point
        compensation: 'none', 'interior', or 'exterior'
        approach_angle: Optional direction tool approaches from in degrees
                       (0=top, 90=right). If specified, overrides automatic direction.

    Returns:
        (x, y) tuple of lead-in start point
    """
    if not path:
        return (0, 0)

    p0 = path[0]
    p0_x, p0_y = p0.get('x', 0), p0.get('y', 0)

    if len(path) < 2:
        return (p0_x, p0_y)

    # If approach_angle is specified, use it to calculate lead-in point
    if approach_angle is not None:
        math_angle = _user_angle_to_math_angle(approach_angle)
        lead_in_x = p0_x + lead_in_distance * math.cos(math_angle)
        lead_in_y = p0_y + lead_in_distance * math.sin(math_angle)
        return (lead_in_x, lead_in_y)

    p1 = path[1]
    p1_x, p1_y = p1.get('x', 0), p1.get('y', 0)

    # Direction from p0 to p1
    dx = p1_x - p0_x
    dy = p1_y - p0_y
    length = math.sqrt(dx * dx + dy * dy)

    if length < 0.0001:
        return (p0_x, p0_y)

    # Normalize direction
    dx /= length
    dy /= length

    # Check if path is closed and compensation is applied
    path_is_closed = is_closed_path(path)

    if path_is_closed and compensation in ('interior', 'exterior'):
        # For closed paths with compensation, offset perpendicular to path
        # toward the waste side (interior for interior cuts, exterior for exterior)

        # Calculate perpendicular (normal) direction
        # (-dy, dx) points LEFT of the path direction
        nx = -dy
        ny = dx

        # Determine which way is "inside" based on path winding
        winding = _calculate_path_winding(path)

        # For CCW (positive winding): LEFT is inside
        # For CW (negative winding): LEFT is outside (RIGHT is inside)
        if compensation == 'interior':
            # Interior cut: waste is inside, lead-in should be inside
            if winding >= 0:
                # CCW path: inside is LEFT (positive normal direction)
                lead_in_x = p0_x + nx * lead_in_distance
                lead_in_y = p0_y + ny * lead_in_distance
            else:
                # CW path: inside is RIGHT (negative normal direction)
                lead_in_x = p0_x - nx * lead_in_distance
                lead_in_y = p0_y - ny * lead_in_distance
        else:  # exterior
            # Exterior cut: waste is outside, lead-in should be outside
            if winding >= 0:
                # CCW path: outside is RIGHT (negative normal direction)
                lead_in_x = p0_x - nx * lead_in_distance
                lead_in_y = p0_y - ny * lead_in_distance
            else:
                # CW path: outside is LEFT (positive normal direction)
                lead_in_x = p0_x + nx * lead_in_distance
                lead_in_y = p0_y + ny * lead_in_distance
    else:
        # Open path or no compensation: extend backward along path direction
        lead_in_x = p0_x - dx * lead_in_distance
        lead_in_y = p0_y - dy * lead_in_distance

    return (lead_in_x, lead_in_y)


def generate_ramp_entry(
    lead_in_x: float,
    lead_in_y: float,
    profile_start_x: float,
    profile_start_y: float,
    depth: float,
    plunge_rate: float
) -> List[str]:
    """
    Generate G-code for ramped entry from lead-in point to profile start.

    The tool moves from (lead_in_x, lead_in_y, 0) to
    (profile_start_x, profile_start_y, -depth) in a single linear move,
    creating a smooth ramp entry.

    Args:
        lead_in_x: Lead-in point X coordinate
        lead_in_y: Lead-in point Y coordinate
        profile_start_x: Profile start X coordinate
        profile_start_y: Profile start Y coordinate
        depth: Target depth (positive value, will be negated)
        plunge_rate: Feed rate for the ramp move (in/min)

    Returns:
        List of G-code command strings
    """
    return [
        f"G01 X{format_coordinate(profile_start_x)} Y{format_coordinate(profile_start_y)} "
        f"Z{format_coordinate(-depth)} F{format_coordinate(plunge_rate, 1)}"
    ]


def generate_ramp_preamble(
    lead_in_x: float,
    lead_in_y: float,
    profile_start_x: float,
    profile_start_y: float,
    pass_depth: float,
    plunge_rate: float
) -> List[str]:
    """
    Generate preamble for ramp lead-in subroutine (replaces vertical plunge).

    Used in subroutines where each call descends one pass_depth using
    relative coordinates. The ramp moves from lead-in point at current Z
    to profile start at (Z - pass_depth).

    Args:
        lead_in_x: Lead-in point X coordinate (absolute)
        lead_in_y: Lead-in point Y coordinate (absolute)
        profile_start_x: Profile start X coordinate (absolute)
        profile_start_y: Profile start Y coordinate (absolute)
        pass_depth: Depth increment per pass (positive value)
        plunge_rate: Feed rate for the ramp move (in/min)

    Returns:
        List of G-code command strings
    """
    # Calculate XY offset from lead-in to profile start
    dx = profile_start_x - lead_in_x
    dy = profile_start_y - lead_in_y

    return [
        "G91",
        f"G01 X{format_coordinate(dx)} Y{format_coordinate(dy)} "
        f"Z{format_coordinate(-pass_depth)} F{format_coordinate(plunge_rate, 1)}",
        "G90",
    ]


def generate_lead_out(
    profile_end_x: float,
    profile_end_y: float,
    lead_in_x: float,
    lead_in_y: float,
    feed_rate: float
) -> List[str]:
    """
    Generate G-code to return from profile end to lead-in point.

    For closed profiles, after completing the cut, we move back to the
    lead-in position (at cutting depth) before the next pass or retract.

    Args:
        profile_end_x: Profile end X coordinate (usually same as start for closed)
        profile_end_y: Profile end Y coordinate
        lead_in_x: Lead-in point X coordinate
        lead_in_y: Lead-in point Y coordinate
        feed_rate: Cutting feed rate for the lead-out move

    Returns:
        List of G-code command strings
    """
    return [
        f"G01 X{format_coordinate(lead_in_x)} Y{format_coordinate(lead_in_y)} "
        f"F{format_coordinate(feed_rate, 1)}"
    ]


def is_closed_path(path: List[dict], tolerance: float = 0.0001) -> bool:
    """
    Check if a line path is closed (first point == last point).

    Args:
        path: List of path points with 'x' and 'y' keys
        tolerance: Maximum distance to consider points coincident

    Returns:
        True if path is closed, False otherwise
    """
    if len(path) < 2:
        return False

    first = path[0]
    last = path[-1]

    dx = abs(first.get('x', 0) - last.get('x', 0))
    dy = abs(first.get('y', 0) - last.get('y', 0))

    return dx < tolerance and dy < tolerance


# --- Helical Lead-In Functions ---

# Minimum helix radius to ensure safe toolpath (tool must fit inside helix)
MIN_HELIX_RADIUS = 0.05  # inches


def calculate_helix_radius_for_circle(
    cut_radius: float,
    tool_diameter: float,
    clearance: float = 0.025
) -> Optional[float]:
    """
    Calculate helix radius for circular cuts.

    The helix must fit inside the circle being cut. For interior cuts,
    the tool center follows a path smaller than the feature radius.
    The helix radius should be small enough that the tool fits inside.

    Args:
        cut_radius: Radius of the toolpath (feature radius - tool_radius for interior)
        tool_diameter: Diameter of the end mill
        clearance: Extra clearance between helix and cut profile

    Returns:
        Helix radius, or None if circle is too small for helical entry
    """
    tool_radius = tool_diameter / 2

    # Helix must be inside the cut radius with clearance
    # The helix radius determines where the tool center spirals
    # Tool edge extends tool_radius beyond center
    max_helix_radius = cut_radius - clearance

    if max_helix_radius < MIN_HELIX_RADIUS:
        return None

    # Use a reasonable helix radius (half the available space or tool_radius, whichever is smaller)
    helix_radius = min(max_helix_radius, tool_radius + clearance)

    # Ensure minimum radius for smooth helical motion
    if helix_radius < MIN_HELIX_RADIUS:
        return None

    return helix_radius


def calculate_helix_radius_for_hexagon(
    flat_to_flat: float,
    tool_diameter: float,
    compensation: str = 'interior',
    clearance: float = 0.025
) -> Optional[float]:
    """
    Calculate helix radius for hexagonal cuts.

    The helix must fit inside the hexagon. For a point-up hexagon,
    the apothem (flat-to-flat / 2) is the inscribed circle radius.

    Args:
        flat_to_flat: Hexagon flat-to-flat distance
        tool_diameter: Diameter of the end mill
        compensation: 'interior' or 'exterior'
        clearance: Extra clearance between helix and hexagon profile

    Returns:
        Helix radius, or None if hexagon is too small for helical entry
    """
    tool_radius = tool_diameter / 2
    apothem = flat_to_flat / 2

    if compensation == 'interior':
        # For interior cut, toolpath is inside the hexagon
        # Available radius is apothem minus tool_radius minus clearance
        available_radius = apothem - tool_radius - clearance
    else:
        # For exterior cut, we can use a larger helix centered on the hexagon
        available_radius = apothem - clearance

    if available_radius < MIN_HELIX_RADIUS:
        return None

    # Use a reasonable helix radius
    helix_radius = min(available_radius, tool_radius + clearance)

    if helix_radius < MIN_HELIX_RADIUS:
        return None

    return helix_radius


def calculate_helix_start_point(
    center_x: float,
    center_y: float,
    helix_radius: float,
    approach_angle: float = 90
) -> Tuple[float, float]:
    """
    Calculate the start point for helical entry.

    The helix starts at the specified approach angle position, which
    matches the circle profile start point convention.

    Args:
        center_x: Helix center X coordinate
        center_y: Helix center Y coordinate
        helix_radius: Radius of the helix
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position

    Returns:
        (x, y) tuple of helix start point
    """
    math_angle = _user_angle_to_math_angle(approach_angle)
    return (
        center_x + helix_radius * math.cos(math_angle),
        center_y + helix_radius * math.sin(math_angle)
    )


def calculate_helix_revolutions(
    target_depth: float,
    helix_pitch: float
) -> int:
    """
    Calculate the number of full revolutions needed to reach target depth.

    Args:
        target_depth: Depth to descend (positive value)
        helix_pitch: Z drop per revolution

    Returns:
        Number of complete revolutions (at least 1)
    """
    if helix_pitch <= 0:
        return 1

    revolutions = math.ceil(target_depth / helix_pitch)
    return max(1, revolutions)


def generate_helical_lead_in(
    center_x: float,
    center_y: float,
    helix_radius: float,
    target_depth: float,
    helix_pitch: float,
    plunge_rate: float,
    approach_angle: float = 90,
    end_feed: Optional[float] = None
) -> List[str]:
    """
    Generate G-code for helical lead-in (spiral descent).

    Uses clockwise (G02) arcs with Z movement to spiral down into
    the material. Each full revolution descends by helix_pitch.

    Feed rate ramping: If end_feed is provided, the feed rate ramps up
    in 3 steps (25%, 50%, 75% of the range from plunge_rate to end_feed).
    The transition arc (generated separately) completes the 4th step at 100%.
    This provides smooth acceleration as the tool establishes itself.

    Args:
        center_x: Helix center X coordinate
        center_y: Helix center Y coordinate
        helix_radius: Radius of the helix
        target_depth: Depth to descend (positive value, will be negated)
        helix_pitch: Z drop per revolution
        plunge_rate: Starting feed rate for the helical descent
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position
        end_feed: Optional ending feed rate. If provided, feed ramps in steps
                 of 25%, 50%, 75% toward end_feed (transition arc does 100%).
                 If None, uses plunge_rate throughout.

    Returns:
        List of G-code command strings
    """
    lines = []

    # Calculate number of revolutions
    revolutions = calculate_helix_revolutions(target_depth, helix_pitch)

    # Convert user angle to math angle
    math_angle = _user_angle_to_math_angle(approach_angle)

    # Start point is at the approach angle position
    start_x = center_x + helix_radius * math.cos(math_angle)
    start_y = center_y + helix_radius * math.sin(math_angle)

    # I/J offset is from current position to center (always points toward center)
    i_offset = -helix_radius * math.cos(math_angle)
    j_offset = -helix_radius * math.sin(math_angle)

    # Descend in full revolutions with 4-step feed ramping (helix gets steps 1-3)
    # Step 1: 25%, Step 2: 50%, Step 3: 75%, Step 4 (transition arc): 100%
    current_depth = 0
    depth_per_rev = target_depth / revolutions

    # Feed step percentages for helix revolutions (transition arc is 100%)
    step_percentages = [0.25, 0.50, 0.75]

    for rev in range(revolutions):
        current_depth += depth_per_rev

        # Calculate stepped feed rate for this revolution
        if end_feed is not None:
            feed_range = end_feed - plunge_rate
            # Distribute revolutions across the 3 helix steps
            if revolutions == 1:
                # Single revolution: use 75% (step 3, just before transition)
                step_pct = 0.75
            elif revolutions == 2:
                # Two revolutions: use 50% and 75%
                step_pct = step_percentages[rev + 1]
            else:
                # 3+ revolutions: map to steps, later revolutions stay at 75%
                step_index = min(rev, 2)
                step_pct = step_percentages[step_index]
            current_feed = plunge_rate + feed_range * step_pct
        else:
            current_feed = plunge_rate

        # G02 full circle with Z descent
        # End point is same as start (full circle)
        lines.append(generate_arc_move(
            "G02",
            start_x, start_y,
            i_offset, j_offset,
            feed=current_feed,
            z=-current_depth
        ))

    return lines


def generate_helical_preamble(
    center_x: float,
    center_y: float,
    helix_radius: float,
    pass_depth: float,
    helix_pitch: float,
    plunge_rate: float,
    approach_angle: float = 90
) -> List[str]:
    """
    Generate preamble for helical lead-in in subroutines.

    Uses relative coordinates for Z descent so the subroutine can be
    called multiple times with L parameter. After helix, switches back
    to absolute mode.

    Args:
        center_x: Helix center X coordinate
        center_y: Helix center Y coordinate
        helix_radius: Radius of the helix
        pass_depth: Depth increment per pass
        helix_pitch: Z drop per revolution
        plunge_rate: Feed rate for the helical descent
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position

    Returns:
        List of G-code command strings
    """
    lines = []

    # Start at Z0
    lines.append("G00 Z0")

    # Calculate revolutions for this pass depth
    revolutions = calculate_helix_revolutions(pass_depth, helix_pitch)
    depth_per_rev = pass_depth / revolutions

    # Convert user angle to math angle
    math_angle = _user_angle_to_math_angle(approach_angle)

    # Start point at approach angle position
    start_x = center_x + helix_radius * math.cos(math_angle)
    start_y = center_y + helix_radius * math.sin(math_angle)
    i_offset = -helix_radius * math.cos(math_angle)
    j_offset = -helix_radius * math.sin(math_angle)

    # Switch to relative mode for Z
    lines.append("G91")

    # Helical descent
    for rev in range(revolutions):
        lines.append(
            f"G02 X{format_coordinate(start_x)} Y{format_coordinate(start_y)} "
            f"Z{format_coordinate(-depth_per_rev)} I{format_coordinate(i_offset)} "
            f"J{format_coordinate(j_offset)} F{format_coordinate(plunge_rate, 1)}"
        )

    # Switch back to absolute mode
    lines.append("G90")

    return lines


def generate_helical_to_profile_circle(
    center_x: float,
    center_y: float,
    helix_radius: float,
    cut_radius: float,
    feed_rate: float,
    approach_angle: float = 90
) -> List[str]:
    """
    Generate G-code to transition from helix end to circle profile.

    After helical descent, the tool is at the helix start point at the
    approach angle. This generates an arc to move tangentially onto the
    larger circle profile.

    Args:
        center_x: Circle center X coordinate
        center_y: Circle center Y coordinate
        helix_radius: Radius of the helix (where tool currently is)
        cut_radius: Radius of the toolpath to cut
        feed_rate: Feed rate for the transition arc
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position

    Returns:
        List of G-code command strings
    """
    # If helix_radius equals cut_radius, no transition needed
    if abs(helix_radius - cut_radius) < 0.001:
        return []

    # Convert user angle to math angle
    math_angle = _user_angle_to_math_angle(approach_angle)

    # Current position: at approach angle on helix radius
    # Target position: at same approach angle on cut radius

    # Arc from helix to profile (expand outward)
    # Use G02 (CW) arc with center at circle center
    lines = []
    target_x = center_x + cut_radius * math.cos(math_angle)
    target_y = center_y + cut_radius * math.sin(math_angle)

    # I/J from current position to arc center
    i_offset = -helix_radius * math.cos(math_angle)
    j_offset = -helix_radius * math.sin(math_angle)

    lines.append(generate_arc_move(
        "G02",
        target_x, target_y,
        i_offset, j_offset,
        feed=feed_rate
    ))

    return lines


def generate_helical_to_profile_hexagon(
    helix_end_x: float,
    helix_end_y: float,
    first_vertex_x: float,
    first_vertex_y: float,
    feed_rate: float,
    approach_angle: float = 90
) -> List[str]:
    """
    Generate G-code to transition from helix end to hexagon first vertex.

    After helical descent at the hexagon center, the tool moves linearly
    to the first vertex of the hexagon to begin the cut.

    Args:
        helix_end_x: X coordinate at end of helix
        helix_end_y: Y coordinate at end of helix
        first_vertex_x: X coordinate of first hexagon vertex
        first_vertex_y: Y coordinate of first hexagon vertex
        feed_rate: Feed rate for the linear move
        approach_angle: Direction tool approaches from in degrees (for future use)

    Returns:
        List of G-code command strings
    """
    # Note: helix_end_x/y are already calculated based on approach_angle
    # so this function just needs to do the linear transition
    return [
        f"G01 X{format_coordinate(first_vertex_x)} Y{format_coordinate(first_vertex_y)} "
        f"F{format_coordinate(feed_rate, 1)}"
    ]


def adjust_helix_depth(
    helix_lines: List[str],
    pass_depth: float,
    cumulative_depth: float
) -> List[str]:
    """
    Adjust helix G-code lines to use cumulative depth instead of pass depth.

    The helical lead-in generator produces lines with Z values relative to
    a single pass. This function adjusts those Z values to the cumulative
    depth for multi-pass operations.

    Args:
        helix_lines: G-code lines from generate_helical_lead_in
        pass_depth: The per-pass depth used when generating helix_lines
        cumulative_depth: The actual cumulative depth to use

    Returns:
        Adjusted G-code lines with correct Z values
    """
    adjusted = []
    old_z = f"Z{format_coordinate(-pass_depth)}"
    new_z = f"Z{format_coordinate(-cumulative_depth)}"

    for line in helix_lines:
        if old_z in line:
            adjusted.append(line.replace(old_z, new_z))
        else:
            adjusted.append(line)

    return adjusted
