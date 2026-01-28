"""Tests for ProjectService."""
import pytest

from web.services.project_service import ProjectService, EMPTY_OPERATIONS
from web.models import Project


class TestProjectCRUD:
    """Tests for project CRUD operations."""

    def test_get_all_empty(self, app):
        """Test getting projects when none exist."""
        with app.app_context():
            projects = ProjectService.get_all()
            assert projects == []

    def test_get_all(self, app, sample_project):
        """Test getting all projects."""
        with app.app_context():
            projects = ProjectService.get_all()
            assert len(projects) == 1
            assert projects[0].name == 'Test Project'

    def test_get_all_ordered_by_modified(self, app, sample_material, sample_tool):
        """Test projects are ordered by modified_at descending."""
        with app.app_context():
            from web.extensions import db
            from datetime import datetime, UTC, timedelta

            # Create first project
            p1 = Project(
                name='Project 1',
                project_type='drill',
                operations=EMPTY_OPERATIONS.copy()
            )
            db.session.add(p1)
            db.session.commit()

            # Create second project (will have later modified_at)
            p2 = Project(
                name='Project 2',
                project_type='drill',
                operations=EMPTY_OPERATIONS.copy()
            )
            db.session.add(p2)
            db.session.commit()

            projects = ProjectService.get_all()
            assert len(projects) == 2
            # Most recently modified should be first
            assert projects[0].name == 'Project 2'

    def test_get_project(self, app, sample_project):
        """Test getting a single project by ID."""
        with app.app_context():
            project_id = sample_project.id
            project = ProjectService.get(project_id)
            assert project is not None
            assert project.name == 'Test Project'
            assert project.project_type == 'drill'

    def test_get_project_not_found(self, app):
        """Test getting a non-existent project."""
        with app.app_context():
            project = ProjectService.get('nonexistent-uuid')
            assert project is None

    def test_get_as_dict(self, app, sample_project):
        """Test getting project as dict for JSON."""
        with app.app_context():
            project_id = sample_project.id
            project_dict = ProjectService.get_as_dict(project_id)

            assert project_dict is not None
            assert project_dict['name'] == 'Test Project'
            assert project_dict['project_type'] == 'drill'
            assert 'operations' in project_dict
            assert 'created_at' in project_dict
            assert 'modified_at' in project_dict
            assert len(project_dict['operations']['drill_holes']) == 2

    def test_get_as_dict_not_found(self, app):
        """Test get_as_dict for non-existent project."""
        with app.app_context():
            result = ProjectService.get_as_dict('nonexistent')
            assert result is None

    def test_create_project(self, app):
        """Test creating a new project."""
        with app.app_context():
            project = ProjectService.create({
                'name': 'New Project',
                'project_type': 'cut'
            })

            assert project.id is not None
            assert project.name == 'New Project'
            assert project.project_type == 'cut'
            assert project.operations == EMPTY_OPERATIONS

    def test_create_project_with_material(self, app, sample_material):
        """Test creating a project with material."""
        with app.app_context():
            project = ProjectService.create({
                'name': 'Project with Material',
                'project_type': 'drill',
                'material_id': sample_material.id
            })

            assert project.material_id == 'test_aluminum_0125'

    def test_save_project(self, app, sample_project):
        """Test saving/updating a project."""
        with app.app_context():
            project_id = sample_project.id
            original_modified = sample_project.modified_at

            updated = ProjectService.save(project_id, {
                'name': 'Updated Project Name',
                'operations': {
                    'drill_holes': [{'id': 'new_hole', 'type': 'single', 'x': 5.0, 'y': 5.0}],
                    'circular_cuts': [],
                    'hexagonal_cuts': [],
                    'line_cuts': []
                }
            })

            assert updated is not None
            assert updated.name == 'Updated Project Name'
            assert len(updated.operations['drill_holes']) == 1
            # modified_at should be updated
            assert updated.modified_at >= original_modified

    def test_save_project_not_found(self, app):
        """Test saving a non-existent project."""
        with app.app_context():
            result = ProjectService.save('nonexistent', {'name': 'Test'})
            assert result is None

    def test_delete_project(self, app, sample_project):
        """Test deleting a project."""
        with app.app_context():
            project_id = sample_project.id
            result = ProjectService.delete(project_id)
            assert result is True

            # Verify deletion
            assert ProjectService.get(project_id) is None

    def test_delete_project_not_found(self, app):
        """Test deleting a non-existent project."""
        with app.app_context():
            result = ProjectService.delete('nonexistent')
            assert result is False

    def test_duplicate_project(self, app, sample_project):
        """Test duplicating a project."""
        with app.app_context():
            project_id = sample_project.id
            duplicate = ProjectService.duplicate(project_id)

            assert duplicate is not None
            assert duplicate.id != project_id
            assert duplicate.name == 'Test Project (Copy)'
            assert duplicate.project_type == sample_project.project_type
            assert duplicate.material_id == sample_project.material_id
            # Operations should be copied
            assert len(duplicate.operations['drill_holes']) == 2

    def test_duplicate_project_with_custom_name(self, app, sample_project):
        """Test duplicating a project with a custom name."""
        with app.app_context():
            project_id = sample_project.id
            duplicate = ProjectService.duplicate(project_id, new_name='Custom Copy Name')

            assert duplicate.name == 'Custom Copy Name'

    def test_duplicate_project_not_found(self, app):
        """Test duplicating a non-existent project."""
        with app.app_context():
            result = ProjectService.duplicate('nonexistent')
            assert result is None

    def test_duplicate_is_deep_copy(self, app, sample_project):
        """Test that duplicated operations are independent."""
        with app.app_context():
            project_id = sample_project.id
            duplicate = ProjectService.duplicate(project_id)

            # Modify the duplicate's operations
            ProjectService.save(duplicate.id, {
                'operations': {
                    'drill_holes': [],
                    'circular_cuts': [],
                    'hexagonal_cuts': [],
                    'line_cuts': []
                }
            })

            # Original should be unchanged
            original = ProjectService.get(project_id)
            assert len(original.operations['drill_holes']) == 2


class TestProjectOperations:
    """Tests for project operations handling."""

    def test_empty_operations_structure(self):
        """Test EMPTY_OPERATIONS has correct structure."""
        assert 'drill_holes' in EMPTY_OPERATIONS
        assert 'circular_cuts' in EMPTY_OPERATIONS
        assert 'hexagonal_cuts' in EMPTY_OPERATIONS
        assert 'line_cuts' in EMPTY_OPERATIONS
        assert all(isinstance(v, list) for v in EMPTY_OPERATIONS.values())

    def test_project_with_pattern_operations(self, app, sample_material):
        """Test project with pattern operations."""
        with app.app_context():
            project = ProjectService.create({
                'name': 'Pattern Project',
                'project_type': 'drill'
            })

            ProjectService.save(project.id, {
                'operations': {
                    'drill_holes': [
                        {'id': 'pattern1', 'type': 'pattern_linear', 'start_x': 1.0, 'start_y': 1.0,
                         'axis': 'x', 'spacing': 0.5, 'count': 5},
                        {'id': 'pattern2', 'type': 'pattern_grid', 'start_x': 5.0, 'start_y': 1.0,
                         'x_spacing': 0.5, 'y_spacing': 0.5, 'x_count': 3, 'y_count': 3}
                    ],
                    'circular_cuts': [],
                    'hexagonal_cuts': [],
                    'line_cuts': []
                }
            })

            updated = ProjectService.get(project.id)
            assert len(updated.operations['drill_holes']) == 2
            assert updated.operations['drill_holes'][0]['type'] == 'pattern_linear'
            assert updated.operations['drill_holes'][1]['type'] == 'pattern_grid'


class TestTubeProjectFields:
    """Tests for tube-specific project fields."""

    def test_get_as_dict_includes_tube_fields(self, app, sample_tube_project):
        """Test that get_as_dict includes working_length and tube_orientation."""
        with app.app_context():
            project_dict = ProjectService.get_as_dict(sample_tube_project.id)

            assert project_dict is not None
            assert project_dict['working_length'] == 24.0
            assert project_dict['tube_orientation'] == 'wide'
            assert project_dict['tube_void_skip'] is True

    def test_save_tube_fields(self, app, sample_tube_project):
        """Test saving working_length and tube_orientation."""
        with app.app_context():
            project_id = sample_tube_project.id

            updated = ProjectService.save(project_id, {
                'working_length': 36.0,
                'tube_orientation': 'narrow'
            })

            assert updated is not None
            assert updated.working_length == 36.0
            assert updated.tube_orientation == 'narrow'

    def test_create_project_with_tube_fields(self, app, sample_tube_material):
        """Test creating a project with tube fields."""
        with app.app_context():
            project = ProjectService.create({
                'name': 'New Tube Project',
                'project_type': 'drill',
                'material_id': sample_tube_material.id,
                'working_length': 18.0,
                'tube_orientation': 'narrow'
            })

            assert project.working_length == 18.0
            assert project.tube_orientation == 'narrow'

    def test_duplicate_copies_tube_fields(self, app, sample_tube_project):
        """Test that duplicate copies working_length and tube_orientation."""
        with app.app_context():
            project_id = sample_tube_project.id
            duplicate = ProjectService.duplicate(project_id)

            assert duplicate is not None
            assert duplicate.working_length == 24.0
            assert duplicate.tube_orientation == 'wide'
            assert duplicate.tube_void_skip is True

    def test_tube_fields_default_to_none(self, app):
        """Test that tube fields default to None for non-tube projects."""
        with app.app_context():
            project = ProjectService.create({
                'name': 'Sheet Project',
                'project_type': 'drill'
            })

            assert project.working_length is None
            assert project.tube_orientation is None
