"""Test configuration and fixtures."""
import pytest
from flask import Flask

from app import create_app
from web.extensions import db
from web.models import Material, MachineSettings, GeneralSettings, Tool, Project


class TestConfig:
    """Test configuration."""
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    APP_PASSWORD = None  # Disable auth for tests


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Provide a database session for tests."""
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_material(app):
    """Create a sample material for testing."""
    with app.app_context():
        material = Material(
            id='test_aluminum_0125',
            display_name='Test Aluminum 1/8"',
            base_material='aluminum',
            form='sheet',
            thickness=0.125,
            gcode_standards={
                'drill': {
                    '0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05}
                },
                'end_mill_1flute': {
                    '0.125': {'spindle_speed': 12000, 'feed_rate': 12.0, 'plunge_rate': 2.0, 'pass_depth': 0.025}
                }
            }
        )
        db.session.add(material)
        db.session.commit()
        yield material


@pytest.fixture
def sample_tube_material(app):
    """Create a sample tube material for testing."""
    with app.app_context():
        material = Material(
            id='test_tube_2x1',
            display_name='Test Tube 2x1',
            base_material='aluminum',
            form='tube',
            outer_width=2.0,
            outer_height=1.0,
            wall_thickness=0.125,
            gcode_standards={
                'drill': {
                    '0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05}
                }
            }
        )
        db.session.add(material)
        db.session.commit()
        yield material


@pytest.fixture
def sample_tool(app):
    """Create a sample drill tool for testing."""
    with app.app_context():
        tool = Tool(
            tool_type='drill',
            size=0.125,
            size_unit='in',
            description='1/8" test drill'
        )
        db.session.add(tool)
        db.session.commit()
        yield tool


@pytest.fixture
def sample_end_mill(app):
    """Create a sample end mill tool for testing."""
    with app.app_context():
        tool = Tool(
            tool_type='end_mill_1flute',
            size=0.125,
            size_unit='in',
            description='1/8" test end mill'
        )
        db.session.add(tool)
        db.session.commit()
        yield tool


@pytest.fixture
def sample_project(app, sample_material, sample_tool):
    """Create a sample project for testing."""
    with app.app_context():
        # Refresh to get IDs
        material = Material.query.get(sample_material.id)
        tool = Tool.query.get(sample_tool.id)

        project = Project(
            name='Test Project',
            project_type='drill',
            material_id=material.id,
            drill_tool_id=tool.id,
            operations={
                'drill_holes': [
                    {'id': 'hole1', 'type': 'single', 'x': 1.0, 'y': 1.0},
                    {'id': 'hole2', 'type': 'single', 'x': 2.0, 'y': 2.0}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }
        )
        db.session.add(project)
        db.session.commit()
        yield project


@pytest.fixture
def sample_cut_project(app, sample_material, sample_end_mill):
    """Create a sample cut project for testing."""
    with app.app_context():
        material = Material.query.get(sample_material.id)
        tool = Tool.query.get(sample_end_mill.id)

        project = Project(
            name='Test Cut Project',
            project_type='cut',
            material_id=material.id,
            end_mill_tool_id=tool.id,
            operations={
                'drill_holes': [],
                'circular_cuts': [
                    {'id': 'circle1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}
                ],
                'hexagonal_cuts': [],
                'line_cuts': []
            }
        )
        db.session.add(project)
        db.session.commit()
        yield project


@pytest.fixture
def machine_settings(app):
    """Create machine settings for testing."""
    with app.app_context():
        settings = MachineSettings(
            id=1,
            name='Test CNC',
            max_x=15.0,
            max_y=15.0,
            units='inches',
            controller_type='mach3',
            supports_subroutines=True,
            supports_canned_cycles=True,
            gcode_base_path='C:\\Mach3\\GCode'
        )
        db.session.add(settings)
        db.session.commit()
        yield settings


@pytest.fixture
def general_settings(app):
    """Create general settings for testing."""
    with app.app_context():
        settings = GeneralSettings(
            id=1,
            safety_height=0.5,
            travel_height=0.2,
            spindle_warmup_seconds=2
        )
        db.session.add(settings)
        db.session.commit()
        yield settings


@pytest.fixture
def sample_tube_project(app, sample_tube_material, sample_tool):
    """Create a sample tube project for testing."""
    with app.app_context():
        material = Material.query.get(sample_tube_material.id)
        tool = Tool.query.get(sample_tool.id)

        project = Project(
            name='Test Tube Project',
            project_type='drill',
            material_id=material.id,
            drill_tool_id=tool.id,
            operations={
                'drill_holes': [
                    {'id': 'hole1', 'type': 'single', 'x': 1.0, 'y': 0.5}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            },
            tube_void_skip=True,
            working_length=24.0,
            tube_orientation='wide'
        )
        db.session.add(project)
        db.session.commit()
        yield project
