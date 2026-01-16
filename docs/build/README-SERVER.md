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
│   ├── file_parser.py          # Keep existing
│   ├── gcode_generator.py      # Refactor for loops + settings integration
│   ├── pattern_expander.py     # NEW: Expand patterns to coordinates
│   ├── tube_void_checker.py    # NEW: Tube void detection
│   ├── visualizer.py           # Modify for web (return SVG/PNG data)
│   └── models.py               # NEW: Shared dataclasses
│
├── web/                        # Web layer
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py             # Home, dashboard
│   │   ├── projects.py         # Project CRUD
│   │   ├── settings.py         # Settings pages
│   │   └── api.py              # AJAX endpoints
│   ├── models.py               # SQLAlchemy database models
│   └── services/
│       ├── __init__.py
│       ├── settings_service.py # Settings management
│       ├── project_service.py  # Project management
│       └── gcode_service.py    # G-code generation orchestration
│
├── templates/                  # Jinja2 templates
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
psycopg2-binary>=2.9.0
matplotlib>=3.8.0
numpy>=1.26.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```

---

## Flask App Setup (app.py)

Create Flask application with blueprints and database:

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from web.routes.main import main_bp
    from web.routes.projects import projects_bp
    from web.routes.settings import settings_bp
    from web.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Configuration (config.py)

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Database URL - Heroku sets DATABASE_URL automatically
    # For local dev, use SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///gcode.db')

    # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

---

## Database Models (web/models.py)

```python
from app import db
from datetime import datetime
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

    # G-code standards stored as JSON
    gcode_standards = db.Column(db.JSON, nullable=False, default=dict)
    # Format: {"drill": {"0.125": {"spindle_speed": 1000, ...}}, "cut": {...}}


class MachineSettings(db.Model):
    """Machine configuration (singleton - one row)."""
    id = db.Column(db.Integer, primary_key=True, default=1)
    name = db.Column(db.String(100), default='OMIO CNC')
    max_x = db.Column(db.Float, default=15.0)
    max_y = db.Column(db.Float, default=15.0)
    units = db.Column(db.String(10), default='inches')
    controller_type = db.Column(db.String(20), default='mach3')
    supports_loops = db.Column(db.Boolean, default=True)
    supports_canned_cycles = db.Column(db.Boolean, default=True)


class GeneralSettings(db.Model):
    """General G-code settings (singleton - one row)."""
    id = db.Column(db.Integer, primary_key=True, default=1)
    safety_height = db.Column(db.Float, default=0.5)
    travel_height = db.Column(db.Float, default=0.2)
    spindle_warmup_seconds = db.Column(db.Integer, default=2)


class Tool(db.Model):
    """Available tools (drill bits and end mills)."""
    id = db.Column(db.Integer, primary_key=True)
    tool_type = db.Column(db.String(20), nullable=False)  # 'drill' or 'end_mill'
    size = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(100))


class Project(db.Model):
    """User project with operations."""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project_type = db.Column(db.String(20), nullable=False)  # 'drill' or 'cut'
    material_id = db.Column(db.String(50), db.ForeignKey('material.id'))
    material = db.relationship('Material')

    drill_bit_size = db.Column(db.Float)
    end_mill_size = db.Column(db.Float)

    # Operations stored as JSON (flexible structure)
    operations = db.Column(db.JSON, nullable=False, default=dict)
    # Format: {"drill_holes": [...], "circular_cuts": [...], "line_cuts": [...]}

    # Tube void settings
    tube_void_skip = db.Column(db.Boolean, default=False)
```

---

## Operations JSON Structure

The `operations` column in the Project model stores a JSON object with this structure:

```json
{
  "drill_holes": [
    {"id": "d1", "type": "single", "x": 1.25, "y": 0.5},
    {
      "id": "d2",
      "type": "pattern_linear",
      "start_x": 1.25, "start_y": 1.0,
      "axis": "y", "spacing": 0.5, "count": 4
    },
    {
      "id": "d3",
      "type": "pattern_grid",
      "start_x": 3.0, "start_y": 0.5,
      "x_spacing": 1.0, "y_spacing": 0.5,
      "x_count": 3, "y_count": 4
    }
  ],
  "circular_cuts": [
    {"id": "c1", "type": "single", "center_x": 1.25, "center_y": 4.02, "diameter": 0.8},
    {
      "id": "c2",
      "type": "pattern_linear",
      "start_center_x": 0.5, "start_center_y": 1.0,
      "diameter": 0.5, "axis": "x", "spacing": 2.0, "count": 4
    }
  ],
  "line_cuts": [
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
  ]
}
```

**Pattern Types:**
- `single`: One point at (x, y)
- `pattern_linear`: Repeat along an axis (start_x, start_y, axis, spacing, count)
- `pattern_grid`: Rectangular grid (start_x, start_y, x_spacing, y_spacing, x_count, y_count)

**Line Types:**
- `straight`: Linear interpolation to this point
- `arc`: Circular arc to this point using `arc_center_x`, `arc_center_y` as the arc center

---

## Pattern Expander (src/pattern_expander.py)

Create a new module to expand pattern definitions into individual coordinates:

```python
import math
from dataclasses import dataclass
from typing import List

@dataclass
class ExpandedPoint:
    x: float
    y: float
    source_id: str


class PatternExpander:
    @staticmethod
    def expand_linear(start_x, start_y, axis, spacing, count, source_id) -> List[ExpandedPoint]:
        """Expand 'every N inches for M items on axis' pattern."""
        points = []
        for i in range(count):
            x = start_x + (i * spacing if axis == 'x' else 0)
            y = start_y + (i * spacing if axis == 'y' else 0)
            points.append(ExpandedPoint(x, y, source_id))
        return points

    @staticmethod
    def expand_grid(start_x, start_y, x_spacing, y_spacing, x_count, y_count, source_id) -> List[ExpandedPoint]:
        """Expand rectangular grid pattern."""
        points = []
        for row in range(y_count):
            for col in range(x_count):
                points.append(ExpandedPoint(
                    start_x + col * x_spacing,
                    start_y + row * y_spacing,
                    source_id
                ))
        return points

    @staticmethod
    def expand_circular(center_x, center_y, radius, count, start_angle, source_id) -> List[ExpandedPoint]:
        """Expand bolt circle pattern."""
        points = []
        for i in range(count):
            angle = math.radians(start_angle) + (i * 2 * math.pi / count)
            points.append(ExpandedPoint(
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
                source_id
            ))
        return points
```

---

## Tube Void Checker (src/tube_void_checker.py)

For tube stock, detect and skip operations that fall within the hollow center:

```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class TubeProfile:
    """Defines the cross-section of a tube."""
    outer_width: float   # inches
    outer_height: float  # inches
    wall_thickness: float  # inches

    @property
    def void_bounds(self) -> Tuple[float, float, float, float]:
        """Return (x_min, y_min, x_max, y_max) of the hollow void."""
        return (
            self.wall_thickness,
            self.wall_thickness,
            self.outer_width - self.wall_thickness,
            self.outer_height - self.wall_thickness
        )


class TubeVoidChecker:
    """Check if operations fall within the void area of tube stock."""

    def __init__(self, tube: TubeProfile):
        self.tube = tube
        self.void = tube.void_bounds

    def point_in_void(self, x: float, y: float, tool_radius: float = 0) -> bool:
        """Check if a point (with tool radius) is entirely in the void."""
        x_min, y_min, x_max, y_max = self.void
        return (
            x - tool_radius > x_min and
            x + tool_radius < x_max and
            y - tool_radius > y_min and
            y + tool_radius < y_max
        )

    def filter_drill_points(self, points: List, tool_radius: float = 0) -> List:
        """Remove drill points that fall entirely in the void."""
        return [p for p in points if not self.point_in_void(p.x, p.y, tool_radius)]

    def segment_crosses_void(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if a line segment crosses the void (for cut operations)."""
        x_min, y_min, x_max, y_max = self.void
        # Check if both endpoints are in void
        if self.point_in_void(x1, y1) and self.point_in_void(x2, y2):
            return True
        return False

    def get_cut_segments(self, points: List) -> List[List]:
        """
        Split a cutting path into segments that skip the void.
        Returns list of point lists, where each list is a continuous cut.
        """
        segments = []
        current_segment = []

        for i, point in enumerate(points):
            in_void = self.point_in_void(point.x, point.y)

            if not in_void:
                current_segment.append(point)
            else:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []

        if current_segment:
            segments.append(current_segment)

        return segments
```

---

## G-Code Generator Updates (src/gcode_generator.py)

Modify the existing generator to:

1. **Accept settings-based parameters** instead of interactive prompts
2. **Use G-code loops** for multi-pass operations (when controller supports it)
3. **Use G83 peck drilling** for drill operations

Key changes to implement:

```python
import math

class GCodeGenerator:
    def __init__(self, params, settings, use_loops=True):
        self.params = params
        self.settings = settings  # General settings (safety_height, travel_height)
        self.use_loops = use_loops
        self.var_counter = 100

    def _generate_peck_drill(self, points, params):
        """Use G83 canned cycle for drilling (reduces file size)."""
        lines = []
        peck_mm = params.pecking_depth * 25.4
        depth_mm = params.material_depth * 25.4

        first = points[0]
        lines.append(f"G83 X{first.x*25.4:.3f} Y{first.y*25.4:.3f} "
                     f"Z-{depth_mm:.3f} R{self.settings['travel_height']*25.4:.3f} "
                     f"Q{peck_mm:.3f} F{params.plunge_rate}")

        for p in points[1:]:
            lines.append(f"X{p.x*25.4:.3f} Y{p.y*25.4:.3f}")

        lines.append("G80 ; Cancel canned cycle")
        return lines

    def _generate_looped_circular_cut(self, cut, params):
        """Use WHILE loop for multi-pass circular cuts."""
        total_depth_mm = params.material_depth * 25.4
        pass_depth_mm = params.path_depth * 25.4
        num_passes = math.ceil(total_depth_mm / pass_depth_mm)

        v = self.var_counter
        self.var_counter += 5

        lines = [
            f"#{v} = 0 (pass counter)",
            f"#{v+1} = {num_passes} (total passes)",
            f"#{v+2} = {pass_depth_mm:.3f} (depth per pass)",
            f"WHILE [#{v} LT #{v+1}] DO1",
            f"  #{v+3} = [[#{v} + 1] * #{v+2}]",
            f"  G1 Z-#{v+3} F{params.plunge_rate}",
            f"  G2 X... Y... I... J0 F{params.feed_rate}",
            f"  #{v} = [#{v} + 1]",
            f"END1"
        ]
        return lines
```

---

## API Routes (web/routes/api.py)

```python
from flask import Blueprint, request, jsonify, send_file
from web.services.project_service import ProjectService
from web.services.gcode_service import GCodeService
import io

api_bp = Blueprint('api', __name__)


@api_bp.route('/projects/<project_id>/save', methods=['POST'])
def save_project(project_id):
    data = request.get_json()
    ProjectService.save(project_id, data)
    return jsonify({'status': 'saved'})


@api_bp.route('/projects/<project_id>/preview', methods=['POST'])
def preview(project_id):
    project = ProjectService.get(project_id)
    svg_data = GCodeService.generate_preview_svg(project)
    return jsonify({'svg': svg_data})


@api_bp.route('/projects/<project_id>/download/<gcode_type>')
def download_gcode(project_id, gcode_type):
    project = ProjectService.get(project_id)
    gcode = GCodeService.generate(project, gcode_type)  # 'drill' or 'cut'

    buffer = io.BytesIO(gcode.encode('utf-8'))
    return send_file(
        buffer,
        mimetype='text/plain',
        as_attachment=True,
        download_name=f"{project['name']}_{gcode_type}.gcode"
    )


@api_bp.route('/projects/<project_id>/validate', methods=['POST'])
def validate(project_id):
    project = ProjectService.get(project_id)
    errors = GCodeService.validate(project)
    return jsonify({'valid': len(errors) == 0, 'errors': errors})
```

---

## Seed Data Script (seed_data.py)

Create a script to populate initial settings:

```python
from app import create_app, db
from web.models import Material, MachineSettings, GeneralSettings, Tool

app = create_app()

with app.app_context():
    # Add default materials
    if not Material.query.first():
        materials = [
            Material(
                id='aluminum_sheet_0125',
                display_name='Aluminum Sheet 1/8"',
                base_material='aluminum',
                form='sheet',
                thickness=0.125,
                gcode_standards={
                    'drill': {'0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05}},
                    'cut': {'0.125': {'spindle_speed': 10000, 'feed_rate': 10.0, 'plunge_rate': 1.5, 'pass_depth': 0.02}}
                }
            ),
            Material(
                id='aluminum_sheet_025',
                display_name='Aluminum Sheet 1/4"',
                base_material='aluminum',
                form='sheet',
                thickness=0.25,
                gcode_standards={
                    'drill': {'0.125': {'spindle_speed': 800, 'feed_rate': 1.5, 'plunge_rate': 0.8, 'pecking_depth': 0.04}},
                    'cut': {'0.125': {'spindle_speed': 8000, 'feed_rate': 8.0, 'plunge_rate': 1.0, 'pass_depth': 0.015}}
                }
            ),
            Material(
                id='polycarbonate_sheet_025',
                display_name='Polycarbonate Sheet 1/4"',
                base_material='polycarbonate',
                form='sheet',
                thickness=0.25,
                gcode_standards={
                    'drill': {'0.125': {'spindle_speed': 2000, 'feed_rate': 4.0, 'plunge_rate': 2.0, 'pecking_depth': 0.1}},
                    'cut': {'0.125': {'spindle_speed': 15000, 'feed_rate': 20.0, 'plunge_rate': 3.0, 'pass_depth': 0.05}}
                }
            ),
            Material(
                id='aluminum_tube_2x1_0125',
                display_name='Aluminum Tube 2x1 (0.125 wall)',
                base_material='aluminum',
                form='tube',
                outer_width=2.0,
                outer_height=1.0,
                wall_thickness=0.125,
                gcode_standards={
                    'drill': {'0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05}},
                    'cut': {'0.125': {'spindle_speed': 10000, 'feed_rate': 10.0, 'plunge_rate': 1.5, 'pass_depth': 0.02}}
                }
            ),
        ]
        db.session.add_all(materials)

    # Add default machine settings
    if not MachineSettings.query.first():
        db.session.add(MachineSettings(
            name='OMIO CNC',
            max_x=15.0,
            max_y=15.0,
            units='inches',
            controller_type='mach3',
            supports_loops=True,
            supports_canned_cycles=True
        ))

    # Add default general settings
    if not GeneralSettings.query.first():
        db.session.add(GeneralSettings(
            safety_height=0.5,
            travel_height=0.2,
            spindle_warmup_seconds=2
        ))

    # Add default tools
    if not Tool.query.first():
        tools = [
            Tool(tool_type='drill', size=0.125, description='1/8" drill bit'),
            Tool(tool_type='drill', size=0.1875, description='3/16" drill bit'),
            Tool(tool_type='drill', size=0.25, description='1/4" drill bit'),
            Tool(tool_type='end_mill', size=0.125, description='1/8" end mill'),
            Tool(tool_type='end_mill', size=0.1875, description='3/16" end mill'),
            Tool(tool_type='end_mill', size=0.25, description='1/4" end mill'),
        ]
        db.session.add_all(tools)

    db.session.commit()
    print("Seed data added successfully!")
```

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
| `config.py` | Create | Configuration with DATABASE_URL |
| `requirements.txt` | Update | Add Flask, SQLAlchemy, psycopg2 |
| `seed_data.py` | Create | Populate default settings |
| `web/__init__.py` | Create | Web package init |
| `web/models.py` | Create | SQLAlchemy models |
| `web/routes/__init__.py` | Create | Routes package init |
| `web/routes/main.py` | Create | Home/dashboard routes |
| `web/routes/projects.py` | Create | Project CRUD routes |
| `web/routes/settings.py` | Create | Settings routes |
| `web/routes/api.py` | Create | API endpoints |
| `web/services/__init__.py` | Create | Services package init |
| `web/services/settings_service.py` | Create | Settings business logic |
| `web/services/project_service.py` | Create | Project business logic |
| `web/services/gcode_service.py` | Create | G-code generation |
| `src/gcode_generator.py` | Modify | Add loops, settings integration |
| `src/pattern_expander.py` | Create | Pattern expansion |
| `src/tube_void_checker.py` | Create | Tube void detection |
| `src/visualizer.py` | Modify | Return SVG/PNG data |
