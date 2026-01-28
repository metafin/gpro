"""Tests for src/hexagon_generator.py module."""
import pytest
import math

from src.hexagon_generator import (
    calculate_hexagon_vertices,
    calculate_compensated_vertices,
    get_hexagon_start_position,
    calculate_hexagon_bounds
)


class TestCalculateHexagonVertices:
    """Tests for calculate_hexagon_vertices function."""

    def test_vertex_count(self):
        """Test that exactly 6 vertices are returned."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)
        assert len(vertices) == 6

    def test_point_up_orientation(self):
        """Test that hexagon is point-up (top vertex on Y axis)."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)
        top_vertex = vertices[0]
        # Top vertex should have X=0 (on Y axis)
        assert abs(top_vertex[0]) < 1e-10

    def test_top_vertex_is_highest(self):
        """Test that first vertex (top) has highest Y."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)
        top_y = vertices[0][1]
        for v in vertices[1:]:
            assert v[1] <= top_y + 1e-10

    def test_bottom_vertex(self):
        """Test that bottom vertex (index 3) is on Y axis."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)
        bottom_vertex = vertices[3]
        assert abs(bottom_vertex[0]) < 1e-10

    def test_circumradius(self):
        """Test that vertices are at correct distance from center."""
        flat_to_flat = 1.0
        expected_circumradius = flat_to_flat / math.sqrt(3)
        vertices = calculate_hexagon_vertices(5.0, 5.0, flat_to_flat)

        for vx, vy in vertices:
            dist = math.sqrt((vx - 5.0)**2 + (vy - 5.0)**2)
            assert abs(dist - expected_circumradius) < 1e-10

    def test_offset_center(self):
        """Test with offset center."""
        center_x, center_y = 10.0, 7.5
        vertices = calculate_hexagon_vertices(center_x, center_y, 1.0)

        # Calculate centroid of vertices
        avg_x = sum(v[0] for v in vertices) / 6
        avg_y = sum(v[1] for v in vertices) / 6

        assert abs(avg_x - center_x) < 1e-10
        assert abs(avg_y - center_y) < 1e-10

    def test_clockwise_order(self):
        """Test vertices are in clockwise order from top."""
        vertices = calculate_hexagon_vertices(0, 0, 1.0)

        # First vertex should be top (highest Y)
        # Moving clockwise, Y should generally decrease for first 3 vertices
        assert vertices[0][1] > vertices[1][1]  # top > upper right
        assert vertices[1][1] > vertices[2][1]  # upper right > lower right
        # Then should increase for last 3
        assert vertices[3][1] < vertices[4][1]  # bottom < lower left
        assert vertices[4][1] < vertices[5][1]  # lower left < upper left


class TestCalculateCompensatedVertices:
    """Tests for calculate_compensated_vertices function."""

    def test_compensated_count(self):
        """Test that 6 compensated vertices are returned."""
        vertices = calculate_compensated_vertices(0, 0, 1.0, 0.125)
        assert len(vertices) == 6

    def test_compensated_closer_to_center(self):
        """Test that compensated vertices are closer to center."""
        center_x, center_y = 5.0, 5.0
        flat_to_flat = 1.0
        tool_diameter = 0.125

        regular = calculate_hexagon_vertices(center_x, center_y, flat_to_flat)
        compensated = calculate_compensated_vertices(center_x, center_y, flat_to_flat, tool_diameter)

        for (rx, ry), (cx, cy) in zip(regular, compensated):
            reg_dist = math.sqrt((rx - center_x)**2 + (ry - center_y)**2)
            comp_dist = math.sqrt((cx - center_x)**2 + (cy - center_y)**2)
            assert comp_dist < reg_dist

    def test_offset_amount(self):
        """Test that offset is correct for tool radius."""
        tool_diameter = 0.25
        tool_radius = 0.125
        # Expected offset = tool_radius * 2 / sqrt(3)
        expected_offset = tool_radius * 2 / math.sqrt(3)

        regular = calculate_hexagon_vertices(0, 0, 2.0)
        compensated = calculate_compensated_vertices(0, 0, 2.0, tool_diameter)

        # Check offset for top vertex
        reg_dist = math.sqrt(regular[0][0]**2 + regular[0][1]**2)
        comp_dist = math.sqrt(compensated[0][0]**2 + compensated[0][1]**2)

        actual_offset = reg_dist - comp_dist
        assert abs(actual_offset - expected_offset) < 1e-10

    def test_zero_tool_diameter(self):
        """Test with zero tool diameter (no compensation)."""
        regular = calculate_hexagon_vertices(5.0, 5.0, 1.0)
        compensated = calculate_compensated_vertices(5.0, 5.0, 1.0, 0)

        for (rx, ry), (cx, cy) in zip(regular, compensated):
            assert abs(rx - cx) < 1e-10
            assert abs(ry - cy) < 1e-10


class TestGetHexagonStartPosition:
    """Tests for get_hexagon_start_position function."""

    def test_returns_first_vertex(self):
        """Test that start position is first vertex."""
        vertices = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
        start = get_hexagon_start_position(vertices)
        assert start == (1.0, 2.0)

    def test_empty_vertices(self):
        """Test with empty vertex list."""
        start = get_hexagon_start_position([])
        assert start == (0, 0)


class TestCalculateHexagonBounds:
    """Tests for calculate_hexagon_bounds function."""

    def test_bounds_at_origin(self):
        """Test bounds for hexagon at origin."""
        flat_to_flat = 1.0
        apothem = 0.5
        circumradius = flat_to_flat / math.sqrt(3)

        min_x, min_y, max_x, max_y = calculate_hexagon_bounds(0, 0, flat_to_flat)

        assert abs(min_x - (-apothem)) < 1e-10
        assert abs(max_x - apothem) < 1e-10
        assert abs(min_y - (-circumradius)) < 1e-10
        assert abs(max_y - circumradius) < 1e-10

    def test_bounds_offset_center(self):
        """Test bounds for hexagon at offset center."""
        center_x, center_y = 5.0, 7.0
        flat_to_flat = 2.0
        apothem = 1.0
        circumradius = flat_to_flat / math.sqrt(3)

        min_x, min_y, max_x, max_y = calculate_hexagon_bounds(center_x, center_y, flat_to_flat)

        assert abs(min_x - (center_x - apothem)) < 1e-10
        assert abs(max_x - (center_x + apothem)) < 1e-10
        assert abs(min_y - (center_y - circumradius)) < 1e-10
        assert abs(max_y - (center_y + circumradius)) < 1e-10

    def test_x_extent_less_than_y_extent(self):
        """Test that X extent (apothem) is less than Y extent (circumradius) for point-up."""
        flat_to_flat = 1.0
        min_x, min_y, max_x, max_y = calculate_hexagon_bounds(0, 0, flat_to_flat)

        x_extent = max_x - min_x
        y_extent = max_y - min_y

        # For point-up hexagon, Y extent should be larger
        assert y_extent > x_extent
