"""Tests for src/utils modules."""
import pytest
import math

from src.utils.units import inches_to_mm, mm_to_inches
from src.utils.multipass import calculate_num_passes, calculate_pass_depths
from src.hexagon_generator import calculate_hexagon_vertices
from src.utils.tool_compensation import (
    get_compensation_offset,
    calculate_cut_radius,
    offset_point_inward,
    calculate_hexagon_compensated_vertices,
    calculate_line_normal,
    offset_line_segment,
    calculate_line_intersection,
    calculate_path_winding,
    compensate_line_path
)
from src.utils.arc_utils import calculate_arc_direction, calculate_ij_offsets
from src.utils.gcode_format import (
    format_coordinate,
    generate_header,
    generate_footer,
    generate_rapid_move,
    generate_linear_move,
    generate_arc_move,
    generate_subroutine_call,
    generate_subroutine_end,
    sanitize_project_name
)
from src.utils.subroutine_generator import (
    get_next_subroutine_number,
    generate_subroutine_file,
    build_subroutine_path,
    SUBROUTINE_RANGES,
    generate_circle_pass_subroutine,
    generate_hexagon_pass_subroutine,
    generate_line_path_subroutine
)
from src.utils.lead_in import (
    calculate_circle_lead_in_point,
    calculate_hexagon_lead_in_point,
    calculate_line_lead_in_point,
    is_closed_path,
    calculate_helix_radius_for_circle,
    calculate_helix_radius_for_hexagon,
    calculate_helix_start_point,
    calculate_helix_revolutions,
    generate_helical_entry,
    MIN_HELIX_RADIUS
)
from src.utils.corner_detection import (
    calculate_segment_angle,
    get_arc_tangent_at_point,
    calculate_direction_vector,
    angle_between_vectors,
    identify_corners,
    calculate_corner_feed_factor,
    generate_corner_slowdown_points,
    get_corner_adjusted_feed
)
from src.utils.validators import (
    validate_bounds,
    validate_all_points,
    validate_tool_in_standards,
    validate_circle_bounds,
    validate_hexagon_bounds,
    validate_arc_geometry,
    validate_stepdown,
    validate_feed_rates
)


class TestUnits:
    """Tests for unit conversion utilities."""

    def test_inches_to_mm(self):
        """Test inches to millimeters conversion."""
        assert inches_to_mm(1.0) == 25.4
        assert inches_to_mm(0.5) == 12.7
        assert inches_to_mm(0) == 0

    def test_mm_to_inches(self):
        """Test millimeters to inches conversion."""
        assert mm_to_inches(25.4) == 1.0
        assert mm_to_inches(12.7) == 0.5
        assert mm_to_inches(0) == 0

    def test_round_trip_conversion(self):
        """Test that conversion round-trips correctly."""
        original = 3.14159
        converted = mm_to_inches(inches_to_mm(original))
        assert abs(converted - original) < 1e-10


class TestMultipass:
    """Tests for multi-pass calculation utilities."""

    def test_calculate_num_passes_exact(self):
        """Test when depth divides evenly."""
        assert calculate_num_passes(0.1, 0.05) == 2
        assert calculate_num_passes(0.125, 0.025) == 5

    def test_calculate_num_passes_ceil(self):
        """Test ceiling behavior for uneven division."""
        assert calculate_num_passes(0.1, 0.03) == 4  # ceil(0.1/0.03) = 4
        assert calculate_num_passes(0.125, 0.04) == 4  # ceil(0.125/0.04) = 4

    def test_calculate_num_passes_minimum_one(self):
        """Test that at least one pass is returned."""
        assert calculate_num_passes(0.01, 0.1) == 1
        assert calculate_num_passes(0, 0.1) == 1

    def test_calculate_num_passes_zero_pass_depth(self):
        """Test handling of zero pass depth."""
        assert calculate_num_passes(0.1, 0) == 1

    def test_calculate_pass_depths(self):
        """Test cumulative depth calculation."""
        depths = calculate_pass_depths(0.1, 0.05)
        assert len(depths) == 2
        assert abs(depths[0] - 0.05) < 1e-10
        assert abs(depths[1] - 0.1) < 1e-10

    def test_calculate_pass_depths_uneven(self):
        """Test evenly distributed depths when not exact multiple."""
        depths = calculate_pass_depths(0.125, 0.04)
        assert len(depths) == 4  # ceil(0.125/0.04) = 4
        # Each pass should be 0.03125
        assert abs(depths[-1] - 0.125) < 1e-10  # Last depth is total


class TestToolCompensation:
    """Tests for tool compensation utilities."""

    def test_calculate_cut_radius(self):
        """Test cut radius calculation."""
        # 1" hole with 0.125" tool = 0.4375" cut radius
        assert calculate_cut_radius(1.0, 0.125) == 0.4375
        # 0.5" hole with 0.125" tool = 0.1875" cut radius
        assert calculate_cut_radius(0.5, 0.125) == 0.1875

    def test_calculate_cut_radius_zero_tool(self):
        """Test with zero tool diameter."""
        assert calculate_cut_radius(1.0, 0) == 0.5

    def test_get_compensation_offset_none(self):
        """Test compensation offset for 'none' - should be zero."""
        assert get_compensation_offset(0.25, 'none') == 0.0
        assert get_compensation_offset(0.125, 'none') == 0.0

    def test_get_compensation_offset_interior(self):
        """Test compensation offset for 'interior' - should be negative tool radius."""
        assert get_compensation_offset(0.25, 'interior') == -0.125
        assert get_compensation_offset(0.5, 'interior') == -0.25

    def test_get_compensation_offset_exterior(self):
        """Test compensation offset for 'exterior' - should be positive tool radius."""
        assert get_compensation_offset(0.25, 'exterior') == 0.125
        assert get_compensation_offset(0.5, 'exterior') == 0.25

    def test_calculate_cut_radius_with_compensation_none(self):
        """Test cut radius with 'none' compensation - tool center follows path."""
        # 1" diameter, 0.25" tool, none = tool center follows 1" diameter
        result = calculate_cut_radius(1.0, 0.25, 'none')
        assert result == 0.5  # Just the feature radius

    def test_calculate_cut_radius_with_compensation_interior(self):
        """Test cut radius with 'interior' compensation - shrink by tool radius."""
        # 1" diameter, 0.25" tool, interior = 0.5 - 0.125 = 0.375
        result = calculate_cut_radius(1.0, 0.25, 'interior')
        assert result == 0.375

    def test_calculate_cut_radius_with_compensation_exterior(self):
        """Test cut radius with 'exterior' compensation - expand by tool radius."""
        # 1" diameter, 0.25" tool, exterior = 0.5 + 0.125 = 0.625
        result = calculate_cut_radius(1.0, 0.25, 'exterior')
        assert result == 0.625

    def test_calculate_cut_radius_default_is_interior(self):
        """Test that default compensation is 'interior' for backward compatibility."""
        # Default should match explicit 'interior'
        default_result = calculate_cut_radius(1.0, 0.25)
        interior_result = calculate_cut_radius(1.0, 0.25, 'interior')
        assert default_result == interior_result

    def test_calculate_hexagon_compensated_vertices_none(self):
        """Test hexagon vertices with 'none' compensation - no offset."""
        regular = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        compensated = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125, 'none')

        # Vertices should be identical
        for reg, comp in zip(regular, compensated):
            assert abs(reg[0] - comp[0]) < 1e-10
            assert abs(reg[1] - comp[1]) < 1e-10

    def test_calculate_hexagon_compensated_vertices_interior(self):
        """Test hexagon vertices with 'interior' compensation - shrink toward center."""
        regular = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        compensated = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125, 'interior')

        # Each compensated vertex should be closer to center
        for reg, comp in zip(regular, compensated):
            reg_dist = math.sqrt((reg[0] - 5.0)**2 + (reg[1] - 5.0)**2)
            comp_dist = math.sqrt((comp[0] - 5.0)**2 + (comp[1] - 5.0)**2)
            assert comp_dist < reg_dist

    def test_calculate_hexagon_compensated_vertices_exterior(self):
        """Test hexagon vertices with 'exterior' compensation - expand from center."""
        regular = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        compensated = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125, 'exterior')

        # Each compensated vertex should be farther from center
        for reg, comp in zip(regular, compensated):
            reg_dist = math.sqrt((reg[0] - 5.0)**2 + (reg[1] - 5.0)**2)
            comp_dist = math.sqrt((comp[0] - 5.0)**2 + (comp[1] - 5.0)**2)
            assert comp_dist > reg_dist

    def test_calculate_hexagon_compensated_vertices_default_is_interior(self):
        """Test that default compensation is 'interior' for backward compatibility."""
        default_result = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125)
        interior_result = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125, 'interior')

        for default_v, interior_v in zip(default_result, interior_result):
            assert abs(default_v[0] - interior_v[0]) < 1e-10
            assert abs(default_v[1] - interior_v[1]) < 1e-10

    def test_offset_point_inward(self):
        """Test point offset toward center."""
        # Point at (2, 0) with center at (0, 0), offset by 0.5
        result = offset_point_inward((2, 0), (0, 0), 0.5)
        assert abs(result[0] - 1.5) < 1e-10
        assert abs(result[1] - 0) < 1e-10

    def test_offset_point_inward_diagonal(self):
        """Test diagonal offset."""
        # Point at (1, 1) with center at (0, 0)
        result = offset_point_inward((1, 1), (0, 0), math.sqrt(2))
        # Should move to (0, 0)
        assert abs(result[0]) < 1e-10
        assert abs(result[1]) < 1e-10

    def test_calculate_hexagon_vertices_count(self):
        """Test that hexagon has 6 vertices."""
        vertices = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        assert len(vertices) == 6

    def test_calculate_hexagon_vertices_symmetry(self):
        """Test hexagon vertex symmetry."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)
        # Top and bottom should be on Y axis
        assert abs(vertices[0][0]) < 1e-10  # Top vertex X = 0
        assert abs(vertices[3][0]) < 1e-10  # Bottom vertex X = 0

    def test_calculate_hexagon_compensated_vertices(self):
        """Test that compensated vertices are closer to center."""
        regular = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        compensated = calculate_hexagon_compensated_vertices(5.0, 5.0, 1.0, 0.125)

        # Each compensated vertex should be closer to center
        for reg, comp in zip(regular, compensated):
            reg_dist = math.sqrt((reg[0] - 5.0)**2 + (reg[1] - 5.0)**2)
            comp_dist = math.sqrt((comp[0] - 5.0)**2 + (comp[1] - 5.0)**2)
            assert comp_dist < reg_dist

    def test_calculate_line_normal_horizontal(self):
        """Test normal calculation for horizontal line."""
        # Line from (0, 0) to (1, 0) - normal should point up (0, 1)
        nx, ny = calculate_line_normal((0, 0), (1, 0))
        assert abs(nx - 0.0) < 1e-10
        assert abs(ny - 1.0) < 1e-10

    def test_calculate_line_normal_vertical(self):
        """Test normal calculation for vertical line."""
        # Line from (0, 0) to (0, 1) - normal should point left (-1, 0)
        nx, ny = calculate_line_normal((0, 0), (0, 1))
        assert abs(nx - (-1.0)) < 1e-10
        assert abs(ny - 0.0) < 1e-10

    def test_calculate_line_normal_diagonal(self):
        """Test normal calculation for diagonal line."""
        # Line at 45 degrees
        nx, ny = calculate_line_normal((0, 0), (1, 1))
        # Normal should be perpendicular, unit length
        length = math.sqrt(nx * nx + ny * ny)
        assert abs(length - 1.0) < 1e-10
        # Dot product with direction should be zero
        dot = nx * 1 + ny * 1  # dot with (1, 1) direction
        # Not directly zero because (1,1) is not unit length
        # But nx, ny should be (-1/sqrt(2), 1/sqrt(2))
        expected_nx = -1 / math.sqrt(2)
        expected_ny = 1 / math.sqrt(2)
        assert abs(nx - expected_nx) < 1e-10
        assert abs(ny - expected_ny) < 1e-10

    def test_offset_line_segment_positive(self):
        """Test segment offset with positive offset (left)."""
        # Horizontal line from (0, 0) to (1, 0), offset by 0.5 to the left
        new_p1, new_p2 = offset_line_segment((0, 0), (1, 0), 0.5)
        # Should move up to Y = 0.5
        assert abs(new_p1[0] - 0.0) < 1e-10
        assert abs(new_p1[1] - 0.5) < 1e-10
        assert abs(new_p2[0] - 1.0) < 1e-10
        assert abs(new_p2[1] - 0.5) < 1e-10

    def test_offset_line_segment_negative(self):
        """Test segment offset with negative offset (right)."""
        # Horizontal line from (0, 0) to (1, 0), offset by -0.5 to the right
        new_p1, new_p2 = offset_line_segment((0, 0), (1, 0), -0.5)
        # Should move down to Y = -0.5
        assert abs(new_p1[0] - 0.0) < 1e-10
        assert abs(new_p1[1] - (-0.5)) < 1e-10
        assert abs(new_p2[0] - 1.0) < 1e-10
        assert abs(new_p2[1] - (-0.5)) < 1e-10

    def test_calculate_line_intersection_perpendicular(self):
        """Test intersection of perpendicular lines."""
        # Line 1: horizontal through y=1
        # Line 2: vertical through x=2
        result = calculate_line_intersection((0, 1), (5, 1), (2, 0), (2, 5))
        assert result is not None
        assert abs(result[0] - 2.0) < 1e-10
        assert abs(result[1] - 1.0) < 1e-10

    def test_calculate_line_intersection_parallel(self):
        """Test that parallel lines return None."""
        # Two horizontal lines
        result = calculate_line_intersection((0, 0), (1, 0), (0, 1), (1, 1))
        assert result is None

    def test_calculate_line_intersection_diagonal(self):
        """Test intersection of diagonal lines."""
        # Line through origin at 45 degrees
        # Line through (1, 0) at -45 degrees
        result = calculate_line_intersection((0, 0), (1, 1), (1, 0), (0, 1))
        assert result is not None
        assert abs(result[0] - 0.5) < 1e-10
        assert abs(result[1] - 0.5) < 1e-10

    def test_calculate_path_winding_ccw_square(self):
        """Test winding for CCW square."""
        # CCW square (positive winding) - explicit closing point
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},
            {'x': 1, 'y': 1},
            {'x': 0, 'y': 1},
            {'x': 0, 'y': 0}
        ]
        winding = calculate_path_winding(path)
        assert winding > 0  # CCW = positive

    def test_calculate_path_winding_cw_square(self):
        """Test winding for CW square."""
        # CW square (negative winding) - explicit closing point
        path = [
            {'x': 0, 'y': 0},
            {'x': 0, 'y': 1},
            {'x': 1, 'y': 1},
            {'x': 1, 'y': 0},
            {'x': 0, 'y': 0}
        ]
        winding = calculate_path_winding(path)
        assert winding < 0  # CW = negative

    def test_compensate_line_path_none(self):
        """Test that 'none' compensation returns original path."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'}
        ]
        result = compensate_line_path(path, 0.125, 'none')
        assert result == path

    def test_compensate_rectangle_exterior(self):
        """Test exterior compensation expands rectangle outward."""
        # 1x1 square at origin, CCW - explicit closing point
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'},
            {'x': 0, 'y': 1, 'line_type': 'straight'},
            {'x': 0, 'y': 0, 'line_type': 'straight'}
        ]
        tool_diameter = 0.25  # 0.125 radius
        result = compensate_line_path(path, tool_diameter, 'exterior')

        # All points should move outward (exterior = expand)
        # For a CCW path, exterior means offset left = positive offset
        # Corner at (0,0) should move to approx (-0.125, -0.125)
        assert result[0]['x'] < 0
        assert result[0]['y'] < 0
        # Corner at (1,0) should move to approx (1.125, -0.125)
        assert result[1]['x'] > 1
        assert result[1]['y'] < 0
        # Corner at (1,1) should move to approx (1.125, 1.125)
        assert result[2]['x'] > 1
        assert result[2]['y'] > 1
        # Corner at (0,1) should move to approx (-0.125, 1.125)
        assert result[3]['x'] < 0
        assert result[3]['y'] > 1

    def test_compensate_rectangle_interior(self):
        """Test interior compensation shrinks rectangle inward."""
        # 1x1 square at origin, CCW - explicit closing point
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'},
            {'x': 0, 'y': 1, 'line_type': 'straight'},
            {'x': 0, 'y': 0, 'line_type': 'straight'}
        ]
        tool_diameter = 0.25  # 0.125 radius
        result = compensate_line_path(path, tool_diameter, 'interior')

        # All points should move inward (interior = shrink)
        # Corner at (0,0) should move to approx (0.125, 0.125)
        assert result[0]['x'] > 0
        assert result[0]['y'] > 0
        # Corner at (1,0) should move to approx (0.875, 0.125)
        assert result[1]['x'] < 1
        assert result[1]['y'] > 0
        # Corner at (1,1) should move to approx (0.875, 0.875)
        assert result[2]['x'] < 1
        assert result[2]['y'] < 1
        # Corner at (0,1) should move to approx (0.125, 0.875)
        assert result[3]['x'] > 0
        assert result[3]['y'] < 1

    def test_compensate_empty_path(self):
        """Test compensation of empty path."""
        result = compensate_line_path([], 0.125, 'exterior')
        assert result == []

    def test_compensate_single_point(self):
        """Test compensation of single point path."""
        path = [{'x': 0, 'y': 0, 'line_type': 'start'}]
        result = compensate_line_path(path, 0.125, 'exterior')
        assert result == path  # Should return unchanged

    def test_compensate_path_with_arc_exterior_ccw(self):
        """Test exterior compensation on CCW path with rightward-curving arc.

        This is the bug case: a rectangle with rounded right edge.
        The arc curves to the right (positive X), and exterior compensation
        should expand the path outward, requiring the arc radius to INCREASE.

        Path: start at (0.5, 0.5), go right to (2, 0.5), arc up to (2, 2.5),
        go left to (0.5, 2.5), then back down to start.
        """
        path = [
            {'x': 0.5, 'y': 0.5, 'line_type': 'start'},
            {'x': 2, 'y': 0.5, 'line_type': 'straight'},
            {'x': 2, 'y': 2.5, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.5, 'arc_direction': 'ccw'},
            {'x': 0.5, 'y': 2.5, 'line_type': 'straight'},
            {'x': 0.5, 'y': 0.5, 'line_type': 'straight'},
        ]
        tool_diameter = 0.1875  # 0.09375 radius
        tool_radius = tool_diameter / 2

        result = compensate_line_path(path, tool_diameter, 'exterior')

        # For exterior compensation on CCW path, all points should expand outward
        # Start point (0.5, 0.5) should move to approximately (0.4062, 0.4062)
        assert result[0]['x'] < 0.5
        assert result[0]['y'] < 0.5

        # End of horizontal line / start of arc (2, 0.5)
        # Y should decrease (move down/outward), X stays at 2 for vertical arc
        assert abs(result[1]['x'] - 2.0) < 0.001  # X unchanged for vertical semicircle
        assert result[1]['y'] < 0.5  # Y moved down (outward)
        assert abs(result[1]['y'] - (0.5 - tool_radius)) < 0.001

        # End of arc (2, 2.5) - Y should increase (move up/outward)
        assert abs(result[2]['x'] - 2.0) < 0.001  # X unchanged for vertical semicircle
        assert result[2]['y'] > 2.5  # Y moved up (outward)
        assert abs(result[2]['y'] - (2.5 + tool_radius)) < 0.001

        # End of top horizontal (0.5, 2.5) - should expand outward
        assert result[3]['x'] < 0.5
        assert result[3]['y'] > 2.5

    def test_compensate_path_with_arc_interior_ccw(self):
        """Test interior compensation on CCW path with rightward-curving arc.

        Interior compensation should shrink the path inward, requiring the
        arc radius to DECREASE.
        """
        path = [
            {'x': 0.5, 'y': 0.5, 'line_type': 'start'},
            {'x': 2, 'y': 0.5, 'line_type': 'straight'},
            {'x': 2, 'y': 2.5, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.5, 'arc_direction': 'ccw'},
            {'x': 0.5, 'y': 2.5, 'line_type': 'straight'},
            {'x': 0.5, 'y': 0.5, 'line_type': 'straight'},
        ]
        tool_diameter = 0.1875
        tool_radius = tool_diameter / 2

        result = compensate_line_path(path, tool_diameter, 'interior')

        # For interior compensation on CCW path, all points should shrink inward
        # Start point should move inward
        assert result[0]['x'] > 0.5
        assert result[0]['y'] > 0.5

        # End of horizontal line / start of arc
        # Y should increase (move up/inward)
        assert abs(result[1]['x'] - 2.0) < 0.001  # X unchanged for vertical semicircle
        assert result[1]['y'] > 0.5  # Y moved up (inward)
        assert abs(result[1]['y'] - (0.5 + tool_radius)) < 0.001

        # End of arc - Y should decrease (move down/inward)
        assert abs(result[2]['x'] - 2.0) < 0.001
        assert result[2]['y'] < 2.5  # Y moved down (inward)
        assert abs(result[2]['y'] - (2.5 - tool_radius)) < 0.001

    def test_compensate_arc_radius_increases_for_exterior(self):
        """Test that arc radius increases for exterior compensation when arc curves outward.

        For a vertical semicircle on the right edge of a CCW path:
        - Original radius = 1.0 (from center to start/end)
        - Exterior compensation should INCREASE radius
        - New radius = 1.0 + tool_radius
        """
        # Simple path: just a vertical line segment followed by a semicircle
        # Arc from (2, 0) to (2, 2) with center at (2, 1), radius = 1
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 2, 'y': 0, 'line_type': 'straight'},
            {'x': 2, 'y': 2, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1, 'arc_direction': 'ccw'},
            {'x': 0, 'y': 2, 'line_type': 'straight'},
            {'x': 0, 'y': 0, 'line_type': 'straight'},
        ]
        tool_diameter = 0.25  # 0.125 radius

        result = compensate_line_path(path, tool_diameter, 'exterior')

        # Arc start point: originally (2, 0), center at (2, 1)
        # Original radius = 1.0, new radius should be 1.125
        # New start: (2, 1 - 1.125) = (2, -0.125)
        assert abs(result[1]['y'] - (-0.125)) < 0.001

        # Arc end point: originally (2, 2), center at (2, 1)
        # New end: (2, 1 + 1.125) = (2, 2.125)
        assert abs(result[2]['y'] - 2.125) < 0.001

    def test_compensate_arc_radius_decreases_for_interior(self):
        """Test that arc radius decreases for interior compensation when arc curves outward."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 2, 'y': 0, 'line_type': 'straight'},
            {'x': 2, 'y': 2, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1, 'arc_direction': 'ccw'},
            {'x': 0, 'y': 2, 'line_type': 'straight'},
            {'x': 0, 'y': 0, 'line_type': 'straight'},
        ]
        tool_diameter = 0.25  # 0.125 radius

        result = compensate_line_path(path, tool_diameter, 'interior')

        # Arc start point: originally (2, 0), center at (2, 1)
        # Original radius = 1.0, new radius should be 0.875
        # New start: (2, 1 - 0.875) = (2, 0.125)
        assert abs(result[1]['y'] - 0.125) < 0.001

        # Arc end point: originally (2, 2), center at (2, 1)
        # New end: (2, 1 + 0.875) = (2, 1.875)
        assert abs(result[2]['y'] - 1.875) < 0.001

    def test_compensate_arc_horizontal_semicircle_exterior(self):
        """Test exterior compensation on a horizontal semicircle.

        Path with a semicircle on top edge, curving upward (positive Y).
        """
        # Rectangle with rounded top: semicircle from (0.5, 2) to (2.5, 2)
        # curving upward with center at (1.5, 2)
        path = [
            {'x': 0.5, 'y': 0, 'line_type': 'start'},
            {'x': 2.5, 'y': 0, 'line_type': 'straight'},
            {'x': 2.5, 'y': 2, 'line_type': 'straight'},
            {'x': 0.5, 'y': 2, 'line_type': 'arc', 'arc_center_x': 1.5, 'arc_center_y': 2, 'arc_direction': 'ccw'},
            {'x': 0.5, 'y': 0, 'line_type': 'straight'},
        ]
        tool_diameter = 0.25
        tool_radius = tool_diameter / 2

        result = compensate_line_path(path, tool_diameter, 'exterior')

        # Arc endpoints should have Y unchanged (horizontal semicircle)
        # but X should expand outward
        # Arc start (2.5, 2) should move to approximately (2.625, 2)
        assert result[3]['x'] < 0.5  # X decreased (outward for left point)
        assert abs(result[3]['y'] - 2.0) < 0.001  # Y unchanged for horizontal semicircle

    def test_compensate_quarter_arc_exterior(self):
        """Test exterior compensation on a quarter circle arc that bulges outward.

        This arc bulges RIGHT of travel direction (toward shape exterior).
        For exterior compensation, the tool stays outside, so the arc radius
        INCREASES (tool follows outside the outward bulge).
        """
        # Path with 90-degree arc in corner
        # Start at (0, 0), go to (2, 0), arc to (3, 1) with center at (2, 1), then up
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 2, 'y': 0, 'line_type': 'straight'},
            {'x': 3, 'y': 1, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1, 'arc_direction': 'ccw'},
            {'x': 3, 'y': 3, 'line_type': 'straight'},
            {'x': 0, 'y': 3, 'line_type': 'straight'},
            {'x': 0, 'y': 0, 'line_type': 'straight'},
        ]
        tool_diameter = 0.25
        tool_radius = tool_diameter / 2

        result = compensate_line_path(path, tool_diameter, 'exterior')

        # This arc bulges OUTWARD (right of walking direction), so for exterior
        # compensation the radius INCREASES (tool stays outside the bulge)
        # Original arc: center (2, 1), radius 1, from (2, 0) to (3, 1)
        # New radius = 1.0 + 0.125 = 1.125

        # Arc start point (2, 0) -> Y = 1 - 1.125 = -0.125
        assert abs(result[1]['y'] - (-0.125)) < 0.001

        # Arc end point (3, 1) -> X = 2 + 1.125 = 3.125
        assert abs(result[2]['x'] - 3.125) < 0.001

    def test_compensate_arc_mismatched_radii(self):
        """Test compensation when arc transitions to straight segment.

        The arc endpoint should be computed using line-circle intersection
        with the next segment, ensuring a continuous toolpath.

        Arc from (2, 0.25) to (2, 1.25) with center at (2, 1.75):
        - Start radius: |1.75 - 0.25| = 1.5
        - End radius: |1.75 - 1.25| = 0.5

        For exterior compensation, the arc end should connect to the
        compensated top edge (Y = 1.25 + 0.0625 = 1.3125).
        """
        path = [
            {'x': 0.25, 'y': 0.25, 'line_type': 'start'},
            {'x': 2, 'y': 0.25, 'line_type': 'straight'},
            {'x': 2, 'y': 1.25, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.75, 'arc_direction': 'ccw'},
            {'x': 0.25, 'y': 1.25, 'line_type': 'straight'},
            {'x': 0.25, 'y': 0.25, 'line_type': 'straight'},
        ]
        tool_diameter = 0.125  # 0.0625 radius

        result = compensate_line_path(path, tool_diameter, 'exterior')

        # Arc start: radius 1.5 -> 1.5 + 0.0625 = 1.5625
        # New Y = 1.75 - 1.5625 = 0.1875
        assert abs(result[1]['y'] - 0.1875) < 0.001, f"Arc start Y: expected 0.1875, got {result[1]['y']}"

        # Arc end: uses line-circle intersection with compensated top edge
        # Top edge is offset up by tool_radius, so Y = 1.25 + 0.0625 = 1.3125
        # The intersection point is where this line meets the arc
        assert abs(result[2]['y'] - 1.3125) < 0.001, f"Arc end Y: expected 1.3125, got {result[2]['y']}"


class TestArcUtils:
    """Tests for arc direction utilities."""

    def test_calculate_arc_direction_ccw(self):
        """Test counter-clockwise arc detection."""
        # Arc from (1, 0) to (0, 1) around origin is CCW
        direction = calculate_arc_direction((1, 0), (0, 1), (0, 0))
        assert direction == "G03"

    def test_calculate_arc_direction_cw(self):
        """Test clockwise arc detection."""
        # Arc from (0, 1) to (1, 0) around origin is CW
        direction = calculate_arc_direction((0, 1), (1, 0), (0, 0))
        assert direction == "G02"

    def test_calculate_arc_direction_semicircle_default(self):
        """Test semicircle defaults to G02 (CW) when cross product is zero."""
        # Semicircle from (1, 16) to (3, 16) with center at (2, 16)
        # Cross product is 0, should default to G02
        direction = calculate_arc_direction((1, 16), (3, 16), (2, 16))
        assert direction == "G02"

    def test_calculate_arc_direction_semicircle_ccw_hint(self):
        """Test semicircle with CCW hint returns G03."""
        # Same semicircle, but with CCW hint to curve upward
        direction = calculate_arc_direction((1, 16), (3, 16), (2, 16), 'ccw')
        assert direction == "G03"

    def test_calculate_arc_direction_semicircle_cw_hint(self):
        """Test semicircle with CW hint returns G02."""
        direction = calculate_arc_direction((1, 16), (3, 16), (2, 16), 'cw')
        assert direction == "G02"

    def test_calculate_arc_direction_hint_overrides_auto(self):
        """Test that direction hint overrides automatic detection."""
        # This arc is naturally CCW (G03)
        auto_direction = calculate_arc_direction((1, 0), (0, 1), (0, 0))
        assert auto_direction == "G03"

        # Force it to CW with hint
        forced_direction = calculate_arc_direction((1, 0), (0, 1), (0, 0), 'cw')
        assert forced_direction == "G02"

    def test_calculate_arc_direction_hint_case_insensitive(self):
        """Test that direction hint is case insensitive."""
        assert calculate_arc_direction((1, 16), (3, 16), (2, 16), 'CCW') == "G03"
        assert calculate_arc_direction((1, 16), (3, 16), (2, 16), 'Ccw') == "G03"
        assert calculate_arc_direction((1, 16), (3, 16), (2, 16), 'CW') == "G02"
        assert calculate_arc_direction((1, 16), (3, 16), (2, 16), 'Cw') == "G02"

    def test_calculate_arc_direction_invalid_hint_falls_through(self):
        """Test that invalid hint falls through to auto-detection."""
        # Invalid hint should be ignored, fall through to auto-detect
        direction = calculate_arc_direction((1, 0), (0, 1), (0, 0), 'invalid')
        assert direction == "G03"  # Natural CCW arc

    def test_calculate_arc_direction_none_hint(self):
        """Test that None hint uses auto-detection."""
        direction = calculate_arc_direction((1, 0), (0, 1), (0, 0), None)
        assert direction == "G03"

    def test_calculate_ij_offsets(self):
        """Test I, J offset calculation."""
        # From (3, 0) to center at (0, 0)
        i, j = calculate_ij_offsets((3, 0), (0, 0))
        assert i == -3
        assert j == 0

    def test_calculate_ij_offsets_offset_center(self):
        """Test I, J with offset center."""
        i, j = calculate_ij_offsets((5, 3), (2, 1))
        assert i == -3
        assert j == -2


class TestGCodeFormat:
    """Tests for G-code formatting utilities."""

    def test_format_coordinate_default(self):
        """Test default coordinate formatting."""
        assert format_coordinate(1.5) == "1.5000"
        assert format_coordinate(0.125) == "0.1250"

    def test_format_coordinate_precision(self):
        """Test custom precision."""
        assert format_coordinate(1.5, precision=2) == "1.50"
        assert format_coordinate(1.5, precision=1) == "1.5"

    def test_generate_header(self):
        """Test G-code header generation."""
        header = generate_header(1000, 2, 0.5)
        assert "G20 G90" in header  # Units and absolute mode
        assert "M03 S1000" in header  # Spindle start
        assert "G04 P2" in header  # Dwell

    def test_generate_header_no_comments(self):
        """Test that header has no comments (for Mach3)."""
        header = generate_header(1000, 2, 0.5)
        for line in header:
            assert '(' not in line
            assert ';' not in line

    def test_generate_footer(self):
        """Test G-code footer generation."""
        footer = generate_footer(0.5)
        assert "M05" in footer  # Spindle stop
        assert "M30" in footer  # Program end

    def test_generate_footer_no_comments(self):
        """Test that footer has no comments."""
        footer = generate_footer(0.5)
        for line in footer:
            assert '(' not in line
            assert ';' not in line

    def test_generate_rapid_move(self):
        """Test rapid move generation."""
        move = generate_rapid_move(x=1.0, y=2.0, z=0.5)
        assert move.startswith("G00")
        assert "X1.0000" in move
        assert "Y2.0000" in move
        assert "Z0.5000" in move

    def test_generate_rapid_move_partial(self):
        """Test rapid move with partial coordinates."""
        move = generate_rapid_move(z=0.5)
        assert move == "G00 Z0.5000"

    def test_generate_linear_move(self):
        """Test linear move generation."""
        move = generate_linear_move(x=1.0, y=2.0, feed=10.0)
        assert move.startswith("G01")
        assert "X1.0000" in move
        assert "F10.0" in move

    def test_generate_arc_move(self):
        """Test arc move generation."""
        arc = generate_arc_move("G02", 1.0, 0.0, -0.5, 0.0, feed=5.0)
        assert arc.startswith("G02")
        assert "X1.0000" in arc
        assert "I-0.5000" in arc
        assert "J0.0000" in arc

    def test_generate_subroutine_call(self):
        """Test M98 subroutine call generation."""
        call = generate_subroutine_call("C:\\Mach3\\GCode\\Test\\1000.nc", 5)
        assert "M98" in call
        assert "(-C:\\Mach3\\GCode\\Test\\1000.nc)" in call
        assert "L5" in call

    def test_generate_subroutine_end(self):
        """Test subroutine end generation."""
        end = generate_subroutine_end()
        assert "M99" in end
        assert "%" in end

    def test_sanitize_project_name(self):
        """Test project name sanitization."""
        assert sanitize_project_name("My Project") == "My_Project"
        assert sanitize_project_name("Test@#$123") == "Test123"
        assert sanitize_project_name("a" * 100)[:50] == "a" * 50  # Truncation

    def test_sanitize_project_name_preserves_hyphens(self):
        """Test that hyphens are preserved."""
        assert sanitize_project_name("Frame-16in") == "Frame-16in"


class TestSubroutineGenerator:
    """Tests for subroutine generation utilities."""

    def test_subroutine_ranges(self):
        """Test that subroutine ranges are defined."""
        assert 'drill' in SUBROUTINE_RANGES
        assert 'circular' in SUBROUTINE_RANGES
        assert 'hexagonal' in SUBROUTINE_RANGES
        assert 'line' in SUBROUTINE_RANGES

    def test_get_next_subroutine_number(self):
        """Test getting next available subroutine number."""
        # First drill subroutine
        num = get_next_subroutine_number('drill', [])
        assert num == 1000

        # With some existing
        num = get_next_subroutine_number('drill', [1000, 1001])
        assert num == 1002

    def test_get_next_subroutine_number_different_types(self):
        """Test different operation types get different ranges."""
        drill_num = get_next_subroutine_number('drill', [])
        circle_num = get_next_subroutine_number('circular', [])
        hex_num = get_next_subroutine_number('hexagonal', [])
        line_num = get_next_subroutine_number('line', [])

        assert 1000 <= drill_num < 1100
        assert 1100 <= circle_num < 1200
        assert 1200 <= hex_num < 1300
        assert 1300 <= line_num < 1400

    def test_generate_subroutine_file(self):
        """Test subroutine file generation."""
        commands = ["G00 Z0", "G01 Z-0.1 F10"]
        content = generate_subroutine_file(commands)

        assert "G00 Z0" in content
        assert "G01 Z-0.1 F10" in content
        assert content.strip().endswith("%")
        assert "M99" in content

    def test_build_subroutine_path(self):
        """Test subroutine path construction."""
        import os
        path = build_subroutine_path("C:\\Mach3\\GCode", "TestProject", 1000)
        # Check path components (platform-independent)
        assert "TestProject" in path
        assert "1000.nc" in path


class TestValidators:
    """Tests for validation utilities."""

    def test_validate_bounds_valid(self):
        """Test valid point within bounds."""
        assert validate_bounds(5.0, 5.0, 15.0, 15.0) is True
        assert validate_bounds(0, 0, 15.0, 15.0) is True
        assert validate_bounds(15.0, 15.0, 15.0, 15.0) is True

    def test_validate_bounds_invalid(self):
        """Test invalid points outside bounds."""
        assert validate_bounds(-1.0, 5.0, 15.0, 15.0) is False
        assert validate_bounds(5.0, -1.0, 15.0, 15.0) is False
        assert validate_bounds(16.0, 5.0, 15.0, 15.0) is False
        assert validate_bounds(5.0, 16.0, 15.0, 15.0) is False

    def test_validate_all_points_valid(self):
        """Test all points valid."""
        points = [(1.0, 1.0), (5.0, 5.0), (10.0, 10.0)]
        errors = validate_all_points(points, 15.0, 15.0)
        assert errors == []

    def test_validate_all_points_some_invalid(self):
        """Test with some invalid points."""
        points = [(1.0, 1.0), (20.0, 5.0), (5.0, -1.0)]
        errors = validate_all_points(points, 15.0, 15.0)
        assert len(errors) == 2

    def test_validate_tool_in_standards_found(self):
        """Test tool found in standards."""
        standards = {
            'drill': {'0.125': {'spindle_speed': 1000}},
            'end_mill_1flute': {'0.125': {'spindle_speed': 12000}}
        }
        assert validate_tool_in_standards('drill', 0.125, standards) is True
        assert validate_tool_in_standards('end_mill_1flute', 0.125, standards) is True

    def test_validate_tool_in_standards_not_found(self):
        """Test tool not found in standards."""
        standards = {
            'drill': {'0.125': {'spindle_speed': 1000}}
        }
        assert validate_tool_in_standards('drill', 0.25, standards) is False
        assert validate_tool_in_standards('end_mill_2flute', 0.125, standards) is False

    def test_validate_tool_in_standards_empty(self):
        """Test with empty standards."""
        assert validate_tool_in_standards('drill', 0.125, {}) is False
        assert validate_tool_in_standards('drill', 0.125, None) is False

    def test_validate_circle_bounds_valid(self):
        """Test circle within bounds."""
        errors = validate_circle_bounds(5.0, 5.0, 2.0, 15.0, 15.0)
        assert errors == []

    def test_validate_circle_bounds_invalid(self):
        """Test circle extending outside bounds."""
        # Circle at (1, 5) with diameter 4 extends past X=0
        errors = validate_circle_bounds(1.0, 5.0, 4.0, 15.0, 15.0)
        assert len(errors) > 0

    def test_validate_hexagon_bounds_valid(self):
        """Test hexagon within bounds."""
        errors = validate_hexagon_bounds(5.0, 5.0, 1.0, 15.0, 15.0)
        assert errors == []

    def test_validate_hexagon_bounds_invalid(self):
        """Test hexagon extending outside bounds."""
        # Hexagon at edge will extend past
        errors = validate_hexagon_bounds(0.25, 5.0, 1.0, 15.0, 15.0)
        assert len(errors) > 0

    def test_validate_arc_geometry_valid(self):
        """Test valid arc where endpoints are equidistant from center."""
        # Valid semicircle: center at (2, 1.5), both endpoints at radius 1.0
        path = [
            {'x': 0.5, 'y': 0.5, 'line_type': 'start'},
            {'x': 2, 'y': 0.5, 'line_type': 'straight'},
            {'x': 2, 'y': 2.5, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.5},
            {'x': 0.5, 'y': 2.5, 'line_type': 'straight'},
        ]
        warnings = validate_arc_geometry(path)
        assert warnings == []

    def test_validate_arc_geometry_invalid_radii(self):
        """Test invalid arc where endpoints have different distances from center."""
        # Invalid arc: center at (2, 1.25)
        # Start (2, 0.5) is 0.75 from center
        # End (2, 2.5) is 1.25 from center
        path = [
            {'x': 0.5, 'y': 0.5, 'line_type': 'start'},
            {'x': 2, 'y': 0.5, 'line_type': 'straight'},
            {'x': 2, 'y': 2.5, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.25},
            {'x': 0.5, 'y': 2.5, 'line_type': 'straight'},
        ]
        warnings = validate_arc_geometry(path)
        assert len(warnings) == 1
        assert "invalid geometry" in warnings[0]
        assert "0.75" in warnings[0]  # start radius
        assert "1.25" in warnings[0]  # end radius

    def test_validate_arc_geometry_missing_center(self):
        """Test arc with missing center coordinates."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 1, 'line_type': 'arc'},  # Missing arc_center_x/y
        ]
        warnings = validate_arc_geometry(path)
        assert len(warnings) == 1
        assert "missing center" in warnings[0]

    def test_validate_arc_geometry_no_arcs(self):
        """Test path with no arcs returns no warnings."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'},
        ]
        warnings = validate_arc_geometry(path)
        assert warnings == []

    def test_validate_arc_geometry_within_tolerance(self):
        """Test arc with radii difference within tolerance."""
        # Slightly different radii but within default 0.001 tolerance
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 2, 'line_type': 'arc', 'arc_center_x': 1, 'arc_center_y': 1.0005},
        ]
        warnings = validate_arc_geometry(path)
        assert warnings == []

    def test_validate_arc_geometry_custom_tolerance(self):
        """Test arc validation with custom tolerance."""
        # Radii differ by 0.1, which exceeds default but is within custom tolerance
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 2, 'y': 0.5, 'line_type': 'straight'},
            {'x': 2, 'y': 2.5, 'line_type': 'arc', 'arc_center_x': 2, 'arc_center_y': 1.25},
        ]
        # With tight tolerance, should warn
        warnings_tight = validate_arc_geometry(path, tolerance=0.001)
        assert len(warnings_tight) == 1

        # With loose tolerance, should pass
        warnings_loose = validate_arc_geometry(path, tolerance=1.0)
        assert warnings_loose == []


class TestLeadIn:
    """Tests for lead-in utilities."""

    def test_calculate_circle_lead_in_point(self):
        """Test lead-in point for circle is radially outward from 3 o'clock."""
        # Circle at (5, 5) with cut_radius 0.5, lead-in distance 0.25
        lead_in_x, lead_in_y = calculate_circle_lead_in_point(5.0, 5.0, 0.5, 0.25)
        # Profile start is at (5.5, 5) - 3 o'clock
        # Lead-in is 0.25 further out: (5.75, 5)
        assert abs(lead_in_x - 5.75) < 1e-10
        assert abs(lead_in_y - 5.0) < 1e-10

    def test_calculate_circle_lead_in_point_zero_distance(self):
        """Test lead-in with zero distance returns profile start."""
        lead_in_x, lead_in_y = calculate_circle_lead_in_point(5.0, 5.0, 0.5, 0)
        assert abs(lead_in_x - 5.5) < 1e-10
        assert abs(lead_in_y - 5.0) < 1e-10

    def test_calculate_hexagon_lead_in_point(self):
        """Test lead-in point for hexagon extends first edge backwards."""
        # Hexagon vertices in point-up orientation, first edge from v0 to v1
        vertices = [
            (5.0, 5.5),   # v0 - top vertex
            (5.4, 5.25),  # v1 - upper right
            (5.4, 4.75),  # v2 - lower right
            (5.0, 4.5),   # v3 - bottom
            (4.6, 4.75),  # v4 - lower left
            (4.6, 5.25),  # v5 - upper left
        ]
        lead_in_x, lead_in_y = calculate_hexagon_lead_in_point(vertices, 0.25)

        # Lead-in should be in the opposite direction from v0 to v1
        # Direction from v0 to v1: (0.4, -0.25), normalized ≈ (0.848, -0.53)
        # Lead-in is v0 - direction * 0.25
        # So lead-in should be slightly above and to the left of v0
        assert lead_in_x < 5.0
        assert lead_in_y > 5.5

    def test_calculate_hexagon_lead_in_point_single_vertex(self):
        """Test lead-in with single vertex returns that vertex."""
        vertices = [(5.0, 5.0)]
        lead_in_x, lead_in_y = calculate_hexagon_lead_in_point(vertices, 0.25)
        assert abs(lead_in_x - 5.0) < 1e-10
        assert abs(lead_in_y - 5.0) < 1e-10

    def test_calculate_line_lead_in_point(self):
        """Test lead-in point for line extends initial direction backwards."""
        # Line from (1, 1) to (2, 1) - horizontal right
        path = [
            {'x': 1, 'y': 1},
            {'x': 2, 'y': 1},
        ]
        lead_in_x, lead_in_y = calculate_line_lead_in_point(path, 0.25)
        # Lead-in should be 0.25 to the left of start: (0.75, 1)
        assert abs(lead_in_x - 0.75) < 1e-10
        assert abs(lead_in_y - 1.0) < 1e-10

    def test_calculate_line_lead_in_point_diagonal(self):
        """Test lead-in for diagonal line."""
        # Line from (0, 0) to (1, 1) - 45 degree diagonal
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 1},
        ]
        lead_in_x, lead_in_y = calculate_line_lead_in_point(path, math.sqrt(2) / 2)
        # Lead-in should be 0.5 in both X and Y negative direction
        assert abs(lead_in_x - (-0.5)) < 1e-10
        assert abs(lead_in_y - (-0.5)) < 1e-10

    def test_calculate_line_lead_in_point_single_point(self):
        """Test lead-in with single point returns that point."""
        path = [{'x': 1, 'y': 1}]
        lead_in_x, lead_in_y = calculate_line_lead_in_point(path, 0.25)
        assert abs(lead_in_x - 1.0) < 1e-10
        assert abs(lead_in_y - 1.0) < 1e-10

    def test_calculate_line_lead_in_point_empty(self):
        """Test lead-in with empty path returns origin."""
        lead_in_x, lead_in_y = calculate_line_lead_in_point([], 0.25)
        assert lead_in_x == 0
        assert lead_in_y == 0

    def test_is_closed_path_closed(self):
        """Test detecting closed path."""
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},
            {'x': 1, 'y': 1},
            {'x': 0, 'y': 0},
        ]
        assert is_closed_path(path) is True

    def test_is_closed_path_open(self):
        """Test detecting open path."""
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},
            {'x': 1, 'y': 1},
        ]
        assert is_closed_path(path) is False

    def test_is_closed_path_within_tolerance(self):
        """Test closed path detection with small gap within tolerance."""
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},
            {'x': 1, 'y': 1},
            {'x': 0.00001, 'y': 0.00001},  # Very close to start
        ]
        assert is_closed_path(path) is True

    def test_is_closed_path_short(self):
        """Test that short paths are not closed."""
        assert is_closed_path([]) is False
        assert is_closed_path([{'x': 0, 'y': 0}]) is False


class TestLeadInSubroutines:
    """Tests for subroutine generation with lead-in."""

    def test_circle_subroutine_without_lead_in(self):
        """Test circle subroutine without lead-in uses vertical plunge."""
        content = generate_circle_pass_subroutine(
            cut_radius=0.5,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_distance=None
        )
        # Should contain vertical plunge preamble (relative mode, plunge, absolute mode)
        # Note: G00 Z0 was removed to fix multi-pass depth bug - subroutine
        # now starts at current Z and plunges incrementally
        assert "G91" in content
        assert "G01 Z-0.0625" in content
        assert "G90" in content
        # Should contain circle arc
        assert "G02 I-0.5000" in content

    def test_circle_subroutine_with_lead_in(self):
        """Test circle subroutine with lead-in uses ramped entry."""
        content = generate_circle_pass_subroutine(
            cut_radius=0.5,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_distance=0.25
        )
        # Should contain ramp lead-in (X and Z in same move)
        assert "G91" in content
        assert "G01 X-0.2500" in content  # Ramp move includes negative X
        assert "Z-0.0625" in content
        # Should contain circle arc
        assert "G02 I-0.5000" in content
        # Should contain lead-out (return to lead-in point)
        assert "G01 X0.2500" in content  # Positive X to return

    def test_hexagon_subroutine_without_lead_in(self):
        """Test hexagon subroutine without lead-in uses vertical plunge."""
        vertices = [
            (5.0, 5.5),
            (5.4, 5.25),
            (5.4, 4.75),
            (5.0, 4.5),
            (4.6, 4.75),
            (4.6, 5.25),
        ]
        content = generate_hexagon_pass_subroutine(
            vertices=vertices,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_point=None
        )
        # Should contain vertical plunge (relative mode, plunge)
        # Note: G00 Z0 was removed to fix multi-pass depth bug
        assert "G91" in content
        assert "G01 Z-0.0625" in content
        # Should NOT contain lead-out
        lines = content.split('\n')
        # Last few lines before M99 should be the closing move
        assert "X5.0000 Y5.5000" in content  # Close back to first vertex

    def test_hexagon_subroutine_with_lead_in(self):
        """Test hexagon subroutine with lead-in uses ramped entry."""
        vertices = [
            (5.0, 5.5),
            (5.4, 5.25),
            (5.4, 4.75),
            (5.0, 4.5),
            (4.6, 4.75),
            (4.6, 5.25),
        ]
        lead_in_point = (4.8, 5.7)  # Sample lead-in point
        content = generate_hexagon_pass_subroutine(
            vertices=vertices,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_point=lead_in_point
        )
        # Should contain ramp entry with relative XY offset
        assert "G91" in content
        # The ramp should move from lead-in to profile start
        # Offset is (5.0-4.8, 5.5-5.7) = (0.2, -0.2)
        assert "X0.2000" in content
        assert "Y-0.2000" in content
        assert "Z-0.0625" in content
        # Should contain lead-out to lead-in point
        assert "X4.8000 Y5.7000" in content

    def test_line_subroutine_without_lead_in(self):
        """Test line subroutine without lead-in uses vertical plunge."""
        path = [
            {'x': 1, 'y': 1, 'line_type': 'start'},
            {'x': 2, 'y': 1, 'line_type': 'straight'},
            {'x': 2, 'y': 2, 'line_type': 'straight'},
        ]
        content = generate_line_path_subroutine(
            path=path,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_point=None
        )
        # Should contain vertical plunge (relative mode, plunge)
        # Note: G00 Z0 was removed to fix multi-pass depth bug
        assert "G91" in content
        assert "G01 Z-0.0625" in content

    def test_line_subroutine_with_lead_in_closed_path(self):
        """Test line subroutine with lead-in for closed path includes lead-out."""
        # Closed rectangle path
        path = [
            {'x': 1, 'y': 1, 'line_type': 'start'},
            {'x': 2, 'y': 1, 'line_type': 'straight'},
            {'x': 2, 'y': 2, 'line_type': 'straight'},
            {'x': 1, 'y': 2, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'},  # Close to start
        ]
        lead_in_point = (0.75, 1.0)
        content = generate_line_path_subroutine(
            path=path,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_point=lead_in_point
        )
        # Should contain ramp entry
        assert "G91" in content
        # Offset from (0.75, 1) to (1, 1) is (0.25, 0)
        assert "X0.2500" in content
        assert "Y0.0000" in content
        # Should contain lead-out for closed path
        assert "X0.7500 Y1.0000" in content

    def test_line_subroutine_with_lead_in_open_path(self):
        """Test line subroutine with lead-in for open path has no lead-out."""
        # Open path (doesn't return to start)
        path = [
            {'x': 1, 'y': 1, 'line_type': 'start'},
            {'x': 2, 'y': 1, 'line_type': 'straight'},
            {'x': 2, 'y': 2, 'line_type': 'straight'},
        ]
        lead_in_point = (0.75, 1.0)
        content = generate_line_path_subroutine(
            path=path,
            pass_depth=0.0625,
            plunge_rate=8.0,
            feed_rate=45.0,
            lead_in_point=lead_in_point
        )
        # Should contain ramp entry
        assert "G91" in content
        # Should NOT contain lead-out to (0.75, 1) - open path ends at (2, 2)
        # The last move should be to (2, 2), not to lead-in point
        lines = [l for l in content.split('\n') if l.strip() and not l.startswith('%')]
        # Find last G01 move
        last_moves = [l for l in lines if l.startswith('G01')]
        # Last move should be to (2, 2), not to lead-in
        assert "X2.0000 Y2.0000" in last_moves[-1]


class TestCornerDetection:
    """Tests for corner detection utilities."""

    def test_calculate_segment_angle_straight(self):
        """Test angle for straight line (0 degrees - same direction)."""
        # Three points in a straight horizontal line
        # Vectors point in same direction, angle between them is 0
        angle = calculate_segment_angle((0, 0), (1, 0), (2, 0))
        assert abs(angle - 0.0) < 0.001

    def test_calculate_segment_angle_right_angle(self):
        """Test angle for right angle (90 degrees)."""
        # Right turn: right then up
        angle = calculate_segment_angle((0, 0), (1, 0), (1, 1))
        assert abs(angle - 90.0) < 0.001

    def test_calculate_segment_angle_acute(self):
        """Test angle for direction change between 90-180 degrees."""
        # Going right, then turn back left-ish
        angle = calculate_segment_angle((0, 0), (1, 0), (0.5, 0.5))
        # This is a sharp turn, so angle > 90 degrees between vectors
        assert angle > 90.0
        assert angle < 180.0

    def test_calculate_segment_angle_gentle_turn(self):
        """Test angle for gentle turn (small angle between directions)."""
        # Gentle turn: going right, then slightly up-right
        # Vectors are nearly the same direction, small angle between them
        angle = calculate_segment_angle((0, 0), (1, 0), (2, 0.5))
        assert angle < 90.0
        assert angle > 0

    def test_calculate_segment_angle_degenerate(self):
        """Test angle for degenerate case (same point)."""
        # Two points at same location
        angle = calculate_segment_angle((0, 0), (0, 0), (1, 0))
        assert abs(angle - 180.0) < 0.001  # Treated as straight

    def test_calculate_direction_vector(self):
        """Test direction vector calculation."""
        # Horizontal right
        dx, dy = calculate_direction_vector((0, 0), (2, 0))
        assert abs(dx - 1.0) < 0.001
        assert abs(dy - 0.0) < 0.001

        # Vertical up
        dx, dy = calculate_direction_vector((0, 0), (0, 3))
        assert abs(dx - 0.0) < 0.001
        assert abs(dy - 1.0) < 0.001

        # Diagonal (45 degrees)
        dx, dy = calculate_direction_vector((0, 0), (1, 1))
        expected = 1.0 / math.sqrt(2)
        assert abs(dx - expected) < 0.001
        assert abs(dy - expected) < 0.001

    def test_angle_between_vectors(self):
        """Test angle between direction vectors."""
        # Same direction = 0 degrees
        angle = angle_between_vectors((1, 0), (1, 0))
        assert abs(angle - 0.0) < 0.001

        # Opposite direction = 180 degrees
        angle = angle_between_vectors((1, 0), (-1, 0))
        assert abs(angle - 180.0) < 0.001

        # Perpendicular = 90 degrees
        angle = angle_between_vectors((1, 0), (0, 1))
        assert abs(angle - 90.0) < 0.001

    def test_get_arc_tangent_ccw(self):
        """Test tangent direction for CCW arc."""
        # Arc centered at origin, point at 3 o'clock
        # CCW tangent should point upward
        tx, ty = get_arc_tangent_at_point((0, 0), (1, 0), 'G03')
        assert abs(tx - 0.0) < 0.001
        assert abs(ty - 1.0) < 0.001

    def test_get_arc_tangent_cw(self):
        """Test tangent direction for CW arc."""
        # Arc centered at origin, point at 3 o'clock
        # CW tangent should point downward
        tx, ty = get_arc_tangent_at_point((0, 0), (1, 0), 'G02')
        assert abs(tx - 0.0) < 0.001
        assert abs(ty - (-1.0)) < 0.001

    def test_identify_corners_simple_square(self):
        """Test corner identification for a square path."""
        # Square with 90-degree corners
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},
            {'x': 1, 'y': 1},
            {'x': 0, 'y': 1},
            {'x': 0, 'y': 0},
        ]
        corners = identify_corners(path, angle_threshold=120.0)
        # Should find 3 corners (indices 1, 2, 3) - 90-degree turns
        assert len(corners) == 3
        for corner in corners:
            assert corner['angle'] < 120.0

    def test_identify_corners_above_threshold(self):
        """Test that path segments with angle >= threshold are not flagged.

        Note: identify_corners() finds corners where angle < threshold.
        The angle represents deviation between consecutive direction vectors:
        - 0 degrees = same direction (straight)
        - 90 degrees = right angle turn
        - 180 degrees = complete reversal

        For a threshold of 120, angles >= 120 are not marked as corners.
        """
        # Path with a U-turn (angle close to 180 between segments)
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},    # Going right
            {'x': 0, 'y': 0.1},  # Reversing direction (angle ~170 degrees)
            {'x': -1, 'y': 0.2}, # Continue leftward
        ]
        # Use threshold where the U-turn angle (>120) won't be flagged
        corners = identify_corners(path, angle_threshold=120.0)
        # The ~170 degree turn should not be flagged as a corner
        # But the second turn might be, depending on exact angles
        # Let's just verify that high-angle turns aren't flagged
        for corner in corners:
            assert corner['angle'] < 120.0

    def test_identify_corners_short_path(self):
        """Test corner identification for too-short path."""
        path = [{'x': 0, 'y': 0}, {'x': 1, 'y': 0}]
        corners = identify_corners(path, angle_threshold=120.0)
        assert len(corners) == 0

    def test_calculate_corner_feed_factor(self):
        """Test corner feed factor based on angle."""
        # Full straight = 1.0
        assert calculate_corner_feed_factor(180.0) == 1.0

        # Not a corner (>= 120) = 1.0
        assert calculate_corner_feed_factor(120.0) == 1.0

        # Mild corner (90-120) = 0.75
        assert calculate_corner_feed_factor(100.0) == 0.75

        # Moderate corner (60-90) = 0.50
        assert calculate_corner_feed_factor(75.0) == 0.50

        # Sharp corner (30-60) = 0.40
        assert calculate_corner_feed_factor(45.0) == 0.40

        # Very sharp corner (< 30) = 0.30
        assert calculate_corner_feed_factor(20.0) == 0.30

    def test_generate_corner_slowdown_points(self):
        """Test generating path with corner feed factors."""
        path = [
            {'x': 0, 'y': 0},
            {'x': 1, 'y': 0},  # Corner here (90 degree turn)
            {'x': 1, 'y': 1},
        ]
        result = generate_corner_slowdown_points(path, angle_threshold=120.0)

        # All points should have corner_feed_factor
        assert all('corner_feed_factor' in p for p in result)

        # First and last should be 1.0 (not corners)
        assert result[0]['corner_feed_factor'] == 1.0
        assert result[-1]['corner_feed_factor'] == 1.0

        # Middle point should have reduced feed factor
        assert result[1]['corner_feed_factor'] < 1.0

    def test_get_corner_adjusted_feed_enabled(self):
        """Test corner-adjusted feed with slowdown enabled."""
        base_feed = 100.0
        corner_point = {'corner_feed_factor': 0.5}

        adjusted = get_corner_adjusted_feed(
            base_feed, corner_point,
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5
        )
        # Should be reduced: 100 * 0.5 * 0.5 = 25
        assert abs(adjusted - 25.0) < 0.001

    def test_get_corner_adjusted_feed_disabled(self):
        """Test corner-adjusted feed with slowdown disabled."""
        base_feed = 100.0
        corner_point = {'corner_feed_factor': 0.5}

        adjusted = get_corner_adjusted_feed(
            base_feed, corner_point,
            corner_slowdown_enabled=False,
            corner_feed_factor=0.5
        )
        # Should be unchanged when disabled
        assert abs(adjusted - 100.0) < 0.001

    def test_get_corner_adjusted_feed_normal_point(self):
        """Test corner-adjusted feed for non-corner point."""
        base_feed = 100.0
        normal_point = {'corner_feed_factor': 1.0}

        adjusted = get_corner_adjusted_feed(
            base_feed, normal_point,
            corner_slowdown_enabled=True,
            corner_feed_factor=0.5
        )
        # Should be unchanged for non-corner points
        assert abs(adjusted - 100.0) < 0.001


class TestHelicalLeadIn:
    """Tests for helical lead-in utilities."""

    def test_calculate_helix_radius_for_circle_normal(self):
        """Test helix radius calculation for normal circle."""
        # 1" diameter circle cut with 0.125" tool
        cut_radius = 0.4375  # (1.0 - 0.125) / 2
        tool_diameter = 0.125

        radius = calculate_helix_radius_for_circle(cut_radius, tool_diameter)
        assert radius is not None
        assert radius > 0
        assert radius < cut_radius

    def test_calculate_helix_radius_for_circle_too_small(self):
        """Test helix radius returns None for tiny circle."""
        # Very small circle that can't fit helix
        cut_radius = 0.04  # Smaller than MIN_HELIX_RADIUS
        tool_diameter = 0.125

        radius = calculate_helix_radius_for_circle(cut_radius, tool_diameter)
        assert radius is None

    def test_calculate_helix_radius_for_hexagon_normal(self):
        """Test helix radius calculation for normal hexagon."""
        flat_to_flat = 1.0
        tool_diameter = 0.125

        radius = calculate_helix_radius_for_hexagon(flat_to_flat, tool_diameter)
        assert radius is not None
        assert radius > 0
        assert radius >= MIN_HELIX_RADIUS

    def test_calculate_helix_radius_for_hexagon_too_small(self):
        """Test helix radius returns None for tiny hexagon."""
        flat_to_flat = 0.1  # Very small hexagon
        tool_diameter = 0.125

        radius = calculate_helix_radius_for_hexagon(flat_to_flat, tool_diameter)
        assert radius is None

    def test_calculate_helix_start_point(self):
        """Test helix start point is at 3 o'clock."""
        center_x, center_y = 5.0, 5.0
        helix_radius = 0.1

        start_x, start_y = calculate_helix_start_point(center_x, center_y, helix_radius)

        assert abs(start_x - 5.1) < 0.001
        assert abs(start_y - 5.0) < 0.001

    def test_calculate_helix_revolutions_single(self):
        """Test helix revolutions for shallow depth."""
        revolutions = calculate_helix_revolutions(0.03, 0.04)
        assert revolutions == 1

    def test_calculate_helix_revolutions_multiple(self):
        """Test helix revolutions for deeper cut."""
        revolutions = calculate_helix_revolutions(0.1, 0.04)
        assert revolutions == 3  # ceil(0.1/0.04) = 3

    def test_calculate_helix_revolutions_zero_pitch(self):
        """Test helix revolutions with zero pitch returns 1."""
        revolutions = calculate_helix_revolutions(0.1, 0)
        assert revolutions == 1

    def test_generate_helical_entry_output(self):
        """Test helical entry G-code generation."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.08,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=8.0,
            center=(5.0, 5.0),
        )

        assert len(lines) > 0
        # Should contain G02 arc moves with Z
        for line in lines:
            assert line.startswith('G02')
            assert 'Z' in line
            assert 'I' in line
            assert 'J' in line
            assert 'F' in line


class TestHelicalEntry:
    """Tests for generate_helical_entry() unified helix function."""

    def test_absolute_mode_basic(self):
        """Test absolute mode: center provided, no transition."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.08,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
        )
        assert len(lines) > 0
        for line in lines:
            assert line.startswith('G02')
            assert 'Z' in line
            assert 'I' in line
            assert 'J' in line

    def test_absolute_mode_produces_absolute_z(self):
        """Absolute mode with center should produce absolute Z coordinates."""
        lines = generate_helical_entry(
            helix_radius=0.1, target_depth=0.08,
            helix_pitch=0.04, plunge_rate=8.0,
            transition_feed=45.0, approach_angle=90,
            center=(5.0, 5.0),
        )
        # 2 revolutions (0.08 / 0.04), absolute Z should descend
        assert len(lines) == 2
        # First rev: Z = -0.04, Second rev: Z = -0.08
        assert 'Z-0.0400' in lines[0]
        assert 'Z-0.0800' in lines[1]
        # Should use absolute XY (not X0 Y0)
        assert 'X5.1' in lines[0]

    def test_relative_z_mode_basic(self):
        """Test relative Z mode: no center, relative_z=True wraps in G91/G90."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            relative_z=True,
        )
        assert lines[0] == "G91"
        assert lines[-1] == "G90"
        # Middle lines should be G02 with X0 Y0
        for line in lines[1:-1]:
            assert line.startswith('G02')
            assert 'X0' in line
            assert 'Y0' in line

    def test_relative_z_mode_no_g91_when_false(self):
        """Without relative_z, no G91/G90 wrapping when center is None."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            relative_z=False,
        )
        assert lines[0].startswith('G02')
        assert 'G91' not in lines
        assert 'G90' not in lines

    def test_arc_transition_absolute(self):
        """Test arc transition in absolute mode."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
            transition='arc',
            cut_radius=0.5,
        )
        # Last line should be the arc transition (G02 without Z)
        arc_line = lines[-1]
        assert arc_line.startswith('G02')
        assert 'Z' not in arc_line
        assert 'F45.0' in arc_line

    def test_arc_transition_relative(self):
        """Test arc transition in relative Z mode uses G91 delta."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            relative_z=True,
            transition='arc',
            cut_radius=0.5,
        )
        # Should have G91..G90 for helix, then G91..G90 for arc transition
        g91_count = lines.count("G91")
        g90_count = lines.count("G90")
        assert g91_count == 2
        assert g90_count == 2

    def test_arc_transition_skipped_when_radii_equal(self):
        """No arc transition when helix_radius equals cut_radius."""
        lines = generate_helical_entry(
            helix_radius=0.5,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
            transition='arc',
            cut_radius=0.5,
        )
        # Only helix lines, no transition
        for line in lines:
            assert 'Z' in line  # All lines are helix (have Z)

    def test_linear_transition(self):
        """Test linear transition to target point."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
            transition='linear',
            target_point=(5.5, 5.0),
        )
        # Last line should be G01 linear move to target
        last = lines[-1]
        assert last.startswith('G01')
        assert 'X5.5' in last
        assert 'F45.0' in last

    def test_feed_ramping(self):
        """Test that feed rate ramps during helix revolutions."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.12,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
        )
        # 3 revolutions for 0.12/0.04 depth
        assert len(lines) == 3
        # Extract feed rates - they should increase
        feeds = []
        for line in lines:
            f_idx = line.index('F')
            feed_str = line[f_idx + 1:].split()[0]
            feeds.append(float(feed_str))
        assert feeds[0] < feeds[1] < feeds[2]

    def test_helix_end_feed_separate_from_transition_feed(self):
        """helix_end_feed controls ramp target, transition_feed controls transition move."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.04,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            helix_end_feed=36.0,  # Arc-adjusted feed for helix ramp
            center=(5.0, 5.0),
            transition='linear',
            target_point=(5.5, 5.0),
        )
        # Helix line ramps toward 36.0, not 45.0
        helix_line = lines[0]
        f_idx = helix_line.index('F')
        helix_feed = float(helix_line[f_idx + 1:].split()[0])
        # Single revolution = 75% step: 8.0 + (36.0 - 8.0) * 0.75 = 29.0
        assert abs(helix_feed - 29.0) < 0.1

        # Transition line uses 80% of helix_end_feed (36.0 * 0.9 = 32.4)
        transition_line = lines[-1]
        assert 'F28.8' in transition_line

    def test_single_revolution(self):
        """Test with a single helix revolution."""
        lines = generate_helical_entry(
            helix_radius=0.1,
            target_depth=0.03,
            helix_pitch=0.04,
            plunge_rate=8.0,
            transition_feed=45.0,
            center=(5.0, 5.0),
        )
        assert len(lines) == 1
        assert lines[0].startswith('G02')

    def test_approach_angle_affects_ij(self):
        """Different approach angles should produce different I/J offsets."""
        lines_90 = generate_helical_entry(
            helix_radius=0.5, target_depth=0.04,
            helix_pitch=0.04, plunge_rate=8.0,
            transition_feed=45.0, approach_angle=90,
            relative_z=True,
        )
        lines_0 = generate_helical_entry(
            helix_radius=0.5, target_depth=0.04,
            helix_pitch=0.04, plunge_rate=8.0,
            transition_feed=45.0, approach_angle=0,
            relative_z=True,
        )
        # At 90° (3 o'clock): I should be negative, J ~0
        helix_90 = lines_90[1]  # Skip G91
        assert 'I-0.5' in helix_90

        # At 0° (12 o'clock): J should be negative, I ~0
        helix_0 = lines_0[1]
        assert 'J-0.5' in helix_0


class TestTransitionFeedRate:
    """Tests that helical transition moves use 80% of cutting feed."""

    def test_circle_preamble_transition_uses_cutting_feed(self):
        """Circle subroutine preamble: arc transition should use 80% of arc feed."""
        from src.utils.subroutine_generator import generate_helical_preamble_circle

        lines = generate_helical_preamble_circle(
            helix_radius=0.1, cut_radius=0.5,
            pass_depth=0.04, helix_pitch=0.04,
            plunge_rate=8.0, feed_rate=45.0,
            approach_angle=90, arc_feed_factor=0.8
        )
        # Find the arc transition (G02 without Z, after the G90 that ends the helix)
        arc_transitions = [l for l in lines if l.startswith('G02') and 'Z' not in l]
        assert len(arc_transitions) == 1
        # Should use 90% of arc_feed (36.0 * 0.9 = 32.4)
        assert 'F28.8' in arc_transitions[0]

    def test_hexagon_preamble_transition_uses_cutting_feed(self):
        """Hexagon subroutine preamble: linear transition should use 80% of arc feed."""
        from src.utils.subroutine_generator import generate_helical_preamble_hexagon

        lines = generate_helical_preamble_hexagon(
            center_x=5.0, center_y=5.0,
            helix_radius=0.1,
            first_vertex_x=5.5, first_vertex_y=5.0,
            pass_depth=0.04, helix_pitch=0.04,
            plunge_rate=8.0, feed_rate=45.0,
            approach_angle=90, arc_feed_factor=0.8
        )
        # Last line should be G01 linear transition to vertex
        linear_transition = lines[-1]
        assert linear_transition.startswith('G01')
        # Should use 90% of arc_feed (36.0 * 0.9 = 32.4)
        assert 'F28.8' in linear_transition

    def test_helix_still_ramps_toward_cutting_feed(self):
        """Helix revolutions should still ramp toward arc_feed, not plunge_rate."""
        from src.utils.subroutine_generator import generate_helical_preamble_circle

        lines = generate_helical_preamble_circle(
            helix_radius=0.1, cut_radius=0.5,
            pass_depth=0.12, helix_pitch=0.04,
            plunge_rate=8.0, feed_rate=45.0,
            approach_angle=90, arc_feed_factor=0.8
        )
        # 3 revolutions (0.12 / 0.04), helix lines are the G02 with Z
        helix_lines = [l for l in lines if l.startswith('G02') and 'Z' in l]
        assert len(helix_lines) == 3

        # Extract feed rates from helix lines
        feeds = []
        for line in helix_lines:
            f_idx = line.index('F')
            feed_str = line[f_idx + 1:].split()[0]
            feeds.append(float(feed_str))

        # arc_feed = 45.0 * 0.8 = 36.0
        # Step 1 (25%): 8 + 0.25 * 28 = 15.0
        # Step 2 (50%): 8 + 0.50 * 28 = 22.0
        # Step 3 (75%): 8 + 0.75 * 28 = 29.0
        assert abs(feeds[0] - 15.0) < 0.1
        assert abs(feeds[1] - 22.0) < 0.1
        assert abs(feeds[2] - 29.0) < 0.1

        # Transition should use 90% of arc_feed (36.0 * 0.9 = 32.4)
        arc_transitions = [l for l in lines if l.startswith('G02') and 'Z' not in l]
        assert len(arc_transitions) == 1
        assert 'F28.8' in arc_transitions[0]


class TestStepdownValidation:
    """Tests for stepdown validation utilities."""

    def test_validate_stepdown_safe(self):
        """Test validation for safe stepdown."""
        errors, warnings = validate_stepdown(0.05, 0.125, 0.5)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_stepdown_warning(self):
        """Test validation for aggressive but allowed stepdown."""
        # 80% of tool diameter - exceeds 50% default
        errors, warnings = validate_stepdown(0.1, 0.125, 0.5)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "80%" in warnings[0]

    def test_validate_stepdown_error(self):
        """Test validation for dangerous stepdown."""
        # Exceeds tool diameter
        errors, warnings = validate_stepdown(0.15, 0.125, 0.5)
        assert len(errors) == 1
        assert "exceeds tool diameter" in errors[0]

    def test_validate_stepdown_zero_values(self):
        """Test validation with zero values."""
        errors, warnings = validate_stepdown(0, 0.125, 0.5)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_feed_rates_normal(self):
        """Test validation for normal feed rates."""
        warnings = validate_feed_rates(45.0, 8.0)
        assert len(warnings) == 0

    def test_validate_feed_rates_plunge_exceeds(self):
        """Test validation when plunge exceeds feed."""
        warnings = validate_feed_rates(45.0, 50.0)
        assert len(warnings) == 1
        assert "exceeds feed rate" in warnings[0]

    def test_validate_feed_rates_equal(self):
        """Test validation when plunge equals feed."""
        warnings = validate_feed_rates(45.0, 45.0)
        assert len(warnings) == 0


class TestArcMoveWithZ:
    """Tests for arc moves with Z parameter (helical interpolation)."""

    def test_generate_arc_move_without_z(self):
        """Test arc move generation without Z parameter."""
        arc = generate_arc_move("G02", 1.0, 0.0, -0.5, 0.0, feed=5.0)
        assert arc.startswith("G02")
        assert "X1.0000" in arc
        assert "Y0.0000" in arc
        assert "I-0.5000" in arc
        assert "J0.0000" in arc
        assert "Z" not in arc

    def test_generate_arc_move_with_z(self):
        """Test arc move generation with Z parameter for helical motion."""
        arc = generate_arc_move("G02", 1.0, 0.0, -0.5, 0.0, feed=5.0, z=-0.05)
        assert arc.startswith("G02")
        assert "X1.0000" in arc
        assert "Y0.0000" in arc
        assert "Z-0.0500" in arc
        assert "I-0.5000" in arc
        assert "J0.0000" in arc

    def test_generate_arc_move_z_position_in_output(self):
        """Test that Z appears before I/J in output."""
        arc = generate_arc_move("G03", 2.0, 1.0, -1.0, 0.5, feed=10.0, z=-0.1)
        # Z should come before I
        z_pos = arc.find("Z")
        i_pos = arc.find("I")
        assert z_pos < i_pos

    def test_generate_arc_move_ccw_with_z(self):
        """Test CCW arc with Z for helical motion."""
        arc = generate_arc_move("G03", 0.0, 1.0, -0.5, 0.0, feed=8.0, z=-0.04)
        assert arc.startswith("G03")
        assert "Z-0.0400" in arc
