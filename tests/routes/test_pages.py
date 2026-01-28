"""Tests for page routes (main, projects, settings)."""
import pytest

from web.models import Project, Material, Tool


class TestMainRoutes:
    """Tests for main blueprint routes."""

    def test_index_page(self, client, app):
        """Test home page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Projects' in response.data

    def test_index_shows_projects(self, client, app, sample_project):
        """Test home page shows projects."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Test Project' in response.data

    def test_login_page(self, client):
        """Test login page loads."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'password' in response.data.lower()

    def test_logout(self, client):
        """Test logout redirects to login."""
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


class TestProjectRoutes:
    """Tests for project blueprint routes."""

    def test_new_project_page(self, client):
        """Test new project form loads."""
        response = client.get('/projects/new')
        assert response.status_code == 200
        assert b'New Project' in response.data

    def test_create_project(self, client, app):
        """Test creating a project via form."""
        response = client.post('/projects/create', data={
            'name': 'Form Created Project',
            'project_type': 'drill'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/projects/' in response.headers['Location']

        # Verify project was created
        with app.app_context():
            project = Project.query.filter_by(name='Form Created Project').first()
            assert project is not None
            assert project.project_type == 'drill'

    def test_edit_project_page(self, client, app, sample_project):
        """Test project edit page loads."""
        with app.app_context():
            project_id = sample_project.id

        response = client.get(f'/projects/{project_id}')
        assert response.status_code == 200
        assert b'Test Project' in response.data
        # Check that JSON data is embedded
        assert b'PROJECT_DATA' in response.data
        assert b'MATERIALS' in response.data

    def test_edit_project_not_found(self, client):
        """Test edit page for non-existent project returns 404."""
        response = client.get('/projects/nonexistent-uuid')
        assert response.status_code == 404

    def test_delete_project(self, client, app, sample_project):
        """Test deleting a project."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(f'/projects/{project_id}/delete', follow_redirects=False)
        assert response.status_code == 302

        # Verify deletion
        with app.app_context():
            project = Project.query.get(project_id)
            assert project is None

    def test_duplicate_project(self, client, app, sample_project):
        """Test duplicating a project."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(f'/projects/{project_id}/duplicate', follow_redirects=False)
        assert response.status_code == 302

        # Verify duplicate was created
        with app.app_context():
            projects = Project.query.all()
            assert len(projects) == 2
            duplicate = Project.query.filter(Project.name.like('%Copy%')).first()
            assert duplicate is not None


class TestSettingsRoutes:
    """Tests for settings blueprint routes."""

    def test_materials_page(self, client, app, sample_material):
        """Test materials list page loads."""
        response = client.get('/settings/materials')
        assert response.status_code == 200
        assert b'Materials' in response.data
        assert b'Test Aluminum' in response.data

    def test_create_material(self, client, app):
        """Test creating a material via form."""
        response = client.post('/settings/materials/create', data={
            'id': 'new_test_material',
            'display_name': 'New Test Material',
            'base_material': 'aluminum',
            'form': 'sheet',
            'thickness': '0.25'
        }, follow_redirects=False)

        assert response.status_code == 302

        with app.app_context():
            material = Material.query.get('new_test_material')
            assert material is not None
            assert material.thickness == 0.25

    def test_edit_material_page(self, client, app, sample_material):
        """Test material edit page loads."""
        response = client.get(f'/settings/materials/{sample_material.id}/edit')
        assert response.status_code == 200
        assert b'Test Aluminum' in response.data

    def test_update_material(self, client, app, sample_material):
        """Test updating a material."""
        response = client.post(f'/settings/materials/{sample_material.id}/update', data={
            'display_name': 'Updated Material Name',
            'base_material': 'aluminum',
            'form': 'sheet',
            'thickness': '0.5'
        }, follow_redirects=False)

        assert response.status_code == 302

        with app.app_context():
            material = Material.query.get(sample_material.id)
            assert material.display_name == 'Updated Material Name'
            assert material.thickness == 0.5

    def test_delete_material(self, client, app, sample_material):
        """Test deleting a material."""
        response = client.post(f'/settings/materials/{sample_material.id}/delete', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            material = Material.query.get(sample_material.id)
            assert material is None

    def test_machine_settings_page(self, client, app, machine_settings):
        """Test machine settings page loads."""
        response = client.get('/settings/machine')
        assert response.status_code == 200
        assert b'Machine' in response.data
        assert b'Test CNC' in response.data

    def test_save_machine_settings(self, client, app, machine_settings):
        """Test saving machine settings."""
        response = client.post('/settings/machine/save', data={
            'name': 'Updated CNC Name',
            'max_x': '20.0',
            'max_y': '20.0',
            'units': 'inches',
            'controller_type': 'mach3',
            'supports_loops': 'on'
        }, follow_redirects=False)

        assert response.status_code == 302

        with app.app_context():
            from web.services.settings_service import SettingsService
            settings = SettingsService.get_machine_settings()
            assert settings.name == 'Updated CNC Name'
            assert settings.max_x == 20.0

    def test_general_settings_page(self, client, app, general_settings):
        """Test general settings page loads."""
        response = client.get('/settings/general')
        assert response.status_code == 200
        assert b'General' in response.data

    def test_save_general_settings(self, client, app, general_settings):
        """Test saving general settings."""
        response = client.post('/settings/general/save', data={
            'safety_height': '1.0',
            'travel_height': '0.3',
            'spindle_warmup_seconds': '5'
        }, follow_redirects=False)

        assert response.status_code == 302

        with app.app_context():
            from web.services.settings_service import SettingsService
            settings = SettingsService.get_general_settings()
            assert settings.safety_height == 1.0
            assert settings.spindle_warmup_seconds == 5

    def test_tools_page(self, client, app, sample_tool):
        """Test tools list page loads."""
        response = client.get('/settings/tools')
        assert response.status_code == 200
        assert b'Tools' in response.data
        assert b'drill' in response.data.lower()

    def test_create_tool(self, client, app):
        """Test creating a tool via form."""
        response = client.post('/settings/tools/create', data={
            'tool_type': 'end_mill_2flute',
            'size': '0.25',
            'size_unit': 'in',
            'description': 'Test end mill'
        }, follow_redirects=False)

        assert response.status_code == 302

        with app.app_context():
            tool = Tool.query.filter_by(tool_type='end_mill_2flute', size=0.25).first()
            assert tool is not None

    def test_delete_tool(self, client, app, sample_tool):
        """Test deleting a tool."""
        with app.app_context():
            tool_id = sample_tool.id

        response = client.post(f'/settings/tools/{tool_id}/delete', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            tool = Tool.query.get(tool_id)
            assert tool is None


class TestAuthenticationRequired:
    """Tests for authentication when APP_PASSWORD is set."""

    def test_protected_routes_with_password(self, app):
        """Test that routes require auth when password is configured."""
        # Create app with password
        app.config['APP_PASSWORD'] = 'test-password'

        with app.test_client() as client:
            # Index should redirect to login
            response = client.get('/', follow_redirects=False)
            assert response.status_code == 302
            assert '/login' in response.headers['Location']

    def test_login_with_correct_password(self, app):
        """Test login with correct password."""
        app.config['APP_PASSWORD'] = 'test-password'

        with app.test_client() as client:
            response = client.post('/login', data={
                'password': 'test-password'
            }, follow_redirects=False)
            assert response.status_code == 302
            assert '/login' not in response.headers['Location']

    def test_login_with_wrong_password(self, app):
        """Test login with incorrect password stays on login page."""
        app.config['APP_PASSWORD'] = 'test-password'

        with app.test_client() as client:
            response = client.post('/login', data={
                'password': 'wrong-password'
            })
            assert response.status_code == 200
            assert b'password' in response.data.lower()
