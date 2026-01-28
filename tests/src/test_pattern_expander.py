"""Tests for src/pattern_expander.py module."""
import pytest

from src.pattern_expander import (
    expand_linear_pattern,
    expand_grid_pattern,
    expand_drill_operations,
    expand_circular_operations,
    expand_hexagonal_operations,
    expand_all_operations
)


class TestExpandLinearPattern:
    """Tests for expand_linear_pattern function."""

    def test_expand_x_axis(self):
        """Test linear pattern along X axis."""
        points = expand_linear_pattern(1.0, 2.0, 'x', 0.5, 3)
        assert len(points) == 3
        assert points[0] == (1.0, 2.0)
        assert points[1] == (1.5, 2.0)
        assert points[2] == (2.0, 2.0)

    def test_expand_y_axis(self):
        """Test linear pattern along Y axis."""
        points = expand_linear_pattern(1.0, 2.0, 'y', 0.5, 3)
        assert len(points) == 3
        assert points[0] == (1.0, 2.0)
        assert points[1] == (1.0, 2.5)
        assert points[2] == (1.0, 3.0)

    def test_expand_single_point(self):
        """Test pattern with count=1."""
        points = expand_linear_pattern(1.0, 2.0, 'x', 0.5, 1)
        assert len(points) == 1
        assert points[0] == (1.0, 2.0)

    def test_expand_case_insensitive_axis(self):
        """Test that axis is case insensitive."""
        points_lower = expand_linear_pattern(0, 0, 'x', 1.0, 2)
        points_upper = expand_linear_pattern(0, 0, 'X', 1.0, 2)
        assert points_lower == points_upper

    def test_expand_zero_spacing(self):
        """Test pattern with zero spacing."""
        points = expand_linear_pattern(1.0, 2.0, 'x', 0, 3)
        assert len(points) == 3
        assert all(p == (1.0, 2.0) for p in points)

    def test_expand_negative_spacing(self):
        """Test pattern with negative spacing."""
        points = expand_linear_pattern(2.0, 2.0, 'x', -0.5, 3)
        assert points[0] == (2.0, 2.0)
        assert points[1] == (1.5, 2.0)
        assert points[2] == (1.0, 2.0)


class TestExpandGridPattern:
    """Tests for expand_grid_pattern function."""

    def test_expand_2x2_grid(self):
        """Test 2x2 grid expansion."""
        points = expand_grid_pattern(1.0, 1.0, 1.0, 1.0, 2, 2)
        assert len(points) == 4
        # Should be row-major order
        assert points[0] == (1.0, 1.0)
        assert points[1] == (2.0, 1.0)
        assert points[2] == (1.0, 2.0)
        assert points[3] == (2.0, 2.0)

    def test_expand_3x2_grid(self):
        """Test 3x2 grid expansion."""
        points = expand_grid_pattern(0, 0, 0.5, 0.5, 3, 2)
        assert len(points) == 6
        # First row
        assert points[0] == (0, 0)
        assert points[1] == (0.5, 0)
        assert points[2] == (1.0, 0)
        # Second row
        assert points[3] == (0, 0.5)
        assert points[4] == (0.5, 0.5)
        assert points[5] == (1.0, 0.5)

    def test_expand_1x1_grid(self):
        """Test single point grid."""
        points = expand_grid_pattern(5.0, 5.0, 1.0, 1.0, 1, 1)
        assert len(points) == 1
        assert points[0] == (5.0, 5.0)


class TestExpandDrillOperations:
    """Tests for expand_drill_operations function."""

    def test_expand_single_holes(self):
        """Test expanding single drill holes."""
        operations = [
            {'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 2.0},
            {'id': 'h2', 'type': 'single', 'x': 3.0, 'y': 4.0}
        ]
        points = expand_drill_operations(operations)
        assert len(points) == 2
        assert points[0] == (1.0, 2.0)
        assert points[1] == (3.0, 4.0)

    def test_expand_linear_pattern(self):
        """Test expanding linear drill pattern."""
        operations = [
            {'id': 'p1', 'type': 'pattern_linear', 'start_x': 1.0, 'start_y': 1.0,
             'axis': 'x', 'spacing': 0.5, 'count': 4}
        ]
        points = expand_drill_operations(operations)
        assert len(points) == 4
        assert points[0] == (1.0, 1.0)
        assert points[3] == (2.5, 1.0)

    def test_expand_grid_pattern(self):
        """Test expanding grid drill pattern."""
        operations = [
            {'id': 'g1', 'type': 'pattern_grid', 'start_x': 0, 'start_y': 0,
             'x_spacing': 1.0, 'y_spacing': 1.0, 'x_count': 2, 'y_count': 3}
        ]
        points = expand_drill_operations(operations)
        assert len(points) == 6

    def test_expand_mixed_operations(self):
        """Test expanding mix of single and patterns."""
        operations = [
            {'id': 'h1', 'type': 'single', 'x': 0, 'y': 0},
            {'id': 'p1', 'type': 'pattern_linear', 'start_x': 1.0, 'start_y': 0,
             'axis': 'x', 'spacing': 0.5, 'count': 3}
        ]
        points = expand_drill_operations(operations)
        assert len(points) == 4  # 1 single + 3 from pattern

    def test_expand_empty_operations(self):
        """Test with empty operations list."""
        points = expand_drill_operations([])
        assert points == []


class TestExpandCircularOperations:
    """Tests for expand_circular_operations function."""

    def test_expand_single_circle(self):
        """Test expanding single circular cut."""
        operations = [
            {'id': 'c1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}
        ]
        circles = expand_circular_operations(operations)
        assert len(circles) == 1
        assert circles[0]['center_x'] == 5.0
        assert circles[0]['center_y'] == 5.0
        assert circles[0]['diameter'] == 1.0

    def test_expand_circular_linear_pattern(self):
        """Test expanding circular linear pattern."""
        operations = [
            {'id': 'cp1', 'type': 'pattern_linear', 'start_center_x': 2.0, 'start_center_y': 5.0,
             'diameter': 0.5, 'axis': 'x', 'spacing': 2.0, 'count': 3}
        ]
        circles = expand_circular_operations(operations)
        assert len(circles) == 3
        assert circles[0]['center_x'] == 2.0
        assert circles[1]['center_x'] == 4.0
        assert circles[2]['center_x'] == 6.0
        assert all(c['diameter'] == 0.5 for c in circles)


class TestExpandHexagonalOperations:
    """Tests for expand_hexagonal_operations function."""

    def test_expand_single_hexagon(self):
        """Test expanding single hexagonal cut."""
        operations = [
            {'id': 'h1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'flat_to_flat': 0.75}
        ]
        hexes = expand_hexagonal_operations(operations)
        assert len(hexes) == 1
        assert hexes[0]['center_x'] == 5.0
        assert hexes[0]['flat_to_flat'] == 0.75

    def test_expand_hexagonal_linear_pattern(self):
        """Test expanding hexagonal linear pattern."""
        operations = [
            {'id': 'hp1', 'type': 'pattern_linear', 'start_center_x': 1.0, 'start_center_y': 1.0,
             'flat_to_flat': 0.5, 'axis': 'y', 'spacing': 1.5, 'count': 3}
        ]
        hexes = expand_hexagonal_operations(operations)
        assert len(hexes) == 3
        assert hexes[0]['center_y'] == 1.0
        assert hexes[1]['center_y'] == 2.5
        assert hexes[2]['center_y'] == 4.0


class TestExpandAllOperations:
    """Tests for expand_all_operations function."""

    def test_expand_all_operation_types(self):
        """Test expanding all operation types at once."""
        operations = {
            'drill_holes': [
                {'id': 'h1', 'type': 'single', 'x': 1.0, 'y': 1.0}
            ],
            'circular_cuts': [
                {'id': 'c1', 'type': 'single', 'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}
            ],
            'hexagonal_cuts': [
                {'id': 'hex1', 'type': 'single', 'center_x': 8.0, 'center_y': 8.0, 'flat_to_flat': 0.5}
            ],
            'line_cuts': [
                {'id': 'l1', 'points': [{'x': 0, 'y': 0}, {'x': 1, 'y': 1}]}
            ]
        }
        result = expand_all_operations(operations)

        assert 'drill_points' in result
        assert 'circular_cuts' in result
        assert 'hexagonal_cuts' in result
        assert 'line_cuts' in result

        assert len(result['drill_points']) == 1
        assert len(result['circular_cuts']) == 1
        assert len(result['hexagonal_cuts']) == 1
        assert len(result['line_cuts']) == 1

    def test_expand_all_empty(self):
        """Test with empty operations."""
        operations = {
            'drill_holes': [],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': []
        }
        result = expand_all_operations(operations)
        assert result['drill_points'] == []
        assert result['circular_cuts'] == []
        assert result['hexagonal_cuts'] == []
        assert result['line_cuts'] == []

    def test_line_cuts_passthrough(self):
        """Test that line cuts are passed through unchanged."""
        line_cut = {
            'id': 'l1',
            'points': [
                {'x': 0, 'y': 0, 'line_type': 'start'},
                {'x': 1, 'y': 0, 'line_type': 'straight'},
                {'x': 1, 'y': 1, 'line_type': 'arc', 'arc_center_x': 0.5, 'arc_center_y': 0.5}
            ]
        }
        operations = {
            'drill_holes': [],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': [line_cut]
        }
        result = expand_all_operations(operations)
        assert result['line_cuts'] == [line_cut]
