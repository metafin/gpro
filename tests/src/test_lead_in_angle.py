"""Tests for per-operation lead-in approach angle functionality."""
import math
import pytest

from src.utils.lead_in import (
    _user_angle_to_math_angle,
    calculate_circle_lead_in_point,
    calculate_helix_start_point,
    calculate_hexagon_lead_in_point,
    calculate_line_lead_in_point,
    generate_helical_entry
)


class TestAngleConversion:
    """Tests for _user_angle_to_math_angle() function."""

    def test_angle_90_returns_zero_radians(self):
        """90° user angle (right/3 o'clock) should convert to 0 radians."""
        result = _user_angle_to_math_angle(90)
        assert abs(result - 0) < 0.0001

    def test_angle_0_returns_pi_over_2(self):
        """0° user angle (top/12 o'clock) should convert to π/2 radians."""
        result = _user_angle_to_math_angle(0)
        assert abs(result - math.pi / 2) < 0.0001

    def test_angle_180_returns_negative_pi_over_2(self):
        """180° user angle (bottom/6 o'clock) should convert to -π/2 radians."""
        result = _user_angle_to_math_angle(180)
        assert abs(result - (-math.pi / 2)) < 0.0001

    def test_angle_270_returns_negative_pi(self):
        """270° user angle (left/9 o'clock) should convert to -π radians.

        Note: -π and +π represent the same direction (left), but the math
        convention uses 90 - 270 = -180 degrees = -π radians.
        """
        result = _user_angle_to_math_angle(270)
        assert abs(result - (-math.pi)) < 0.0001

    def test_angle_45_returns_positive(self):
        """45° user angle should convert to π/4 radians (45° math)."""
        result = _user_angle_to_math_angle(45)
        assert abs(result - math.pi / 4) < 0.0001


class TestCircleLeadInPoint:
    """Tests for calculate_circle_lead_in_point() with approach angle."""

    def test_default_angle_90_matches_original_behavior(self):
        """Default 90° angle should position lead-in at 3 o'clock (positive X)."""
        cx, cy = 5.0, 5.0
        cut_radius = 1.0
        lead_in_distance = 0.25

        x, y = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance)

        # Lead-in at 90° (3 o'clock): X = cx + cut_radius + lead_in_distance
        expected_x = cx + cut_radius + lead_in_distance
        expected_y = cy

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_angle_0_positions_at_top(self):
        """0° angle should position lead-in at 12 o'clock (positive Y)."""
        cx, cy = 5.0, 5.0
        cut_radius = 1.0
        lead_in_distance = 0.25

        x, y = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance, approach_angle=0)

        # Lead-in at 0° (12 o'clock): Y = cy + cut_radius + lead_in_distance
        expected_x = cx
        expected_y = cy + cut_radius + lead_in_distance

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_angle_180_positions_at_bottom(self):
        """180° angle should position lead-in at 6 o'clock (negative Y)."""
        cx, cy = 5.0, 5.0
        cut_radius = 1.0
        lead_in_distance = 0.25

        x, y = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance, approach_angle=180)

        # Lead-in at 180° (6 o'clock): Y = cy - cut_radius - lead_in_distance
        expected_x = cx
        expected_y = cy - cut_radius - lead_in_distance

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_angle_270_positions_at_left(self):
        """270° angle should position lead-in at 9 o'clock (negative X)."""
        cx, cy = 5.0, 5.0
        cut_radius = 1.0
        lead_in_distance = 0.25

        x, y = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance, approach_angle=270)

        # Lead-in at 270° (9 o'clock): X = cx - cut_radius - lead_in_distance
        expected_x = cx - cut_radius - lead_in_distance
        expected_y = cy

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001


class TestHelixStartPoint:
    """Tests for calculate_helix_start_point() with approach angle."""

    def test_default_angle_90_matches_original_behavior(self):
        """Default 90° angle should position helix start at 3 o'clock."""
        cx, cy = 5.0, 5.0
        helix_radius = 0.5

        x, y = calculate_helix_start_point(cx, cy, helix_radius)

        expected_x = cx + helix_radius
        expected_y = cy

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_angle_0_positions_at_top(self):
        """0° angle should position helix start at 12 o'clock."""
        cx, cy = 5.0, 5.0
        helix_radius = 0.5

        x, y = calculate_helix_start_point(cx, cy, helix_radius, approach_angle=0)

        expected_x = cx
        expected_y = cy + helix_radius

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_angle_270_positions_at_left(self):
        """270° angle should position helix start at 9 o'clock."""
        cx, cy = 5.0, 5.0
        helix_radius = 0.5

        x, y = calculate_helix_start_point(cx, cy, helix_radius, approach_angle=270)

        expected_x = cx - helix_radius
        expected_y = cy

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001


class TestHexagonLeadInPoint:
    """Tests for calculate_hexagon_lead_in_point() with approach angle."""

    def test_default_uses_edge_direction(self):
        """Without approach_angle, should extend along first edge direction."""
        vertices = [
            (1.0, 0.0),  # v0
            (0.5, 0.866),  # v1 (roughly)
            (-0.5, 0.866),
            (-1.0, 0.0),
            (-0.5, -0.866),
            (0.5, -0.866)
        ]
        lead_in_distance = 0.25

        x, y = calculate_hexagon_lead_in_point(vertices, lead_in_distance)

        # Should extend backward along v0->v1 direction
        # Direction v0->v1: (-0.5, 0.866), normalized
        # Lead-in extends backward from v0
        assert x > vertices[0][0]  # Should be to the right of v0

    def test_with_approach_angle_uses_radial_method(self):
        """With approach_angle and center, should use radial method."""
        vertices = [
            (1.0, 0.0),
            (0.5, 0.866),
            (-0.5, 0.866),
            (-1.0, 0.0),
            (-0.5, -0.866),
            (0.5, -0.866)
        ]
        center = (0.0, 0.0)
        lead_in_distance = 0.25

        x, y = calculate_hexagon_lead_in_point(
            vertices, lead_in_distance,
            center=center, approach_angle=0
        )

        # At 0° (top), lead-in should be at positive Y
        assert abs(x - 0) < 0.1  # Near center X
        assert y > 0  # Positive Y direction


class TestLineLeadInPoint:
    """Tests for calculate_line_lead_in_point() with approach angle."""

    def test_default_extends_backward_along_path(self):
        """Without approach_angle, should extend backward along path direction."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'},
            {'x': 1, 'y': 1, 'line_type': 'straight'}
        ]
        lead_in_distance = 0.25

        x, y = calculate_line_lead_in_point(path, lead_in_distance)

        # Path starts going right (+X), so lead-in extends left
        expected_x = -lead_in_distance
        expected_y = 0

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_approach_angle_overrides_path_direction(self):
        """With approach_angle, should use specified direction."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 1, 'y': 0, 'line_type': 'straight'}
        ]
        lead_in_distance = 0.25

        x, y = calculate_line_lead_in_point(path, lead_in_distance, approach_angle=0)

        # At 0° (top), lead-in should be at positive Y from start point
        expected_x = 0
        expected_y = lead_in_distance

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001

    def test_approach_angle_90_positions_to_right(self):
        """90° approach angle should position lead-in to the right."""
        path = [
            {'x': 0, 'y': 0, 'line_type': 'start'},
            {'x': 0, 'y': 1, 'line_type': 'straight'}  # Path goes up
        ]
        lead_in_distance = 0.25

        x, y = calculate_line_lead_in_point(path, lead_in_distance, approach_angle=90)

        # At 90° (right), lead-in should be at positive X from start
        expected_x = lead_in_distance
        expected_y = 0

        assert abs(x - expected_x) < 0.0001
        assert abs(y - expected_y) < 0.0001


class TestHelicalLeadInGcode:
    """Tests for generate_helical_entry() with approach angle."""

    def test_default_angle_90_has_negative_i_offset(self):
        """Default 90° should produce G02 commands with negative I offset."""
        lines = generate_helical_entry(
            helix_radius=0.5,
            target_depth=0.1,
            helix_pitch=0.04,
            plunge_rate=10,
            transition_feed=10,
            center=(5.0, 5.0),
        )

        # Check that G02 commands exist with I offset
        g02_lines = [line for line in lines if line.startswith('G02')]
        assert len(g02_lines) > 0

        # At 90° angle, I offset should be negative (pointing from 3 o'clock to center)
        for line in g02_lines:
            assert 'I-0.5' in line or 'I-0.50' in line

    def test_angle_0_has_negative_j_offset(self):
        """0° angle should produce G02 commands with negative J offset."""
        lines = generate_helical_entry(
            helix_radius=0.5,
            target_depth=0.1,
            helix_pitch=0.04,
            plunge_rate=10,
            transition_feed=10,
            approach_angle=0,
            center=(5.0, 5.0),
        )

        g02_lines = [line for line in lines if line.startswith('G02')]
        assert len(g02_lines) > 0

        # At 0° angle, J offset should be negative (pointing from 12 o'clock to center)
        for line in g02_lines:
            assert 'J-0.5' in line or 'J-0.50' in line


class TestRegressionBehavior:
    """Regression tests to ensure default behavior matches original implementation."""

    def test_circle_lead_in_90_degrees_equals_original(self):
        """90° approach angle should produce same results as original hardcoded behavior."""
        cx, cy = 10.0, 10.0
        cut_radius = 2.0
        lead_in_distance = 0.5

        # With explicit 90° angle
        x1, y1 = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance, approach_angle=90)

        # Without angle (default)
        x2, y2 = calculate_circle_lead_in_point(cx, cy, cut_radius, lead_in_distance)

        assert abs(x1 - x2) < 0.0001
        assert abs(y1 - y2) < 0.0001

    def test_helix_start_90_degrees_equals_original(self):
        """90° approach angle should produce same helix start as original."""
        cx, cy = 10.0, 10.0
        helix_radius = 0.75

        # With explicit 90° angle
        x1, y1 = calculate_helix_start_point(cx, cy, helix_radius, approach_angle=90)

        # Without angle (default)
        x2, y2 = calculate_helix_start_point(cx, cy, helix_radius)

        assert abs(x1 - x2) < 0.0001
        assert abs(y1 - y2) < 0.0001
