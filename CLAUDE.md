# CLAUDE.md

Instructions for Claude Code sessions working on this repository.

## IMPORTANT: Read Documentation First

**Before making ANY code changes, read the relevant documentation.**

This project has comprehensive documentation. Reading it first will save time and prevent mistakes.

### Documentation Library

**Architecture (how the code works):**
- `docs/architecture/README-GCODE.md` - G-code generation pipeline, algorithms, utilities
- `docs/architecture/README-GCODE-SAFETY.md` - Safety features (helical lead-in, corner slowdown, validation)
- `docs/architecture/README-SERVER.md` - Flask routes, services, API design
- `docs/architecture/README-UI.md` - Templates, JavaScript, styling
- `docs/architecture/README-DATA.md` - Database models, schemas, relationships

**Usage (how features work):**
- `docs/usage/README-PROJECTS.md` - Project workflow, operations, validation
- `docs/usage/README-SETTINGS.md` - Materials, tools, machine configuration

### Which Docs to Read

| Task | Read First |
|------|------------|
| G-code generation bug | `docs/architecture/README-GCODE.md` |
| Safety/lead-in/feed issue | `docs/architecture/README-GCODE-SAFETY.md` |
| API or route issue | `docs/architecture/README-SERVER.md` |
| Frontend/template issue | `docs/architecture/README-UI.md` |
| Database/model change | `docs/architecture/README-DATA.md` |
| New operation type | All architecture docs |
| Settings feature | `docs/architecture/README-DATA.md`, `docs/usage/README-SETTINGS.md` |

## IMPORTANT: Stay DRY

**Don't Repeat Yourself.** This codebase follows DRY principles strictly.

### Before Writing New Code

1. **Check for existing utilities** in `src/utils/`:
   - `units.py` - Unit conversion
   - `multipass.py` - Multi-pass depth calculations
   - `tool_compensation.py` - Tool radius offsets
   - `arc_utils.py` - Arc direction and I/J calculations
   - `gcode_format.py` - G-code command formatting
   - `subroutine_generator.py` - M98 subroutine generation
   - `validators.py` - Coordinate and stepdown validation
   - `file_manager.py` - File output handling
   - `lead_in.py` - Lead-in strategies (helical, ramp)
   - `corner_detection.py` - Corner analysis and feed reduction

2. **Check for existing patterns** in services:
   - `web/services/project_service.py` - Project CRUD
   - `web/services/settings_service.py` - Settings management
   - `web/services/gcode_service.py` - G-code orchestration

3. **Check for existing UI components** in templates:
   - `templates/partials/coord_input.html` - Coordinate input fields
   - `templates/partials/pattern_fields.html` - Pattern type selection
   - `templates/partials/modal_footer.html` - Modal buttons

4. **Check for existing JS utilities** in static:
   - `static/js/api.js` - API communication
   - `static/js/validation.js` - Input validation

### Creating Reusable Code

When adding new functionality:

1. **Extract shared logic** to utility modules
2. **Create template partials** for repeated HTML
3. **Add to existing utilities** rather than creating new files
4. **Follow existing patterns** for consistency

## Project Overview

GPRO is a Flask web application that generates G-code for OMIO CNC machines. Built for FIRST Robotics teams.

### Core Components

```
src/                    # G-code generation core
├── gcode_generator.py  # Main orchestrator
├── pattern_expander.py # Pattern → coordinates
├── hexagon_generator.py # Hexagon geometry
├── tube_void_checker.py # Tube void detection
└── utils/              # Shared utilities

web/                    # Flask application
├── models.py           # SQLAlchemy models
├── routes/             # Blueprints (main, projects, settings, api)
└── services/           # Business logic layer
```

### Key Patterns

1. **Application Factory** (`app.py`): Flask app created via `create_app()`
2. **Service Layer**: All business logic in `web/services/`, routes are thin
3. **Static Service Methods**: No instance state, all methods are `@staticmethod`
4. **Singleton Settings**: Machine/General settings auto-create with `id=1`
5. **JSON Operations**: Project operations stored as JSON for flexibility

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
flask run --debug

# Run tests
pytest

# Run tests with coverage
pytest --cov

# Database migrations
flask db migrate -m "Description"
flask db upgrade
```

## Common Tasks

### Adding a New Utility Function

1. Find the appropriate file in `src/utils/`
2. Add the function following existing patterns
3. Import and use in calling code
4. Add tests in `tests/src/`

### Adding a New API Endpoint

1. Read `docs/architecture/README-SERVER.md`
2. Add route to appropriate blueprint in `web/routes/`
3. Add business logic to appropriate service in `web/services/`
4. Use response helpers from `web/utils/responses.py`
5. Add tests in `tests/routes/`

### Adding a New Template

1. Read `docs/architecture/README-UI.md`
2. Extend `base.html`
3. Use existing partials where possible
4. Follow Bootstrap 5 patterns
5. Pass data via template variables, not inline JSON

### Modifying G-Code Output

1. Read `docs/architecture/README-GCODE.md` thoroughly
2. Understand the generation pipeline
3. Use existing formatting utilities in `src/utils/gcode_format.py`
4. **Remember: No comments in G-code** (breaks Mach3 M98 parsing)
5. Add tests in `tests/src/`

## Critical Conventions

### Units
- **UI and storage**: Inches
- **G-code output**: Inches (G20)
- Tool sizes stored with unit field for flexibility

### Hexagons
- **Orientation**: Point-up (vertices at top/bottom)
- **Measurement**: Flat-to-flat distance

### Arcs
- **Direction**: Calculated automatically via cross product
- **G02**: Clockwise, **G03**: Counterclockwise

### M98 Subroutines (Mach3)
- Full absolute paths required
- Numeric filenames (1000.nc, 1100.nc, etc.)
- **No comments in G-code files**

## Testing

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/src/test_gcode_generator.py
pytest tests/services/test_project_service.py
pytest tests/routes/test_api.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov --cov-report=html
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Check `__init__.py` files, verify virtual environment |
| Database errors | Run `flask db upgrade` |
| Missing data | Run `python seed_data.py` |
| Template not found | Check template path in route |
| API returning 404 | Check blueprint registration in `app.py` |

### Debugging Tips

1. Check Flask debug output in terminal
2. Use browser dev tools for frontend issues
3. Add `print()` statements (remove before commit)
4. Check test output for expected behavior
