# G-Code Generator Web Application - Frontend Build Instructions

Build instructions for Claude Code to create the frontend UI.

**Tech Stack**: Jinja2 templates + Bootstrap 5 + Vanilla JavaScript

---

## Styling & Theming

### Color Palette

Override Bootstrap's default colors in `styles.css`:

| Role | Color | Usage |
|------|-------|-------|
| Primary | `#2F055A` | Buttons, links, navbar, active states, drill badges |
| Secondary | `#6c757d` | Secondary buttons, muted text |
| Info | `#5a7a8a` | Informational elements, circle badges (muted teal) |
| Light | `#f8f9fa` | Backgrounds, cards |
| Dark | `#343a40` | Text, dark UI elements |
| Success | `#5a8a6e` | Success alerts, save confirmations, line badges (muted green) |
| Warning | `#c9a87c` | Warning alerts, hex badges (muted tan/amber) |
| Danger | `#a85a6e` | Error alerts, delete buttons (muted pink) |

Use CSS custom properties to override Bootstrap:
```css
:root {
  --bs-primary: #2F055A;
  --bs-primary-rgb: 47, 5, 90;
  --bs-info: #5a7a8a;
  --bs-success: #5a8a6e;
  --bs-warning: #c9a87c;
  --bs-danger: #a85a6e;
}
```

### Base Font

Use Avenir as the primary font with fallbacks:

```css
body {
  font-family: 'Avenir', 'Avenir Next', 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

Avenir is a system font on macOS. For broader support, include Nunito from Google Fonts as a fallback (visually similar):

```html
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap" rel="stylesheet">
```

### Brand Font

The project name "GPRO" uses a custom TTF font. Load via `@font-face`:

```css
@font-face {
  font-family: 'GPRO-Brand';
  src: url('../fonts/gpro-brand.ttf') format('truetype');
  font-weight: normal;
  font-style: normal;
}

.brand-logo {
  font-family: 'GPRO-Brand', sans-serif;
}
```

**Usage**: Apply `.brand-logo` class ONLY to the "GPRO" text in the navbar. All other UI text uses the Avenir/Nunito base font.

### Branding

- **Project name**: GPRO (G-Code Pro)
- **Team**: 9771 FPRO (FIRST Robotics)
- **Navbar brand**: "GPRO" in brand font
- **Footer**: "GPRO is an FPRO Production" (centered, muted text)

---

## File Structure

```
templates/
├── base.html                    # Base template: nav (GPRO brand logo), flash messages, footer ("GPRO is an FPRO Production")
├── login.html                   # Login page (shown if APP_PASSWORD is set)
├── index.html                   # Projects dashboard (list all projects)
├── partials/                    # Reusable template fragments (use {% include %})
│   ├── coord_input.html         # X/Y coordinate input pair
│   ├── pattern_fields.html      # Linear/grid pattern fields
│   └── modal_footer.html        # Standard confirm/cancel modal footer
├── project/
│   ├── new.html                 # New project form (name, type, material)
│   └── edit.html                # Project editor (main workspace)
└── settings/
    ├── index.html               # Settings dashboard (links to subsections)
    ├── tools.html               # Tools management (drill bits, end mills)
    ├── materials.html           # Materials list
    ├── material_edit.html       # Edit material + G-code standards
    ├── machine.html             # Machine settings
    └── general.html             # General G-code settings

static/
├── css/
│   └── styles.css               # Custom styles, color overrides, brand font
├── fonts/
│   └── gpro-brand.ttf           # Brand font (used only for "GPRO" logo text)
└── js/
    ├── api.js                   # Shared API utilities (apiPost, apiGet, error handling)
    ├── validation.js            # Shared validation utilities
    ├── project-editor.js        # Project editor controller class
    └── unsaved-changes.js       # Tracks dirty state, warns before navigation
```

---

## Implementation Phases

1. **Phase 1**: Foundation
   - Base template
   - Shared JS utilities (`api.js`, `validation.js`)
   - Template partials (`coord_input.html`, `pattern_fields.html`, `modal_footer.html`)

2. **Phase 2**: Settings pages (tools, materials, machine, general)

3. **Phase 3**: Projects dashboard + new project form

4. **Phase 4**: Project editor (main workspace) - uses all shared components

5. **Phase 5**: Polish (validation feedback, error handling, edge cases)

---

## Data Schemas

### Tool Schema

```javascript
{
    "id": 1,                          // Integer ID (auto-increment)
    "tool_type": "drill" | "end_mill_1flute" | "end_mill_2flute",
    "size": 0.125,                    // Diameter in inches or mm
    "size_unit": "in" | "mm",         // Unit for the size value
    "description": "1/8\" cobalt drill bit"
}
```

### Material Schema

```javascript
{
    "id": "aluminum_tube_2x1_0125",   // Unique ID (no spaces)
    "display_name": "2x1 Aluminum Tube 0.125\" wall",
    "base_material": "aluminum" | "polycarbonate",
    "form": "sheet" | "tube",

    // Sheet only:
    "thickness": 0.125,

    // Tube only:
    "outer_width": 2.0,
    "outer_height": 1.0,
    "wall_thickness": 0.125,

    // G-code standards per tool_type and size (set via material_edit page)
    // Keys are tool sizes as strings (e.g., "0.125" for 1/8")
    "gcode_standards": {
        "drill": {
            "0.125": {
                "spindle_speed": 1000,      // RPM
                "feed_rate": 2.0,           // in/min
                "plunge_rate": 1.0,         // in/min
                "pecking_depth": 0.05       // in per peck
            }
        },
        "end_mill_1flute": {
            "0.125": {
                "spindle_speed": 12000,
                "feed_rate": 12.0,
                "plunge_rate": 2.0,
                "pass_depth": 0.025         // in per pass
            }
        },
        "end_mill_2flute": {
            "0.125": {
                "spindle_speed": 10000,
                "feed_rate": 10.0,
                "plunge_rate": 1.5,
                "pass_depth": 0.02          // in per pass
            }
        }
    }
}
```

### Machine Settings Schema

```javascript
{
    "name": "OMIO CNC",
    "max_x": 15.0,                   // inches - table size limit
    "max_y": 15.0,                   // inches - table size limit
    "units": "inches",               // Default unit for coordinates/dimensions
    "controller_type": "mach3" | "mach4" | "grbl" | "linuxcnc",
    "supports_loops": true,          // WHILE/DO for multi-pass
    "supports_canned_cycles": true   // G83 peck drilling
}
```

**Note:** Machine settings are loaded from the server. The UI receives these via `MACHINE` JavaScript variable (see Template Data Passing). Do not hardcode defaults in the frontend.

### General Settings Schema

```javascript
{
    "safety_height": 0.5,            // Height before spindle start (inches)
    "travel_height": 0.2,            // Height during rapid moves (inches)
    "spindle_warmup_seconds": 2      // Dwell after spindle on (G4)
}
```

**Note:** General settings are loaded from the server. These values are shown here for reference only - the authoritative defaults are defined in README-SERVER.md seed data.

### Project Schema

```javascript
{
    "id": "uuid-string",
    "name": "Drivetrain Gusset",
    "project_type": "drill" | "cut",      // Each project is ONE type only
    "material_id": "aluminum_tube_2x1_0125",
    "drill_tool_id": 1,                   // Foreign key to Tool (for drill projects)
    "end_mill_tool_id": 4,                // Foreign key to Tool (for cut projects)

    // For tube materials only:
    "tube_void_skip": false,              // Skip cutting through hollow center

    "operations": {
        // For drill projects:
        "drill_holes": [
            // Single point
            { "id": "op_1", "type": "single", "x": 1.0, "y": 2.0 },

            // Linear pattern (e.g., "hole every 0.5\" along X for 12\"")
            {
                "id": "op_2",
                "type": "pattern_linear",
                "start_x": 0.5,
                "start_y": 1.0,
                "axis": "x" | "y",
                "spacing": 0.5,
                "count": 24
            },

            // Grid pattern
            {
                "id": "op_3",
                "type": "pattern_grid",
                "start_x": 0.5,
                "start_y": 0.5,
                "x_spacing": 1.0,
                "y_spacing": 1.0,
                "x_count": 4,
                "y_count": 3
            }
        ],

        // For cut projects:
        "circular_cuts": [
            // Single circle
            {
                "id": "op_1",
                "type": "single",
                "center_x": 2.0,
                "center_y": 2.0,
                "diameter": 0.5
            },

            // Linear pattern of circles
            {
                "id": "op_2",
                "type": "pattern_linear",
                "start_center_x": 1.0,
                "start_center_y": 1.0,
                "diameter": 0.5,
                "axis": "x",
                "spacing": 2.0,
                "count": 4
            }
        ],

        "hexagonal_cuts": [
            // Single hexagon
            {
                "id": "op_1",
                "type": "single",
                "center_x": 2.0,
                "center_y": 2.0,
                "flat_to_flat": 0.5      // Distance between parallel flat sides
            },

            // Linear pattern of hexagons
            {
                "id": "op_2",
                "type": "pattern_linear",
                "start_center_x": 1.0,
                "start_center_y": 1.0,
                "flat_to_flat": 0.5,
                "axis": "x",
                "spacing": 2.0,
                "count": 4
            }
        ],

        "line_cuts": [
            {
                "id": "op_1",
                "points": [
                    { "x": 0, "y": 0, "line_type": "start" },
                    { "x": 5, "y": 0, "line_type": "straight" },
                    { "x": 5, "y": 3, "line_type": "straight" },
                    // For arcs: arc_center defines the curve; direction (G2/G3) computed from geometry
                    { "x": 0, "y": 3, "line_type": "arc", "arc_center_x": 2.5, "arc_center_y": 3 },
                    { "x": 0, "y": 0, "line_type": "straight" }
                ],
                "closed": true    // Default: true (most cuts are closed shapes)
            }
        ]
    },

    "created_at": "2024-01-15T10:30:00",
    "modified_at": "2024-01-15T14:22:00"
}
```

---

## Shared Components (DRY)

Build these reusable components/patterns to avoid repetitive code:

### 1. Coordinate Input Pair
Used everywhere: drill points, circle/hex centers, line points, pattern starts, arc centers.
- Reusable partial or JS component for X/Y input pair
- Accepts: labels, step value, field name prefix
- Include validation (numeric, within machine limits)

### 2. Pattern Fields
Linear patterns are identical across drills, circles, and hexes:
- Start X/Y (use coordinate input pair)
- Axis selector (X or Y)
- Spacing input
- Count input

Grid pattern (drills only) extends this with X/Y counts and spacings.

Build as a togglable fieldset that shows/hides based on pattern type selection.

### 3. Operation Modal Base
All "Add Operation" modals share:
- Pattern type selector (single vs linear vs grid)
- Dynamic field visibility based on pattern type
- Confirm/Cancel footer
- Form validation before confirm

Build a base modal pattern, then extend for each operation type's specific fields.

### 4. Operations List Item
Each operation in the list needs:
- Type badge (color-coded)
- Summary text (generated from operation data)
- Remove button with confirmation

Build a single `renderOperationItem(type, operation, index)` function that handles all types.

### 5. Settings Form Card
Machine settings and General settings pages are nearly identical:
- Card with form inputs
- Save button
- Cancel link back to settings index

Use same template structure, just different fields.

### 6. CRUD List Page
Tools and Materials pages share the pattern:
- Header with title + "Add" button
- Table or card list of items
- Edit/Delete actions per item
- Add modal

### 7. Validation Utilities (JS)
Centralize in `static/js/validation.js`:
- `isValidCoordinate(value, maxX, maxY)` - checks bounds
- `isPositiveNumber(value)` - for spacing, diameter, size, count
- `validateOperation(type, operation)` - returns array of error messages
- `validateProject(project)` - validates entire project before download

### 8. API Utilities (JS)
Centralize in `static/js/api.js`:
- `apiPost(url, data)` - POST with JSON, error handling
- `apiGet(url)` - GET with error handling
- Consistent error display pattern

---

## Page Specifications

### Settings: Tools (`/settings/tools`)

- List all tools grouped by type (drill, end_mill_1flute, end_mill_2flute)
- Each tool shows: size (with unit), description
- Add tool modal: tool_type (dropdown: drill, single flute end mill, double flute end mill), size, size_unit, description
- Edit tool (inline or modal)
- Delete tool (with confirmation)

### Settings: Materials (`/settings/materials`)

- List all materials showing: name, base material, form, dimensions
- Add material modal: display name, ID, base material, form, dimensions
- Edit link goes to material_edit page
- Delete (with confirmation)

### Settings: Material Edit (`/settings/materials/<id>/edit`)

- Basic info section: display name, base material, form, dimensions
- G-code standards section with tabs for "Drill", "Single Flute End Mill", "Double Flute End Mill"
- Under each tab: show every tool of that type with input fields for spindle_speed, feed_rate, plunge_rate, pecking_depth (drill) or pass_depth (end mills)
- This is where users dial in optimal settings per material/tool combo

### Settings: Machine (`/settings/machine`)

- Machine name
- Max X and Y travel (table size limits)
- Controller type dropdown
- Checkboxes: supports_loops, supports_canned_cycles

### Settings: General (`/settings/general`)

- Safety height input
- Travel height input
- Spindle warmup seconds input

### Projects Dashboard (`/`)

- Card grid of all projects showing: name, type badge (drill/cut), material, last modified
- Each card has: Edit button, Download button, Delete button
- "New Project" button

### New Project (`/projects/new`)

- Project name input
- Project type select (Drill or Cut)
- Material select (populated from materials list)
- Create button: creates project with default tool (first matching tool for type), redirects to editor

### Project Editor (`/projects/<id>/edit`)

**Layout**: Two columns on desktop (left: project info + operations, right: preview + download)

**Left Column - Project Info Card**:
- Name (editable)
- Type (editable - but changing clears operations, with warning)
- Material dropdown
- Tool dropdown (filtered by project type: drills for drill projects, end mills for cut)
- Tube void skip checkbox (only shown when material.form == "tube")

**Left Column - Operations Card**:
- Header with "Add" buttons based on project type:
  - Drill projects: "+ Drill" button
  - Cut projects: "+ Circle", "+ Hex", and "+ Line" buttons
- List of current operations with description and remove button
- Each operation shows summary (e.g., "Point at (1.0, 2.0)" or "4 holes along X, 0.5\" spacing")

**Add Drill Modal**:
- Pattern type: Single Point, Linear Pattern, Grid Pattern
- Fields change based on pattern type
- Single: X, Y coordinates
- Linear: start X/Y, axis (X or Y), spacing, count
- Grid: start X/Y, X spacing, Y spacing, X count, Y count

**Add Circle Modal**:
- Pattern type: Single Circle, Linear Pattern
- Single: center X/Y, diameter
- Linear: start center X/Y, diameter, axis, spacing, count

**Add Hex Modal**:
- Pattern type: Single Hexagon, Linear Pattern
- Single: center X/Y, flat_to_flat (distance between parallel flat sides)
- Linear: start center X/Y, flat_to_flat, axis, spacing, count

**Add Line Modal**:
- Points list with add/remove
- Each point: X, Y, line_type (start/straight/arc)
- If arc: show arc_center_x, arc_center_y fields
- Closed path checkbox

**Right Column - Preview Card**:
- Preview container (400px min height)
- "Refresh" button to generate SVG preview
- Preview shows toolpaths on coordinate grid

**Right Column - Download Card**:
- Validation errors display area
- Download G-Code button
- Validates: coordinates within machine limits, required fields set

**Unsaved Changes**:
- Track dirty state by comparing current data to last saved
- Show floating indicator with "Save" and "Discard" buttons when dirty
- `beforeunload` event to warn before leaving page

---

## Template Data Passing

The server passes JSON data to templates via `render_template()`. See **README-SERVER.md § Project Routes** for the complete list of template variables and their source service methods.

**Project Editor Variables** (available in `project/edit.html`):

| Variable | Type | Purpose |
|----------|------|---------|
| `PROJECT_ID` | String | Project UUID |
| `PROJECT_DATA` | Object | Full project data (see Project Schema) |
| `MATERIALS` | Object | All materials keyed by ID |
| `TOOLS` | Array | All tools as list |
| `MACHINE` | Object | Machine settings (max_x, max_y for validation) |

**Template usage:**
```html
{% block scripts %}
<script>
    const PROJECT_ID = "{{ project.id }}";
    const PROJECT_DATA = {{ project_json | safe }};
    const MATERIALS = {{ materials_json | safe }};
    const TOOLS = {{ tools_json | safe }};
    const MACHINE = {{ machine_json | safe }};
</script>
<script src="{{ url_for('static', filename='js/project-editor.js') }}"></script>
{% endblock %}
```

The `| safe` filter prevents Jinja from escaping JSON.

---

## API Endpoints (for AJAX calls)

See **README-SERVER.md § API Routes** for detailed request/response schemas.

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/projects/<id>/save` | POST | Save project | `{status: "ok", data: {modified_at}}` |
| `/api/projects/<id>/preview` | POST | Generate SVG | `{svg: "<svg>..."}` |
| `/api/projects/<id>/download` | GET | Download G-code | `.nc` file (uses project's type) |
| `/api/projects/<id>/validate` | POST | Validate project | `{valid: bool, errors: [...]}` |

---

## Validation Rules

**Project creation**:
- Name required, non-empty
- Project type required (drill or cut)
- Material required

**Operations**:
- All coordinates must be numbers
- Coordinates must be within machine limits (0 to max_x, 0 to max_y)
- Patterns: count >= 1, spacing > 0
- Circles: diameter > 0
- Hexagons: flat_to_flat > 0
- Lines: minimum 2 points

**Before download**:
- Project must have at least one operation
- Tool must be selected
- All operations must be valid

---

## Key Behaviors

1. **Project type change**: Warn user that changing type will clear operations, then clear operations arrays

2. **Material change**: If switching between tube/sheet forms, reset tube_void_skip

3. **Tool filtering**: Only show drills for drill projects, only show end mills for cut projects

4. **Preview refresh**: POST current (possibly unsaved) data to preview endpoint, not saved data

5. **Download**: Validates first, then triggers file download. Must save before download (prompt if unsaved changes)

6. **Tube void skip**: When enabled and material is tube, G-code generator should skip the hollow center area when cutting

---

## Conventions & Defaults

### Units
- **All UI coordinates are in inches** - this is the FIRST Robotics standard
- Tool sizes can be entered in inches or mm (stored with unit, converted as needed for G-code)
- G-code output is in mm (converted from inches, standard for OMIO CNC)

### Arc Direction
- Arcs are defined by: start point (previous point), end point (current point), and arc center
- **Arc direction is automatically determined**: if arc center is to the left of the travel direction, it's counterclockwise (G3); if to the right, clockwise (G2)
- The UI doesn't ask for direction; it's computed from geometry

### Pattern Support
- **Drills**: Single, Linear, Grid patterns
- **Circles**: Single, Linear patterns
- **Hexagons**: Single, Linear patterns
- **Lines**: No patterns (freeform point entry)

Grid patterns are drill-only because grid arrangements of cut shapes are less common.

### Defaults
- **Closed path**: Default `true` for line cuts (most outlines are closed shapes)
- **Tube void skip**: Default `false`

### Operation Badge Colors
Use Bootstrap contextual classes (colors defined in palette above):
- Drill: `badge bg-primary` (purple #2F055A)
- Circle: `badge bg-info` (muted teal #5a7a8a)
- Hex: `badge bg-warning` (amber #c9a87c)
- Line: `badge bg-success` (muted green #5a8a6e)
