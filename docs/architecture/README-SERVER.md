# Server Architecture

This document describes the Flask backend architecture of GPRO, covering application structure, routes, services, and API design.

## Overview

GPRO uses Flask with the application factory pattern. The backend handles:

- Session-based authentication (optional)
- Project and settings CRUD operations
- G-code generation orchestration
- RESTful API for AJAX operations

## Technology Stack

- **Flask 3.0+**: Web framework
- **Flask-SQLAlchemy**: ORM
- **Flask-Migrate**: Database migrations (Alembic)
- **Flask-CORS**: Cross-origin support for API
- **Gunicorn**: WSGI server (production)
- **PostgreSQL** (production) / **SQLite** (development)

## File Structure

```
├── app.py              # Application factory
├── config.py           # Configuration management
├── seed_data.py        # Database initialization
├── Procfile            # Heroku process definition
├── runtime.txt         # Python version (3.13.0)
│
└── web/
    ├── __init__.py
    ├── extensions.py   # SQLAlchemy & Migrate instances
    ├── auth.py         # Authentication decorator
    ├── models.py       # SQLAlchemy models
    ├── routes/         # Flask blueprints
    │   ├── main.py     # Home, login, logout
    │   ├── projects.py # Project CRUD pages
    │   ├── settings.py # Settings management
    │   └── api.py      # AJAX API endpoints
    ├── services/       # Business logic
    │   ├── project_service.py
    │   ├── settings_service.py
    │   └── gcode_service.py
    └── utils/
        └── responses.py  # API response helpers
```

## Application Factory (`app.py`)

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints (inside factory to avoid circular imports)
    # URL prefixes are set here, not in the blueprint definitions
    from web.routes.main import main_bp
    from web.routes.projects import projects_bp
    from web.routes.settings import settings_bp
    from web.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app

app = create_app()  # Global instance for gunicorn
```

**Entry Points:**
- `create_app()` for testing and migrations
- `app` global for `gunicorn app:app`

## Configuration (`config.py`)

Environment-based configuration:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask session signing | `'dev-key-change-in-production'` |
| `DATABASE_URL` | Database connection | `'sqlite:///gcode.db'` |
| `APP_PASSWORD` | Optional simple auth | `None` (no auth) |
| `SESSION_TIMEOUT_MINUTES` | Session expiry | `480` (8 hours) |

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Heroku PostgreSQL compatibility
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///gcode.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url

    APP_PASSWORD = os.environ.get('APP_PASSWORD')
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 480))
```

## Extensions (`web/extensions.py`)

Shared extension instances to avoid circular imports:

```python
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
```

## Authentication (`web/auth.py`)

Simple password-based authentication (optional):

```python
def is_authenticated() -> bool:
    """Check if user is authenticated and session not expired."""
    if not current_app.config.get('APP_PASSWORD'):
        return True  # No password configured = open access

    if not session.get('authenticated'):
        return False

    # Check timeout
    last_activity = session.get('last_activity')
    timeout = current_app.config.get('SESSION_TIMEOUT_MINUTES', 480)
    if datetime.utcnow() - last_activity > timedelta(minutes=timeout):
        session.clear()
        return False

    session['last_activity'] = datetime.utcnow()
    return True

def login_required(f):
    """Decorator for protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def authenticate(password: str) -> bool:
    """Attempt authentication."""
    if password == current_app.config.get('APP_PASSWORD'):
        session['authenticated'] = True
        session['last_activity'] = datetime.utcnow()
        return True
    return False

def logout():
    """Clear session."""
    session.clear()
```

## Routes

### Main Routes (`web/routes/main.py`)

```python
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Projects dashboard."""
    projects = ProjectService.get_all()
    return render_template('index.html', projects=projects)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authentication page."""
    if request.method == 'POST':
        if authenticate(request.form.get('password', '')):
            return redirect(url_for('main.index'))
        flash('Invalid password', 'error')
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    auth.logout()
    return redirect(url_for('main.login'))
```

### Project Routes (`web/routes/projects.py`)

```python
projects_bp = Blueprint('projects', __name__)
# Note: url_prefix='/projects' is set in app.py during registration

@projects_bp.route('/new')
@login_required
def new():
    """New project form."""
    materials = SettingsService.get_all_materials()
    tools = SettingsService.get_all_tools()
    return render_template('project/new.html',
                           materials=materials, tools=tools)

@projects_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create project and redirect to editor."""
    data = {
        'name': request.form.get('name'),
        'project_type': request.form.get('project_type'),
        'material_id': request.form.get('material_id'),
        'drill_tool_id': request.form.get('drill_tool_id'),
        'end_mill_tool_id': request.form.get('end_mill_tool_id'),
    }
    project = ProjectService.create(data)
    return redirect(url_for('projects.edit', project_id=project.id))

@projects_bp.route('/<project_id>')
@login_required
def edit(project_id):
    """Project editor page."""
    project = ProjectService.get_as_dict(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('main.index'))

    return render_template('project/edit.html',
                           project=project,
                           materials=SettingsService.get_materials_dict(),
                           tools=SettingsService.get_tools_as_list(),
                           machine=SettingsService.get_machine_settings())

@projects_bp.route('/<project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    """Delete project."""
    if ProjectService.delete(project_id):
        flash('Project deleted', 'success')
    else:
        flash('Project not found', 'error')
    return redirect(url_for('main.index'))

@projects_bp.route('/<project_id>/duplicate', methods=['POST'])
@login_required
def duplicate(project_id):
    """Duplicate project with new name."""
    new_name = request.form.get('name', 'Copy')
    new_project = ProjectService.duplicate(project_id, new_name)
    if new_project:
        return redirect(url_for('projects.edit', project_id=new_project.id))
    flash('Project not found', 'error')
    return redirect(url_for('main.index'))
```

### Settings Routes (`web/routes/settings.py`)

```python
settings_bp = Blueprint('settings', __name__)
# Note: url_prefix='/settings' is set in app.py during registration

# Materials
@settings_bp.route('/materials')
@login_required
def materials():
    return render_template('settings/materials.html',
                           materials=SettingsService.get_all_materials())

@settings_bp.route('/materials/<material_id>/edit')
@login_required
def material_edit(material_id):
    material = SettingsService.get_material(material_id)
    tools = SettingsService.get_all_tools()
    return render_template('settings/material_edit.html',
                           material=material, tools=tools)

# Machine Settings (singleton)
@settings_bp.route('/machine')
@login_required
def machine():
    return render_template('settings/machine.html',
                           settings=SettingsService.get_machine_settings())

@settings_bp.route('/machine/save', methods=['POST'])
@login_required
def machine_save():
    SettingsService.update_machine_settings(request.form)
    flash('Machine settings saved', 'success')
    return redirect(url_for('settings.machine'))

# General Settings (singleton)
@settings_bp.route('/general')
@login_required
def general():
    return render_template('settings/general.html',
                           settings=SettingsService.get_general_settings())

# Tools
@settings_bp.route('/tools')
@login_required
def tools():
    return render_template('settings/tools.html',
                           tools=SettingsService.get_all_tools())
```

### API Routes (`web/routes/api.py`)

All return JSON with consistent structure:

```python
api_bp = Blueprint('api', __name__)
# Note: url_prefix='/api' is set in app.py during registration

@api_bp.route('/projects/<project_id>/save', methods=['POST'])
@login_required
def save_project(project_id):
    """Save project operations."""
    data = request.get_json()
    project = ProjectService.save(project_id, data)
    if project:
        return success_response({'modified_at': project.modified_at.isoformat()})
    return error_response('Project not found', 404)

@api_bp.route('/projects/<project_id>/preview', methods=['POST'])
@login_required
def preview(project_id):
    """Generate SVG preview from operations."""
    project = ProjectService.get(project_id)
    operations = request.get_json().get('operations', {})
    svg = GCodeService.generate_preview_svg(project, operations)
    return success_response({'svg': svg})

@api_bp.route('/projects/<project_id>/download')
@login_required
def download(project_id):
    """Download G-code ZIP file."""
    project = ProjectService.get(project_id)
    if not project:
        return error_response('Project not found', 404)

    zip_bytes, filename = GCodeService.generate_download(project)
    return Response(
        zip_bytes,
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@api_bp.route('/projects/<project_id>/validate', methods=['POST'])
@login_required
def validate(project_id):
    """Validate project, return errors."""
    project = ProjectService.get(project_id)
    errors = GCodeService.validate(project)
    return validation_response(errors)

@api_bp.route('/materials/<material_id>/gcode-params')
@login_required
def gcode_params(material_id):
    """Get G-code parameters for material/tool combination."""
    tool_type = request.args.get('tool_type')
    tool_size = request.args.get('tool_size')
    params = GCodeService.get_gcode_params(material_id, tool_size, tool_type)
    return success_response({'params': params})
```

### API Response Helpers (`web/utils/responses.py`)

```python
def success_response(data: dict, status: int = 200):
    return jsonify({'status': 'ok', 'data': data}), status

def error_response(message: str, status: int = 400):
    return jsonify({'status': 'error', 'message': message}), status

def validation_response(errors: List[str]):
    if errors:
        return jsonify({'status': 'error', 'errors': errors}), 400
    return jsonify({'status': 'ok', 'errors': []}), 200
```

## Services Layer

Services contain business logic, keeping routes thin. All methods are static (no instance state).

### ProjectService (`web/services/project_service.py`)

```python
class ProjectService:
    @staticmethod
    def get_all() -> List[Project]:
        """Get all projects ordered by modified_at desc."""
        return Project.query.order_by(Project.modified_at.desc()).all()

    @staticmethod
    def get(project_id: str) -> Optional[Project]:
        return Project.query.get(project_id)

    @staticmethod
    def get_as_dict(project_id: str) -> Optional[Dict]:
        """Get project as JSON-serializable dict."""
        project = Project.query.get(project_id)
        return project.to_dict() if project else None

    @staticmethod
    def create(data: dict) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            name=data['name'],
            project_type=data['project_type'],
            material_id=data.get('material_id'),
            drill_tool_id=data.get('drill_tool_id'),
            end_mill_tool_id=data.get('end_mill_tool_id'),
            operations={'drill_holes': [], 'circular_cuts': [],
                        'hexagonal_cuts': [], 'line_cuts': []},
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow()
        )
        db.session.add(project)
        db.session.commit()
        return project

    @staticmethod
    def save(project_id: str, data: dict) -> Optional[Project]:
        project = Project.query.get(project_id)
        if not project:
            return None
        if 'operations' in data:
            project.operations = data['operations']
        if 'tube_void_skip' in data:
            project.tube_void_skip = data['tube_void_skip']
        project.modified_at = datetime.utcnow()
        db.session.commit()
        return project

    @staticmethod
    def delete(project_id: str) -> bool:
        project = Project.query.get(project_id)
        if project:
            db.session.delete(project)
            db.session.commit()
            return True
        return False

    @staticmethod
    def duplicate(project_id: str, new_name: str) -> Optional[Project]:
        original = Project.query.get(project_id)
        if not original:
            return None
        new_project = Project(
            id=str(uuid.uuid4()),
            name=new_name,
            project_type=original.project_type,
            material_id=original.material_id,
            drill_tool_id=original.drill_tool_id,
            end_mill_tool_id=original.end_mill_tool_id,
            operations=copy.deepcopy(original.operations),
            tube_void_skip=original.tube_void_skip,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow()
        )
        db.session.add(new_project)
        db.session.commit()
        return new_project
```

### SettingsService (`web/services/settings_service.py`)

Singleton pattern for machine/general settings:

```python
class SettingsService:
    @staticmethod
    def get_machine_settings() -> MachineSettings:
        """Get or create singleton machine settings."""
        settings = MachineSettings.query.get(1)
        if not settings:
            settings = MachineSettings(
                id=1,
                name='OMIO CNC',
                max_x=12.0,
                max_y=8.0,
                units='in',
                controller_type='mach3',
                supports_subroutines=True,
                supports_canned_cycles=True,
                gcode_base_path='C:\\Mach3\\GCode'
            )
            db.session.add(settings)
            db.session.commit()
        return settings

    @staticmethod
    def get_general_settings() -> GeneralSettings:
        """Get or create singleton general settings."""
        settings = GeneralSettings.query.get(1)
        if not settings:
            settings = GeneralSettings(
                id=1,
                safety_height=0.5,
                travel_height=0.2,
                spindle_warmup_seconds=3
            )
            db.session.add(settings)
            db.session.commit()
        return settings
```

### GCodeService (`web/services/gcode_service.py`)

Orchestrates G-code generation, validation, and preview:

```python
class GCodeService:
    @staticmethod
    def get_gcode_params(material: Material, tool_size: float, tool_type: str) -> Optional[Dict]:
        """Get G-code parameters for a material/tool combination."""
        # Returns dict with spindle_speed, feed_rate, plunge_rate, and
        # pecking_depth (drill) or pass_depth (end mills)

    @staticmethod
    def validate(project: Project) -> List[str]:
        """Validate project and return error messages."""
        errors = []
        machine = SettingsService.get_machine_settings()

        # Check required fields (material, tool selection)
        # Check operations exist
        # Validate coordinates within machine bounds
        # Validate line cut compensation (checks if arcs are too small)

        return errors

    @staticmethod
    def generate_preview_svg(project: Project, operations: Optional[Dict] = None,
                             coords_mode: str = 'off') -> str:
        """
        Generate an SVG preview of the project toolpaths.

        Args:
            project: The project to preview
            operations: Optional operations dict (for previewing unsaved changes)
            coords_mode: 'off', 'feature' (show feature coords), or 'toolpath' (show compensated coords)

        Returns:
            SVG markup string
        """
        # Handles tube dimensions, tool compensation preview (dashed lines)
        # Shows sequence numbers on each operation

    @staticmethod
    def generate(project: Project) -> GenerationResult:
        """Generate G-code for a project (in-memory, not saved)."""

    @staticmethod
    def generate_and_save(project: Project) -> Dict:
        """Generate G-code and save to filesystem."""
        # Returns dict with directory, main_file, subroutines, project_name, warnings

    @staticmethod
    def generate_download(project: Project) -> Tuple[bytes, str]:
        """Generate G-code and return ZIP bytes + filename."""
        save_result = GCodeService.generate_and_save(project)
        zip_bytes = package_for_download(save_result['directory'])
        return zip_bytes, f"{save_result['project_name']}.zip"

    @staticmethod
    def get_gcode_preview(project: Project) -> Dict:
        """Generate G-code and return as preview (not saved to filesystem)."""
        # Returns dict with main_gcode, subroutines, project_name, warnings
```

## Database Migrations

Using Flask-Migrate (Alembic wrapper):

```bash
# Create migration
flask db migrate -m "Add new column"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

Migrations stored in `migrations/versions/`.

## Deployment

### Local Development
```bash
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
python seed_data.py
flask run --debug
```

### Heroku
```bash
heroku create app-name
heroku addons:create heroku-postgresql:essential-0
heroku config:set SECRET_KEY=your-secret-key
heroku config:set APP_PASSWORD=your-password
git push heroku main
heroku run flask db upgrade
heroku run python seed_data.py
```

Key files:
- **Procfile**: `web: gunicorn app:app`
- **runtime.txt**: `python-3.13.0`

## Key Design Patterns

1. **Application Factory**: Enables testing with different configs, avoids circular imports.

2. **Blueprint Organization**: Routes grouped by domain (main, projects, settings, api).

3. **Service Layer**: Business logic separated from routes for testability.

4. **Static Service Methods**: No instance state, all methods are class methods.

5. **Singleton Settings**: Machine and General settings auto-create if missing.

6. **Consistent API Responses**: All endpoints return `{status, data/message}` JSON.
