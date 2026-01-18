# G-Code Generation - Build Instructions

This document describes how to generate G-code from project data. It covers the inputs, algorithms, and output format.

---

## Part A: Inputs

G-code generation requires two categories of input: **settings** (from database) and **project instructions** (user-defined operations).

---

### A1. Settings (from Database)

#### Machine Settings
Retrieved via `SettingsService.get_machine_settings()`:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `max_x` | float | Maximum X travel (inches) | 15.0 |
| `max_y` | float | Maximum Y travel (inches) | 15.0 |
| `controller_type` | string | Controller software | "mach3" |
| `supports_subroutines` | bool | Can use M98 subroutine calls | true |
| `supports_canned_cycles` | bool | Can use G83 peck drilling | true |
| `gcode_base_path` | string | Absolute path where G-code directories are stored | "C:\Mach3\GCode" |

#### General Settings
Retrieved via `SettingsService.get_general_settings()`:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `safety_height` | float | Z height for safe moves (inches) | 0.5 |
| `travel_height` | float | Z height during rapid moves (inches) | 0.25 |
| `spindle_warmup_seconds` | int | Dwell time after spindle start | 2 |

#### Material Settings
Retrieved via project's `material` relationship:

| Field | Type | Description |
|-------|------|-------------|
| `form` | string | "sheet" or "tube" |
| `thickness` | float | Sheet thickness (inches) - for sheets only |
| `wall_thickness` | float | Tube wall thickness (inches) - for tubes only |
| `outer_width` | float | Tube outer width (inches) - for tubes only |
| `outer_height` | float | Tube outer height (inches) - for tubes only |
| `gcode_standards` | JSON | Cutting parameters by tool_type and size |

**gcode_standards format:**
```json
{
  "drill": {
    "0.125": {
      "spindle_speed": 1000,
      "feed_rate": 2.0,
      "plunge_rate": 1.0,
      "pecking_depth": 0.05
    }
  },
  "end_mill_1flute": {
    "0.125": {
      "spindle_speed": 12000,
      "feed_rate": 12.0,
      "plunge_rate": 2.0,
      "pass_depth": 0.025
    }
  },
  "end_mill_2flute": {
    "0.125": {
      "spindle_speed": 10000,
      "feed_rate": 10.0,
      "plunge_rate": 1.5,
      "pass_depth": 0.02
    }
  }
}
```

**Tool types:**
- `drill` - standard drill bit (used for drilling operations)
- `end_mill_1flute` - single flute end mill (better chip clearance, good for aluminum/plastics)
- `end_mill_2flute` - double flute end mill (general purpose, better surface finish)

---

### A2. Project Instructions (Operations JSON)

The project's `operations` field contains all machining operations:

```json
{
  "drill_holes": [...],
  "circular_cuts": [...],
  "hexagonal_cuts": [...],
  "line_cuts": [...]
}
```

#### Drill Holes

**Single point:**
```json
{"id": "d1", "type": "single", "x": 1.25, "y": 0.5}
```

**Linear pattern** (repeat along axis):
```json
{
  "id": "d2",
  "type": "pattern_linear",
  "start_x": 1.25,
  "start_y": 1.0,
  "axis": "y",
  "spacing": 0.5,
  "count": 4
}
```

**Grid pattern** (rectangular array):
```json
{
  "id": "d3",
  "type": "pattern_grid",
  "start_x": 3.0,
  "start_y": 0.5,
  "x_spacing": 1.0,
  "y_spacing": 0.5,
  "x_count": 3,
  "y_count": 4
}
```

#### Circular Cuts

**Single circle:**
```json
{"id": "c1", "type": "single", "center_x": 1.25, "center_y": 4.02, "diameter": 0.8}
```

**Linear pattern of circles:**
```json
{
  "id": "c2",
  "type": "pattern_linear",
  "start_center_x": 0.5,
  "start_center_y": 1.0,
  "diameter": 0.5,
  "axis": "x",
  "spacing": 2.0,
  "count": 4
}
```

#### Hexagonal Cuts

**Single hexagon:**
```json
{"id": "h1", "type": "single", "center_x": 2.0, "center_y": 3.0, "flat_to_flat": 0.75}
```

- `flat_to_flat`: Distance between parallel flat sides (the "wrench size")
- Hexagons are oriented with flats parallel to X-axis (point-up)

**Linear pattern of hexagons:**
```json
{
  "id": "h2",
  "type": "pattern_linear",
  "start_center_x": 1.0,
  "start_center_y": 1.0,
  "flat_to_flat": 0.5,
  "axis": "x",
  "spacing": 1.5,
  "count": 3
}
```

#### Line Cuts

```json
{
  "id": "l1",
  "points": [
    {"x": 0, "y": 0, "line_type": "start"},
    {"x": 5.5, "y": 0, "line_type": "straight"},
    {"x": 5.5, "y": 2.5, "line_type": "straight"},
    {"x": 2.5, "y": 2.5, "line_type": "arc", "arc_center_x": 4.0, "arc_center_y": 2.5}
  ],
  "closed": true
}
```

**Line types:**
- `start`: First point (rapid move, no cutting)
- `straight`: Linear cut (G1)
- `arc`: Circular arc cut (G2/G3) - requires `arc_center_x`, `arc_center_y`

---

## Part B: G-Code Generation

### B1. Pattern Expansion

Before generating G-code, expand all patterns into individual coordinates.

**Module:** `src/pattern_expander.py`

#### Linear Pattern Expansion
```
expand_linear(start_x, start_y, axis, spacing, count) → List[Point]

For i in 0..count-1:
  if axis == 'x': point = (start_x + i*spacing, start_y)
  if axis == 'y': point = (start_x, start_y + i*spacing)
```

#### Grid Pattern Expansion
```
expand_grid(start_x, start_y, x_spacing, y_spacing, x_count, y_count) → List[Point]

For row in 0..y_count-1:
  For col in 0..x_count-1:
    point = (start_x + col*x_spacing, start_y + row*y_spacing)
```

#### Hexagon Vertex Calculation

Given center (cx, cy) and flat_to_flat distance:

```
apothem = flat_to_flat / 2
circumradius = apothem / cos(30°) = flat_to_flat / √3

Vertices (starting at top, clockwise):
  v0 = (cx, cy + circumradius)                    # top
  v1 = (cx + apothem, cy + circumradius/2)        # upper right
  v2 = (cx + apothem, cy - circumradius/2)        # lower right
  v3 = (cx, cy - circumradius)                    # bottom
  v4 = (cx - apothem, cy - circumradius/2)        # lower left
  v5 = (cx - apothem, cy + circumradius/2)        # upper left
```

---

### B2. Subroutine Strategy (M98 Calls)

**Module:** `src/subroutine_generator.py`

When `machine_settings.supports_subroutines` is true, generate M98 subroutine calls to external files. This reduces file size for repeated operations (patterns, multi-pass cuts).

#### Critical Mach3 Requirements

These requirements are **mandatory** for subroutines to work correctly:

| Requirement | Details |
|-------------|---------|
| Hyphen after opening parenthesis | `M98 (-C:\...` NOT `M98 (C:\...` |
| Full absolute path | `C:\Mach3\GCode\ProjectName\1000.nc` |
| File extension included | `.nc` |
| Numeric filename only | `1000.nc`, `2000.nc` - NOT `drill.nc` |
| No comments anywhere | Comments use parentheses which breaks M98 syntax |
| Subroutine ends with M99 then % | Required for L parameter (loop count) to work |

#### Output Directory Structure

G-code output is a **directory** named after the project (sanitized for filesystem):

```
{gcode_base_path}\{project_name}\
├── main.nc              (main program)
├── 1000.nc              (subroutine 1: e.g., peck drill cycle)
├── 1001.nc              (subroutine 2: e.g., circle cut cycle)
├── 1002.nc              (subroutine 3: e.g., hexagon cut cycle)
└── ...
```

**Project name sanitization:**
- Replace spaces with underscores
- Remove special characters except underscores and hyphens
- Truncate to 50 characters max

#### Subroutine Numbering

Subroutines are numbered starting at 1000, incrementing by 1:

| Number Range | Purpose |
|--------------|---------|
| 1000-1099 | Drilling operations |
| 1100-1199 | Circular cut operations |
| 1200-1299 | Hexagonal cut operations |
| 1300-1399 | Line cut operations |

#### M98 Call Syntax

```gcode
M98 (-{gcode_base_path}\{project_name}\{subroutine_number}.nc) L{loop_count}
```

Example:
```gcode
M98 (-C:\Mach3\GCode\Frame16in\1000.nc) L31
```

This calls subroutine `1000.nc` and executes it 31 times.

#### Subroutine File Structure

Every subroutine file must follow this exact structure:

```gcode
{subroutine body - G-code commands}
M99
%
```

**Critical rules:**
- NO comments anywhere in the file
- Must end with `M99` on its own line
- Must have `%` as the final line (enables L parameter looping)
- Typically uses G91 (relative mode) for the operation, then G90 before M99

#### When to Use Subroutines

| Operation | Subroutine Use |
|-----------|----------------|
| Single drill hole | No subroutine needed |
| Linear drill pattern | Subroutine for peck cycle, L = hole count |
| Grid drill pattern | Subroutine for peck cycle, called per row with L = column count |
| Single circle/hex | Subroutine for multi-pass cut cycle |
| Linear pattern of circles/hex | Subroutine for cut cycle, L = pattern count |
| Multi-pass line cuts | Subroutine for single-pass path, L = pass count |

#### Fallback (No Subroutine Support)

If `supports_subroutines` is false, expand all operations inline in a single file. This results in larger files but works on all controllers.

---

### B3. Tube Void Detection

**Module:** `src/tube_void_checker.py`

For tube stock, the center is hollow. Operations falling entirely within the void should be skipped.

**Void bounds calculation:**
```
void_x_min = wall_thickness
void_y_min = wall_thickness
void_x_max = outer_width - wall_thickness
void_y_max = outer_height - wall_thickness
```

**Point-in-void check (with tool radius):**
```
point_in_void(x, y, tool_radius):
  return (x - tool_radius > void_x_min AND
          x + tool_radius < void_x_max AND
          y - tool_radius > void_y_min AND
          y + tool_radius < void_y_max)
```

If `project.tube_void_skip` is true and material is a tube, filter out operations that fall entirely in the void.

---

### B4. G-Code Output Structure

**Units:** Inches (G20) - all coordinates in inches, no conversion needed
**Positioning:** Absolute (G90) in main file; subroutines may use relative (G91)
**No comments:** Comments are NOT allowed in generated G-code (breaks M98 parsing)

#### Main File Header

```gcode
G20 G90
G00 X0 Y0 Z0
G00 Z{safety_height}
M03 S{spindle_speed}
G04 P{warmup_seconds}
```

Note: No comments, no blank lines between commands.

#### Main File Footer

```gcode
M05
G00 Z{safety_height}
G00 X0 Y0
M30
```

#### Subroutine File Template

```gcode
{operation commands}
M99
%
```

---

### B5. Drilling Operations

**Get parameters from:** `material.gcode_standards['drill'][tool_size]`

Where `tool_size` comes from the Tool referenced by `project.drill_tool_id`.

**Material depth:** Use `material.thickness` (sheets) or `material.wall_thickness` (tubes)

#### Peck Drill Subroutine

Create subroutine `1000.nc` (or next available in 1000-1099 range) for the peck drill cycle.

**Subroutine content (peck drill with relative moves):**

```gcode
G00 Z0
G91
G01 Z-{peck_1} F{plunge_rate}
G00 Z{peck_1}
G01 Z-{peck_2} F{plunge_rate}
G00 Z{peck_2}
...
G01 Z-{final_depth} F{plunge_rate}
G00 Z{retract_to_travel_height}
G00 {axis}{spacing}
G90
M99
%
```

**Peck sequence calculation:**
```
pecks = []
current_depth = 0
while current_depth < total_depth:
    current_depth += pecking_depth
    if current_depth > total_depth:
        current_depth = total_depth
    pecks.append(current_depth)
```

Each peck plunges to cumulative depth, then retracts fully before next peck.

#### Linear Drill Pattern

**Main file:**
```gcode
G00 X{start_x} Y{start_y} Z{travel_height}
M98 (-{base_path}\{project}\1000.nc) L{count}
```

**Subroutine 1000.nc** includes:
- Peck drill cycle (relative Z moves)
- Move to next position: `G00 Y{spacing}` (or X for x-axis patterns)
- The L parameter repeats the entire subroutine `count` times

#### Grid Drill Pattern

For grids, generate the pattern row by row in the main file:

**Main file:**
```gcode
G00 X{start_x} Y{start_y} Z{travel_height}
M98 (-{base_path}\{project}\1000.nc) L{x_count}
G00 X{start_x} Y{start_y + y_spacing} Z{travel_height}
M98 (-{base_path}\{project}\1000.nc) L{x_count}
...repeat for each row...
```

**Subroutine 1000.nc** moves along X-axis after each hole.

#### Single Drill Hole

For single holes, inline the peck drill sequence in the main file (no subroutine needed):

```gcode
G00 X{x} Y{y} Z{travel_height}
G00 Z0
G01 Z-{peck_1} F{plunge_rate}
G00 Z{safety_height}
G00 Z0
G01 Z-{peck_2} F{plunge_rate}
...
G00 Z{safety_height}
```

#### G83 Canned Cycle Alternative

If `supports_canned_cycles` is true, can use G83 instead of manual peck:

```gcode
G00 X{x} Y{y}
G83 Z-{total_depth} R{travel_height} Q{pecking_depth} F{plunge_rate}
G80
```

For patterns with G83, each hole position is listed, and G83 parameters carry forward after the first call.

---

### B6. Circular Cut Operations

**Get parameters from:** `material.gcode_standards[end_mill.tool_type][tool_size]`

Where `end_mill` is the Tool referenced by `project.end_mill_tool_id`.

**Tool compensation:** `cut_radius = (diameter - tool_diameter) / 2`

**Start position:** 3 o'clock position: `(center_x + cut_radius, center_y)`

#### Multi-Pass Circle Subroutine

Create subroutine `1100.nc` (or next available in 1100-1199 range).

**Calculate number of passes:**
```
num_passes = ceil(material_depth / pass_depth)
actual_pass_depth = material_depth / num_passes
```

**Subroutine content:**

```gcode
G91
G01 Z-{pass_depth} F{plunge_rate}
G90
G02 I-{cut_radius} J0 F{feed_rate}
M99
%
```

This cuts one pass (plunge + full circle). The L parameter controls how many passes.

**Main file for single circle:**

```gcode
G00 X{center_x + cut_radius} Y{center_y} Z{travel_height}
G00 Z0
M98 (-{base_path}\{project}\1100.nc) L{num_passes}
G00 Z{safety_height}
```

#### Linear Pattern of Circles

For patterns, the main file moves to each circle position and calls the subroutine:

**Main file:**
```gcode
G00 X{pos1_x + cut_radius} Y{pos1_y} Z{travel_height}
G00 Z0
M98 (-{base_path}\{project}\1100.nc) L{num_passes}
G00 Z{safety_height}
G00 X{pos2_x + cut_radius} Y{pos2_y} Z{travel_height}
G00 Z0
M98 (-{base_path}\{project}\1100.nc) L{num_passes}
G00 Z{safety_height}
...
```

Alternatively, create a second subroutine that includes the circle cut + move to next position, and use L for the pattern count.

---

### B7. Hexagonal Cut Operations

Same parameters as circular cuts. Cut the hexagon as 6 line segments.

**Tool compensation:** Offset each vertex inward by tool_radius along the angle bisector.

#### Compensated Vertex Calculation

```
For each vertex at angle θ from center:
  offset_distance = tool_radius / sin(60°)  # = tool_radius * 2/√3
  compensated_vertex = vertex moved toward center by offset_distance
```

#### Multi-Pass Hexagon Subroutine

Create subroutine `1200.nc` (or next available in 1200-1299 range).

**Subroutine content:**

```gcode
G91
G01 Z-{pass_depth} F{plunge_rate}
G90
G01 X{v1_x} Y{v1_y} F{feed_rate}
G01 X{v2_x} Y{v2_y}
G01 X{v3_x} Y{v3_y}
G01 X{v4_x} Y{v4_y}
G01 X{v5_x} Y{v5_y}
G01 X{v0_x} Y{v0_y}
M99
%
```

Note: Hexagon vertices are absolute coordinates (G90), only the plunge is relative.

**Main file for single hexagon:**

```gcode
G00 X{v0_x} Y{v0_y} Z{travel_height}
G00 Z0
M98 (-{base_path}\{project}\1200.nc) L{num_passes}
G00 Z{safety_height}
```

#### Linear Pattern of Hexagons

Similar to circles - main file positions at each hexagon start, calls subroutine with L = num_passes.

---

### B8. Line Cut Operations

For each point in the path after the start point:

**Straight segments:** Use G01
**Arc segments:** Use G02 (CW) or G03 (CCW). Arc center specified as I, J offsets from current position.

#### Arc Direction Determination

Use cross product to determine CW vs CCW:

```
vector_to_center = (center_x - current_x, center_y - current_y)
vector_to_dest = (dest_x - current_x, dest_y - current_y)
cross = vector_to_center.x * vector_to_dest.y - vector_to_center.y * vector_to_dest.x

if cross > 0: use G03 (CCW)
if cross < 0: use G02 (CW)
```

#### I, J Offset Calculation

```
I = center_x - current_x
J = center_y - current_y
```

#### Multi-Pass Line Cut Subroutine

Create subroutine `1300.nc` (or next available in 1300-1399 range).

**Subroutine content:**

```gcode
G91
G01 Z-{pass_depth} F{plunge_rate}
G90
G01 X{p1_x} Y{p1_y} F{feed_rate}
G01 X{p2_x} Y{p2_y}
G02 X{p3_x} Y{p3_y} I{i} J{j}
...
G01 X{p0_x} Y{p0_y}  (if closed path)
M99
%
```

**Main file:**

```gcode
G00 X{start_x} Y{start_y} Z{travel_height}
G00 Z0
M98 (-{base_path}\{project}\1300.nc) L{num_passes}
G00 Z{safety_height}
```

#### Fallback (No Subroutine Support)

Expand all passes inline, repeating the full path at each depth.

---

### B9. SVG Preview Generation

**Module:** `src/visualizer.py` - add `WebVisualizer` class

Generate an SVG string showing all operations on the material.

**Coordinate transformation:**
- Scale: 50 pixels per inch
- Flip Y axis (SVG Y increases downward, CNC Y increases upward)
- Add padding around material outline

**Color coding:**
| Element | Color |
|---------|-------|
| Material outline | #333333 |
| Drill points | #0066cc (blue) |
| Circular cuts | #cc6600 (orange) |
| Hexagonal cuts | #9933cc (purple) |
| Line cuts | #009933 (green) |
| Tube void area | #ffcccc with #cc0000 dashed border |

**Include:**
- Grid pattern on material background (1" spacing)
- Axis labels (X, Y)
- Scale markers
- Legend

---

## Part C: Shared Utilities

To maintain DRY principles, extract common functionality into shared utility modules.

---

### C1. Unit Conversion

**Module:** `src/utils/units.py`

| Function | Purpose |
|----------|---------|
| `inches_to_mm(value: float) → float` | Convert inches to millimeters (×25.4) |
| `mm_to_inches(value: float) → float` | Convert millimeters to inches (÷25.4) |

Note: Current G-code output uses inches (G20). These utilities retained for potential future use or display purposes.

---

### C2. Multi-Pass Calculations

**Module:** `src/utils/multipass.py`

| Function | Purpose |
|----------|---------|
| `calculate_num_passes(total_depth: float, pass_depth: float) → int` | Returns `ceil(total_depth / pass_depth)` |
| `calculate_pass_depths(total_depth: float, pass_depth: float) → List[float]` | Returns list of cumulative depths for each pass |
| `get_material_depth(material: Material) → float` | Returns `thickness` (sheet) or `wall_thickness` (tube) |

Used by: B6 Circular, B7 Hexagonal, B8 Line cuts

---

### C3. Tool Compensation

**Module:** `src/utils/tool_compensation.py`

| Function | Purpose |
|----------|---------|
| `calculate_cut_radius(feature_diameter: float, tool_diameter: float) → float` | Returns `(feature_diameter - tool_diameter) / 2` |
| `offset_point_inward(point: Point, center: Point, tool_radius: float) → Point` | Offset a vertex toward center by tool radius |
| `calculate_hexagon_compensated_vertices(center: Point, flat_to_flat: float, tool_diameter: float) → List[Point]` | Returns 6 vertices offset inward along angle bisectors |

Used by: B6 Circular, B7 Hexagonal cuts

---

### C4. Arc Direction

**Module:** `src/utils/arc_utils.py`

| Function | Purpose |
|----------|---------|
| `calculate_arc_direction(current: Point, destination: Point, center: Point) → str` | Returns "G02" (CW) or "G03" (CCW) based on cross product |
| `calculate_ij_offsets(current: Point, center: Point) → Tuple[float, float]` | Returns (I, J) offsets for arc command |

Used by: B8 Line cuts (arc segments)

---

### C5. G-Code Formatting

**Module:** `src/utils/gcode_format.py`

| Function | Purpose |
|----------|---------|
| `format_coordinate(value: float, precision: int = 4) → str` | Format number with appropriate decimal places |
| `generate_header(spindle_speed: int, warmup_seconds: int, safety_height: float) → List[str]` | Standard G-code header lines (no comments) |
| `generate_footer(safety_height: float) → List[str]` | Standard G-code footer lines (no comments) |
| `generate_rapid_move(x: float = None, y: float = None, z: float = None) → str` | G00 command |
| `generate_linear_move(x: float = None, y: float = None, z: float = None, feed: float = None) → str` | G01 command |
| `generate_arc_move(direction: str, x: float, y: float, i: float, j: float, feed: float = None) → str` | G02/G03 command |
| `generate_subroutine_call(file_path: str, loop_count: int) → str` | M98 command with proper syntax |
| `generate_subroutine_end() → List[str]` | Returns `["M99", "%"]` |
| `sanitize_project_name(name: str) → str` | Clean project name for filesystem use |

**Important:** No function in this module generates comments. All output is pure G-code.

Used by: All operation generators

---

### C6. Subroutine Generation

**Module:** `src/utils/subroutine_generator.py`

| Function | Purpose |
|----------|---------|
| `get_next_subroutine_number(operation_type: str, existing: List[int]) → int` | Returns next available number in range for operation type |
| `generate_subroutine_file(commands: List[str]) → str` | Wraps commands with M99 and % ending |
| `build_subroutine_path(base_path: str, project_name: str, subroutine_number: int) → str` | Constructs full absolute path for M98 call |
| `generate_peck_drill_subroutine(pecks: List[float], plunge_rate: float, travel_height: float, axis: str, spacing: float) → str` | Complete peck drill subroutine content |
| `generate_circle_pass_subroutine(cut_radius: float, pass_depth: float, plunge_rate: float, feed_rate: float) → str` | Single-pass circle cut subroutine |
| `generate_hexagon_pass_subroutine(vertices: List[Point], pass_depth: float, plunge_rate: float, feed_rate: float) → str` | Single-pass hexagon cut subroutine |
| `generate_line_path_subroutine(path: List[PathSegment], pass_depth: float, plunge_rate: float, feed_rate: float) → str` | Single-pass line path subroutine |

Used by: B5 Drilling, B6 Circular, B7 Hexagonal, B8 Line cuts

---

### C7. Coordinate Validation

**Module:** `src/utils/validators.py`

| Function | Purpose |
|----------|---------|
| `validate_bounds(x: float, y: float, max_x: float, max_y: float) → bool` | Check if point is within machine bounds |
| `validate_all_points(points: List[Point], max_x: float, max_y: float) → List[str]` | Returns list of error messages for out-of-bounds points |
| `validate_tool_in_standards(tool_type: str, size: str, gcode_standards: dict) → bool` | Check if tool parameters exist |

Used by: Validation step before G-code generation

---

### C8. File Management

**Module:** `src/utils/file_manager.py`

| Function | Purpose |
|----------|---------|
| `create_output_directory(base_path: str, project_name: str) → str` | Creates project directory, returns full path |
| `write_main_file(directory: str, content: str) → str` | Writes main.nc, returns file path |
| `write_subroutine_file(directory: str, number: int, content: str) → str` | Writes {number}.nc, returns file path |
| `package_for_download(directory: str) → bytes` | Creates zip archive of directory for download |

Used by: G-code generation endpoint

---

## Module Summary

| Module | Purpose |
|--------|---------|
| `src/pattern_expander.py` | Expand patterns to coordinates |
| `src/tube_void_checker.py` | Filter operations in tube void |
| `src/hexagon_generator.py` | Calculate hexagon vertices |
| `src/gcode_generator.py` | Main G-code generation orchestrator |
| `src/visualizer.py` | Generate SVG preview (WebVisualizer class) |
| `src/utils/units.py` | Unit conversion (inches ↔ mm) |
| `src/utils/multipass.py` | Multi-pass depth calculations |
| `src/utils/tool_compensation.py` | Tool radius offset calculations |
| `src/utils/arc_utils.py` | Arc direction and I/J offset calculations |
| `src/utils/gcode_format.py` | G-code command formatting (no comments) |
| `src/utils/subroutine_generator.py` | M98 subroutine file generation |
| `src/utils/validators.py` | Coordinate and parameter validation |
| `src/utils/file_manager.py` | Output directory and file management |

---

## Validation

Before generating G-code, validate using functions from `src/utils/validators.py`:

1. **Material is selected** - required for cutting parameters
2. **Tool is selected** - drill_tool_id for drilling, end_mill_tool_id for cutting
3. **All coordinates within bounds** - use `validate_all_points()` against machine max_x, max_y
4. **Tool size exists in gcode_standards** - use `validate_tool_in_standards()`, fallback to defaults if not found

---

## Complete Example

### Input

**Project:** "Frame16in"
**Material:** 0.125" aluminum sheet
**Operation:** Linear drill pattern, 31 holes, Y-axis, 0.5" spacing, starting at (0.25, 0.25)
**Tool:** 0.201" drill bit
**Settings:** pecking_depth=0.05", plunge_rate=10 in/min

### Output Directory

```
C:\Mach3\GCode\Frame16in\
├── main.nc
└── 1000.nc
```

### main.nc

```gcode
G20 G90
G00 X0 Y0 Z0
G00 Z0.5
M03 S1000
G04 P2
G00 X0.25 Y0.25 Z0.25
M98 (-C:\Mach3\GCode\Frame16in\1000.nc) L31
M05
G00 Z0.5
G00 X0 Y0
M30
```

### 1000.nc

```gcode
G00 Z0
G91
G01 Z-0.05 F10
G00 Z0.05
G01 Z-0.10 F10
G00 Z0.10
G01 Z-0.125 F10
G00 Z0.25
G00 Y0.5
G90
M99
%
```

This drills 31 holes along the Y-axis, each with a 3-peck cycle through 0.125" material.
