# Data Layer Architecture

This document describes the database models, schemas, and data conventions in GPRO.

## Overview

GPRO uses SQLAlchemy ORM with Flask-Migrate for database management. The data layer includes:

- Five SQLAlchemy models
- JSON fields for flexible nested data
- Singleton pattern for settings
- UUID-based project identification

## Technology

- **ORM**: Flask-SQLAlchemy
- **Migrations**: Flask-Migrate (Alembic)
- **Production DB**: PostgreSQL (Heroku)
- **Development DB**: SQLite

## Model Files

```
web/
├── extensions.py   # SQLAlchemy instance
└── models.py       # All model definitions
```

## Database Models

### Project

User-defined CNC projects containing operations.

```python
class Project(db.Model):
    __tablename__ = 'project'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(200), nullable=False)
    project_type = db.Column(db.String(20), nullable=False)  # 'drill' or 'cut'

    # Relationships
    material_id = db.Column(db.String(50), db.ForeignKey('material.id'))
    material = db.relationship('Material')

    drill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'))
    drill_tool = db.relationship('Tool', foreign_keys=[drill_tool_id])

    end_mill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'))
    end_mill_tool = db.relationship('Tool', foreign_keys=[end_mill_tool_id])

    # Operations stored as JSON
    operations = db.Column(db.JSON, default=dict)

    # Tube settings
    tube_void_skip = db.Column(db.Boolean, default=False)
    working_length = db.Column(db.Float, nullable=True)  # Length of tube segment being machined
    tube_orientation = db.Column(db.String(10), nullable=True)  # 'wide' or 'narrow' - which face is up

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    modified_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
```

**Project Types:**
- `drill`: Uses drill tool, generates drill operations only
- `cut`: Uses end mill, generates circular/hexagonal/line cuts

**Operations JSON Schema:**
```json
{
  "drill_holes": [
    {
      "id": "d1",
      "type": "single",
      "x": 1.0,
      "y": 2.0
    },
    {
      "id": "d2",
      "type": "pattern_linear",
      "x": 0.5,
      "y": 0.5,
      "axis": "x",
      "spacing": 0.5,
      "count": 4
    },
    {
      "id": "d3",
      "type": "pattern_grid",
      "x": 0.0,
      "y": 0.0,
      "x_spacing": 1.0,
      "y_spacing": 0.5,
      "x_count": 3,
      "y_count": 2
    }
  ],
  "circular_cuts": [
    {
      "id": "c1",
      "type": "single",
      "center_x": 2.0,
      "center_y": 3.0,
      "diameter": 0.5,
      "compensation": "interior"
    }
  ],
  "hexagonal_cuts": [
    {
      "id": "h1",
      "type": "single",
      "center_x": 4.0,
      "center_y": 2.0,
      "flat_to_flat": 0.75,
      "compensation": "interior"
    }
  ],
  "line_cuts": [
    {
      "id": "l1",
      "points": [
        {"x": 0, "y": 0, "line_type": "start"},
        {"x": 2, "y": 0, "line_type": "straight"},
        {"x": 2, "y": 1, "line_type": "straight"},
        {"x": 0, "y": 1, "line_type": "straight"},
        {"x": 0, "y": 0, "line_type": "straight"}
      ],
      "compensation": "none"
    }
  ]
}
```

### Material

Material definitions with G-code cutting parameters.

```python
class Material(db.Model):
    __tablename__ = 'material'

    id = db.Column(db.String(50), primary_key=True)  # e.g., 'aluminum_sheet_0125'
    display_name = db.Column(db.String(100), nullable=False)
    base_material = db.Column(db.String(50), nullable=False)  # 'aluminum', 'polycarbonate'
    form = db.Column(db.String(20), nullable=False)  # 'sheet' or 'tube'

    # Sheet dimensions
    thickness = db.Column(db.Float)  # inches (sheets only)

    # Tube dimensions
    outer_width = db.Column(db.Float)   # inches
    outer_height = db.Column(db.Float)  # inches
    wall_thickness = db.Column(db.Float)  # inches

    # G-code standards - nested JSON by tool type and size
    gcode_standards = db.Column(db.JSON, default=dict)
```

**Material Forms:**
- `sheet`: Uses `thickness` for depth
- `tube`: Uses `wall_thickness` for depth, `outer_width`/`outer_height` for bounds

**G-Code Standards JSON Schema:**
```json
{
  "drill": {
    "0.125": {
      "spindle_speed": 1000,
      "feed_rate": 5.0,
      "plunge_rate": 2.0,
      "pecking_depth": 0.05
    },
    "0.1875": {
      "spindle_speed": 900,
      "feed_rate": 4.5,
      "plunge_rate": 1.8,
      "pecking_depth": 0.06
    }
  },
  "end_mill_1flute": {
    "0.125": {
      "spindle_speed": 12000,
      "feed_rate": 20.0,
      "plunge_rate": 5.0,
      "pass_depth": 0.03
    }
  },
  "end_mill_2flute": {
    "0.125": {
      "spindle_speed": 10000,
      "feed_rate": 15.0,
      "plunge_rate": 4.0,
      "pass_depth": 0.025
    }
  }
}
```

**Parameter Units:**
- `spindle_speed`: RPM
- `feed_rate`: inches/minute
- `plunge_rate`: inches/minute (Z-axis)
- `pecking_depth`: inches (drill peck increment)
- `pass_depth`: inches (cutting pass increment)

### Tool

Drill bits and end mills available for projects.

```python
class Tool(db.Model):
    __tablename__ = 'tool'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tool_type = db.Column(db.String(30), nullable=False)
    size = db.Column(db.Float, nullable=False)  # Diameter
    size_unit = db.Column(db.String(5), default='in')  # 'in' or 'mm'
    description = db.Column(db.String(100))  # User-friendly label
```

**Tool Types:**
- `drill`: Standard drill bit
- `end_mill_1flute`: Single-flute end mill (better for plastics)
- `end_mill_2flute`: Two-flute end mill (general purpose)

**Common Sizes (inches):**
- 0.125 (1/8")
- 0.1875 (3/16")
- 0.25 (1/4")
- 0.375 (3/8")
- 0.5 (1/2")

### MachineSettings

Singleton model for CNC machine configuration. Always has `id=1`.

```python
class MachineSettings(db.Model):
    __tablename__ = 'machine_settings'

    id = db.Column(db.Integer, primary_key=True)  # Always 1
    name = db.Column(db.String(100), default='OMIO CNC')

    # Travel limits
    max_x = db.Column(db.Float, default=15.0)  # inches
    max_y = db.Column(db.Float, default=15.0)  # inches

    # Units
    units = db.Column(db.String(10), default='inches')  # 'inches' or 'mm'

    # Controller type
    controller_type = db.Column(db.String(20), default='mach3')
    # Options: 'mach3', 'mach4', 'grbl', 'linuxcnc'

    # Capabilities
    supports_subroutines = db.Column(db.Boolean, default=True)
    supports_canned_cycles = db.Column(db.Boolean, default=True)

    # Output path for G-code files
    gcode_base_path = db.Column(db.String(500), default='C:\\Mach3\\GCode')
```

**Singleton Pattern:**
The service layer auto-creates this row if missing:

```python
@staticmethod
def get_machine_settings():
    settings = MachineSettings.query.get(1)
    if not settings:
        settings = MachineSettings(id=1, ...)
        db.session.add(settings)
        db.session.commit()
    return settings
```

### GeneralSettings

Singleton model for G-code generation defaults. Always has `id=1`.

```python
class GeneralSettings(db.Model):
    __tablename__ = 'general_settings'

    id = db.Column(db.Integer, primary_key=True)  # Always 1

    # Z heights
    safety_height = db.Column(db.Float, default=0.5)   # inches
    travel_height = db.Column(db.Float, default=0.2)   # inches

    # Spindle warmup
    spindle_warmup_seconds = db.Column(db.Integer, default=2)
```

**Height Definitions:**
- `safety_height`: Z position for safe moves (clears all clamps/fixtures)
- `travel_height`: Z position during rapid moves between operations

## Entity Relationships

```
Project ──────┬──────> Material
              │           │
              │           └──> gcode_standards (JSON)
              │
              ├──────> Tool (drill_tool)
              │
              └──────> Tool (end_mill_tool)

MachineSettings (singleton, id=1)

GeneralSettings (singleton, id=1)
```

## JSON Field Conventions

### Operation IDs

Each operation has a unique `id` field for tracking:

```python
def generate_id():
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# Examples: "d_a1b2c3d4", "c_e5f6g7h8"
```

### Pattern Types

Operations support three pattern types:

| Type | Fields |
|------|--------|
| `single` | `x`, `y` |
| `pattern_linear` | `x`, `y`, `axis`, `spacing`, `count` |
| `pattern_grid` | `x`, `y`, `x_spacing`, `y_spacing`, `x_count`, `y_count` |

### Line Cut Points

Line cuts have an array of points with types:

| Type | Description |
|------|-------------|
| `start` | First point (move to, no cut) |
| `straight` | Linear move (G01) |
| `arc` | Arc move (G02/G03), includes `arc_center_x`, `arc_center_y` |

**Arc Point Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `x`, `y` | Yes | Destination coordinates |
| `line_type` | Yes | Must be `"arc"` |
| `arc_center_x`, `arc_center_y` | Yes | Arc center coordinates |
| `arc_direction` | No | Optional `"cw"` or `"ccw"` to override auto-detection |

**Arc Direction Override:**

For semicircles (180° arcs), the automatic direction detection cannot determine which way to curve. Use `arc_direction` to specify explicitly:

```json
{
  "x": 3.0,
  "y": 16.0,
  "line_type": "arc",
  "arc_center_x": 2.0,
  "arc_center_y": 16.0,
  "arc_direction": "ccw"
}
```

- `"cw"`: Clockwise (G02) - for horizontal arcs going left-to-right, curves DOWN
- `"ccw"`: Counter-clockwise (G03) - for horizontal arcs going left-to-right, curves UP
- Omitted: Auto-detect using cross product (defaults to `"cw"` for semicircles)

## Database Migrations

### Creating Migrations

```bash
# After modifying models
flask db migrate -m "Description of change"
```

### Applying Migrations

```bash
# Development
flask db upgrade

# Production (Heroku)
heroku run flask db upgrade
```

### Migration Files

Stored in `migrations/versions/`:

```
migrations/
├── env.py
├── alembic.ini
└── versions/
    ├── abc123_initial.py
    ├── def456_add_tube_void.py
    └── ...
```

## Seed Data (`seed_data.py`)

Initializes database with default data:

```python
def seed_database():
    # Default materials
    materials = [
        Material(
            id='aluminum_sheet_0125',
            display_name='Aluminum Sheet 1/8"',
            base_material='aluminum',
            form='sheet',
            thickness=0.125,
            gcode_standards={...}
        ),
        Material(
            id='aluminum_tube_1x1',
            display_name='Aluminum Tube 1"x1"',
            base_material='aluminum',
            form='tube',
            outer_width=1.0,
            outer_height=1.0,
            wall_thickness=0.0625,
            gcode_standards={...}
        ),
        # ...
    ]

    # Default tools
    tools = [
        Tool(tool_type='drill', size=0.125, description='1/8" Drill'),
        Tool(tool_type='drill', size=0.1875, description='3/16" Drill'),
        Tool(tool_type='end_mill_1flute', size=0.125, description='1/8" 1-Flute'),
        Tool(tool_type='end_mill_2flute', size=0.125, description='1/8" 2-Flute'),
        # ...
    ]

    for material in materials:
        if not Material.query.get(material.id):
            db.session.add(material)

    for tool in tools:
        existing = Tool.query.filter_by(
            tool_type=tool.tool_type,
            size=tool.size
        ).first()
        if not existing:
            db.session.add(tool)

    db.session.commit()
```

Run with:
```bash
python seed_data.py
```

## Data Validation

### Model-Level

Basic constraints via SQLAlchemy:

```python
name = db.Column(db.String(100), nullable=False)
```

### Service-Level

Business logic validation in services:

```python
def validate(project):
    errors = []

    if not project.material:
        errors.append('No material selected')

    if project.project_type == 'drill' and not project.drill_tool:
        errors.append('No drill tool selected')

    # Validate operations within bounds
    for op in project.operations.get('drill_holes', []):
        if op['x'] > machine.max_x:
            errors.append(f"Drill at ({op['x']}, {op['y']}) exceeds X limit")

    return errors
```

## Key Conventions

1. **UUID Project IDs**: Projects use UUID strings for unique identification across environments.

2. **String Material IDs**: Materials use descriptive string IDs like `aluminum_sheet_0125` for readability.

3. **Auto-Increment Tool IDs**: Tools use simple integer IDs since they're managed centrally.

4. **Singleton Settings**: Machine and General settings always use `id=1`, auto-created if missing.

5. **JSON for Flexibility**: Operations and G-code standards use JSON for nested, schema-flexible data.

6. **UTC Timestamps**: All timestamps stored in UTC, converted for display.

7. **Inches as Base Unit**: All dimensions stored in inches; G-code output also uses inches (G20).
