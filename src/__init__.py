"""G-code generation modules for CNC machining operations."""

from .gcode_generator import (
    WebGCodeGenerator,
    GenerationSettings,
    ToolParams,
    GenerationResult
)
from .pattern_expander import (
    expand_all_operations,
    expand_linear_pattern,
    expand_grid_pattern,
    expand_drill_operations,
    expand_circular_operations,
    expand_hexagonal_operations
)
from .tube_void_checker import (
    calculate_void_bounds,
    point_in_void,
    filter_operations_for_tube
)
from .hexagon_generator import (
    calculate_hexagon_vertices,
    calculate_compensated_vertices,
    calculate_hexagon_bounds
)

__all__ = [
    # Main generator
    'WebGCodeGenerator',
    'GenerationSettings',
    'ToolParams',
    'GenerationResult',
    # Pattern expansion
    'expand_all_operations',
    'expand_linear_pattern',
    'expand_grid_pattern',
    'expand_drill_operations',
    'expand_circular_operations',
    'expand_hexagonal_operations',
    # Tube void
    'calculate_void_bounds',
    'point_in_void',
    'filter_operations_for_tube',
    # Hexagon
    'calculate_hexagon_vertices',
    'calculate_compensated_vertices',
    'calculate_hexagon_bounds',
]
