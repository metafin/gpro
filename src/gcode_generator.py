"""G-code generation module for CNC machining operations.

This module orchestrates G-code generation from project data, supporting:
- Drilling operations with peck cycles
- Circular cuts with multi-pass
- Hexagonal cuts with tool compensation
- Line cuts with arc support
- M98 subroutine calls for repeated operations
"""
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .hexagon_generator import calculate_compensated_vertices
from .utils.multipass import calculate_num_passes, calculate_pass_depths, iter_passes
from .utils.tool_compensation import calculate_cut_radius, compensate_line_path
from .utils.gcode_format import (
    format_coordinate,
    generate_header,
    generate_footer,
    generate_rapid_move,
    generate_linear_move,
    generate_arc_move,
    generate_subroutine_call,
    sanitize_project_name
)
from .utils.arc_utils import calculate_arc_direction, calculate_ij_offsets
from .utils.subroutine_generator import (
    get_next_subroutine_number,
    build_subroutine_path,
    generate_peck_drill_subroutine,
    generate_circle_pass_subroutine,
    generate_hexagon_pass_subroutine,
    generate_line_path_subroutine
)
from .utils.validators import validate_arc_geometry
from .utils.lead_in import (
    calculate_lead_in_distance,
    calculate_circle_lead_in_point,
    calculate_hexagon_lead_in_point,
    calculate_line_lead_in_point,
    is_closed_path,
    calculate_helix_radius_for_circle,
    calculate_helix_radius_for_hexagon,
    calculate_helix_start_point,
    generate_helical_lead_in,
    generate_helical_to_profile_circle,
    generate_helical_to_profile_hexagon,
    adjust_helix_depth
)
from .utils.corner_detection import generate_corner_slowdown_points
from .utils.safety import create_safety_coordinator, FeedContext


@dataclass
class GenerationSettings:
    """Settings needed for G-code generation."""
    safety_height: float
    travel_height: float
    spindle_warmup_seconds: int
    supports_subroutines: bool
    supports_canned_cycles: bool
    gcode_base_path: str
    max_x: float
    max_y: float
    # Per-cut-type lead-in settings
    circle_lead_in_type: str = 'helical'  # 'none', 'ramp', 'helical'
    hexagon_lead_in_type: str = 'helical'  # 'none', 'ramp', 'helical'
    line_lead_in_type: str = 'ramp'  # 'none', 'ramp' (no helical for lines)
    ramp_angle: float = 3.0  # Ramp entry angle in degrees (2-5° recommended)
    helix_pitch: float = 0.04  # Z drop per revolution for helical lead-in
    first_pass_feed_factor: float = 0.7  # Reduce first pass feed to 70%
    max_stepdown_factor: float = 0.5  # Warn if pass_depth > 50% of tool diameter
    corner_slowdown_enabled: bool = True
    corner_feed_factor: float = 0.5  # Reduce feed to 50% at sharp corners
    arc_slowdown_enabled: bool = True
    arc_feed_factor: float = 0.8  # Reduce feed to 80% on arcs


@dataclass
class ToolParams:
    """Tool-specific cutting parameters."""
    spindle_speed: int
    feed_rate: float
    plunge_rate: float
    pecking_depth: Optional[float] = None  # For drills
    pass_depth: Optional[float] = None      # For end mills
    tool_diameter: float = 0.125


@dataclass
class GenerationResult:
    """Result of G-code generation."""
    main_gcode: str
    subroutines: Dict[int, str]  # number -> content
    project_name: str
    warnings: List[str]


@dataclass
class PathMove:
    """A single move in a cutting path."""
    x: float
    y: float
    move_type: str = 'linear'  # 'linear', 'arc', 'full_circle'
    # Arc params (when move_type is 'arc' or 'full_circle')
    arc_center_x: Optional[float] = None
    arc_center_y: Optional[float] = None
    arc_direction: Optional[str] = None  # 'G02', 'G03', or None for auto
    i_offset: Optional[float] = None  # For full_circle
    j_offset: Optional[float] = None
    corner_feed_factor: float = 1.0  # For corner slowdown


@dataclass
class LeadInConfig:
    """Lead-in strategy configuration."""
    lead_in_type: str = 'none'  # 'none', 'ramp', 'helical'
    lead_in_point: Optional[Tuple[float, float]] = None
    helix_center: Optional[Tuple[float, float]] = None
    helix_radius: Optional[float] = None
    helix_pitch: float = 0.04
    profile_transition: str = 'arc'  # 'arc' or 'linear'
    profile_transition_target: Optional[Tuple[float, float]] = None
    approach_angle: float = 90  # Direction tool approaches from (0=top, 90=right)


@dataclass
class CutPathConfig:
    """Complete cutting path configuration."""
    moves: List[PathMove]
    profile_start: Tuple[float, float]
    lead_in: LeadInConfig
    is_closed: bool = True
    apply_corner_slowdown: bool = False
    shape_type: str = 'generic'  # 'circle', 'hexagon', 'line'


class WebGCodeGenerator:
    """G-code generator for web application integration."""

    def __init__(
        self,
        settings: GenerationSettings,
        project_name: str,
        material_depth: float
    ):
        """
        Initialize the generator.

        Args:
            settings: Generation settings from database
            project_name: Name of the project (will be sanitized)
            material_depth: Depth of material to cut through
        """
        self.settings = settings
        self.project_name = sanitize_project_name(project_name)
        self.material_depth = material_depth
        self.subroutines: Dict[int, str] = {}
        self.used_subroutine_numbers: List[int] = []
        self.warnings: List[str] = []
        # Default lead-in distance (will be recalculated in generate() based on pass_depth)
        self.lead_in_distance = 0.25
        # Safety coordinator for feed rate adjustments
        self.safety_coordinator = create_safety_coordinator(settings)

    def _get_adjusted_feed(
        self,
        base_feed_rate: float,
        pass_num: int,
        is_arc: bool = False,
        corner_factor: float = 1.0
    ) -> float:
        """
        Get the feed rate with all safety adjustments applied.

        This is the main method for getting feed rates with safety features.
        It uses the safety coordinator to apply all enabled adjustments.

        Args:
            base_feed_rate: Normal feed rate
            pass_num: Zero-indexed pass number
            is_arc: True if this is an arc move (G02/G03)
            corner_factor: Corner severity factor (1.0 = not a corner)

        Returns:
            Adjusted feed rate with all applicable safety reductions
        """
        context = FeedContext(
            base_feed=base_feed_rate,
            pass_num=pass_num,
            is_arc=is_arc,
            corner_factor=corner_factor
        )
        return self.safety_coordinator.get_adjusted_feed(base_feed_rate, context)

    def _generate_move_from_path(
        self,
        move: PathMove,
        current_pos: Tuple[float, float],
        feed: float
    ) -> str:
        """
        Generate G-code for a single path move.

        Args:
            move: PathMove object describing the move
            current_pos: Current (x, y) position
            feed: Feed rate for this move

        Returns:
            G-code command string
        """
        if move.move_type == 'full_circle':
            # Full circle using I/J offsets
            return (
                f"G02 I{format_coordinate(move.i_offset)} J{format_coordinate(move.j_offset)} "
                f"F{format_coordinate(feed, 1)}"
            )
        elif move.move_type == 'arc':
            # Arc move with center point
            arc_cx = move.arc_center_x if move.arc_center_x is not None else move.x
            arc_cy = move.arc_center_y if move.arc_center_y is not None else move.y
            direction = move.arc_direction
            if direction is None:
                direction = calculate_arc_direction(
                    current_pos, (move.x, move.y), (arc_cx, arc_cy)
                )
            i, j = calculate_ij_offsets(current_pos, (arc_cx, arc_cy))
            return (
                f"{direction} X{format_coordinate(move.x)} Y{format_coordinate(move.y)} "
                f"I{format_coordinate(i)} J{format_coordinate(j)} "
                f"F{format_coordinate(feed, 1)}"
            )
        else:
            # Linear move
            return generate_linear_move(x=move.x, y=move.y, feed=feed)

    def _generate_path_cut(
        self,
        config: CutPathConfig,
        params: ToolParams
    ) -> List[str]:
        """
        Generate G-code for a cutting path using unified logic.

        This method handles all shape types (circle, hexagon, line) using a
        common path representation. It manages:
        - Multi-pass iteration with depth accumulation
        - Lead-in handling (helical, ramp, none)
        - Feed rate adjustments (first pass, corners, arcs)
        - Safety height movements

        Args:
            config: Complete path configuration including moves and lead-in
            params: Tool-specific cutting parameters

        Returns:
            List of G-code lines
        """
        lines = []
        pass_depth = params.pass_depth or 0.025
        lead_in = config.lead_in
        approach_angle = lead_in.approach_angle

        # Determine starting position based on lead-in type
        if lead_in.lead_in_type == 'helical' and lead_in.helix_center and lead_in.helix_radius:
            start_x, start_y = calculate_helix_start_point(
                lead_in.helix_center[0], lead_in.helix_center[1], lead_in.helix_radius,
                approach_angle
            )
        elif lead_in.lead_in_type == 'ramp' and lead_in.lead_in_point:
            start_x, start_y = lead_in.lead_in_point
        else:
            start_x, start_y = config.profile_start

        # Rapid to start position
        lines.append(generate_rapid_move(x=start_x, y=start_y, z=self.settings.travel_height))
        lines.append(generate_rapid_move(z=0))

        # Multi-pass cutting
        for pass_num, current_depth, actual_pass_depth in iter_passes(self.material_depth, pass_depth):
            current_feed = self._get_adjusted_feed(params.feed_rate, pass_num)

            # Execute lead-in based on type
            if lead_in.lead_in_type == 'helical' and lead_in.helix_center and lead_in.helix_radius:
                # Helical descent with feed ramping from plunge_rate to current_feed
                helix_lines = generate_helical_lead_in(
                    lead_in.helix_center[0], lead_in.helix_center[1],
                    lead_in.helix_radius, actual_pass_depth,
                    lead_in.helix_pitch, params.plunge_rate,
                    approach_angle, end_feed=current_feed
                )
                lines.extend(adjust_helix_depth(helix_lines, actual_pass_depth, current_depth))

                # Transition to profile (at current_feed since helix ramped up to it)
                if lead_in.profile_transition == 'arc' and lead_in.profile_transition_target:
                    # Arc transition (for circles) - calculate profile radius from target
                    target_x, target_y = lead_in.profile_transition_target
                    cx, cy = lead_in.helix_center
                    profile_radius = math.sqrt((target_x - cx) ** 2 + (target_y - cy) ** 2)
                    # Only add arc if helix radius differs from profile radius
                    if abs(lead_in.helix_radius - profile_radius) > 0.001:
                        arc_lines = generate_helical_to_profile_circle(
                            cx, cy,
                            lead_in.helix_radius, profile_radius, current_feed,
                            approach_angle
                        )
                        lines.extend(arc_lines)
                elif lead_in.profile_transition == 'linear' and lead_in.profile_transition_target:
                    # Linear transition (for hexagons)
                    target_x, target_y = lead_in.profile_transition_target
                    helix_start_x, helix_start_y = calculate_helix_start_point(
                        lead_in.helix_center[0], lead_in.helix_center[1],
                        lead_in.helix_radius, approach_angle
                    )
                    hex_to_vertex = generate_helical_to_profile_hexagon(
                        helix_start_x, helix_start_y,
                        target_x, target_y, current_feed,
                        approach_angle
                    )
                    lines.extend(hex_to_vertex)

            elif lead_in.lead_in_type == 'ramp' and lead_in.lead_in_point:
                # Ramp from lead-in to profile start while descending
                profile_x, profile_y = config.profile_start
                lines.append(
                    f"G01 X{format_coordinate(profile_x)} Y{format_coordinate(profile_y)} "
                    f"Z{format_coordinate(-current_depth)} F{format_coordinate(params.plunge_rate, 1)}"
                )
            else:
                # Vertical plunge
                lines.append(generate_linear_move(z=-current_depth, feed=params.plunge_rate))

            # Execute path moves
            current_x, current_y = config.profile_start
            for move in config.moves:
                # Apply corner slowdown if configured
                move_feed = current_feed
                if config.apply_corner_slowdown and move.corner_feed_factor < 1.0:
                    move_feed = self._get_adjusted_feed(
                        params.feed_rate, pass_num,
                        is_arc=(move.move_type == 'arc'),
                        corner_factor=move.corner_feed_factor
                    )
                elif move.move_type == 'arc':
                    move_feed = self._get_adjusted_feed(
                        params.feed_rate, pass_num, is_arc=True
                    )

                lines.append(self._generate_move_from_path(move, (current_x, current_y), move_feed))
                current_x, current_y = move.x, move.y

            # Lead-out for closed paths
            if config.is_closed:
                if lead_in.lead_in_type == 'helical' and lead_in.helix_center and lead_in.helix_radius:
                    # Return to helix start (at approach angle)
                    helix_start_x, helix_start_y = calculate_helix_start_point(
                        lead_in.helix_center[0], lead_in.helix_center[1],
                        lead_in.helix_radius, approach_angle
                    )
                    lines.append(
                        f"G01 X{format_coordinate(helix_start_x)} Y{format_coordinate(helix_start_y)} "
                        f"F{format_coordinate(current_feed, 1)}"
                    )
                elif lead_in.lead_in_type == 'ramp' and lead_in.lead_in_point:
                    # Return to lead-in point
                    lead_x, lead_y = lead_in.lead_in_point
                    lines.append(
                        f"G01 X{format_coordinate(lead_x)} Y{format_coordinate(lead_y)} "
                        f"F{format_coordinate(current_feed, 1)}"
                    )

        # Retract to safety height
        lines.append(generate_rapid_move(z=self.settings.safety_height))
        return lines

    def _circle_to_path_config(
        self,
        circle: Dict[str, float],
        params: ToolParams
    ) -> CutPathConfig:
        """
        Convert circle data to unified path configuration.

        Args:
            circle: Circle dict with center_x, center_y, diameter, compensation
            params: Tool parameters

        Returns:
            CutPathConfig for the circle
        """
        cx, cy = circle['center_x'], circle['center_y']
        compensation = circle.get('compensation', 'interior')
        cut_radius = calculate_cut_radius(circle['diameter'], params.tool_diameter, compensation)

        # Determine lead-in settings (per-operation or global)
        lead_in_mode = circle.get('lead_in_mode', 'auto')
        if lead_in_mode == 'manual':
            lead_in_type = circle.get('lead_in_type', 'helical')
            approach_angle = circle.get('lead_in_approach_angle', 90)
        else:
            lead_in_type = self.settings.circle_lead_in_type
            approach_angle = 90  # Default for auto mode

        # Convert approach angle to math angle for profile start calculation
        # User angle convention: 0° = top, 90° = right (clockwise)
        # Math convention: 0° = right, 90° = top (counter-clockwise)
        math_angle = math.radians(90 - approach_angle)

        # Profile start at approach angle position
        profile_start = (
            cx + cut_radius * math.cos(math_angle),
            cy + cut_radius * math.sin(math_angle)
        )

        # Configure lead-in
        helix_radius = None
        if lead_in_type == 'helical':
            helix_radius = calculate_helix_radius_for_circle(cut_radius, params.tool_diameter)
        effective_lead_in_type, helix_radius = self._determine_effective_lead_in(
            lead_in_type, helix_radius, f"Circle d={circle['diameter']}\""
        )

        lead_in = LeadInConfig(lead_in_type='none', approach_angle=approach_angle)
        if effective_lead_in_type == 'helical' and helix_radius:
            lead_in = LeadInConfig(
                lead_in_type='helical',
                helix_center=(cx, cy),
                helix_radius=helix_radius,
                helix_pitch=self.settings.helix_pitch,
                profile_transition='arc',
                profile_transition_target=profile_start,
                approach_angle=approach_angle
            )
        elif effective_lead_in_type == 'ramp' and self.lead_in_distance > 0:
            lead_in_point = calculate_circle_lead_in_point(
                cx, cy, cut_radius, self.lead_in_distance, approach_angle
            )
            lead_in = LeadInConfig(
                lead_in_type='ramp',
                lead_in_point=lead_in_point,
                approach_angle=approach_angle
            )

        # Circle is a single full-circle move with I/J pointing to center from approach angle
        i_offset = -cut_radius * math.cos(math_angle)
        j_offset = -cut_radius * math.sin(math_angle)
        moves = [PathMove(
            x=profile_start[0],
            y=profile_start[1],
            move_type='full_circle',
            i_offset=i_offset,
            j_offset=j_offset
        )]

        return CutPathConfig(
            moves=moves,
            profile_start=profile_start,
            lead_in=lead_in,
            is_closed=True,
            apply_corner_slowdown=False,
            shape_type='circle'
        )

    def _hexagon_to_path_config(
        self,
        hexagon: Dict[str, float],
        params: ToolParams
    ) -> CutPathConfig:
        """
        Convert hexagon data to unified path configuration.

        Args:
            hexagon: Hexagon dict with center_x, center_y, flat_to_flat, compensation
            params: Tool parameters

        Returns:
            CutPathConfig for the hexagon
        """
        cx, cy = hexagon['center_x'], hexagon['center_y']
        flat_to_flat = hexagon['flat_to_flat']
        compensation = hexagon.get('compensation', 'interior')

        vertices = calculate_compensated_vertices(
            cx, cy, flat_to_flat, params.tool_diameter, compensation
        )
        profile_start = vertices[0]

        # Determine lead-in settings (per-operation or global)
        lead_in_mode = hexagon.get('lead_in_mode', 'auto')
        if lead_in_mode == 'manual':
            lead_in_type = hexagon.get('lead_in_type', 'helical')
            approach_angle = hexagon.get('lead_in_approach_angle', 90)
        else:
            lead_in_type = self.settings.hexagon_lead_in_type
            approach_angle = 90  # Default for auto mode

        # Configure lead-in
        helix_radius = None
        if lead_in_type == 'helical':
            helix_radius = calculate_helix_radius_for_hexagon(
                flat_to_flat, params.tool_diameter, compensation
            )
        effective_lead_in_type, helix_radius = self._determine_effective_lead_in(
            lead_in_type, helix_radius,
            f"Hexagon ftf={flat_to_flat}\" at ({cx}, {cy})"
        )

        lead_in = LeadInConfig(lead_in_type='none', approach_angle=approach_angle)
        if effective_lead_in_type == 'helical' and helix_radius:
            lead_in = LeadInConfig(
                lead_in_type='helical',
                helix_center=(cx, cy),
                helix_radius=helix_radius,
                helix_pitch=self.settings.helix_pitch,
                profile_transition='linear',
                profile_transition_target=profile_start,
                approach_angle=approach_angle
            )
        elif effective_lead_in_type == 'ramp' and self.lead_in_distance > 0:
            lead_in_point = calculate_hexagon_lead_in_point(
                vertices, self.lead_in_distance,
                center=(cx, cy), approach_angle=approach_angle if lead_in_mode == 'manual' else None
            )
            lead_in = LeadInConfig(
                lead_in_type='ramp',
                lead_in_point=lead_in_point,
                approach_angle=approach_angle
            )

        # Build moves for hexagon: traverse all vertices and close
        moves = []
        for i in range(1, len(vertices)):
            vx, vy = vertices[i]
            moves.append(PathMove(x=vx, y=vy, move_type='linear'))
        # Close back to start
        moves.append(PathMove(x=profile_start[0], y=profile_start[1], move_type='linear'))

        return CutPathConfig(
            moves=moves,
            profile_start=profile_start,
            lead_in=lead_in,
            is_closed=True,
            apply_corner_slowdown=False,
            shape_type='hexagon'
        )

    def _line_to_path_config(
        self,
        path: List[Dict],
        params: ToolParams,
        compensation: str = 'none',
        operation: Optional[Dict] = None
    ) -> CutPathConfig:
        """
        Convert line path data to unified path configuration.

        Args:
            path: List of path points (already compensated if needed)
            params: Tool parameters
            compensation: Compensation type for lead-in calculation
            operation: Optional operation dict with lead-in settings

        Returns:
            CutPathConfig for the line
        """
        if not path:
            return CutPathConfig(
                moves=[],
                profile_start=(0, 0),
                lead_in=LeadInConfig(),
                is_closed=False,
                shape_type='line'
            )

        # Pre-process path for corner slowdown
        if self.settings.corner_slowdown_enabled:
            processed_path = generate_corner_slowdown_points(
                path,
                angle_threshold=120.0,
                base_feed_factor=self.settings.corner_feed_factor
            )
        else:
            processed_path = path

        start_x = processed_path[0].get('x', 0)
        start_y = processed_path[0].get('y', 0)
        profile_start = (start_x, start_y)
        path_is_closed = is_closed_path(processed_path)

        # Determine lead-in settings (per-operation or global)
        if operation:
            lead_in_mode = operation.get('lead_in_mode', 'auto')
        else:
            lead_in_mode = 'auto'

        if lead_in_mode == 'manual' and operation:
            lead_in_type = operation.get('lead_in_type', 'ramp')
            approach_angle = operation.get('lead_in_approach_angle', 90)
        else:
            lead_in_type = self.settings.line_lead_in_type
            approach_angle = None  # Use automatic direction for auto mode

        # Configure lead-in (lines only support ramp)
        lead_in = LeadInConfig(lead_in_type='none', approach_angle=approach_angle or 90)
        use_lead_in = lead_in_type == 'ramp' and self.lead_in_distance > 0

        if use_lead_in:
            lead_in_point = calculate_line_lead_in_point(
                processed_path, self.lead_in_distance, compensation, approach_angle
            )
            lead_in = LeadInConfig(
                lead_in_type='ramp',
                lead_in_point=lead_in_point,
                approach_angle=approach_angle or 90
            )

        # Build moves from path points
        moves = []
        for point in processed_path[1:]:
            x = point.get('x', 0)
            y = point.get('y', 0)
            line_type = point.get('line_type', 'straight')
            corner_factor = point.get('corner_feed_factor', 1.0)

            if line_type == 'arc':
                moves.append(PathMove(
                    x=x,
                    y=y,
                    move_type='arc',
                    arc_center_x=point.get('arc_center_x'),
                    arc_center_y=point.get('arc_center_y'),
                    arc_direction=point.get('arc_direction'),
                    corner_feed_factor=corner_factor
                ))
            else:
                moves.append(PathMove(
                    x=x,
                    y=y,
                    move_type='linear',
                    corner_feed_factor=corner_factor
                ))

        return CutPathConfig(
            moves=moves,
            profile_start=profile_start,
            lead_in=lead_in,
            is_closed=path_is_closed,
            apply_corner_slowdown=self.settings.corner_slowdown_enabled,
            shape_type='line'
        )

    def _determine_effective_lead_in(
        self,
        lead_in_type: str,
        helix_radius: Optional[float],
        shape_desc: str
    ) -> Tuple[str, Optional[float]]:
        """
        Determine effective lead-in type, falling back to ramp if helix not possible.

        Args:
            lead_in_type: Requested lead-in type ('none', 'ramp', 'helical')
            helix_radius: Calculated helix radius (None if helix not possible)
            shape_desc: Description for warning message (e.g., "Circle d=0.5\"")

        Returns:
            Tuple of (effective_lead_in_type, helix_radius)
        """
        if lead_in_type == 'helical' and helix_radius is None:
            self.warnings.append(
                f"{shape_desc} too small for helical lead-in, using ramp"
            )
            return ('ramp', None)
        return (lead_in_type, helix_radius)

    def generate_drill_gcode(
        self,
        drill_points: List[Tuple[float, float]],
        params: ToolParams,
        operations: List[Dict] = None
    ) -> List[str]:
        """
        Generate G-code for drilling operations.

        Args:
            drill_points: List of (x, y) drill coordinates
            params: Drilling parameters
            operations: Original operations (for pattern detection)

        Returns:
            List of G-code lines for main file
        """
        if not drill_points:
            return []

        lines = []
        pecking_depth = params.pecking_depth or 0.05

        # Calculate peck sequence
        pecks = calculate_pass_depths(self.material_depth, pecking_depth)

        # Check if we should use subroutines
        use_subroutines = (
            self.settings.supports_subroutines and
            operations and
            len(drill_points) > 1
        )

        if use_subroutines and operations:
            # Generate subroutine-based drilling
            lines.extend(self._generate_drill_with_subroutines(
                drill_points, params, pecks, operations
            ))
        else:
            # Generate inline drilling
            lines.extend(self._generate_drill_inline(
                drill_points, params, pecks
            ))

        return lines

    def _generate_drill_inline(
        self,
        points: List[Tuple[float, float]],
        params: ToolParams,
        pecks: List[float]
    ) -> List[str]:
        """Generate inline (no subroutine) drilling G-code."""
        lines = []

        for x, y in points:
            # Move to position
            lines.append(generate_rapid_move(x=x, y=y, z=self.settings.travel_height))
            lines.append(generate_rapid_move(z=0))

            # Peck drill cycle
            for peck_depth in pecks:
                lines.append(generate_linear_move(z=-peck_depth, feed=params.plunge_rate))
                lines.append(generate_rapid_move(z=self.settings.safety_height))
                if peck_depth < pecks[-1]:  # Not the last peck
                    lines.append(generate_rapid_move(z=0))

        return lines

    def _generate_drill_with_subroutines(
        self,
        points: List[Tuple[float, float]],
        params: ToolParams,
        pecks: List[float],
        operations: List[Dict]
    ) -> List[str]:
        """Generate subroutine-based drilling G-code."""
        lines = []

        # Group points by pattern for efficient subroutine use
        for op in operations:
            op_type = op.get('type', 'single')

            if op_type == 'single':
                # Single holes inline
                x, y = op['x'], op['y']
                lines.append(generate_rapid_move(x=x, y=y, z=self.settings.travel_height))
                lines.append(generate_rapid_move(z=0))
                for peck_depth in pecks:
                    lines.append(generate_linear_move(z=-peck_depth, feed=params.plunge_rate))
                    lines.append(generate_rapid_move(z=self.settings.safety_height))
                    if peck_depth < pecks[-1]:
                        lines.append(generate_rapid_move(z=0))

            elif op_type == 'pattern_linear':
                # Linear pattern uses subroutine
                sub_num = get_next_subroutine_number('drill', self.used_subroutine_numbers)
                self.used_subroutine_numbers.append(sub_num)

                sub_content = generate_peck_drill_subroutine(
                    pecks, params.plunge_rate, self.settings.travel_height,
                    op['axis'], op['spacing']
                )
                self.subroutines[sub_num] = sub_content

                # Position at start and call subroutine
                lines.append(generate_rapid_move(
                    x=op['start_x'], y=op['start_y'], z=self.settings.travel_height
                ))
                sub_path = build_subroutine_path(
                    self.settings.gcode_base_path, self.project_name, sub_num
                )
                lines.append(generate_subroutine_call(sub_path, op['count']))

            elif op_type == 'pattern_grid':
                # Grid pattern: subroutine for rows, loop through columns
                sub_num = get_next_subroutine_number('drill', self.used_subroutine_numbers)
                self.used_subroutine_numbers.append(sub_num)

                sub_content = generate_peck_drill_subroutine(
                    pecks, params.plunge_rate, self.settings.travel_height,
                    'x', op['x_spacing']
                )
                self.subroutines[sub_num] = sub_content

                sub_path = build_subroutine_path(
                    self.settings.gcode_base_path, self.project_name, sub_num
                )

                # Call subroutine for each row
                for row in range(op['y_count']):
                    y_pos = op['start_y'] + row * op['y_spacing']
                    lines.append(generate_rapid_move(
                        x=op['start_x'], y=y_pos, z=self.settings.travel_height
                    ))
                    lines.append(generate_subroutine_call(sub_path, op['x_count']))

        return lines

    def generate_circular_gcode(
        self,
        circles: List[Dict[str, float]],
        params: ToolParams
    ) -> List[str]:
        """
        Generate G-code for circular cuts.

        Supports three entry types:
        - none: Vertical plunge (highest risk of tool breakage)
        - ramp: Linear ramped entry (good for lines, fallback for circles)
        - helical: Spiral descent (best for circles, reduces tool stress)

        Args:
            circles: List of dicts with center_x, center_y, diameter, and optional compensation
            params: Cutting parameters

        Returns:
            List of G-code lines for main file
        """
        if not circles:
            return []

        lines = []
        pass_depth = params.pass_depth or 0.025
        num_passes = calculate_num_passes(self.material_depth, pass_depth)
        actual_pass_depth = self.material_depth / num_passes

        # Determine lead-in type (circle-specific setting)
        lead_in_type = self.settings.circle_lead_in_type

        # Separate circles with manual lead-in settings (use inline) from auto (can use subroutines)
        auto_circles = []
        manual_circles = []
        for circle in circles:
            if circle.get('lead_in_mode') == 'manual':
                manual_circles.append(circle)
            else:
                auto_circles.append(circle)

        # Handle circles with manual lead-in settings inline (supports custom approach angles)
        for circle in manual_circles:
            lines.extend(self._generate_circle_inline(circle, params))

        # Create subroutine for circle cutting if supported (auto mode only)
        if self.settings.supports_subroutines and auto_circles:
            # Group circles by (diameter, compensation, hold_time) for shared subroutines
            # Different compensation types need different cut radii
            circle_groups: Dict[Tuple[float, str, float], List[Dict]] = {}
            for circle in auto_circles:
                d = circle['diameter']
                comp = circle.get('compensation', 'interior')
                hold_time = circle.get('hold_time', 0)
                key = (d, comp, hold_time)
                if key not in circle_groups:
                    circle_groups[key] = []
                circle_groups[key].append(circle)

            for (diameter, compensation, hold_time), group in circle_groups.items():
                cut_radius = calculate_cut_radius(diameter, params.tool_diameter, compensation)

                # Calculate helix radius if using helical lead-in
                helix_radius = None
                if lead_in_type == 'helical':
                    helix_radius = calculate_helix_radius_for_circle(
                        cut_radius, params.tool_diameter
                    )
                effective_lead_in_type, helix_radius = self._determine_effective_lead_in(
                    lead_in_type, helix_radius, f"Circle d={diameter}\""
                )

                sub_num = get_next_subroutine_number('circular', self.used_subroutine_numbers)
                self.used_subroutine_numbers.append(sub_num)

                # Auto mode uses default 90° approach angle
                sub_content = generate_circle_pass_subroutine(
                    cut_radius, actual_pass_depth, params.plunge_rate, params.feed_rate,
                    lead_in_distance=self.lead_in_distance if effective_lead_in_type == 'ramp' else None,
                    lead_in_type=effective_lead_in_type,
                    helix_radius=helix_radius,
                    helix_pitch=self.settings.helix_pitch,
                    approach_angle=90,
                    hold_time=hold_time
                )
                self.subroutines[sub_num] = sub_content

                sub_path = build_subroutine_path(
                    self.settings.gcode_base_path, self.project_name, sub_num
                )

                for circle in group:
                    cx, cy = circle['center_x'], circle['center_y']

                    if effective_lead_in_type == 'helical' and helix_radius:
                        # Position at helix start (3 o'clock on helix)
                        helix_start_x, helix_start_y = calculate_helix_start_point(
                            cx, cy, helix_radius
                        )
                        lines.append(generate_rapid_move(x=helix_start_x, y=helix_start_y, z=self.settings.travel_height))
                    elif effective_lead_in_type == 'ramp' and self.lead_in_distance:
                        # Position at lead-in point (offset radially outward)
                        lead_in_x, lead_in_y = calculate_circle_lead_in_point(
                            cx, cy, cut_radius, self.lead_in_distance
                        )
                        lines.append(generate_rapid_move(x=lead_in_x, y=lead_in_y, z=self.settings.travel_height))
                    else:
                        # Position at profile start (3 o'clock)
                        start_x = cx + cut_radius
                        lines.append(generate_rapid_move(x=start_x, y=cy, z=self.settings.travel_height))

                    lines.append(generate_rapid_move(z=0))
                    lines.append(generate_subroutine_call(sub_path, num_passes))
                    lines.append(generate_rapid_move(z=self.settings.safety_height))
        elif auto_circles:
            # Inline generation for auto circles when subroutines not supported
            for circle in auto_circles:
                lines.extend(self._generate_circle_inline(circle, params))

        return lines

    def _generate_circle_inline(
        self,
        circle: Dict[str, float],
        params: ToolParams
    ) -> List[str]:
        """Generate inline circle cut G-code using unified path cutting."""
        config = self._circle_to_path_config(circle, params)
        return self._generate_path_cut(config, params)

    def generate_hexagonal_gcode(
        self,
        hexagons: List[Dict[str, float]],
        params: ToolParams
    ) -> List[str]:
        """
        Generate G-code for hexagonal cuts.

        Supports three entry types:
        - none: Vertical plunge at first vertex
        - ramp: Linear ramped entry along first edge direction
        - helical: Spiral descent at center, then linear to first vertex

        Args:
            hexagons: List of dicts with center_x, center_y, flat_to_flat, and optional compensation
            params: Cutting parameters

        Returns:
            List of G-code lines for main file
        """
        if not hexagons:
            return []

        lines = []
        pass_depth = params.pass_depth or 0.025
        num_passes = calculate_num_passes(self.material_depth, pass_depth)
        actual_pass_depth = self.material_depth / num_passes

        # Determine lead-in type (hexagon-specific setting)
        global_lead_in_type = self.settings.hexagon_lead_in_type

        if self.settings.supports_subroutines:
            # Note: Hexagon subroutines use absolute coordinates for vertices,
            # so each hexagon at a different position needs its own subroutine.
            for hexagon in hexagons:
                flat_to_flat = hexagon['flat_to_flat']
                compensation = hexagon.get('compensation', 'interior')
                cx, cy = hexagon['center_x'], hexagon['center_y']
                hold_time = hexagon.get('hold_time', 0)

                vertices = calculate_compensated_vertices(
                    cx, cy, flat_to_flat, params.tool_diameter, compensation
                )

                # Determine lead-in settings (per-operation or global)
                lead_in_mode = hexagon.get('lead_in_mode', 'auto')
                if lead_in_mode == 'manual':
                    lead_in_type = hexagon.get('lead_in_type', 'helical')
                    approach_angle = hexagon.get('lead_in_approach_angle', 90)
                else:
                    lead_in_type = global_lead_in_type
                    approach_angle = 90  # Default for auto mode

                # Determine effective lead-in type and parameters
                lead_in_point = None
                helix_radius = None
                center = None

                if lead_in_type == 'helical':
                    helix_radius = calculate_helix_radius_for_hexagon(
                        flat_to_flat, params.tool_diameter, compensation
                    )
                effective_lead_in_type, helix_radius = self._determine_effective_lead_in(
                    lead_in_type, helix_radius,
                    f"Hexagon ftf={flat_to_flat}\" at ({cx}, {cy})"
                )
                if effective_lead_in_type == 'helical' and helix_radius:
                    center = (cx, cy)

                if effective_lead_in_type == 'ramp' and self.lead_in_distance > 0:
                    lead_in_point = calculate_hexagon_lead_in_point(
                        vertices, self.lead_in_distance,
                        center=(cx, cy), approach_angle=approach_angle if lead_in_mode == 'manual' else None
                    )

                sub_num = get_next_subroutine_number('hexagonal', self.used_subroutine_numbers)
                self.used_subroutine_numbers.append(sub_num)

                sub_content = generate_hexagon_pass_subroutine(
                    vertices, actual_pass_depth, params.plunge_rate, params.feed_rate,
                    lead_in_point=lead_in_point,
                    lead_in_type=effective_lead_in_type,
                    center=center,
                    helix_radius=helix_radius,
                    helix_pitch=self.settings.helix_pitch,
                    approach_angle=approach_angle,
                    hold_time=hold_time
                )
                self.subroutines[sub_num] = sub_content

                sub_path = build_subroutine_path(
                    self.settings.gcode_base_path, self.project_name, sub_num
                )

                # Position tool at start point based on entry type
                if effective_lead_in_type == 'helical' and helix_radius:
                    helix_start_x, helix_start_y = calculate_helix_start_point(
                        cx, cy, helix_radius, approach_angle
                    )
                    lines.append(generate_rapid_move(x=helix_start_x, y=helix_start_y, z=self.settings.travel_height))
                elif effective_lead_in_type == 'ramp' and lead_in_point:
                    lines.append(generate_rapid_move(x=lead_in_point[0], y=lead_in_point[1], z=self.settings.travel_height))
                else:
                    start_x, start_y = vertices[0]
                    lines.append(generate_rapid_move(x=start_x, y=start_y, z=self.settings.travel_height))

                lines.append(generate_rapid_move(z=0))
                lines.append(generate_subroutine_call(sub_path, num_passes))
                lines.append(generate_rapid_move(z=self.settings.safety_height))
        else:
            # Inline generation
            for hexagon in hexagons:
                lines.extend(self._generate_hexagon_inline(hexagon, params))

        return lines

    def _generate_hexagon_inline(
        self,
        hexagon: Dict[str, float],
        params: ToolParams
    ) -> List[str]:
        """Generate inline hexagon cut G-code using unified path cutting."""
        config = self._hexagon_to_path_config(hexagon, params)
        return self._generate_path_cut(config, params)

    def generate_line_gcode(
        self,
        line_cuts: List[Dict],
        params: ToolParams
    ) -> List[str]:
        """
        Generate G-code for line cuts.

        Args:
            line_cuts: List of line cut dicts with points
            params: Cutting parameters

        Returns:
            List of G-code lines for main file
        """
        if not line_cuts:
            return []

        lines = []
        pass_depth = params.pass_depth or 0.025
        num_passes = calculate_num_passes(self.material_depth, pass_depth)
        actual_pass_depth = self.material_depth / num_passes

        # Global lead-in setting (fallback for auto mode)
        global_use_lead_in = self.settings.line_lead_in_type == 'ramp' and self.lead_in_distance > 0

        for line_cut in line_cuts:
            path = line_cut.get('points', [])
            compensation = line_cut.get('compensation', 'none')
            hold_time = line_cut.get('hold_time', 0)

            if not path:
                continue

            # Validate arc geometry before compensation
            arc_warnings = validate_arc_geometry(path)
            self.warnings.extend(arc_warnings)

            # Apply tool compensation if specified
            if compensation != 'none':
                try:
                    path = compensate_line_path(
                        path, params.tool_diameter, compensation
                    )
                except ValueError as e:
                    self.warnings.append(str(e))
                    continue

            # Determine lead-in settings (per-operation or global)
            lead_in_mode = line_cut.get('lead_in_mode', 'auto')
            if lead_in_mode == 'manual':
                op_lead_in_type = line_cut.get('lead_in_type', 'ramp')
                approach_angle = line_cut.get('lead_in_approach_angle', 90)
                use_lead_in = op_lead_in_type == 'ramp' and self.lead_in_distance > 0
            else:
                approach_angle = None  # Use automatic direction for auto mode
                use_lead_in = global_use_lead_in

            # Calculate lead-in point if enabled
            lead_in_point = None
            if use_lead_in:
                lead_in_point = calculate_line_lead_in_point(
                    path, self.lead_in_distance, compensation, approach_angle
                )

            if self.settings.supports_subroutines:
                sub_num = get_next_subroutine_number('line', self.used_subroutine_numbers)
                self.used_subroutine_numbers.append(sub_num)

                sub_content = generate_line_path_subroutine(
                    path, actual_pass_depth, params.plunge_rate, params.feed_rate,
                    lead_in_point=lead_in_point,
                    hold_time=hold_time
                )
                self.subroutines[sub_num] = sub_content

                sub_path = build_subroutine_path(
                    self.settings.gcode_base_path, self.project_name, sub_num
                )

                if use_lead_in:
                    lines.append(generate_rapid_move(x=lead_in_point[0], y=lead_in_point[1], z=self.settings.travel_height))
                else:
                    start_x = path[0].get('x', 0)
                    start_y = path[0].get('y', 0)
                    lines.append(generate_rapid_move(x=start_x, y=start_y, z=self.settings.travel_height))

                lines.append(generate_rapid_move(z=0))
                lines.append(generate_subroutine_call(sub_path, num_passes))
                lines.append(generate_rapid_move(z=self.settings.safety_height))
            else:
                lines.extend(self._generate_line_inline(path, params, compensation, line_cut))

        return lines

    def _generate_line_inline(
        self,
        path: List[Dict],
        params: ToolParams,
        compensation: str = 'none',
        operation: Optional[Dict] = None
    ) -> List[str]:
        """Generate inline line cut G-code using unified path cutting."""
        config = self._line_to_path_config(path, params, compensation, operation)
        return self._generate_path_cut(config, params)

    def generate(
        self,
        expanded_ops: Dict[str, List],
        drill_params: Optional[ToolParams] = None,
        cut_params: Optional[ToolParams] = None,
        original_operations: Optional[Dict] = None
    ) -> GenerationResult:
        """
        Generate complete G-code for all operations.

        Args:
            expanded_ops: Expanded operations dict from pattern_expander
            drill_params: Parameters for drilling (if drill operations exist)
            cut_params: Parameters for cutting (if cut operations exist)
            original_operations: Original operations dict (for pattern detection)

        Returns:
            GenerationResult with main G-code, subroutines, and warnings
        """
        main_lines = []

        # Calculate lead-in distance from ramp angle and pass depth
        if cut_params and cut_params.pass_depth:
            self.lead_in_distance = calculate_lead_in_distance(
                self.settings.ramp_angle, cut_params.pass_depth
            )
        else:
            self.lead_in_distance = 0.25  # Default fallback

        # Determine spindle speed (use drill or cut params)
        spindle_speed = 1000
        if drill_params:
            spindle_speed = drill_params.spindle_speed
        elif cut_params:
            spindle_speed = cut_params.spindle_speed

        # Header
        main_lines.extend(generate_header(
            spindle_speed,
            self.settings.spindle_warmup_seconds,
            self.settings.safety_height
        ))

        # Drilling operations
        if drill_params and expanded_ops.get('drill_points'):
            drill_ops = original_operations.get('drill_holes', []) if original_operations else None
            drill_lines = self.generate_drill_gcode(
                expanded_ops['drill_points'], drill_params, drill_ops
            )
            main_lines.extend(drill_lines)

        # Circular cuts
        if cut_params and expanded_ops.get('circular_cuts'):
            circle_lines = self.generate_circular_gcode(
                expanded_ops['circular_cuts'], cut_params
            )
            main_lines.extend(circle_lines)

        # Hexagonal cuts
        if cut_params and expanded_ops.get('hexagonal_cuts'):
            hex_lines = self.generate_hexagonal_gcode(
                expanded_ops['hexagonal_cuts'], cut_params
            )
            main_lines.extend(hex_lines)

        # Line cuts
        if cut_params and expanded_ops.get('line_cuts'):
            line_lines = self.generate_line_gcode(
                expanded_ops['line_cuts'], cut_params
            )
            main_lines.extend(line_lines)

        # Footer
        main_lines.extend(generate_footer(self.settings.safety_height))

        return GenerationResult(
            main_gcode='\n'.join(main_lines),
            subroutines=self.subroutines,
            project_name=self.project_name,
            warnings=self.warnings
        )
