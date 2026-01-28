# GPRO - G-Code Generator for CNC

A web-based G-code generator for OMIO CNC machines, built for FIRST Robotics teams to create custom metal and plastic parts.

## Features

- **Project-based workflow**: Create, save, and manage machining projects
- **Multiple operation types**: Drill holes, circular cuts, hexagonal cuts, line cuts
- **Pattern support**: Single points, linear patterns, grid patterns
- **Visual preview**: See toolpath before generating G-code
- **Material library**: Pre-configured cutting parameters for common materials
- **M98 subroutines**: Efficient G-code using Mach3 subroutine calls
- **Tube support**: Automatic void detection for hollow stock

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL (production) or SQLite (development)

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd generate-g-code

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade
python seed_data.py

# Run development server
flask run --debug
```

Open http://localhost:5000 in your browser.

### Production (Heroku)

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:essential-0
heroku config:set SECRET_KEY=your-secret-key
heroku config:set APP_PASSWORD=your-password
git push heroku main
heroku run flask db upgrade
heroku run python seed_data.py
```

## Usage

1. **Configure Settings**: Set up your machine limits, tools, and materials
2. **Create a Project**: Choose project type (drill or cut), material, and tool
3. **Add Operations**: Define drill holes, circles, hexagons, or line paths
4. **Preview**: Verify the toolpath visually
5. **Download**: Generate and download G-code as a ZIP file

## Project Types

| Type | Tool | Operations |
|------|------|------------|
| Drill | Drill bit | Drill holes (single, linear pattern, grid pattern) |
| Cut | End mill | Circular cuts, hexagonal cuts, line cuts |

## Documentation

Comprehensive documentation is available in the `docs/` directory:

### Architecture (for developers)

- [G-Code Generation](docs/architecture/README-GCODE.md) - Core algorithms and pipeline
- [Server Architecture](docs/architecture/README-SERVER.md) - Flask backend structure
- [UI Architecture](docs/architecture/README-UI.md) - Frontend templates and JavaScript
- [Data Layer](docs/architecture/README-DATA.md) - Database models and schemas

### Usage (for users)

- [Projects Guide](docs/usage/README-PROJECTS.md) - Creating and managing projects
- [Settings Guide](docs/usage/README-SETTINGS.md) - Configuring materials, tools, and machine

## Tech Stack

- **Backend**: Flask 3.0+, Flask-SQLAlchemy, Flask-Migrate
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Jinja2 templates, Bootstrap 5, vanilla JavaScript
- **Server**: Gunicorn (WSGI)
- **Deployment**: Heroku

## Project Structure

```
├── app.py              # Flask application factory
├── config.py           # Configuration management
├── seed_data.py        # Database initialization
│
├── src/                # Core G-code generation
│   ├── gcode_generator.py
│   ├── pattern_expander.py
│   ├── hexagon_generator.py
│   ├── tube_void_checker.py
│   └── utils/          # Shared utilities
│
├── web/                # Web application layer
│   ├── models.py       # SQLAlchemy models
│   ├── routes/         # Flask blueprints
│   └── services/       # Business logic
│
├── templates/          # Jinja2 templates
├── static/             # CSS, JS, fonts
├── tests/              # Test suite
└── docs/               # Documentation
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/src/test_gcode_generator.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session key | `dev-key-change-in-production` |
| `DATABASE_URL` | Database connection | `sqlite:///gcode.db` |
| `APP_PASSWORD` | Optional login password | None (no auth) |
| `SESSION_TIMEOUT_MINUTES` | Session expiry | 480 (8 hours) |

## Contributing

1. Read the architecture documentation in `docs/architecture/`
2. Follow existing code patterns and conventions
3. Add tests for new functionality
4. Update documentation as needed

## License

Built for FIRST Robotics teams. See LICENSE for details.

---

GPRO is an FPRO Production
