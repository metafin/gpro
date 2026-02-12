"""Subroutine generation utilities for M98 calls."""
import math
from typing import List, Tuple, Optional

from .gcode_format import (
    format_coordinate,
    generate_rapid_move,
    generate_linear_move,
    generate_arc_move,
    generate_subroutine_end
)
from .lead_in import generate_helical_entry, _user_angle_to_math_angle


# Subroutine number ranges by operation type
SUBROUTINE_RANGES = {
    'drill': (1000, 1099),
    'circular': (1100, 1199),
    'hexagonal': (1200, 1299),
    'line': (1300, 1399),
}


def get_next_subroutine_number(operation_type: str, existing: List[int]) -> int:
    """
    Get the next available subroutine number for an operation type.

    Args:
        operation_type: One of 'drill', 'circular', 'hexagonal', 'line'
        existing: List of already-used subroutine numbers

    Returns:
        Next available number in the appropriate range
    """
    start, end = SUBROUTINE_RANGES.get(operation_type, (1000, 1099))

    for num in range(start, end + 1):
        if num not in existing:
            return num

    # Fallback: use next number after range
    return end + 1


def generate_subroutine_file(commands: List[str]) -> str:
    """
    Wrap commands into a complete subroutine file.

    Args:
        commands: List of G-code command strings

    Returns:
        Complete subroutine file content with M99 and % ending
    """
    lines = commands + generate_subroutine_end()
    return '\n'.join(lines)


def generate_cut_preamble(pass_depth: float, plunge_rate: float) -> List[str]:
    """
    Generate standard preamble for cut subroutines (vertical plunge).

    Uses relative Z movement so multi-pass with L parameter works correctly.
    Each subroutine call descends one pass_depth from current Z position.

    Args:
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate (in/min)

    Returns:
        List of preamble G-code commands
    """
    return [
        "G91",
        f"G01 Z{format_coordinate(-pass_depth)} F{format_coordinate(plunge_rate, 1)}",
        "G90",
    ]


def generate_ramp_preamble_circle(
    lead_in_distance: float,
    pass_depth: float,
    plunge_rate: float,
    approach_angle: float = 90
) -> List[str]:
    """
    Generate ramp lead-in preamble for circle subroutines.

    Uses relative movement to ramp from lead-in point to profile start
    while descending one pass depth. Each subroutine call descends from
    current Z position for multi-pass with L parameter.

    Args:
        lead_in_distance: Distance from lead-in point to profile start
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate for the ramp (in/min)
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original behavior (X-only movement)

    Returns:
        List of preamble G-code commands
    """
    # Convert user angle to math angle
    math_angle = _user_angle_to_math_angle(approach_angle)

    # Calculate XY offset from lead-in to profile start (opposite of approach direction)
    # Lead-in is at (profile + lead_in_distance in approach direction)
    # So movement is from lead-in toward center (negative of approach direction)
    dx = -lead_in_distance * math.cos(math_angle)
    dy = -lead_in_distance * math.sin(math_angle)

    # Only include Y in command if it's non-zero (to minimize G-code changes from original)
    if abs(dy) < 0.0001:
        return [
            "G91",
            f"G01 X{format_coordinate(dx)} Z{format_coordinate(-pass_depth)} F{format_coordinate(plunge_rate, 1)}",
            "G90",
        ]
    else:
        return [
            "G91",
            f"G01 X{format_coordinate(dx)} Y{format_coordinate(dy)} Z{format_coordinate(-pass_depth)} F{format_coordinate(plunge_rate, 1)}",
            "G90",
        ]


def generate_ramp_preamble_absolute(
    lead_in_x: float,
    lead_in_y: float,
    profile_start_x: float,
    profile_start_y: float,
    pass_depth: float,
    plunge_rate: float
) -> List[str]:
    """
    Generate ramp lead-in preamble using absolute coordinates.

    Ramps from lead-in point to profile start while descending one pass
    depth. Each subroutine call descends from current Z position for
    multi-pass with L parameter.

    Args:
        lead_in_x: Lead-in point X coordinate
        lead_in_y: Lead-in point Y coordinate
        profile_start_x: Profile start X coordinate
        profile_start_y: Profile start Y coordinate
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate for the ramp (in/min)

    Returns:
        List of preamble G-code commands
    """
    # Calculate relative offsets
    dx = profile_start_x - lead_in_x
    dy = profile_start_y - lead_in_y

    return [
        "G91",
        f"G01 X{format_coordinate(dx)} Y{format_coordinate(dy)} Z{format_coordinate(-pass_depth)} F{format_coordinate(plunge_rate, 1)}",
        "G90",
    ]


def generate_helical_preamble_circle(
    helix_radius: float,
    cut_radius: float,
    pass_depth: float,
    helix_pitch: float,
    plunge_rate: float,
    feed_rate: float,
    approach_angle: float = 90,
    arc_feed_factor: float = 1.0
) -> List[str]:
    """
    Generate helical lead-in preamble for circle subroutines.

    Thin wrapper around generate_helical_entry() for relative Z mode
    with arc transition from helix to cut profile.

    Args:
        helix_radius: Radius of the helical descent
        cut_radius: Radius of the circle toolpath
        pass_depth: Depth increment per pass
        helix_pitch: Z drop per revolution
        plunge_rate: Starting feed rate for the helical descent
        feed_rate: Base cutting feed rate
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
        arc_feed_factor: Multiplier for arc moves (default 1.0, use 0.8 for 80%)

    Returns:
        List of preamble G-code commands
    """
    arc_feed = feed_rate * arc_feed_factor

    return generate_helical_entry(
        helix_radius=helix_radius,
        target_depth=pass_depth,
        helix_pitch=helix_pitch,
        plunge_rate=plunge_rate,
        transition_feed=plunge_rate,
        approach_angle=approach_angle,
        helix_end_feed=arc_feed,
        transition='arc',
        cut_radius=cut_radius,
        relative_z=True,
    )


def generate_helical_preamble_hexagon(
    center_x: float,
    center_y: float,
    helix_radius: float,
    first_vertex_x: float,
    first_vertex_y: float,
    pass_depth: float,
    helix_pitch: float,
    plunge_rate: float,
    feed_rate: float,
    approach_angle: float = 90,
    arc_feed_factor: float = 1.0
) -> List[str]:
    """
    Generate helical lead-in preamble for hexagon subroutines.

    Thin wrapper around generate_helical_entry() for relative Z mode
    with linear transition from helix end to first hexagon vertex.

    Args:
        center_x: Hexagon center X coordinate
        center_y: Hexagon center Y coordinate
        helix_radius: Radius of the helical descent
        first_vertex_x: X coordinate of first hexagon vertex
        first_vertex_y: Y coordinate of first hexagon vertex
        pass_depth: Depth increment per pass
        helix_pitch: Z drop per revolution
        plunge_rate: Starting feed rate for the helical descent
        feed_rate: Base cutting feed rate
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
        arc_feed_factor: Multiplier for arc moves (default 1.0, use 0.8 for 80%)

    Returns:
        List of preamble G-code commands
    """
    arc_feed = feed_rate * arc_feed_factor

    return generate_helical_entry(
        helix_radius=helix_radius,
        target_depth=pass_depth,
        helix_pitch=helix_pitch,
        plunge_rate=plunge_rate,
        transition_feed=plunge_rate,
        approach_angle=approach_angle,
        helix_end_feed=arc_feed,
        transition='linear',
        target_point=(first_vertex_x, first_vertex_y),
        relative_z=True,
    )


def build_subroutine_path(
    base_path: str,
    project_name: str,
    subroutine_number: int
) -> str:
    """
    Construct full absolute path for M98 call.

    Args:
        base_path: Base G-code directory (e.g., "C:\\Mach3\\GCode")
        project_name: Sanitized project name
        subroutine_number: Subroutine file number

    Returns:
        Full path like "C:\\Mach3\\GCode\\ProjectName\\1000.nc"
    """
    # Always use Windows backslashes since G-code runs on PC with Mach3
    path = f"{base_path}\\{project_name}\\{subroutine_number}.nc"
    # Normalize any forward slashes to backslashes
    return path.replace('/', '\\')


def generate_peck_drill_subroutine(
    pecks: List[float],
    plunge_rate: float,
    travel_height: float,
    axis: str,
    spacing: float
) -> str:
    """
    Generate a peck drill subroutine.

    The subroutine drills one hole with peck cycles, then moves to the next
    position along the specified axis.

    Args:
        pecks: List of cumulative peck depths
        plunge_rate: Plunge feed rate (in/min)
        travel_height: Z height for rapid moves
        axis: Axis for pattern movement ('x' or 'y')
        spacing: Distance to next hole position

    Returns:
        Complete subroutine file content
    """
    lines = [
        "G00 Z0",
        "G91",  # Relative mode
    ]

    # Generate peck sequence
    current_depth = 0
    for peck_depth in pecks:
        # Plunge to next peck depth (relative from current)
        depth_increment = peck_depth - current_depth
        lines.append(f"G01 Z{format_coordinate(-depth_increment)} F{format_coordinate(plunge_rate, 1)}")
        # Retract to clear chips
        lines.append(f"G00 Z{format_coordinate(peck_depth)}")
        current_depth = 0  # After full retract, we're back at Z0

    # Final retract to travel height (relative)
    lines.append(f"G00 Z{format_coordinate(travel_height)}")

    # Move to next hole position (relative)
    if axis.lower() == 'x':
        lines.append(f"G00 X{format_coordinate(spacing)}")
    else:
        lines.append(f"G00 Y{format_coordinate(spacing)}")

    lines.append("G90")  # Back to absolute mode

    return generate_subroutine_file(lines)


def generate_circle_pass_subroutine(
    cut_radius: float,
    pass_depth: float,
    plunge_rate: float,
    feed_rate: float,
    lead_in_distance: Optional[float] = None,
    lead_in_type: str = 'ramp',
    helix_radius: Optional[float] = None,
    helix_pitch: float = 0.04,
    approach_angle: float = 90,
    hold_time: float = 0,
    arc_feed_factor: float = 1.0
) -> str:
    """
    Generate a single-pass circle cut subroutine.

    Cuts one full circle at relative depth. Use L parameter for multi-pass.
    Supports three entry types: vertical plunge, ramped entry, or helical entry.

    Arc slowdown: All arc moves (helix, transition, profile, lead-out) use
    feed_rate * arc_feed_factor to reduce stress on arcs.

    Args:
        cut_radius: Radius of toolpath (feature radius - tool radius)
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate (in/min)
        feed_rate: Base cutting feed rate (in/min)
        lead_in_distance: Lead-in distance for ramped entry (used if lead_in_type='ramp')
        lead_in_type: Entry type - 'none', 'ramp', or 'helical'
        helix_radius: Radius for helical entry (used if lead_in_type='helical')
        helix_pitch: Z drop per revolution for helical entry
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position
        hold_time: Dwell time in seconds at start of each pass (0 = no dwell)
        arc_feed_factor: Multiplier for arc moves (default 1.0, use 0.8 for 80%)

    Returns:
        Complete subroutine file content
    """
    lines = []

    # Apply arc slowdown to feed rate for all arc moves
    arc_feed = feed_rate * arc_feed_factor

    # Convert user angle to math angle for I/J calculations
    math_angle = _user_angle_to_math_angle(approach_angle)

    if lead_in_type == 'helical' and helix_radius is not None and helix_radius > 0:
        # Helical lead-in: spiral down then arc to profile
        lines.extend(generate_helical_preamble_circle(
            helix_radius, cut_radius, pass_depth, helix_pitch, plunge_rate, feed_rate,
            approach_angle, arc_feed_factor
        ))
    elif lead_in_type == 'ramp' and lead_in_distance is not None and lead_in_distance > 0:
        # Ramp lead-in: start at lead-in point, ramp to profile start
        lines.extend(generate_ramp_preamble_circle(lead_in_distance, pass_depth, plunge_rate, approach_angle))
    else:
        # Traditional vertical plunge
        lines.extend(generate_cut_preamble(pass_depth, plunge_rate))

    # Add dwell right after G91, before plunge - value in milliseconds for Mach3
    if hold_time > 0:
        hold_time_ms = int(hold_time * 1000)
        lines.insert(1, f"G04 P{hold_time_ms}")

    # Full circle arc - I/J point from current position (at approach angle) to center
    i_offset = -cut_radius * math.cos(math_angle)
    j_offset = -cut_radius * math.sin(math_angle)
    lines.append(f"G02 I{format_coordinate(i_offset)} J{format_coordinate(j_offset)} F{format_coordinate(arc_feed, 1)}")

    if lead_in_type == 'helical' and helix_radius is not None and helix_radius > 0:
        # Lead-out for helical: arc back to helix start position
        if abs(helix_radius - cut_radius) > 0.001:
            delta_x = (helix_radius - cut_radius) * math.cos(math_angle)
            delta_y = (helix_radius - cut_radius) * math.sin(math_angle)
            lines.append("G91")
            lines.append(
                f"G02 X{format_coordinate(delta_x)} Y{format_coordinate(delta_y)} "
                f"I{format_coordinate(i_offset)} J{format_coordinate(j_offset)} F{format_coordinate(arc_feed, 1)}"
            )
            lines.append("G90")
    elif lead_in_type == 'ramp' and lead_in_distance is not None and lead_in_distance > 0:
        # Lead-out: return to lead-in point at cutting depth
        # After circle, we're at profile start (at approach angle position)
        # Move radially outward by lead_in_distance in the approach direction
        delta_x = lead_in_distance * math.cos(math_angle)
        delta_y = lead_in_distance * math.sin(math_angle)
        lines.append("G91")
        if abs(delta_y) < 0.0001:
            lines.append(f"G01 X{format_coordinate(delta_x)} F{format_coordinate(feed_rate, 1)}")
        else:
            lines.append(f"G01 X{format_coordinate(delta_x)} Y{format_coordinate(delta_y)} F{format_coordinate(feed_rate, 1)}")
        lines.append("G90")

    return generate_subroutine_file(lines)


def generate_hexagon_pass_subroutine(
    vertices: List[Tuple[float, float]],
    pass_depth: float,
    plunge_rate: float,
    feed_rate: float,
    lead_in_point: Optional[Tuple[float, float]] = None,
    lead_in_type: str = 'ramp',
    center: Optional[Tuple[float, float]] = None,
    helix_radius: Optional[float] = None,
    helix_pitch: float = 0.04,
    approach_angle: float = 90,
    hold_time: float = 0,
    arc_feed_factor: float = 1.0
) -> str:
    """
    Generate a single-pass hexagon cut subroutine.

    Cuts around all 6 vertices at relative depth. Use L parameter for multi-pass.
    Supports three entry types: vertical plunge, ramped entry, or helical entry.

    Arc slowdown: Helix arc moves use feed_rate * arc_feed_factor. The hexagon
    profile cuts are linear (G01), so arc_feed_factor only affects the helix.

    Args:
        vertices: List of 6 (x, y) vertex coordinates (absolute)
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate (in/min)
        feed_rate: Base cutting feed rate (in/min)
        lead_in_point: (x, y) lead-in point for ramped entry
        lead_in_type: Entry type - 'none', 'ramp', or 'helical'
        center: (x, y) hexagon center for helical entry
        helix_radius: Radius for helical entry
        helix_pitch: Z drop per revolution for helical entry
        approach_angle: Direction tool approaches from in degrees (0=top, 90=right)
                       Default 90° matches original 3 o'clock position
        hold_time: Dwell time in seconds at start of each pass (0 = no dwell)
        arc_feed_factor: Multiplier for arc moves (default 1.0, use 0.8 for 80%)

    Returns:
        Complete subroutine file content
    """
    lines = []

    profile_start_x, profile_start_y = vertices[0]

    # Convert user angle to math angle for helix position calculations
    math_angle = _user_angle_to_math_angle(approach_angle)

    if lead_in_type == 'helical' and center is not None and helix_radius is not None and helix_radius > 0:
        # Helical lead-in: spiral down at center, then linear to first vertex
        center_x, center_y = center
        lines.extend(generate_helical_preamble_hexagon(
            center_x, center_y, helix_radius,
            profile_start_x, profile_start_y,
            pass_depth, helix_pitch, plunge_rate, feed_rate,
            approach_angle, arc_feed_factor
        ))
        # Track helix end position for lead-out (at approach angle)
        helix_end_x = center_x + helix_radius * math.cos(math_angle)
        helix_end_y = center_y + helix_radius * math.sin(math_angle)
    elif lead_in_type == 'ramp' and lead_in_point is not None:
        lead_in_x, lead_in_y = lead_in_point
        lines.extend(generate_ramp_preamble_absolute(
            lead_in_x, lead_in_y,
            profile_start_x, profile_start_y,
            pass_depth, plunge_rate
        ))
        helix_end_x, helix_end_y = None, None
    else:
        lines.extend(generate_cut_preamble(pass_depth, plunge_rate))
        helix_end_x, helix_end_y = None, None

    # Add dwell right after G91, before plunge - value in milliseconds for Mach3
    if hold_time > 0:
        hold_time_ms = int(hold_time * 1000)
        lines.insert(1, f"G04 P{hold_time_ms}")

    # Cut to each vertex (starting from second, as we start at first)
    for i in range(1, len(vertices)):
        x, y = vertices[i]
        lines.append(f"G01 X{format_coordinate(x)} Y{format_coordinate(y)} F{format_coordinate(feed_rate, 1)}")

    # Close back to first vertex
    x, y = vertices[0]
    lines.append(f"G01 X{format_coordinate(x)} Y{format_coordinate(y)}")

    # Lead-out based on entry type
    if lead_in_type == 'helical' and helix_end_x is not None:
        # Return to helix start position for next pass
        lines.append(f"G01 X{format_coordinate(helix_end_x)} Y{format_coordinate(helix_end_y)}")
    elif lead_in_type == 'ramp' and lead_in_point is not None:
        # Lead-out: return to lead-in point at cutting depth
        lead_in_x, lead_in_y = lead_in_point
        lines.append(f"G01 X{format_coordinate(lead_in_x)} Y{format_coordinate(lead_in_y)}")

    return generate_subroutine_file(lines)


def generate_line_path_subroutine(
    path: List[dict],
    pass_depth: float,
    plunge_rate: float,
    feed_rate: float,
    lead_in_point: Optional[Tuple[float, float]] = None,
    hold_time: float = 0
) -> str:
    """
    Generate a single-pass line path cut subroutine.

    Supports straight lines and arcs. Use L parameter for multi-pass.
    When lead_in_point is provided, uses ramped entry instead of vertical plunge.
    For closed paths with lead-in, returns to lead-in point after completing path.

    Args:
        path: List of path points with 'x', 'y', 'line_type', and optional arc data
        pass_depth: Depth increment per pass
        plunge_rate: Plunge feed rate (in/min)
        feed_rate: Cutting feed rate (in/min)
        lead_in_point: Optional (x, y) lead-in point for ramped entry
        hold_time: Dwell time in seconds at start of each pass (0 = no dwell)

    Returns:
        Complete subroutine file content
    """
    if not path:
        return generate_subroutine_file([])

    lines = []

    profile_start_x = path[0].get('x', 0)
    profile_start_y = path[0].get('y', 0)

    if lead_in_point is not None:
        lead_in_x, lead_in_y = lead_in_point
        lines.extend(generate_ramp_preamble_absolute(
            lead_in_x, lead_in_y,
            profile_start_x, profile_start_y,
            pass_depth, plunge_rate
        ))
    else:
        lines.extend(generate_cut_preamble(pass_depth, plunge_rate))

    # Add dwell right after G91, before plunge - value in milliseconds for Mach3
    if hold_time > 0:
        hold_time_ms = int(hold_time * 1000)
        lines.insert(1, f"G04 P{hold_time_ms}")

    # Track current position for arc calculations
    current_x = profile_start_x
    current_y = profile_start_y

    # Process each point after the start
    for point in path[1:]:
        x = point.get('x', 0)
        y = point.get('y', 0)
        line_type = point.get('line_type', 'straight')

        if line_type == 'arc':
            # Arc move
            arc_center_x = point.get('arc_center_x', x)
            arc_center_y = point.get('arc_center_y', y)
            arc_dir_hint = point.get('arc_direction')

            # Calculate I, J offsets
            i_offset = arc_center_x - current_x
            j_offset = arc_center_y - current_y

            # Determine direction
            from .arc_utils import calculate_arc_direction
            direction = calculate_arc_direction(
                (current_x, current_y),
                (x, y),
                (arc_center_x, arc_center_y),
                arc_dir_hint
            )

            lines.append(
                f"{direction} X{format_coordinate(x)} Y{format_coordinate(y)} "
                f"I{format_coordinate(i_offset)} J{format_coordinate(j_offset)} "
                f"F{format_coordinate(feed_rate, 1)}"
            )
        else:
            # Straight line
            lines.append(
                f"G01 X{format_coordinate(x)} Y{format_coordinate(y)} "
                f"F{format_coordinate(feed_rate, 1)}"
            )

        current_x = x
        current_y = y

    # For closed paths with lead-in, return to lead-in point
    if lead_in_point is not None:
        from .lead_in import is_closed_path
        if is_closed_path(path):
            lead_in_x, lead_in_y = lead_in_point
            lines.append(f"G01 X{format_coordinate(lead_in_x)} Y{format_coordinate(lead_in_y)}")

    return generate_subroutine_file(lines)
