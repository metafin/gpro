# G-Code Generator Web Application - Backend Build Instructions

This document provides instructions for Claude Code sessions to build the Flask backend for the G-code generator web application.

## Overview

Transform the existing Python CLI G-code generator into a web application backend with:
- Settings management (materials, machine parameters, G-code standards)
- Project CRUD operations with drill/cut operations and patterns
- G-code generation on-demand
- PostgreSQL database for persistent storage

**Tech Stack**: Flask + SQLAlchemy + PostgreSQL + Gunicorn

---

## Shared Definitions

This section defines schemas, constants, and patterns used throughout the application. Reference these definitions rather than duplicating them.

---

### Constants

#### Tool Types
Define in `src/constants.py` and import wherever needed:

| Constant | Value | Description |
|----------|-------|-------------|
| `TOOL_TYPE_DRILL` | `'drill'` | Standard drill bit |
| `TOOL_TYPE_END_MILL_1FLUTE` | `'end_mill_1flute'` | Single flute end mill |
| `TOOL_TYPE_END_MILL_2FLUTE` | `'end_mill_2flute'` | Double flute end mill |

```python
VALID_TOOL_TYPES = ['drill', 'end_mill_1flute', 'end_mill_2flute']
```

#### Project Types
| Constant | Value |
|----------|-------|
| `PROJECT_TYPE_DRILL` | `'drill'` |
| `PROJECT_TYPE_CUT` | `'cut'` |

#### Material Forms
| Constant | Value |
|----------|-------|
| `MATERIAL_FORM_SHEET` | `'sheet'` |
| `MATERIAL_FORM_TUBE` | `'tube'` |

#### Operation Types
| Constant | Value |
|----------|-------|
| `OP_TYPE_SINGLE` | `'single'` |
| `OP_TYPE_PATTERN_LINEAR` | `'pattern_linear'` |
| `OP_TYPE_PATTERN_GRID` | `'pattern_grid'` |

#### Line Types (for line cuts)
| Constant | Value |
|----------|-------|
| `LINE_TYPE_START` | `'start'` |
| `LINE_TYPE_STRAIGHT` | `'straight'` |
| `LINE_TYPE_ARC` | `'arc'` |

---

### JSON Schemas

These schemas are the single source of truth. All services, routes, and API endpoints use these structures.

#### Operations Schema
Used in: `Project.operations`, API save/preview requests, `get_as_dict()` output.

```json
{
  "drill_holes": [
    {"id": "string", "type": "single", "x": 0.0, "y": 0.0},
    {"id": "string", "type": "pattern_linear", "start_x": 0.0, "start_y": 0.0, "axis": "x|y", "spacing": 0.0, "count": 0},
    {"id": "string", "type": "pattern_grid", "start_x": 0.0, "start_y": 0.0, "x_spacing": 0.0, "y_spacing": 0.0, "x_count": 0, "y_count": 0}
  ],
  "circular_cuts": [
    {"id": "string", "type": "single", "center_x": 0.0, "center_y": 0.0, "diameter": 0.0},
    {"id": "string", "type": "pattern_linear", "start_center_x": 0.0, "start_center_y": 0.0, "diameter": 0.0, "axis": "x|y", "spacing": 0.0, "count": 0}
  ],
  "hexagonal_cuts": [
    {"id": "string", "type": "single", "center_x": 0.0, "center_y": 0.0, "flat_to_flat": 0.0},
    {"id": "string", "type": "pattern_linear", "start_center_x": 0.0, "start_center_y": 0.0, "flat_to_flat": 0.0, "axis": "x|y", "spacing": 0.0, "count": 0}
  ],
  "line_cuts": [
    {"id": "string", "points": [{"x": 0.0, "y": 0.0, "line_type": "start|straight|arc", "arc_center_x?": 0.0, "arc_center_y?": 0.0}], "closed": true}
  ]
}
```

#### Project Dict Schema
Used in: `ProjectService.get_as_dict()`, `project_json` template variable, API responses.

```json
{
  "id": "uuid-string",
  "name": "string",
  "project_type": "drill|cut",
  "material_id": "string|null",
  "drill_tool_id": "int|null",
  "end_mill_tool_id": "int|null",
  "operations": "{Operations Schema}",
  "tube_void_skip": false,
  "created_at": "ISO-8601",
  "modified_at": "ISO-8601"
}
```

#### Material Dict Schema
Used in: `SettingsService.get_materials_dict()`, `materials_json` template variable.

```json
{
  "material_id": {
    "id": "string",
    "display_name": "string",
    "base_material": "aluminum|polycarbonate",
    "form": "sheet|tube",
    "thickness": "float|null (sheets only)",
    "outer_width": "float|null (tubes only)",
    "outer_height": "float|null (tubes only)",
    "wall_thickness": "float|null (tubes only)",
    "gcode_standards": "{GCode Standards Schema}"
  }
}
```

#### GCode Standards Schema
Used in: `Material.gcode_standards`, API gcode-params response.

```json
{
  "drill": {
    "0.125": {"spindle_speed": 1000, "feed_rate": 2.0, "plunge_rate": 1.0, "pecking_depth": 0.05}
  },
  "end_mill_1flute": {
    "0.125": {"spindle_speed": 12000, "feed_rate": 12.0, "plunge_rate": 2.0, "pass_depth": 0.025}
  },
  "end_mill_2flute": {
    "0.125": {"spindle_speed": 10000, "feed_rate": 10.0, "plunge_rate": 1.5, "pass_depth": 0.02}
  }
}
```

**Note:** Tool sizes are stored as string keys in JSON (e.g., `"0.125"` for 1/8"). When looking up parameters in Python, convert the tool size to string: `gcode_standards.get(tool_type, {}).get(str(tool_size))`.

---

### API Response Patterns

All API endpoints follow these response patterns. Use helper functions in `web/utils/responses.py`.

#### Success Response
```python
def success_response(data=None, message=None):
    response = {"status": "ok"}
    if data: response["data"] = data
    if message: response["message"] = message
    return jsonify(response), 200
```

#### Error Response
```python
def error_response(message, status_code=400):
    return jsonify({"status": "error", "message": message}), status_code
```

#### Validation Response
```python
def validation_response(errors):
    return jsonify({"valid": len(errors) == 0, "errors": errors}), 200
```

---

### Service Conventions

All service classes follow these patterns:

1. **Static Methods**: All methods are `@staticmethod` (no instance state)
2. **Singleton Pattern**: Settings models (MachineSettings, GeneralSettings) auto-create if missing
3. **Return Types**:
   - `get_*()` returns model instance or `None`
   - `get_all_*()` returns `List[Model]`
   - `get_*_dict()` returns `Dict` for JSON serialization
   - `create_*()` returns new model instance
   - `update_*()` returns updated model or `None` if not found
   - `delete_*()` returns `bool` (True if deleted, False if not found or in use)
4. **Database Commits**: Services call `db.session.commit()` after mutations

---

## Project Structure

Create this directory structure:

```
generate-g-code/
├── app.py                      # Flask app entry point
├── config.py                   # Configuration management
├── Procfile                    # Heroku: web: gunicorn app:app
├── runtime.txt                 # Heroku: python-3.13.0
├── requirements.txt            # Updated dependencies
├── seed_data.py                # Populate default settings
│
├── migrations/                 # Flask-Migrate database migrations
│
├── src/                        # Core logic (existing + new)
│   ├── __init__.py
│   ├── constants.py            # NEW: Shared constants (tool types, etc.)
│   ├── file_parser.py          # Keep existing
│   ├── gcode_generator.py      # Refactor for loops + settings integration
│   ├── pattern_expander.py     # NEW: Expand patterns to coordinates
│   ├── tube_void_checker.py    # NEW: Tube void detection
│   ├── hexagon_generator.py    # NEW: Generate hexagon cut paths
│   ├── visualizer.py           # Modify for web (return SVG/PNG data)
│   ├── models.py               # NEW: Shared dataclasses
│   └── utils/                  # NEW: Shared utility modules
│       ├── __init__.py
│       ├── units.py            # Unit conversion (inches ↔ mm)
│       ├── multipass.py        # Multi-pass depth calculations
│       ├── tool_compensation.py # Tool radius offset calculations
│       ├── arc_utils.py        # Arc direction and I/J offsets
│       ├── gcode_format.py     # G-code command formatting
│       ├── loop_generator.py   # WHILE loop G-code generation
│       └── validators.py       # Coordinate and parameter validation
│
├── web/                        # Web layer
│   ├── __init__.py
│   ├── extensions.py           # SQLAlchemy, Migrate instances
│   ├── auth.py                 # Simple password authentication
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py             # Home, dashboard, login
│   │   ├── projects.py         # Project CRUD
│   │   ├── settings.py         # Settings pages
│   │   └── api.py              # AJAX endpoints
│   ├── models.py               # SQLAlchemy database models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── settings_service.py # Settings management
│   │   ├── project_service.py  # Project management
│   │   └── gcode_service.py    # G-code generation orchestration
│   └── utils/
│       ├── __init__.py
│       └── responses.py        # API response helpers
│
├── templates/                  # Jinja2 templates
│   ├── base.html               # Base template with common layout
│   ├── login.html              # Login page (if password enabled)
│   └── ...
└── static/                     # CSS, JS, images
```

---

## Dependencies (requirements.txt)

```
Flask>=3.0.0
gunicorn>=21.0.0
WTForms>=3.1.0
Flask-WTF>=1.2.0
Flask-SQLAlchemy>=3.1.0
Flask-Migrate>=4.0.0
Flask-Cors>=4.0.0
psycopg2-binary>=2.9.0
matplotlib>=3.8.0
numpy>=1.26.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```

---

## Database Extensions (web/extensions.py)

Create `db` and `migrate` instances in a separate file to avoid circular imports. All models and services import `db` from `web.extensions`, NOT from `app.py`.

---

## Flask App Setup (app.py)

Use the application factory pattern (`create_app()`). Register these blueprints:

| Blueprint | Prefix | Module |
|-----------|--------|--------|
| `main_bp` | (none) | `web.routes.main` |
| `projects_bp` | `/projects` | `web.routes.projects` |
| `settings_bp` | `/settings` | `web.routes.settings` |
| `api_bp` | `/api` | `web.routes.api` |

Import blueprints inside `create_app()` to avoid circular imports.

---

## Configuration (config.py)

**Environment Variables:**

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session signing | `'dev-key-change-in-production'` |
| `DATABASE_URL` | PostgreSQL connection string | `'sqlite:///gcode.db'` |
| `APP_PASSWORD` | Simple auth password (optional) | `None` (no auth) |
| `SESSION_TIMEOUT_MINUTES` | Session expiry | `480` (8 hours) |

**Important:** Heroku sets `DATABASE_URL` with `postgres://` but SQLAlchemy requires `postgresql://`. Add logic to replace the prefix if it starts with `postgres://`.

---

## Security Setup

### Simple Password Authentication

Add password protection without full user management. Create `web/auth.py`:

The auth module should:
1. Check if `APP_PASSWORD` is configured in environment
2. If set, require login before accessing any routes
3. Store authentication state in Flask session
4. Provide `/login` and `/logout` routes
5. Use a decorator `@login_required` for protected routes

### CORS Configuration

Add `flask-cors` to requirements.txt. Configure in `app.py`:
- Allow requests only from same origin by default
- For local development, allow localhost origins

### Session Security

Configure secure session cookies in `config.py`:
```python
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
```

---

## Database Models (web/models.py)

```python
from web.extensions import db
from datetime import datetime, UTC
import uuid

class Material(db.Model):
    """Material type with G-code standards per tool size."""
    id = db.Column(db.String(50), primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    base_material = db.Column(db.String(50), nullable=False)  # 'aluminum', 'polycarbonate'
    form = db.Column(db.String(20), nullable=False)  # 'sheet' or 'tube'

    # For sheets
    thickness = db.Column(db.Float, nullable=True)

    # For tubes
    outer_width = db.Column(db.Float, nullable=True)
    outer_height = db.Column(db.Float, nullable=True)
    wall_thickness = db.Column(db.Float, nullable=True)

    # G-code standards stored as JSON, keyed by tool_type then size (as string)
    gcode_standards = db.Column(db.JSON, nullable=False, default=dict)
    # Format: {
    #   "drill": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pecking_depth": ...}},
    #   "end_mill_1flute": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pass_depth": ...}},
    #   "end_mill_2flute": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pass_depth": ...}}
    # }
    #
    # NOTE: Tool sizes are string keys in JSON. When looking up parameters, convert tool size to string:
    #   params = material.gcode_standards.get(tool_type, {}).get(str(tool.size))


class MachineSettings(db.Model):
    """Machine configuration (singleton - one row)."""
    id = db.Column(db.Integer, primary_key=True, default=1)
    name = db.Column(db.String(100), default='OMIO CNC')
    max_x = db.Column(db.Float, default=15.0)
    max_y = db.Column(db.Float, default=15.0)
    units = db.Column(db.String(10), default='inches')  # Default unit for coordinates/dimensions
    controller_type = db.Column(db.String(20), default='mach3')
    supports_loops = db.Column(db.Boolean, default=True)
    supports_canned_cycles = db.Column(db.Boolean, default=True)

# Note: MachineSettings.units is the default unit for coordinates and dimensions.
# Individual tools may have their own size_unit if they differ from this default.
# G-code output is always converted to mm (standard for OMIO CNC).


class GeneralSettings(db.Model):
    """General G-code settings (singleton - one row)."""
    id = db.Column(db.Integer, primary_key=True, default=1)
    safety_height = db.Column(db.Float, default=0.5)
    travel_height = db.Column(db.Float, default=0.2)
    spindle_warmup_seconds = db.Column(db.Integer, default=2)


class Tool(db.Model):
    """Available tools (drill bits and end mills)."""
    id = db.Column(db.Integer, primary_key=True)
    tool_type = db.Column(db.String(20), nullable=False)  # 'drill', 'end_mill_1flute', 'end_mill_2flute'
    size = db.Column(db.Float, nullable=False)  # diameter
    size_unit = db.Column(db.String(5), nullable=False, default='in')  # 'in' or 'mm'
    description = db.Column(db.String(100))

# Valid tool_type values:
#   'drill'           - standard drill bit
#   'end_mill_1flute' - single flute end mill (better for plastics, aluminum)
#   'end_mill_2flute' - double flute end mill (general purpose)


class Project(db.Model):
    """User project with operations."""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    modified_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    project_type = db.Column(db.String(20), nullable=False)  # 'drill' or 'cut'
    material_id = db.Column(db.String(50), db.ForeignKey('material.id'))
    material = db.relationship('Material')

    # Tool references (foreign keys to Tool table)
    drill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=True)
    end_mill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=True)
    drill_tool = db.relationship('Tool', foreign_keys=[drill_tool_id])
    end_mill_tool = db.relationship('Tool', foreign_keys=[end_mill_tool_id])

    # Operations stored as JSON (flexible structure)
    operations = db.Column(db.JSON, nullable=False, default=dict)
    # Format: {"drill_holes": [...], "circular_cuts": [...], "hexagonal_cuts": [...], "line_cuts": [...]}

    # Tube void settings
    tube_void_skip = db.Column(db.Boolean, default=False)
```

---

## Operations JSON Structure

The `operations` column in the Project model uses the **Operations Schema** defined in the Shared Definitions section.

**Additional Notes:**

- **Hexagonal Cuts**: `flat_to_flat` is the "wrench size" - distance between parallel flat sides. Hexagons are oriented point-up (flats parallel to X-axis).
- **Line Cut Arcs**: `arc_center_x` and `arc_center_y` define the circle center. Arc direction (G2/G3) is determined automatically from geometry.

---

## G-Code Generation Modules

The `src/` modules handle G-code generation. See **README-GCODE.md** for the complete module list with detailed algorithms, function signatures, and specifications.

Key modules: `gcode_generator.py` (orchestrator), `pattern_expander.py`, `hexagon_generator.py`, `tube_void_checker.py`, `visualizer.py`, and the `utils/` shared utilities.

---

## Shared Dataclasses (src/models.py)

Define these dataclasses for use across G-code generation modules:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Point:
    """A 2D coordinate point."""
    x: float
    y: float

@dataclass
class GCodeParams:
    """G-code generation parameters for a specific material/tool combination."""
    spindle_speed: int
    feed_rate: float      # inches/min
    plunge_rate: float    # inches/min
    material_depth: float # inches (thickness or wall_thickness)

    # Drill-specific
    pecking_depth: Optional[float] = None  # inches per peck

    # End mill-specific
    pass_depth: Optional[float] = None     # inches per pass

@dataclass
class CircleCut:
    """A circular cut operation."""
    center: Point
    diameter: float

@dataclass
class HexCut:
    """A hexagonal cut operation."""
    center: Point
    flat_to_flat: float

@dataclass
class LineCutPoint:
    """A point in a line cut path."""
    x: float
    y: float
    line_type: str  # 'start', 'straight', 'arc'
    arc_center_x: Optional[float] = None
    arc_center_y: Optional[float] = None

@dataclass
class LineCut:
    """A line cut operation (path of connected segments)."""
    points: List[LineCutPoint]
    closed: bool = True
```

These dataclasses are used by:
- `src/pattern_expander.py` - returns `List[Point]` for expanded patterns
- `src/gcode_generator.py` - accepts these types as input
- `web/services/gcode_service.py` - creates `GCodeParams` from database settings

---

## Seed Data (seed_data.py)

Create a script to populate initial settings. Use `create_app()` context and only insert if tables are empty.

### Default Materials

| id | display_name | base_material | form | thickness | outer_width | outer_height | wall_thickness |
|----|--------------|---------------|------|-----------|-------------|--------------|----------------|
| `aluminum_sheet_0125` | Aluminum Sheet 1/8" | aluminum | sheet | 0.125 | - | - | - |
| `aluminum_sheet_025` | Aluminum Sheet 1/4" | aluminum | sheet | 0.25 | - | - | - |
| `polycarbonate_sheet_025` | Polycarbonate Sheet 1/4" | polycarbonate | sheet | 0.25 | - | - | - |
| `aluminum_tube_2x1_0125` | Aluminum Tube 2x1 (0.125 wall) | aluminum | tube | - | 2.0 | 1.0 | 0.125 |

### Default G-Code Standards (per material, tool_type, size)

**Aluminum Sheet 1/8" (`aluminum_sheet_0125`) - 0.125" tools:**

| tool_type | spindle_speed | feed_rate | plunge_rate | pecking_depth | pass_depth |
|-----------|---------------|-----------|-------------|---------------|------------|
| drill | 1000 | 2.0 | 1.0 | 0.05 | - |
| end_mill_1flute | 12000 | 12.0 | 2.0 | - | 0.025 |
| end_mill_2flute | 10000 | 10.0 | 1.5 | - | 0.02 |

**Aluminum Sheet 1/4" (`aluminum_sheet_025`) - 0.125" tools:**

| tool_type | spindle_speed | feed_rate | plunge_rate | pecking_depth | pass_depth |
|-----------|---------------|-----------|-------------|---------------|------------|
| drill | 800 | 1.5 | 0.8 | 0.04 | - |
| end_mill_1flute | 10000 | 10.0 | 1.2 | - | 0.02 |
| end_mill_2flute | 8000 | 8.0 | 1.0 | - | 0.015 |

**Polycarbonate Sheet 1/4" (`polycarbonate_sheet_025`) - 0.125" tools:**

| tool_type | spindle_speed | feed_rate | plunge_rate | pecking_depth | pass_depth |
|-----------|---------------|-----------|-------------|---------------|------------|
| drill | 2000 | 4.0 | 2.0 | 0.1 | - |
| end_mill_1flute | 18000 | 25.0 | 4.0 | - | 0.06 |
| end_mill_2flute | 15000 | 20.0 | 3.0 | - | 0.05 |

**Aluminum Tube 2x1 (`aluminum_tube_2x1_0125`) - 0.125" tools:**

| tool_type | spindle_speed | feed_rate | plunge_rate | pecking_depth | pass_depth |
|-----------|---------------|-----------|-------------|---------------|------------|
| drill | 1000 | 2.0 | 1.0 | 0.05 | - |
| end_mill_1flute | 12000 | 12.0 | 2.0 | - | 0.025 |
| end_mill_2flute | 10000 | 10.0 | 1.5 | - | 0.02 |

### Default Machine Settings (singleton)

| Field | Value |
|-------|-------|
| name | OMIO CNC |
| max_x | 15.0 |
| max_y | 15.0 |
| units | inches |
| controller_type | mach3 |
| supports_loops | true |
| supports_canned_cycles | true |

### Default General Settings (singleton)

| Field | Value |
|-------|-------|
| safety_height | 0.5 |
| travel_height | 0.2 |
| spindle_warmup_seconds | 2 |

### Default Tools

| tool_type | size | size_unit | description |
|-----------|------|-----------|-------------|
| drill | 0.125 | in | 1/8" drill bit |
| drill | 0.1875 | in | 3/16" drill bit |
| drill | 0.25 | in | 1/4" drill bit |
| end_mill_1flute | 0.125 | in | 1/8" single flute end mill |
| end_mill_1flute | 0.1875 | in | 3/16" single flute end mill |
| end_mill_1flute | 0.25 | in | 1/4" single flute end mill |
| end_mill_2flute | 0.125 | in | 1/8" double flute end mill |
| end_mill_2flute | 0.1875 | in | 3/16" double flute end mill |
| end_mill_2flute | 0.25 | in | 1/4" double flute end mill |

---

## Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database migrations (first time only)
flask db init

# Create and run migrations
flask db migrate -m "Initial models"
flask db upgrade

# Seed default data
python seed_data.py

# Run locally
flask run --debug

# Or with gunicorn (production-like)
gunicorn app:app
```

---

## Implementation Order

1. **Phase 1**: Flask app setup
   - Create `app.py` with blueprints and SQLAlchemy
   - Create `config.py` for configuration
   - Create `web/models.py` with all database models
   - Set up Flask-Migrate

2. **Phase 2**: Services layer
   - Create `web/services/settings_service.py`
   - Create `web/services/project_service.py`
   - Create `web/services/gcode_service.py`

3. **Phase 3**: Core modules
   - Create `src/pattern_expander.py`
   - Create `src/tube_void_checker.py`
   - Refactor `src/gcode_generator.py` for loops (G83, WHILE)

4. **Phase 4**: Routes
   - Create `web/routes/main.py` for home/dashboard
   - Create `web/routes/projects.py` for project CRUD
   - Create `web/routes/settings.py` for settings management
   - Create `web/routes/api.py` for AJAX endpoints

5. **Phase 5**: Seed data
   - Create `seed_data.py`
   - Test with local SQLite database

---

## Key Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app.py` | Create | Flask entry point with db init |
| `config.py` | Create | Configuration with DATABASE_URL, APP_PASSWORD |
| `requirements.txt` | Update | Add Flask, SQLAlchemy, psycopg2, Flask-Cors |
| `seed_data.py` | Create | Populate default settings |
| `web/__init__.py` | Create | Web package init (empty, just marks as package) |
| `web/extensions.py` | Create | SQLAlchemy and Migrate instances |
| `web/auth.py` | Create | Simple password authentication decorator |
| `web/models.py` | Create | SQLAlchemy models |
| `web/routes/__init__.py` | Create | Routes package init (empty) |
| `web/routes/main.py` | Create | Home/dashboard/login routes |
| `web/routes/projects.py` | Create | Project CRUD routes |
| `web/routes/settings.py` | Create | Settings routes |
| `web/routes/api.py` | Create | API endpoints |
| `web/services/__init__.py` | Create | Services package init (empty) |
| `web/services/settings_service.py` | Create | Settings business logic |
| `web/services/project_service.py` | Create | Project business logic |
| `web/services/gcode_service.py` | Create | G-code generation |
| `src/__init__.py` | Create | Src package init (empty) |
| `src/constants.py` | Create | Shared constants (tool types, project types, etc.) |
| `src/gcode_generator.py` | Modify | Add loops, settings integration |
| `src/pattern_expander.py` | Create | Pattern expansion |
| `src/hexagon_generator.py` | Create | Hexagon vertex and path generation |
| `src/tube_void_checker.py` | Create | Tube void detection |
| `src/visualizer.py` | Modify | Add WebVisualizer class for SVG output |
| `src/utils/__init__.py` | Create | Utils package init (empty) |
| `src/utils/units.py` | Create | Unit conversion (inches ↔ mm) |
| `src/utils/multipass.py` | Create | Multi-pass depth calculations |
| `src/utils/tool_compensation.py` | Create | Tool radius offset calculations |
| `src/utils/arc_utils.py` | Create | Arc direction and I/J offset calculations |
| `src/utils/gcode_format.py` | Create | G-code command formatting |
| `src/utils/loop_generator.py` | Create | WHILE loop G-code generation |
| `src/utils/validators.py` | Create | Coordinate and parameter validation |
| `web/utils/__init__.py` | Create | Web utils package init (empty) |
| `web/utils/responses.py` | Create | API response helper functions |

**Note on `__init__.py` files**: All `__init__.py` files can be empty. They exist only to mark directories as Python packages.

---

## Services Layer

### Settings Service (web/services/settings_service.py)

Manages all settings models. All methods are `@staticmethod`.

**Material Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all_materials()` | `List[Material]` | All materials, ordered by display_name |
| `get_material(material_id)` | `Optional[Material]` | Single material by ID |
| `get_materials_dict()` | `Dict[str, Dict]` | All materials as dict for JSON (keyed by id, includes all fields + gcode_standards) |
| `create_material(data)` | `Material` | Create from dict with all Material fields |
| `update_material(material_id, data)` | `Optional[Material]` | Update existing, returns None if not found |
| `delete_material(material_id)` | `bool` | Delete if no associated projects, returns False if in use |

**Machine Settings Methods** (singleton pattern - auto-create if missing):

| Method | Returns | Description |
|--------|---------|-------------|
| `get_machine_settings()` | `MachineSettings` | Get singleton (id=1), create with defaults if missing |
| `update_machine_settings(data)` | `MachineSettings` | Update from dict |

**General Settings Methods** (singleton pattern):

| Method | Returns | Description |
|--------|---------|-------------|
| `get_general_settings()` | `GeneralSettings` | Get singleton (id=1), create with defaults if missing |
| `update_general_settings(data)` | `GeneralSettings` | Update from dict |

**Tool Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all_tools()` | `List[Tool]` | All tools, ordered by tool_type then size |
| `get_tools_by_type(tool_type)` | `List[Tool]` | Filter by type (e.g., 'drill', 'end_mill_1flute'), ordered by size |
| `get_tools_as_list()` | `List[Dict]` | All tools as list of dicts for JSON |
| `create_tool(data)` | `Tool` | Create from dict (tool_type, size, size_unit, description) |
| `delete_tool(tool_id)` | `bool` | Delete tool, returns False if not found |

**JSON Serialization Methods** (for passing data to templates):

| Method | Returns | Description |
|--------|---------|-------------|
| `get_machine_settings_dict()` | `Dict` | Machine settings as dict for JSON |
| `get_general_settings_dict()` | `Dict` | General settings as dict for JSON |

**Tool List Schema** (returned by `get_tools_as_list()`):
```json
[
  {"id": 1, "tool_type": "drill", "size": 0.125, "size_unit": "in", "description": "1/8\" drill bit"},
  {"id": 4, "tool_type": "end_mill_1flute", "size": 0.125, "size_unit": "in", "description": "1/8\" single flute"}
]
```

**Machine Settings Dict Schema** (returned by `get_machine_settings_dict()`):
```json
{
  "name": "OMIO CNC",
  "max_x": 15.0,
  "max_y": 15.0,
  "units": "inches",
  "controller_type": "mach3",
  "supports_loops": true,
  "supports_canned_cycles": true
}
```

**General Settings Dict Schema** (returned by `get_general_settings_dict()`):
```json
{
  "safety_height": 0.5,
  "travel_height": 0.2,
  "spindle_warmup_seconds": 2
}
```

---

### Project Service (web/services/project_service.py)

Manages project CRUD operations. All methods are `@staticmethod`.

**Constants:**
```python
EMPTY_OPERATIONS = {
    'drill_holes': [],
    'circular_cuts': [],
    'hexagonal_cuts': [],
    'line_cuts': []
}
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all()` | `List[Project]` | All projects, ordered by modified_at desc |
| `get(project_id)` | `Optional[Project]` | Single project by UUID |
| `get_as_dict(project_id)` | `Optional[Dict]` | Project as dict for JSON (see schema below) |
| `create(data)` | `Project` | Create with new UUID, empty operations |
| `save(project_id, data)` | `Optional[Project]` | Update from editor data, sets modified_at |
| `delete(project_id)` | `bool` | Delete project |
| `duplicate(project_id, new_name=None)` | `Optional[Project]` | Deep copy with new UUID, appends " (Copy)" if no name given |

**`get_as_dict()` output:** Returns **Project Dict Schema** (see Shared Definitions).

---

### G-Code Service (web/services/gcode_service.py)

This service orchestrates G-code generation. It delegates actual G-code logic to the modules in `src/` (see **README-GCODE.md** for algorithms).

**Methods to implement:**

1. `get_gcode_params(material, tool_size, operation_type)` → GCodeParams dataclass
   - Look up material's gcode_standards for the tool size
   - Fall back to sensible defaults if not found
   - Get material_depth from material.thickness (sheets) or material.wall_thickness (tubes)

2. `expand_operations(operations)` → (drill_points, circular_cuts, hexagonal_cuts, line_cuts)
   - Expand all pattern types (single, pattern_linear, pattern_grid) to individual coordinates
   - For hexagonal cuts, just pass through the center + flat_to_flat (vertex calculation happens in gcode_generator)
   - Apply tube void filtering if project.tube_void_skip is enabled

3. `generate(project, gcode_type)` → str
   - Get settings from SettingsService (general settings, machine settings)
   - Get appropriate tool from project (drill_tool for 'drill', end_mill_tool for 'cut')
   - Get tool size and convert to machine units if needed (tool.size_unit vs machine.units)
   - Validate that material is set (raise error if not)
   - Call expand_operations to get all coordinates
   - Use GCodeGenerator from src/gcode_generator.py to produce output
   - For cuts: generate circular cuts, then hexagonal cuts, then line cuts

4. `generate_preview_svg(project)` → str
   - Expand operations
   - Call WebVisualizer.generate_svg() from src/visualizer.py
   - Material dimensions come from material (tube: outer_width × outer_height, sheet: use machine max_x × max_y)

5. `validate(project)` → List[str] (errors)
   - Check required fields (material, appropriate tool size)
   - Check all coordinates are within machine bounds (from MachineSettings)
   - Return empty list if valid

**Important**: All parameters come from database settings - no hard-coded values. If a required setting is missing, raise a descriptive error.

---

## Route Handlers

### Main Routes (web/routes/main.py)

Blueprint: `main_bp` (no prefix)

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page - list all projects |
| `/login` | GET, POST | Login page (if APP_PASSWORD set) |
| `/logout` | GET | Clear session and redirect to login |

Use the `@login_required` decorator from `web.auth` on all routes except login/logout.

---

### Project Routes (web/routes/projects.py)

Blueprint: `projects_bp` (prefix: `/projects`)

| Route | Method | Description |
|-------|--------|-------------|
| `/new` | GET | New project form |
| `/create` | POST | Create project, redirect to edit |
| `/<project_id>` | GET | Project editor page |
| `/<project_id>/delete` | POST | Delete project |
| `/<project_id>/duplicate` | POST | Duplicate project |

The edit page passes JSON data to the template for JavaScript initialization.

**Template Variables** (embedded as `<script>` variables via Jinja2):

| Variable | Source | Schema |
|----------|--------|--------|
| `PROJECT_ID` | `project.id` | String (UUID) |
| `PROJECT_DATA` | `ProjectService.get_as_dict(project_id)` | **Project Dict Schema** |
| `MATERIALS` | `SettingsService.get_materials_dict()` | **Material Dict Schema** |
| `TOOLS` | `SettingsService.get_tools_as_list()` | **Tool List Schema** |
| `MACHINE` | `SettingsService.get_machine_settings_dict()` | **Machine Settings Dict Schema** |

**Route implementation example:**
```python
@projects_bp.route('/<project_id>')
@login_required
def edit(project_id):
    project = ProjectService.get(project_id)
    if not project:
        abort(404)
    return render_template('project/edit.html',
        project=project,
        project_json=json.dumps(ProjectService.get_as_dict(project_id)),
        materials_json=json.dumps(SettingsService.get_materials_dict()),
        tools_json=json.dumps(SettingsService.get_tools_as_list()),
        machine_json=json.dumps(SettingsService.get_machine_settings_dict())
    )
```

---

### Settings Routes (web/routes/settings.py)

Blueprint: `settings_bp` (prefix: `/settings`)

**Materials:**
| Route | Method | Description |
|-------|--------|-------------|
| `/materials` | GET | List all materials |
| `/materials/create` | POST | Create new material |
| `/materials/<id>/edit` | GET | Edit material form |
| `/materials/<id>/update` | POST | Update material |
| `/materials/<id>/delete` | POST | Delete material (fails if in use) |

**Machine Settings:**
| Route | Method | Description |
|-------|--------|-------------|
| `/machine` | GET | Machine settings form |
| `/machine/save` | POST | Save machine settings |

**General Settings:**
| Route | Method | Description |
|-------|--------|-------------|
| `/general` | GET | General settings form |
| `/general/save` | POST | Save general settings |

**Tools:**
| Route | Method | Description |
|-------|--------|-------------|
| `/tools` | GET | List all tools |
| `/tools/create` | POST | Add new tool |
| `/tools/<id>/delete` | POST | Delete tool |

---

### API Routes (web/routes/api.py)

Blueprint: `api_bp` (prefix: `/api`)

These endpoints are called by JavaScript in the frontend. All responses use the **API Response Patterns** defined in Shared Definitions.

---

#### POST `/api/projects/<project_id>/save`

Save project data from the editor.

**Request Body:** Uses **Project Dict Schema** fields (excluding `id`, `created_at`, `modified_at`)

**Response:** `success_response(data={"modified_at": "ISO-8601"})` or `error_response("Project not found", 404)`

---

#### POST `/api/projects/<project_id>/preview`

Generate SVG preview. Can preview unsaved changes by passing operations in body.

**Request Body (optional):** `{"operations": {Operations Schema}}`

**Response:** `{"svg": "<svg>...</svg>"}`

---

#### GET `/api/projects/<project_id>/download`

Download generated G-code file. Uses the project's `project_type` to determine output format (drill or cut).

**Response:** File download with `Content-Disposition: attachment`, filename like `ProjectName_drill.nc` or `ProjectName_cut.nc`

**Errors:**
- `error_response("Project not found", 404)`
- `error_response("No material selected", 400)`
- `error_response("No tool selected", 400)`

---

#### POST `/api/projects/<project_id>/validate`

Validate project configuration before generating G-code.

**Response:** `validation_response(errors)` - returns `{"valid": bool, "errors": [...]}`

---

#### GET `/api/materials/<material_id>/gcode-params`

Get G-code parameters for a material (useful for displaying current settings).

**Response:** `{"id": "material_id", "gcode_standards": {GCode Standards Schema}}`

