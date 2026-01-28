"""
Tests for the SVG arc calculation module.

These tests verify that CNC arc specifications are correctly converted to SVG arc parameters.

Key concepts:
- CNC coordinates: Y-up (math convention)
- SVG coordinates: Y-down (screen convention)
- User specifies: center point + direction (CW/CCW)
- large_arc_flag is CALCULATED, not specified
"""

import pytest
import math
from src.utils.svg_arc import (
    calculate_svg_arc_flags,
    calculate_arc_radius,
    calculate_arc_angular_span,
    cnc_to_svg_coords,
    generate_svg_arc_command
)


class TestCalculateArcAngularSpan:
    """Tests for angular span calculation."""

    def test_quarter_arc_ccw(self):
        """90° CCW arc should have 90° span."""
        # Arc from (1, 0) to (0, 1) around origin - 90° CCW
        span = calculate_arc_angular_span(1, 0, 0, 1, 0, 0, clockwise=False)
        assert abs(span - 90) < 0.1

    def test_quarter_arc_cw(self):
        """90° CW arc should have 270° span (going the long way)."""
        # Arc from (1, 0) to (0, 1) around origin - going CW is the long way
        span = calculate_arc_angular_span(1, 0, 0, 1, 0, 0, clockwise=True)
        assert abs(span - 270) < 0.1

    def test_semicircle(self):
        """180° arc should have 180° span."""
        # Arc from (-1, 0) to (1, 0) around origin
        span = calculate_arc_angular_span(-1, 0, 1, 0, 0, 0, clockwise=False)
        assert abs(span - 180) < 0.1

    def test_small_arc_ccw(self):
        """Small CCW arc from (4,1) to (6,1) around (5,4) - about 37°."""
        span = calculate_arc_angular_span(4, 1, 6, 1, 5, 4, clockwise=False)
        assert 30 < span < 45  # Approximately 37°

    def test_large_arc_cw(self):
        """Large CW arc from (4,1) to (6,1) around (5,4) - about 323°."""
        span = calculate_arc_angular_span(4, 1, 6, 1, 5, 4, clockwise=True)
        assert 315 < span < 330  # Approximately 323°


class TestCalculateSvgArcFlags:
    """Tests for calculate_svg_arc_flags function."""

    # ============================================================
    # Test case: Arc from (4,1) to (6,1) around center (5,4)
    # The center is ABOVE the chord connecting the two points.
    # CCW takes the SHORT path (~37°), CW takes the LONG path (~323°)
    # ============================================================

    def test_ccw_short_arc_center_above(self):
        """
        CCW arc from (4,1) to (6,1) with center at (5,4).
        CCW from start to end is the SHORT path (~37°).
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=4, start_y=1,
            end_x=6, end_y=1,
            center_x=5, center_y=4,
            arc_direction='ccw'
        )
        # CCW in CNC = sweep=0 in SVG (same visual direction after Y flip)
        assert sweep == 0, "CCW in CNC should map to sweep=0 in SVG"
        # Short arc (<180°) = large_arc_flag=0
        assert large_arc == 0, "CCW is the short arc (~37°), so large_arc=0"

    def test_cw_long_arc_center_above(self):
        """
        CW arc from (4,1) to (6,1) with center at (5,4).
        CW from start to end is the LONG path (~323°).
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=4, start_y=1,
            end_x=6, end_y=1,
            center_x=5, center_y=4,
            arc_direction='cw'
        )
        # CW in CNC = sweep=1 in SVG
        assert sweep == 1, "CW in CNC should map to sweep=1 in SVG"
        # Long arc (>180°) = large_arc_flag=1
        assert large_arc == 1, "CW is the long arc (~323°), so large_arc=1"

    def test_auto_detect_takes_short_path(self):
        """
        Auto-detect should choose the shorter arc.
        For (4,1) to (6,1) around (5,4), CCW is shorter.
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=4, start_y=1,
            end_x=6, end_y=1,
            center_x=5, center_y=4,
            arc_direction=None
        )
        # Short path is CCW in CNC = sweep=0 in SVG
        assert sweep == 0, "Auto-detect should choose CCW (short path) = sweep=0"
        assert large_arc == 0, "Short path should have large_arc_flag=0"

    # ============================================================
    # Rounded rectangle corners (from Base Plate Cut Real)
    # All corners are 90° CCW arcs (quarter circles)
    # ============================================================

    def test_ccw_quarter_arc_bottom_right_corner(self):
        """
        Bottom-right corner: (11.975, 0) to (12.225, 0.25) around (11.975, 0.25).
        90° CCW arc.
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=11.975, start_y=0,
            end_x=12.225, end_y=0.25,
            center_x=11.975, center_y=0.25,
            arc_direction='ccw'
        )
        assert sweep == 0, "CCW in CNC = sweep=0 in SVG"
        assert large_arc == 0, "90° arc is less than 180°"

    def test_ccw_quarter_arc_top_right_corner(self):
        """
        Top-right corner: (12.225, 29.75) to (11.975, 30) around (11.975, 29.75).
        90° CCW arc.
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=12.225, start_y=29.75,
            end_x=11.975, end_y=30,
            center_x=11.975, center_y=29.75,
            arc_direction='ccw'
        )
        assert sweep == 0, "CCW in CNC = sweep=0 in SVG"
        assert large_arc == 0, "90° arc is less than 180°"

    def test_ccw_quarter_arc_top_left_corner(self):
        """
        Top-left corner: (0.25, 30) to (0, 29.75) around (0.25, 29.75).
        90° CCW arc.
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=0.25, start_y=30,
            end_x=0, end_y=29.75,
            center_x=0.25, center_y=29.75,
            arc_direction='ccw'
        )
        assert sweep == 0, "CCW in CNC = sweep=0 in SVG"
        assert large_arc == 0, "90° arc is less than 180°"

    def test_ccw_quarter_arc_bottom_left_corner(self):
        """
        Bottom-left corner: (0, 0.25) to (0.25, 0) around (0.25, 0.25).
        90° CCW arc.
        """
        large_arc, sweep = calculate_svg_arc_flags(
            start_x=0, start_y=0.25,
            end_x=0.25, end_y=0,
            center_x=0.25, center_y=0.25,
            arc_direction='ccw'
        )
        assert sweep == 0, "CCW in CNC = sweep=0 in SVG"
        assert large_arc == 0, "90° arc is less than 180°"

    # ============================================================
    # Direction consistency tests
    # ============================================================

    def test_ccw_always_maps_to_sweep_0(self):
        """CCW in CNC should always map to sweep=0 in SVG."""
        test_cases = [
            (0, 0, 1, 0, 0.5, 0.5),
            (1, 0, 1, 1, 0.5, 0.5),
            (0, 1, 0, 0, 0.5, 0.5),
            (1, 1, 0, 1, 0.5, 0.5),
        ]
        for sx, sy, ex, ey, cx, cy in test_cases:
            _, sweep = calculate_svg_arc_flags(sx, sy, ex, ey, cx, cy, 'ccw')
            assert sweep == 0, f"CCW should always give sweep=0"

    def test_cw_always_maps_to_sweep_1(self):
        """CW in CNC should always map to sweep=1 in SVG."""
        test_cases = [
            (0, 0, 1, 0, 0.5, 0.5),
            (1, 0, 1, 1, 0.5, 0.5),
            (0, 1, 0, 0, 0.5, 0.5),
            (1, 1, 0, 1, 0.5, 0.5),
        ]
        for sx, sy, ex, ey, cx, cy in test_cases:
            _, sweep = calculate_svg_arc_flags(sx, sy, ex, ey, cx, cy, 'cw')
            assert sweep == 1, f"CW should always give sweep=1"

    # ============================================================
    # large_arc_flag tests (derived from geometry)
    # ============================================================

    def test_quarter_arc_small_arc_flag(self):
        """90° arc should have large_arc_flag=0."""
        large_arc, _ = calculate_svg_arc_flags(1, 0, 0, 1, 0, 0, 'ccw')
        assert large_arc == 0

    def test_three_quarter_arc_large_arc_flag(self):
        """270° arc should have large_arc_flag=1."""
        # Going CW from (1,0) to (0,1) around origin is 270°
        large_arc, _ = calculate_svg_arc_flags(1, 0, 0, 1, 0, 0, 'cw')
        assert large_arc == 1

    def test_semicircle_edge_case(self):
        """180° arc is the boundary - should be large_arc_flag=0."""
        large_arc, _ = calculate_svg_arc_flags(-1, 0, 1, 0, 0, 0, 'ccw')
        assert large_arc == 0  # 180° is not > 180°

    # ============================================================
    # Edge cases
    # ============================================================

    def test_direction_case_insensitive(self):
        """Arc direction should be case insensitive."""
        for direction in ['CCW', 'Ccw', 'ccw']:
            _, sweep = calculate_svg_arc_flags(0, 0, 1, 1, 0.5, 0.5, direction)
            assert sweep == 0

        for direction in ['CW', 'Cw', 'cw']:
            _, sweep = calculate_svg_arc_flags(0, 0, 1, 1, 0.5, 0.5, direction)
            assert sweep == 1

    def test_empty_direction_uses_auto_detect(self):
        """Empty string should auto-detect."""
        result1 = calculate_svg_arc_flags(0, 0, 1, 1, 0.5, 0.5, '')
        result2 = calculate_svg_arc_flags(0, 0, 1, 1, 0.5, 0.5, None)
        assert result1 == result2


class TestCalculateArcRadius:
    """Tests for calculate_arc_radius function."""

    def test_unit_radius(self):
        radius = calculate_arc_radius(1, 0, 0, 0)
        assert abs(radius - 1.0) < 0.0001

    def test_quarter_inch_radius(self):
        radius = calculate_arc_radius(11.975, 0, 11.975, 0.25)
        assert abs(radius - 0.25) < 0.0001

    def test_pythagorean_radius(self):
        radius = calculate_arc_radius(3, 4, 0, 0)
        assert abs(radius - 5.0) < 0.0001


class TestCncToSvgCoords:
    """Tests for coordinate conversion."""

    def test_y_inversion(self):
        svg_x, svg_y = cnc_to_svg_coords(0, 0, height=100)
        assert svg_x == 0
        assert svg_y == 100

        svg_x, svg_y = cnc_to_svg_coords(0, 100, height=100)
        assert svg_x == 0
        assert svg_y == 0

    def test_with_scale_and_padding(self):
        svg_x, svg_y = cnc_to_svg_coords(5, 10, height=100, scale=2.0, padding=50)
        assert svg_x == 60   # 50 + 5*2
        assert svg_y == 230  # 50 + (100-10)*2


class TestGenerateSvgArcCommand:
    """Tests for SVG arc command generation."""

    def test_generates_valid_command(self):
        cmd = generate_svg_arc_command(
            start_x=0, start_y=0,
            end_x=1, end_y=1,
            center_x=0.5, center_y=0.5,
            arc_direction='ccw',
            height=10, scale=1, padding=0
        )
        assert cmd.startswith('A ')
        parts = cmd.split()
        assert len(parts) == 8

    def test_quarter_arc_flags(self):
        """Quarter arc should have correct flags."""
        cmd = generate_svg_arc_command(
            start_x=11.975, start_y=0,
            end_x=12.225, end_y=0.25,
            center_x=11.975, center_y=0.25,
            arc_direction='ccw',
            height=30, scale=10, padding=5
        )
        parts = cmd.split()
        assert parts[4] == '0', "Quarter arc: large_arc=0"
        assert parts[5] == '0', "CCW in CNC: sweep=0"


class TestRoundedRectangleIntegration:
    """Integration test with all four corners."""

    def test_all_ccw_corners_consistent(self):
        """All CCW quarter-circle corners should have sweep=0, large_arc=0."""
        corners = [
            (11.975, 0, 12.225, 0.25, 11.975, 0.25),
            (12.225, 29.75, 11.975, 30, 11.975, 29.75),
            (0.25, 30, 0, 29.75, 0.25, 29.75),
            (0, 0.25, 0.25, 0, 0.25, 0.25),
        ]
        for i, (sx, sy, ex, ey, cx, cy) in enumerate(corners):
            large_arc, sweep = calculate_svg_arc_flags(sx, sy, ex, ey, cx, cy, 'ccw')
            assert sweep == 0, f"Corner {i+1}: CCW should give sweep=0"
            assert large_arc == 0, f"Corner {i+1}: 90° arc should give large_arc=0"
