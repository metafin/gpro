"""Tests for src/tube_void_checker.py module."""
import pytest
from unittest.mock import MagicMock

from src.tube_void_checker import (
    calculate_void_bounds,
    point_in_void,
    circle_in_void,
    hexagon_in_void,
    filter_drill_points,
    filter_circular_cuts,
    filter_hexagonal_cuts,
    filter_operations_for_tube
)


class TestCalculateVoidBounds:
    """Tests for calculate_void_bounds function."""

    def test_basic_bounds(self):
        """Test basic void bounds calculation."""
        bounds = calculate_void_bounds(2.0, 1.0, 0.125)
        void_x_min, void_y_min, void_x_max, void_y_max = bounds

        assert void_x_min == 0.125
        assert void_y_min == 0.125
        assert void_x_max == 1.875  # 2.0 - 0.125
        assert void_y_max == 0.875  # 1.0 - 0.125

    def test_thick_wall(self):
        """Test with thicker wall."""
        bounds = calculate_void_bounds(4.0, 2.0, 0.5)
        void_x_min, void_y_min, void_x_max, void_y_max = bounds

        assert void_x_min == 0.5
        assert void_y_min == 0.5
        assert void_x_max == 3.5
        assert void_y_max == 1.5


class TestPointInVoid:
    """Tests for point_in_void function."""

    def test_point_in_void(self):
        """Test point clearly in void."""
        bounds = (0.125, 0.125, 1.875, 0.875)  # 2x1 tube with 0.125 wall
        # Point at center (1.0, 0.5) should be in void
        assert point_in_void(1.0, 0.5, bounds) is True

    def test_point_on_wall(self):
        """Test point on wall (not in void)."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Point at (0.1, 0.5) is on the wall
        assert point_in_void(0.1, 0.5, bounds) is False

    def test_point_with_tool_radius(self):
        """Test point considering tool radius."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Point at (0.2, 0.5) with 0.1 tool radius would touch wall
        assert point_in_void(0.2, 0.5, bounds, tool_radius=0.1) is False
        # Point at (1.0, 0.5) with 0.1 tool radius is still in void
        assert point_in_void(1.0, 0.5, bounds, tool_radius=0.1) is True

    def test_point_at_void_edge(self):
        """Test point exactly at void boundary."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Point exactly at void_x_min boundary is NOT in void
        assert point_in_void(0.125, 0.5, bounds) is False


class TestCircleInVoid:
    """Tests for circle_in_void function."""

    def test_small_circle_in_void(self):
        """Test small circle entirely in void."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Small circle at center
        assert circle_in_void(1.0, 0.5, 0.2, bounds) is True

    def test_large_circle_extends_to_wall(self):
        """Test circle that extends to wall."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Circle at (1.0, 0.5) with diameter 1.5 extends to wall
        assert circle_in_void(1.0, 0.5, 1.5, bounds) is False

    def test_circle_on_wall(self):
        """Test circle on the wall area."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Circle at (0.1, 0.5) is on wall
        assert circle_in_void(0.1, 0.5, 0.1, bounds) is False


class TestHexagonInVoid:
    """Tests for hexagon_in_void function."""

    def test_small_hexagon_in_void(self):
        """Test small hexagon entirely in void."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Small hexagon at center
        assert hexagon_in_void(1.0, 0.5, 0.2, bounds) is True

    def test_large_hexagon_extends_to_wall(self):
        """Test hexagon that extends to wall."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        # Large hexagon extends to wall
        assert hexagon_in_void(1.0, 0.5, 1.0, bounds) is False


class TestFilterDrillPoints:
    """Tests for filter_drill_points function."""

    def test_filter_some_points(self):
        """Test filtering some points that are in void."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        points = [
            (0.05, 0.5),   # On wall (keep)
            (1.0, 0.5),    # In void (skip)
            (1.9, 0.5),    # On wall (keep)
            (1.0, 0.06),   # On wall (keep)
        ]
        valid, skipped = filter_drill_points(points, bounds, 0.05)

        assert len(valid) == 3
        assert len(skipped) == 1
        assert (1.0, 0.5) in skipped

    def test_filter_all_valid(self):
        """Test when all points are on wall."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        points = [(0.05, 0.5), (1.9, 0.5)]  # All on wall
        valid, skipped = filter_drill_points(points, bounds, 0.05)

        assert len(valid) == 2
        assert len(skipped) == 0

    def test_filter_empty_list(self):
        """Test with empty points list."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        valid, skipped = filter_drill_points([], bounds, 0.125)

        assert valid == []
        assert skipped == []


class TestFilterCircularCuts:
    """Tests for filter_circular_cuts function."""

    def test_filter_circles(self):
        """Test filtering circular cuts."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        cuts = [
            {'center_x': 1.0, 'center_y': 0.5, 'diameter': 0.1},  # In void
            {'center_x': 0.05, 'center_y': 0.5, 'diameter': 0.1},  # On wall
        ]
        valid, skipped = filter_circular_cuts(cuts, bounds, 0.125)

        assert len(valid) == 1
        assert len(skipped) == 1


class TestFilterHexagonalCuts:
    """Tests for filter_hexagonal_cuts function."""

    def test_filter_hexagons(self):
        """Test filtering hexagonal cuts."""
        bounds = (0.125, 0.125, 1.875, 0.875)
        cuts = [
            {'center_x': 1.0, 'center_y': 0.5, 'flat_to_flat': 0.1},  # In void
            {'center_x': 0.1, 'center_y': 0.5, 'flat_to_flat': 0.1},  # On wall
        ]
        valid, skipped = filter_hexagonal_cuts(cuts, bounds, 0.125)

        assert len(valid) == 1
        assert len(skipped) == 1


class TestFilterOperationsForTube:
    """Tests for filter_operations_for_tube function."""

    def test_filter_for_sheet_material_passthrough(self):
        """Test that sheet material passes through unchanged."""
        material = MagicMock()
        material.form = 'sheet'

        expanded_ops = {
            'drill_points': [(1.0, 1.0)],
            'circular_cuts': [{'center_x': 5.0, 'center_y': 5.0, 'diameter': 1.0}],
            'hexagonal_cuts': [],
            'line_cuts': []
        }

        result = filter_operations_for_tube(expanded_ops, material)

        # Should be unchanged for sheet
        assert result['drill_points'] == expanded_ops['drill_points']
        assert result['circular_cuts'] == expanded_ops['circular_cuts']
        assert result['skipped_drill_points'] == []

    def test_filter_for_tube_material(self):
        """Test filtering for tube material."""
        material = MagicMock()
        material.form = 'tube'
        material.outer_width = 2.0
        material.outer_height = 1.0
        material.wall_thickness = 0.125

        expanded_ops = {
            'drill_points': [
                (0.05, 0.5),   # On wall
                (1.0, 0.5),    # In void
            ],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': []
        }

        result = filter_operations_for_tube(
            expanded_ops, material,
            drill_diameter=0.125
        )

        assert len(result['drill_points']) == 1
        assert len(result['skipped_drill_points']) == 1
        assert (1.0, 0.5) in result['skipped_drill_points']

    def test_line_cuts_not_filtered(self):
        """Test that line cuts are never filtered."""
        material = MagicMock()
        material.form = 'tube'
        material.outer_width = 2.0
        material.outer_height = 1.0
        material.wall_thickness = 0.125

        line_cut = {'id': 'l1', 'points': [{'x': 1.0, 'y': 0.5}]}
        expanded_ops = {
            'drill_points': [],
            'circular_cuts': [],
            'hexagonal_cuts': [],
            'line_cuts': [line_cut]
        }

        result = filter_operations_for_tube(expanded_ops, material)

        # Line cuts should pass through
        assert result['line_cuts'] == [line_cut]
