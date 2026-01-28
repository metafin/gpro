"""Tests for src/gcode_generator.py module."""
import pytest

from src.gcode_generator import (
    WebGCodeGenerator,
    GenerationSettings,
    ToolParams,
    GenerationResult
)


@pytest.fixture
def generation_settings():
    """Create test generation settings."""
    return GenerationSettings(
        safety_height=0.5,
        travel_height=0.25,
        spindle_warmup_seconds=2,
        supports_subroutines=True,
        supports_canned_cycles=True,
        gcode_base_path="C:\\Mach3\\GCode",
        max_x=15.0,
        max_y=15.0
    )


@pytest.fixture
def drill_params():
    """Create test drill parameters."""
    return ToolParams(
        spindle_speed=1000,
        feed_rate=2.0,
        plunge_rate=1.0,
        pecking_depth=0.05,
        tool_diameter=0.125
    )


@pytest.fixture
def cut_params():
    """Create test cut parameters."""
    return ToolParams(
        spindle_speed=12000,
        feed_rate=12.0,
        plunge_rate=2.0,
        pass_depth=0.025,
        tool_diameter=0.125
    )


class TestGenerationSettings:
    """Tests for GenerationSettings dataclass."""

    def test_settings_creation(self, generation_settings):
        """Test creating generation settings."""
        assert generation_settings.safety_height == 0.5
        assert generation_settings.supports_subroutines is True
        assert generation_settings.gcode_base_path == "C:\\Mach3\\GCode"


class TestToolParams:
    """Tests for ToolParams dataclass."""

    def test_drill_params(self, drill_params):
        """Test drill parameters."""
        assert drill_params.spindle_speed == 1000
        assert drill_params.pecking_depth == 0.05
        assert drill_params.pass_depth is None

    def test_cut_params(self, cut_params):
        """Test cut parameters."""
        assert cut_params.spindle_speed == 12000
        assert cut_params.pass_depth == 0.025
        assert cut_params.pecking_depth is None


class TestWebGCodeGenerator:
    """Tests for WebGCodeGenerator class."""

    def test_generator_initialization(self, generation_settings):
        """Test generator initialization."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="Test Project",
            material_depth=0.125
        )
        assert generator.project_name == "Test_Project"  # Sanitized
        assert generator.material_depth == 0.125
        assert generator.subroutines == {}

    def test_project_name_sanitization(self, generation_settings):
        """Test that project name is sanitized."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="My Test@#$ Project!",
            material_depth=0.125
        )
        assert generator.project_name == "My_Test_Project"


class TestDrillGCodeGeneration:
    """Tests for drill G-code generation."""

    def test_generate_drill_inline(self, generation_settings, drill_params):
        """Test inline drill generation."""
        # Disable subroutines for inline test
        generation_settings.supports_subroutines = False

        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="DrillTest",
            material_depth=0.125
        )

        drill_points = [(1.0, 1.0), (2.0, 2.0)]
        lines = generator.generate_drill_gcode(drill_points, drill_params)

        # Should contain rapid moves to each position
        gcode = '\n'.join(lines)
        assert 'G00' in gcode  # Rapid moves
        assert 'G01' in gcode  # Feed moves (plunge)
        assert 'X1.0000' in gcode
        assert 'X2.0000' in gcode

    def test_generate_drill_with_subroutines(self, generation_settings, drill_params):
        """Test drill generation with subroutines."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="DrillTest",
            material_depth=0.125
        )

        drill_points = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0)]
        operations = [{
            'id': 'p1', 'type': 'pattern_linear',
            'start_x': 1.0, 'start_y': 1.0,
            'axis': 'x', 'spacing': 0.5, 'count': 3
        }]

        lines = generator.generate_drill_gcode(drill_points, drill_params, operations)
        gcode = '\n'.join(lines)

        # Should have M98 subroutine call
        assert 'M98' in gcode
        # Should have generated a subroutine
        assert len(generator.subroutines) > 0

    def test_empty_drill_points(self, generation_settings, drill_params):
        """Test with no drill points."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="DrillTest",
            material_depth=0.125
        )

        lines = generator.generate_drill_gcode([], drill_params)
        assert lines == []


class TestCircularGCodeGeneration:
    """Tests for circular cut G-code generation."""

    def test_generate_circular_inline(self, generation_settings, cut_params):
        """Test inline circular cut generation."""
        generation_settings.supports_subroutines = False

        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="CircleTest",
            material_depth=0.125
        )

        circles = [{'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}]
        lines = generator.generate_circular_gcode(circles, cut_params)
        gcode = '\n'.join(lines)

        # Should contain G02 arc command
        assert 'G02' in gcode
        # Should have I offset (negative cut radius)
        assert 'I' in gcode

    def test_generate_circular_with_subroutines(self, generation_settings, cut_params):
        """Test circular cut with subroutines."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="CircleTest",
            material_depth=0.125
        )

        circles = [
            {'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0},
            {'center_x': 7.0, 'center_y': 5.0, 'diameter': 1.0}
        ]
        lines = generator.generate_circular_gcode(circles, cut_params)
        gcode = '\n'.join(lines)

        # Should have M98 calls
        assert 'M98' in gcode
        # Should have subroutine
        assert len(generator.subroutines) > 0

    def test_empty_circles(self, generation_settings, cut_params):
        """Test with no circles."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="CircleTest",
            material_depth=0.125
        )

        lines = generator.generate_circular_gcode([], cut_params)
        assert lines == []


class TestHexagonalGCodeGeneration:
    """Tests for hexagonal cut G-code generation."""

    def test_generate_hexagonal_inline(self, generation_settings, cut_params):
        """Test inline hexagonal cut generation."""
        generation_settings.supports_subroutines = False

        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="HexTest",
            material_depth=0.125
        )

        hexagons = [{'center_x': 5.0, 'center_y': 5.0, 'flat_to_flat': 0.75}]
        lines = generator.generate_hexagonal_gcode(hexagons, cut_params)
        gcode = '\n'.join(lines)

        # Should contain linear moves (G01) for hexagon sides
        assert 'G01' in gcode

    def test_generate_hexagonal_with_subroutines(self, generation_settings, cut_params):
        """Test hexagonal cut with subroutines."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="HexTest",
            material_depth=0.125
        )

        hexagons = [
            {'center_x': 5.0, 'center_y': 5.0, 'flat_to_flat': 0.75},
            {'center_x': 7.0, 'center_y': 5.0, 'flat_to_flat': 0.75}
        ]
        lines = generator.generate_hexagonal_gcode(hexagons, cut_params)
        gcode = '\n'.join(lines)

        assert 'M98' in gcode
        assert len(generator.subroutines) > 0

    def test_empty_hexagons(self, generation_settings, cut_params):
        """Test with no hexagons."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="HexTest",
            material_depth=0.125
        )

        lines = generator.generate_hexagonal_gcode([], cut_params)
        assert lines == []


class TestLineGCodeGeneration:
    """Tests for line cut G-code generation."""

    def test_generate_line_inline(self, generation_settings, cut_params):
        """Test inline line cut generation."""
        generation_settings.supports_subroutines = False

        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="LineTest",
            material_depth=0.125
        )

        line_cuts = [{
            'points': [
                {'x': 0, 'y': 0, 'line_type': 'start'},
                {'x': 1.0, 'y': 0, 'line_type': 'straight'},
                {'x': 1.0, 'y': 1.0, 'line_type': 'straight'},
                {'x': 0, 'y': 0, 'line_type': 'straight'}
            ]
        }]
        lines = generator.generate_line_gcode(line_cuts, cut_params)
        gcode = '\n'.join(lines)

        assert 'G01' in gcode
        assert 'X1.0000' in gcode
        assert 'Y1.0000' in gcode

    def test_generate_line_with_arc(self, generation_settings, cut_params):
        """Test line cut with arc segment."""
        generation_settings.supports_subroutines = False

        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="LineTest",
            material_depth=0.125
        )

        line_cuts = [{
            'points': [
                {'x': 0, 'y': 0, 'line_type': 'start'},
                {'x': 1.0, 'y': 0, 'line_type': 'straight'},
                {'x': 1.0, 'y': 1.0, 'line_type': 'arc', 'arc_center_x': 1.0, 'arc_center_y': 0.5}
            ]
        }]
        lines = generator.generate_line_gcode(line_cuts, cut_params)
        gcode = '\n'.join(lines)

        # Should have arc command (G02 or G03)
        assert 'G02' in gcode or 'G03' in gcode
        assert 'I' in gcode
        assert 'J' in gcode

    def test_empty_line_cuts(self, generation_settings, cut_params):
        """Test with no line cuts."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="LineTest",
            material_depth=0.125
        )

        lines = generator.generate_line_gcode([], cut_params)
        assert lines == []


class TestFullGeneration:
    """Tests for complete G-code generation."""

    def test_generate_complete(self, generation_settings, drill_params):
        """Test complete G-code generation."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="FullTest",
            material_depth=0.125
        )

        expanded_ops = {
            'drill_points': [(1.0, 1.0), (2.0, 2.0)],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': []
        }
        original_ops = {
            'drill_holes': [
                {'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 1.0},
                {'id': 'h2', 'type': 'single', 'x': 2.0, 'y': 2.0}
            ]
        }

        result = generator.generate(
            expanded_ops=expanded_ops,
            drill_params=drill_params,
            original_operations=original_ops
        )

        assert isinstance(result, GenerationResult)
        assert result.main_gcode is not None
        assert 'G20 G90' in result.main_gcode  # Header
        assert 'M03' in result.main_gcode  # Spindle on
        assert 'M05' in result.main_gcode  # Spindle off
        assert 'M30' in result.main_gcode  # Program end

    def test_generate_result_structure(self, generation_settings, drill_params):
        """Test GenerationResult structure."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="ResultTest",
            material_depth=0.125
        )

        expanded_ops = {
            'drill_points': [(1.0, 1.0)],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': []
        }

        result = generator.generate(
            expanded_ops=expanded_ops,
            drill_params=drill_params
        )

        assert hasattr(result, 'main_gcode')
        assert hasattr(result, 'subroutines')
        assert hasattr(result, 'project_name')
        assert hasattr(result, 'warnings')
        assert isinstance(result.subroutines, dict)
        assert isinstance(result.warnings, list)

    def test_generate_no_comments(self, generation_settings, drill_params):
        """Test that generated G-code has no comments (for Mach3)."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="NoCommentTest",
            material_depth=0.125
        )

        expanded_ops = {
            'drill_points': [(1.0, 1.0)],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': []
        }

        result = generator.generate(
            expanded_ops=expanded_ops,
            drill_params=drill_params
        )

        # Should not have semicolon or parenthesis comments
        # (except in M98 calls which have required parenthesis syntax)
        lines = result.main_gcode.split('\n')
        for line in lines:
            if 'M98' not in line:
                assert ';' not in line
                assert '(' not in line

    def test_generate_with_mixed_operations(self, generation_settings, drill_params, cut_params):
        """Test generation with both drill and cut operations."""
        generator = WebGCodeGenerator(
            settings=generation_settings,
            project_name="MixedTest",
            material_depth=0.125
        )

        expanded_ops = {
            'drill_points': [(1.0, 1.0)],
            'circular_cuts': [{'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}],
            'hexagonal_cuts': [],
            'line_cuts': []
        }

        result = generator.generate(
            expanded_ops=expanded_ops,
            drill_params=drill_params,
            cut_params=cut_params
        )

        assert result.main_gcode is not None
        # Should have drill operations in main code
        assert 'G01' in result.main_gcode  # Feed moves for drilling
        # Circle arc is in subroutine when subroutines are enabled
        assert 'M98' in result.main_gcode  # Subroutine call for circle
        # The G02 arc is in the subroutine
        assert len(result.subroutines) > 0
        subroutine_content = list(result.subroutines.values())[0]
        assert 'G02' in subroutine_content  # Arc in subroutine
