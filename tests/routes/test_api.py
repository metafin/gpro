"""Tests for API routes."""
import pytest
import json
import zipfile
import io

from web.models import Project


class TestProjectSaveAPI:
    """Tests for POST /api/projects/<id>/save endpoint."""

    def test_save_project(self, client, app, sample_project):
        """Test saving a project via API."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(
            f'/api/projects/{project_id}/save',
            data=json.dumps({
                'name': 'API Updated Name',
                'operations': {
                    'drill_holes': [{'id': 'new', 'type': 'single', 'x': 3.0, 'y': 3.0}],
                    'circular_cuts': [],
                    'hexagonal_cuts': [],
                    'line_cuts': []
                }
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'modified_at' in data['data']

    def test_save_project_not_found(self, client):
        """Test saving non-existent project returns 404."""
        response = client.post(
            '/api/projects/nonexistent-id/save',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'

    def test_save_project_no_data(self, client, app, sample_project):
        """Test saving project without JSON data returns error."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(f'/api/projects/{project_id}/save')

        # Flask returns 415 (Unsupported Media Type) when no content-type is set
        # or 400 when content-type is JSON but body is empty
        assert response.status_code in (400, 415)


class TestProjectPreviewAPI:
    """Tests for POST /api/projects/<id>/preview endpoint."""

    def test_preview_project(self, client, app, sample_project, machine_settings):
        """Test generating SVG preview."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(
            f'/api/projects/{project_id}/preview',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'svg' in data['data']
        assert data['data']['svg'].startswith('<svg')

    def test_preview_project_with_custom_operations(self, client, app, sample_project, machine_settings):
        """Test previewing with custom operations."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(
            f'/api/projects/{project_id}/preview',
            data=json.dumps({
                'operations': {
                    'drill_holes': [{'id': 'custom', 'type': 'single', 'x': 7.0, 'y': 7.0}],
                    'circular_cuts': [],
                    'hexagonal_cuts': [],
                    'line_cuts': []
                }
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert '<svg' in data['data']['svg']

    def test_preview_project_not_found(self, client):
        """Test preview of non-existent project returns 404."""
        response = client.post(
            '/api/projects/nonexistent/preview',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 404


class TestProjectDownloadAPI:
    """Tests for GET /api/projects/<id>/download endpoint."""

    def test_download_gcode(self, client, app, sample_project, machine_settings, general_settings):
        """Test downloading G-code as ZIP with main file and subroutines."""
        with app.app_context():
            project_id = sample_project.id

        response = client.get(f'/api/projects/{project_id}/download')

        assert response.status_code == 200
        assert response.content_type == 'application/zip'
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        assert '.zip' in response.headers.get('Content-Disposition', '')

        # Verify ZIP contents
        zip_buffer = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            filenames = zf.namelist()
            # Should have a main.tap file
            assert any('main.tap' in f for f in filenames)
            # Should have a config.txt file
            assert any('config.txt' in f for f in filenames)

            # Read main file and check G-code content
            for filename in filenames:
                if 'main.tap' in filename:
                    gcode = zf.read(filename).decode('utf-8')
                    assert 'G90' in gcode
                elif 'config.txt' in filename:
                    config = zf.read(filename).decode('utf-8')
                    assert 'G-CODE GENERATION CONFIG' in config
                    assert 'RAW OPERATIONS' in config

    def test_download_gcode_no_material(self, client, app, sample_tool):
        """Test download fails without material."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No Material',
                project_type='drill',
                drill_tool_id=sample_tool.id,
                operations={'drill_holes': [], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id

        response = client.get(f'/api/projects/{project_id}/download')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'material' in data['message'].lower()

    def test_download_gcode_no_drill_tool(self, client, app, sample_material):
        """Test download fails without drill tool for drill project."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No Tool',
                project_type='drill',
                material_id=sample_material.id,
                operations={'drill_holes': [], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id

        response = client.get(f'/api/projects/{project_id}/download')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'tool' in data['message'].lower()

    def test_download_gcode_not_found(self, client):
        """Test download of non-existent project returns 404."""
        response = client.get('/api/projects/nonexistent/download')

        assert response.status_code == 404


class TestProjectValidateAPI:
    """Tests for POST /api/projects/<id>/validate endpoint."""

    def test_validate_valid_project(self, client, app, sample_project, machine_settings):
        """Test validating a valid project."""
        with app.app_context():
            project_id = sample_project.id

        response = client.post(f'/api/projects/{project_id}/validate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] is True
        assert data['errors'] == []

    def test_validate_invalid_project(self, client, app, machine_settings):
        """Test validating an invalid project returns errors."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='Invalid Project',
                project_type='drill',
                operations={'drill_holes': [], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id

        response = client.post(f'/api/projects/{project_id}/validate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] is False
        assert len(data['errors']) > 0

    def test_validate_project_not_found(self, client):
        """Test validate of non-existent project returns 404."""
        response = client.post('/api/projects/nonexistent/validate')

        assert response.status_code == 404


class TestMaterialGCodeParamsAPI:
    """Tests for GET /api/materials/<id>/gcode-params endpoint."""

    def test_get_gcode_params(self, client, app, sample_material):
        """Test getting G-code params for a material."""
        with app.app_context():
            material_id = sample_material.id

        response = client.get(f'/api/materials/{material_id}/gcode-params')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['data']['id'] == 'test_aluminum_0125'
        assert 'gcode_standards' in data['data']
        assert 'drill' in data['data']['gcode_standards']

    def test_get_gcode_params_not_found(self, client):
        """Test getting params for non-existent material returns 404."""
        response = client.get('/api/materials/nonexistent/gcode-params')

        assert response.status_code == 404
