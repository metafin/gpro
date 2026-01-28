# G-Code Generation Architecture

This document describes the G-code generation pipeline in GPRO, covering the core algorithms and modules in `src/`.

## Overview

The G-code generation system converts user-defined operations (drill holes, circular cuts, hexagonal cuts, line cuts) into machine-readable G-code for OMIO CNC machines. The pipeline handles:

- Pattern expansion (single points → linear/grid patterns)
- Geometry calculations (hexagon vertices, arc directions)
- Multi-pass depth management
- Tool radius compensation
- M98 subroutine generation for Mach3
- Tube void detection and filtering

## Module Structure

```
src/
├── constants.py          # Enums and type constants
├── models.py             # Dataclasses for Points, Cuts, Parameters
├── gcode_generator.py    # Main orchestrator (WebGCodeGenerator)
├── pattern_expander.py   # Pattern → coordinate expansion
├── hexagon_generator.py  # Hexagon vertex calculations
├── tube_void_checker.py  # Hollow tube center detection
└── utils/
    ├── units.py              # Unit conversion (in ↔ mm)
    ├── multipass.py          # Multi-pass depth calculations
    ├── tool_compensation.py  # Tool radius offset
    ├── arc_utils.py          # Arc direction & I/J offsets
    ├── gcode_format.py       # G-code command formatting
    ├── subroutine_generator.py  # M98 subroutine files
    ├── lead_in.py            # Ramped lead-in geometry calculations
    ├── validators.py         # Coordinate validation
    └── file_manager.py       # Output file handling
```

## Data Models (`src/models.py`)

Core dataclasses used throughout the pipeline:

```python
@dataclass
class Point:
    x: float
    y: float

@dataclass
class GCodeParams:
    spindle_speed: int                  # RPM
    feed_rate: float                    # in/min
    plunge_rate: float                  # in/min (Z-axis feed)
    material_depth: float               # Total cut depth (inches)
    pecking_depth: Optional[float]      # Drill peck increment
    pass_depth: Optional[float]         # Cutting pass increment

@dataclass
class CircleCut:
    center: Point
    diameter: float

@dataclass
class HexCut:
    center: Point
    flat_to_flat: float     # Distance between parallel flats

@dataclass
class LineCutPoint:
    x: float
    y: float
    line_type: str              # 'start', 'straight', 'arc'
    arc_center_x: float         # For arc segments
    arc_center_y: float         # For arc segments
    arc_direction: str = None   # Optional: 'cw' or 'ccw' to override auto-detection

@dataclass
class LineCut:
    points: List[LineCutPoint]
```

For closed paths, include a final point returning to start. Closure is auto-detected.

**Tool Compensation Types (passed separately in operations):**
- `none`: Tool center follows the exact path (default)
- `interior`: Tool offsets inward (for pockets/windows - material stays outside)
- `exterior`: Tool offsets outward (for cutting out shapes - material stays inside)

Compensation is specified per-operation in the operations dict, not in the dataclass.

## Constants (`src/constants.py`)

Shared enumerations:

```python
# Tool types
TOOL_TYPE_DRILL = 'drill'
TOOL_TYPE_END_MILL_1FLUTE = 'end_mill_1flute'
TOOL_TYPE_END_MILL_2FLUTE = 'end_mill_2flute'

# Project types
PROJECT_TYPE_DRILL = 'drill'
PROJECT_TYPE_CUT = 'cut'

# Material forms
MATERIAL_FORM_SHEET = 'sheet'
MATERIAL_FORM_TUBE = 'tube'

# Operation pattern types
OP_TYPE_SINGLE = 'single'
OP_TYPE_PATTERN_LINEAR = 'pattern_linear'
OP_TYPE_PATTERN_GRID = 'pattern_grid'

# Line segment types
LINE_TYPE_START = 'start'
LINE_TYPE_STRAIGHT = 'straight'
LINE_TYPE_ARC = 'arc'
```

## Pattern Expansion (`src/pattern_expander.py`)

Converts pattern definitions to individual coordinates.

### Single Point
No expansion needed - returns as-is.

### Linear Pattern
```python
expand_linear_pattern(start_x, start_y, axis, spacing, count)
```
Generates `count` points along `axis` ('x' or 'y') with given `spacing`.

Example: `(0, 0, 'x', 0.5, 4)` → `[(0,0), (0.5,0), (1.0,0), (1.5,0)]`

### Grid Pattern
```python
expand_grid_pattern(start_x, start_y, x_spacing, y_spacing, x_count, y_count)
```
Generates a rectangular grid of points.

Example: `(0, 0, 1.0, 0.5, 3, 2)` → 6 points in a 3×2 grid

### Operation Expanders
```python
expand_drill_operations(operations) → List[Tuple[float, float]]
expand_circular_operations(operations) → List[Dict]
expand_hexagonal_operations(operations) → List[Dict]
expand_all_operations(operations) → Dict  # All types combined
```

## Hexagon Geometry (`src/hexagon_generator.py`)

Calculates vertices for **point-up** hexagons (vertices at top/bottom, flats on left/right sides).

### Key Formulas
```python
apothem = flat_to_flat / 2                    # Center to flat edge
circumradius = flat_to_flat / sqrt(3)         # Center to vertex
```

### Vertex Order (clockwise from top)
```
        1 (top)
       / \
      /   \
   6 /     \ 2
     \     /
      \   /
   5   \ / 3
        4 (bottom)
```

### Functions
```python
calculate_hexagon_vertices(center_x, center_y, flat_to_flat)
    → List[Tuple[float, float]]  # 6 vertices

calculate_compensated_vertices(center_x, center_y, flat_to_flat, tool_diameter, compensation='interior')
    → List[Tuple[float, float]]  # Vertices offset based on compensation type

get_hexagon_start_position(vertices) → Tuple[float, float]

calculate_hexagon_bounds(center_x, center_y, flat_to_flat)
    → Tuple[min_x, min_y, max_x, max_y]
```

### Tool Compensation
Vertices are offset by `tool_radius * 2 / sqrt(3)` along the angle bisector:
- `interior` (default): Offset inward - resulting hexagon matches flat_to_flat
- `exterior`: Offset outward - cuts out a hexagon of flat_to_flat size
- `none`: No compensation - tool center follows exact vertices

The canonical implementation is in `src/utils/tool_compensation.py`; `hexagon_generator.py` re-exports it for backward compatibility.

## Tube Void Detection (`src/tube_void_checker.py`)

For hollow tube stock, operations entirely within the void are skipped.

### Void Calculation
```python
calculate_void_bounds(outer_width, outer_height, wall_thickness)
    → (void_x_min, void_y_min, void_x_max, void_y_max)
```

The void is the rectangular hollow area inside the tube walls.

### Containment Checks
```python
point_in_void(x, y, void_bounds, tool_radius) → bool
circle_in_void(center_x, center_y, diameter, void_bounds, tool_diameter) → bool
hexagon_in_void(center_x, center_y, flat_to_flat, void_bounds, tool_diameter) → bool
```

### Filtering
```python
filter_operations_for_tube(operations, material, tube_void_skip, tool_diameter)
    → Dict  # Filtered operations with void items removed
```

Only applies when `material.form == 'tube'` and `tube_void_skip == True`.

## Utility Modules (`src/utils/`)

### units.py
```python
inches_to_mm(value) → float  # value * 25.4
mm_to_inches(value) → float  # value / 25.4
```

### multipass.py
```python
calculate_num_passes(total_depth, pass_depth) → int
calculate_pass_depths(total_depth, pass_depth) → List[float]  # Cumulative depths

get_material_depth(material) → float
    # Returns thickness (sheet) or wall_thickness (tube)
```

### tool_compensation.py

This module provides the core tool compensation logic for all shape types.

#### Core Compensation Functions
```python
get_compensation_offset(tool_diameter, compensation) → float
    # Core abstraction for all compensation
    # Returns: 0 (none), -tool_radius (interior), +tool_radius (exterior)

calculate_cut_radius(feature_diameter, tool_diameter, compensation='interior') → float
    # Calculate toolpath radius for circular cuts
    # Returns: feature_radius + get_compensation_offset(tool_diameter, compensation)

offset_point_inward(point, center, offset_distance) → Tuple[float, float]
    # Moves point toward center by offset_distance
    # Positive = toward center, Negative = away from center
```

#### Hexagon Compensation
```python
calculate_hexagon_compensated_vertices(center_x, center_y, flat_to_flat, tool_diameter, compensation='interior')
    → List[Tuple[float, float]]
    # Canonical implementation for hexagon vertex compensation
    # Each vertex offset by tool_radius * 2 / sqrt(3) along angle bisector
    # Re-exported by hexagon_generator.py as calculate_compensated_vertices()
```

#### Line Path Compensation
For line cuts, tool compensation offsets the entire path by the tool radius to achieve precise dimensions.

```python
calculate_line_normal(p1, p2) → Tuple[float, float]
    # Unit vector perpendicular to line segment (points left of direction)

offset_line_segment(p1, p2, offset) → Tuple[Tuple, Tuple]
    # Offset both endpoints perpendicular to segment
    # Positive offset = left, Negative offset = right

calculate_line_intersection(l1_p1, l1_p2, l2_p1, l2_p2) → Optional[Tuple]
    # Find where two infinite lines cross (for corner handling)
    # Returns None for parallel lines

calculate_path_winding(path) → float
    # Signed area: Positive = CCW, Negative = CW
    # Used to determine inside vs outside of path

compensate_line_path(path, tool_diameter, compensation_type) → List[Dict]
    # Main entry point for line path compensation
    # compensation_type: "none", "interior", or "exterior"
    # Closed paths are auto-detected (first == last point)
```

#### Arc Segment Compensation
```python
offset_arc_segment(start, end, offset, is_exterior) → Tuple[Dict, Tuple]
    # Adjust arc radius for compensation
    # Exterior: radius increases (tool outside arc)
    # Interior: radius decreases (tool inside arc)
    # Raises ValueError if interior compensation would make radius negative
```

#### Helper Functions
```python
_is_path_closed(path, tolerance=0.0001) → bool
    # Check if first and last points match within tolerance
```

**Compensation Algorithm:**
1. Auto-detect if path is closed (first and last points match)
2. Calculate path winding (CCW or CW) to determine inside/outside
3. Determine offset direction based on compensation type:
   - **Exterior**: Tool stays outside path (shape being cut out)
   - **Interior**: Tool stays inside path (pocket/window cut)
4. For each segment:
   - **Straight segments**: Offset parallel to segment direction
   - **Arc segments**: Adjust arc radius (increase for exterior, decrease for interior)
5. Calculate corner intersections between adjacent offset segments
6. Return compensated path with adjusted coordinates

**Example:**
```python
# 1" square at origin, CCW, with 0.25" tool
path = [
    {'x': 0, 'y': 0, 'line_type': 'start'},
    {'x': 1, 'y': 0, 'line_type': 'straight'},
    {'x': 1, 'y': 1, 'line_type': 'straight'},
    {'x': 0, 'y': 1, 'line_type': 'straight'}
]

# Exterior: expands to ~1.125" square (corners at -0.125, 1.125)
exterior = compensate_line_path(path, 0.25, 'exterior')

# Interior: shrinks to ~0.875" square (corners at 0.125, 0.875)
interior = compensate_line_path(path, 0.25, 'interior')
```

### arc_utils.py
```python
calculate_arc_direction(current, destination, center, direction_hint=None) → str
    # Returns "G02" (CW) or "G03" (CCW)
    # Uses cross product for automatic detection
    # direction_hint: Optional 'cw' or 'ccw' to override (case insensitive)

calculate_ij_offsets(current, center) → Tuple[float, float]
    # I = center_x - current_x, J = center_y - current_y
```

**Arc Direction Override:**

For semicircles (180° arcs), the cross product equals zero and the algorithm cannot determine direction. It defaults to G02 (clockwise). Use `arc_direction` in the path point to override:

```python
# Semicircle from (1, 16) to (3, 16), center at (2, 16)
# Without arc_direction: defaults to G02 (curves DOWN below Y=16)
# With arc_direction='ccw': returns G03 (curves UP above Y=16)
{
    'x': 3.0,
    'y': 16.0,
    'line_type': 'arc',
    'arc_center_x': 2.0,
    'arc_center_y': 16.0,
    'arc_direction': 'ccw'  # Forces counter-clockwise (G03)
}
```

### gcode_format.py
**Critical: No comments in output** (breaks Mach3 M98 parsing).

```python
format_coordinate(value, precision=4) → str
generate_header(spindle_speed, warmup_seconds, safety_height) → List[str]
generate_footer(safety_height) → List[str]
generate_rapid_move(x, y, z) → str        # G00 X... Y... Z...
generate_linear_move(x, y, z, feed) → str # G01 X... Y... F...
generate_arc_move(direction, x, y, i, j, feed) → str  # G02/G03 X... Y... I... J...
generate_subroutine_call(file_path, loop_count) → str
    # M98 (-C:\Mach3\GCode\Project\1000.nc) L31
generate_subroutine_end() → List[str]     # ["M99", "%"]
sanitize_project_name(name) → str         # Safe filename
```

### subroutine_generator.py
Generates M98 subroutine files for Mach3.

```python
get_next_subroutine_number(operation_type, existing) → int
    # Drill: 1000-1099, Circle: 1100-1199, Hex: 1200-1299, Line: 1300-1399

generate_subroutine_file(commands) → str  # Content with M99 + %

build_subroutine_path(base_path, project_name, subroutine_number) → str

generate_peck_drill_subroutine(pecks, plunge_rate, travel_height, axis, spacing)
generate_circle_pass_subroutine(cut_radius, pass_depth, plunge_rate, feed_rate, lead_in_distance=None)
generate_hexagon_pass_subroutine(vertices, pass_depth, plunge_rate, feed_rate, lead_in_point=None)
generate_line_path_subroutine(path, pass_depth, plunge_rate, feed_rate, lead_in_point=None)
```

### lead_in.py
Calculates lead-in geometry for ramped entry to profile cuts. Ramped entry eliminates the shock loading that occurs when transitioning from vertical plunge to lateral cut, which can snap end mills.

```python
calculate_circle_lead_in_point(center_x, center_y, cut_radius, lead_in_distance)
    → Tuple[float, float]
    # Returns point radially outward from 3 o'clock position

calculate_hexagon_lead_in_point(vertices, lead_in_distance)
    → Tuple[float, float]
    # Returns point extending first edge (v0→v1) backwards

calculate_line_lead_in_point(path, lead_in_distance)
    → Tuple[float, float]
    # Returns point extending initial cut direction backwards

is_closed_path(path, tolerance=0.0001) → bool
    # Checks if first and last points coincide
```

**Lead-In Geometry by Shape:**

| Shape | Profile Start | Lead-In Point |
|-------|---------------|---------------|
| Circle | 3 o'clock `(cx + cut_radius, cy)` | Radially outward `(cx + cut_radius + distance, cy)` |
| Hexagon | First vertex `v0` | Extend `v0→v1` backwards by distance |
| Line | First point `p0` | Extend `p0→p1` backwards by distance |

**Ramp Entry vs Vertical Plunge:**

Without lead-in (vertical plunge):
```gcode
G00 Z0              ← Rapid to surface
G91                 ← Relative mode
G01 Z-0.0625 F8     ← Vertical plunge
G90                 ← Absolute mode
G01 X... F45        ← Immediate lateral cut (shock load!)
```

With ramped lead-in:
```gcode
G00 Z0              ← Rapid to surface (at lead-in point)
G91                 ← Relative mode
G01 X-0.25 Z-0.0625 F8  ← Ramp: simultaneous XY/Z movement
G90                 ← Absolute mode
G01 X... F45        ← Continue profile cut (smooth transition)
```

**Lead-Out:**
For closed profiles (circles, hexagons, closed line paths), after completing the cut the tool returns to the lead-in point at cutting depth before the next pass. Open line paths simply retract at the endpoint.

### validators.py
```python
validate_bounds(x, y, max_x, max_y) → bool
validate_all_points(points, max_x, max_y) → List[str]  # Error messages
validate_tool_in_standards(tool_type, size, gcode_standards) → bool
```

### file_manager.py
```python
create_output_directory(base_path, project_name) → str
write_main_file(directory, content) → str
write_subroutine_file(directory, number, content) → str
package_for_download(directory) → bytes  # ZIP archive
```

## Main Generator (`src/gcode_generator.py`)

### GenerationSettings
```python
@dataclass
class GenerationSettings:
    safety_height: float           # Z height for safe moves (0.5")
    travel_height: float           # Z height during rapids (0.2")
    spindle_warmup_seconds: int    # Dwell after spindle start
    supports_subroutines: bool     # Machine capability
    supports_canned_cycles: bool   # Machine capability
    gcode_base_path: str           # e.g., "C:\Mach3\GCode"
    max_x: float                   # Machine travel limit
    max_y: float                   # Machine travel limit
    lead_in_type: str = 'ramp'     # 'none' or 'ramp' (for profile cuts)
    lead_in_distance: float = 0.25 # Distance from profile start (inches)
```

### ToolParams
```python
@dataclass
class ToolParams:
    spindle_speed: int              # RPM
    feed_rate: float                # in/min
    plunge_rate: float              # in/min (Z-axis feed)
    pecking_depth: Optional[float]  # For drills - peck increment
    pass_depth: Optional[float]     # For end mills - depth per pass
    tool_diameter: float = 0.125    # Tool diameter for compensation
```

### WebGCodeGenerator
Main orchestrator class:

```python
class WebGCodeGenerator:
    def __init__(self, settings: GenerationSettings, project_name: str, material_depth: float):
        ...

    def generate_drill_gcode(self, drill_points, params: ToolParams, operations) → List[str]
    def generate_circular_gcode(self, circles, params: ToolParams) → List[str]
    def generate_hexagonal_gcode(self, hexagons, params: ToolParams) → List[str]
    def generate_line_gcode(self, line_cuts, params: ToolParams) → List[str]

    def generate(self, expanded_ops: Dict[str, List],
                 drill_params: Optional[ToolParams] = None,
                 cut_params: Optional[ToolParams] = None,
                 original_operations: Optional[Dict] = None) → GenerationResult
```

**Operation Dicts with Compensation:**

Circular and hexagonal operations support a `compensation` field:
```python
circle = {
    'center_x': 2.0,
    'center_y': 3.0,
    'diameter': 0.5,
    'compensation': 'interior'  # 'none', 'interior', or 'exterior'
}

hexagon = {
    'center_x': 4.0,
    'center_y': 5.0,
    'flat_to_flat': 1.0,
    'compensation': 'interior'  # 'none', 'interior', or 'exterior'
}
```

Line cuts pass compensation separately:
```python
line_cut = {
    'points': [...],
    'compensation': 'exterior'  # 'none', 'interior', or 'exterior'
}
```

### GenerationResult
```python
@dataclass
class GenerationResult:
    main_gcode: str                  # Contents of main.nc
    subroutines: Dict[int, str]      # {1000: "...", 1100: "...", ...}
    project_name: str                # Sanitized name
    warnings: List[str]              # Non-fatal issues
```

## Generation Pipeline

1. **Validate** operations within machine bounds
2. **Filter** tube void operations (if applicable)
3. **Expand** patterns to coordinates
4. **Generate** G-code for each operation type:
   - Calculate multi-pass depths
   - Create subroutine files (if supported)
   - Generate M98 calls or inline G-code
5. **Assemble** main.nc + subroutine files
6. **Package** as ZIP for download

## Output File Structure

```
ProjectName.zip
├── main.nc          # Main program with M98 calls
├── 1000.nc          # Drill subroutine
├── 1100.nc          # Circle subroutine
├── 1200.nc          # Hexagon subroutine
└── 1300.nc          # Line subroutine
```

### M98 Subroutine Syntax (Mach3)
```gcode
M98 (-C:\Mach3\GCode\ProjectName\1000.nc) L31
```
- Full absolute path in parentheses with leading hyphen
- `L` specifies loop count (repetitions)
- No comments allowed in G-code (breaks parsing)

## Key Design Decisions

1. **No Comments**: G-code output omits comments because parentheses break M98 parsing in Mach3.

2. **Inches Throughout**: UI and G-code use inches (G20). Tool sizes stored with unit for conversion.

3. **Point-Up Hexagons**: Industry standard orientation with flats parallel to X-axis.

4. **Automatic Arc Direction**: Uses cross product to determine CW (G02) vs CCW (G03). For semicircles where cross product is zero, use `arc_direction` field to override.

5. **Subroutine Architecture**: Enables efficient looping for repeated operations (linear patterns).

6. **Static Utility Functions**: All utilities are stateless for testability.

7. **Ramped Lead-In**: Profile cuts (circles, hexagons, lines) use ramped entry by default to eliminate shock loading. The tool descends gradually while moving toward the profile start, instead of plunging vertically then immediately cutting laterally.

8. **Lead-In Not For Drills**: Drilling operations use vertical plunge with optional peck cycles. Lead-in is only applied to profile cuts where the tool will move laterally at depth.
