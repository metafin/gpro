"""Tests for GCodeService."""
import pytest

from web.services.gcode_service import GCodeService
from web.models import Material, Project


class TestGetGCodeParams:
    """Tests for get_gcode_params method."""

    def test_get_gcode_params_drill(self, app, sample_material):
        """Test getting G-code params for drill."""
        with app.app_context():
            material = Material.query.get(sample_material.id)
            params = GCodeService.get_gcode_params(material, 0.125, 'drill')

            assert params is not None
            assert params['spindle_speed'] == 1000
            assert params['feed_rate'] == 2.0
            assert params['plunge_rate'] == 1.0
            assert params['pecking_depth'] == 0.05
            assert params['material_depth'] == 0.125

    def test_get_gcode_params_end_mill(self, app, sample_material):
        """Test getting G-code params for end mill."""
        with app.app_context():
            material = Material.query.get(sample_material.id)
            params = GCodeService.get_gcode_params(material, 0.125, 'end_mill_1flute')

            assert params is not None
            assert params['spindle_speed'] == 12000
            assert params['feed_rate'] == 12.0
            assert params['pass_depth'] == 0.025

    def test_get_gcode_params_tube_material(self, app, sample_tube_material):
        """Test getting params for tube material uses wall_thickness."""
        with app.app_context():
            material = Material.query.get(sample_tube_material.id)
            params = GCodeService.get_gcode_params(material, 0.125, 'drill')

            assert params['material_depth'] == 0.125  # wall_thickness

    def test_get_gcode_params_not_found(self, app, sample_material):
        """Test getting params for non-existent tool size."""
        with app.app_context():
            material = Material.query.get(sample_material.id)
            params = GCodeService.get_gcode_params(material, 0.5, 'drill')  # 0.5 not defined
            assert params is None

    def test_get_gcode_params_no_material(self, app):
        """Test getting params with None material."""
        with app.app_context():
            params = GCodeService.get_gcode_params(None, 0.125, 'drill')
            assert params is None


class TestExpandOperations:
    """Tests for expand_operations method."""

    def test_expand_single_drill_holes(self, app):
        """Test expanding single drill holes."""
        with app.app_context():
            operations = {
                'drill_holes': [
                    {'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 2.0},
                    {'id': 'h2', 'type': 'single', 'x': 3.0, 'y': 4.0}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            drill_points, circles, hexes, lines = GCodeService.expand_operations(operations)

            assert len(drill_points) == 2
            # drill_points are now tuples (x, y)
            assert drill_points[0] == (1.0, 2.0)
            assert drill_points[1] == (3.0, 4.0)

    def test_expand_linear_pattern_x_axis(self, app):
        """Test expanding linear pattern along X axis."""
        with app.app_context():
            operations = {
                'drill_holes': [
                    {'id': 'p1', 'type': 'pattern_linear', 'start_x': 1.0, 'start_y': 2.0,
                     'axis': 'x', 'spacing': 0.5, 'count': 3}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            drill_points, _, _, _ = GCodeService.expand_operations(operations)

            assert len(drill_points) == 3
            # drill_points are now tuples (x, y)
            assert drill_points[0] == (1.0, 2.0)
            assert drill_points[1] == (1.5, 2.0)
            assert drill_points[2] == (2.0, 2.0)

    def test_expand_linear_pattern_y_axis(self, app):
        """Test expanding linear pattern along Y axis."""
        with app.app_context():
            operations = {
                'drill_holes': [
                    {'id': 'p1', 'type': 'pattern_linear', 'start_x': 1.0, 'start_y': 2.0,
                     'axis': 'y', 'spacing': 0.5, 'count': 3}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            drill_points, _, _, _ = GCodeService.expand_operations(operations)

            assert len(drill_points) == 3
            # drill_points are now tuples (x, y)
            assert drill_points[0] == (1.0, 2.0)
            assert drill_points[1] == (1.0, 2.5)
            assert drill_points[2] == (1.0, 3.0)

    def test_expand_grid_pattern(self, app):
        """Test expanding grid pattern."""
        with app.app_context():
            operations = {
                'drill_holes': [
                    {'id': 'g1', 'type': 'pattern_grid', 'start_x': 1.0, 'start_y': 1.0,
                     'x_spacing': 1.0, 'y_spacing': 1.0, 'x_count': 2, 'y_count': 2}
                ],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            drill_points, _, _, _ = GCodeService.expand_operations(operations)

            assert len(drill_points) == 4
            # Grid should be: (1,1), (2,1), (1,2), (2,2) as tuples
            expected = [
                (1.0, 1.0),
                (2.0, 1.0),
                (1.0, 2.0),
                (2.0, 2.0)
            ]
            assert drill_points == expected

    def test_expand_circular_cuts(self, app):
        """Test expanding circular cuts."""
        with app.app_context():
            operations = {
                'drill_holes': [],
                'circular_cuts': [
                    {'id': 'c1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}
                ],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            _, circles, _, _ = GCodeService.expand_operations(operations)

            assert len(circles) == 1
            assert circles[0]['center_x'] == 5.0
            assert circles[0]['center_y'] == 5.0
            assert circles[0]['diameter'] == 1.0

    def test_expand_circular_linear_pattern(self, app):
        """Test expanding circular cuts with linear pattern."""
        with app.app_context():
            operations = {
                'drill_holes': [],
                'circular_cuts': [
                    {'id': 'cp1', 'type': 'pattern_linear', 'start_center_x': 2.0, 'start_center_y': 5.0,
                     'diameter': 0.5, 'axis': 'x', 'spacing': 2.0, 'count': 3}
                ],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            _, circles, _, _ = GCodeService.expand_operations(operations)

            assert len(circles) == 3
            assert circles[0]['center_x'] == 2.0
            assert circles[1]['center_x'] == 4.0
            assert circles[2]['center_x'] == 6.0
            assert all(c['diameter'] == 0.5 for c in circles)

    def test_expand_hexagonal_cuts(self, app):
        """Test expanding hexagonal cuts."""
        with app.app_context():
            operations = {
                'drill_holes': [],
                'circular_cuts': [],
                'hexagonal_cuts': [
                    {'id': 'h1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'flat_to_flat': 0.5}
                ],
                'line_cuts': []
            }

            _, _, hexes, _ = GCodeService.expand_operations(operations)

            assert len(hexes) == 1
            assert hexes[0]['center_x'] == 5.0
            assert hexes[0]['flat_to_flat'] == 0.5

    def test_expand_line_cuts_passthrough(self, app):
        """Test that line cuts are passed through without expansion."""
        with app.app_context():
            operations = {
                'drill_holes': [],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': [
                    {'id': 'l1', 'points': [
                        {'x': 0, 'y': 0, 'line_type': 'start'},
                        {'x': 1, 'y': 0, 'line_type': 'straight'},
                        {'x': 1, 'y': 1, 'line_type': 'straight'},
                        {'x': 0, 'y': 0, 'line_type': 'straight'}
                    ]}
                ]
            }

            _, _, _, lines = GCodeService.expand_operations(operations)

            assert len(lines) == 1
            assert len(lines[0]['points']) == 4

    def test_expand_empty_operations(self, app):
        """Test expanding empty operations."""
        with app.app_context():
            operations = {
                'drill_holes': [],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }

            drill_points, circles, hexes, lines = GCodeService.expand_operations(operations)

            assert drill_points == []
            assert circles == []
            assert hexes == []
            assert lines == []


class TestValidate:
    """Tests for validate method."""

    def test_validate_valid_drill_project(self, app, sample_project, machine_settings):
        """Test validation of a valid drill project."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            errors = GCodeService.validate(project)
            assert errors == []

    def test_validate_missing_material(self, app, machine_settings):
        """Test validation catches missing material."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No Material Project',
                project_type='drill',
                operations={'drill_holes': [{'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 1.0}],
                           'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            errors = GCodeService.validate(project)
            assert 'No material selected' in errors

    def test_validate_missing_drill_tool(self, app, sample_material, machine_settings):
        """Test validation catches missing drill tool for drill project."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No Tool Project',
                project_type='drill',
                material_id=sample_material.id,
                operations={'drill_holes': [{'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 1.0}],
                           'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            errors = GCodeService.validate(project)
            assert 'No drill tool selected' in errors

    def test_validate_missing_end_mill_tool(self, app, sample_material, machine_settings):
        """Test validation catches missing end mill for cut project."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No End Mill Project',
                project_type='cut',
                material_id=sample_material.id,
                operations={'drill_holes': [], 'circular_cuts': [
                    {'id': 'c1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}
                ], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            errors = GCodeService.validate(project)
            assert 'No end mill tool selected' in errors

    def test_validate_no_operations(self, app, sample_material, sample_tool, machine_settings):
        """Test validation catches empty operations."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='Empty Project',
                project_type='drill',
                material_id=sample_material.id,
                drill_tool_id=sample_tool.id,
                operations={'drill_holes': [], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            errors = GCodeService.validate(project)
            assert 'Project has no operations' in errors

    def test_validate_out_of_bounds_drill(self, app, sample_material, sample_tool, machine_settings):
        """Test validation catches out-of-bounds drill points."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='Out of Bounds Project',
                project_type='drill',
                material_id=sample_material.id,
                drill_tool_id=sample_tool.id,
                operations={'drill_holes': [
                    {'id': 'h1', 'type': 'single', 'x': 20.0, 'y': 5.0}  # x > max_x (15)
                ], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            errors = GCodeService.validate(project)
            assert any('exceeds machine bounds' in e for e in errors)


class TestGeneratePreviewSVG:
    """Tests for generate_preview_svg method."""

    def test_generate_preview_svg_basic(self, app, sample_project, machine_settings):
        """Test generating SVG preview."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            svg = GCodeService.generate_preview_svg(project)

            assert svg is not None
            assert svg.startswith('<svg')
            assert '</svg>' in svg
            # Should contain drill point circles
            assert '<circle' in svg

    def test_generate_preview_svg_with_custom_operations(self, app, sample_project, machine_settings):
        """Test generating SVG preview with custom operations."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            custom_ops = {
                'drill_holes': [{'id': 'custom', 'type': 'single', 'x': 7.5, 'y': 7.5}],
                'circular_cuts': [],
                'hexagonal_cuts': [],
                'line_cuts': []
            }
            svg = GCodeService.generate_preview_svg(project, operations=custom_ops)

            assert svg is not None
            assert '<circle' in svg

    def test_generate_preview_svg_with_cuts(self, app, sample_cut_project, machine_settings):
        """Test generating SVG preview with circular cuts."""
        with app.app_context():
            project = Project.query.get(sample_cut_project.id)
            svg = GCodeService.generate_preview_svg(project)

            assert svg is not None
            # Should contain circle for the circular cut
            assert '<circle' in svg


class TestGenerate:
    """Tests for generate method (G-code generation)."""

    def test_generate_drill_gcode(self, app, sample_project, machine_settings, general_settings):
        """Test generating drill G-code."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            result = GCodeService.generate(project)

            assert result is not None
            assert result.main_gcode is not None
            assert 'G90' in result.main_gcode  # Absolute positioning
            assert 'M03' in result.main_gcode  # Spindle on
            assert 'M05' in result.main_gcode  # Spindle off
            assert result.project_name is not None

    def test_generate_returns_generation_result(self, app, sample_project, machine_settings, general_settings):
        """Test that generate returns a GenerationResult object."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            result = GCodeService.generate(project)

            # Check GenerationResult structure
            assert hasattr(result, 'main_gcode')
            assert hasattr(result, 'subroutines')
            assert hasattr(result, 'project_name')
            assert hasattr(result, 'warnings')
            assert isinstance(result.subroutines, dict)
            assert isinstance(result.warnings, list)

    def test_generate_raises_on_missing_material(self, app, machine_settings, general_settings):
        """Test generate raises error for missing material."""
        with app.app_context():
            from web.extensions import db
            project = Project(
                name='No Material',
                project_type='drill',
                operations={'drill_holes': [{'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 1.0}],
                           'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}
            )
            db.session.add(project)
            db.session.commit()

            with pytest.raises(ValueError) as exc_info:
                GCodeService.generate(project)
            assert 'validation failed' in str(exc_info.value).lower()

    def test_generate_gcode_preview(self, app, sample_project, machine_settings, general_settings):
        """Test get_gcode_preview returns proper dict."""
        with app.app_context():
            project = Project.query.get(sample_project.id)
            preview = GCodeService.get_gcode_preview(project)

            assert 'main_gcode' in preview
            assert 'subroutines' in preview
            assert 'project_name' in preview
            assert 'warnings' in preview
            assert isinstance(preview['subroutines'], dict)
