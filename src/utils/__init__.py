"""Shared utility modules for G-code generation."""

from .units import inches_to_mm, mm_to_inches
from .multipass import calculate_num_passes, calculate_pass_depths, get_material_depth
from .tool_compensation import (
    get_compensation_offset,
    calculate_cut_radius,
    offset_point_inward,
    calculate_hexagon_compensated_vertices
)
from .arc_utils import calculate_arc_direction, calculate_ij_offsets
from .gcode_format import (
    format_coordinate,
    generate_header,
    generate_footer,
    generate_rapid_move,
    generate_linear_move,
    generate_arc_move,
    generate_subroutine_call,
    generate_subroutine_end,
    sanitize_project_name
)
from .subroutine_generator import (
    get_next_subroutine_number,
    generate_subroutine_file,
    build_subroutine_path,
    generate_peck_drill_subroutine,
    generate_circle_pass_subroutine,
    generate_hexagon_pass_subroutine,
    generate_line_path_subroutine
)
from .validators import (
    validate_bounds,
    validate_all_points,
    validate_tool_in_standards
)
from .file_manager import (
    create_output_directory,
    write_main_file,
    write_subroutine_file,
    package_for_download
)

__all__ = [
    # units
    'inches_to_mm',
    'mm_to_inches',
    # multipass
    'calculate_num_passes',
    'calculate_pass_depths',
    'get_material_depth',
    # tool_compensation
    'get_compensation_offset',
    'calculate_cut_radius',
    'offset_point_inward',
    'calculate_hexagon_compensated_vertices',
    # arc_utils
    'calculate_arc_direction',
    'calculate_ij_offsets',
    # gcode_format
    'format_coordinate',
    'generate_header',
    'generate_footer',
    'generate_rapid_move',
    'generate_linear_move',
    'generate_arc_move',
    'generate_subroutine_call',
    'generate_subroutine_end',
    'sanitize_project_name',
    # subroutine_generator
    'get_next_subroutine_number',
    'generate_subroutine_file',
    'build_subroutine_path',
    'generate_peck_drill_subroutine',
    'generate_circle_pass_subroutine',
    'generate_hexagon_pass_subroutine',
    'generate_line_path_subroutine',
    # validators
    'validate_bounds',
    'validate_all_points',
    'validate_tool_in_standards',
    # file_manager
    'create_output_directory',
    'write_main_file',
    'write_subroutine_file',
    'package_for_download',
]
