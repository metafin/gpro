"""SVG preview generation service for toolpath visualization."""
import math
from typing import Dict, List, Optional, Tuple

from src.utils.tool_compensation import (
    calculate_cut_radius,
    calculate_hexagon_compensated_vertices,
    compensate_line_path
)
from src.utils.lead_in import calculate_line_lead_in_point, is_closed_path
from src.utils.svg_arc import calculate_svg_arc_flags, calculate_arc_radius


# Color palette for different operation types
class Colors:
    """SVG color constants for preview elements."""
    # Operation colors
    DRILL = '#2F055A'        # Purple
    CIRCLE = '#5a7a8a'       # Teal
    HEXAGON = '#c9a87c'      # Amber
    LINE = '#5a8a6e'         # Green
    LEAD_IN = '#ff8c00'      # Orange
    LEAD_IN_STROKE = '#cc7000'  # Darker orange for stroke

    # Background/grid colors
    BACKGROUND = '#f8f9fa'   # Off-white
    GRID = '#e9ecef'         # Light gray
    MATERIAL_OUTLINE = '#dee2e6'  # Gray
    TUBE_VOID_FILL = '#e9ecef'    # Light gray
    TUBE_VOID_STROKE = '#ced4da'  # Medium gray
    AXIS_LABEL = '#6c757d'   # Dark gray


class PreviewService:
    """Service for generating SVG previews of toolpaths."""

    # SVG rendering constants
    PADDING = 20
    SCALE = 50  # pixels per inch

    @staticmethod
    def generate_svg(
        width: float,
        height: float,
        drill_points: List,
        circular_cuts: List,
        hexagonal_cuts: List,
        line_cuts: List,
        wall_thickness: Optional[float] = None,
        tool_diameter: Optional[float] = None,
        coords_mode: str = 'off',
        lead_in_settings: Optional[Dict] = None
    ) -> str:
        """
        Generate SVG markup for toolpath preview.

        Args:
            width: Material width in inches
            height: Material height in inches
            drill_points: List of (x, y) drill coordinates
            circular_cuts: List of circular cut dicts
            hexagonal_cuts: List of hexagonal cut dicts
            line_cuts: List of line cut dicts
            wall_thickness: Tube wall thickness (for void display)
            tool_diameter: Tool diameter for compensation preview
            coords_mode: 'off', 'feature', or 'toolpath'
            lead_in_settings: Dict with 'type' and 'distance' for lead-in preview

        Returns:
            Complete SVG markup string
        """
        padding = PreviewService.PADDING
        scale = PreviewService.SCALE

        svg_width = width * scale + padding * 2
        svg_height = height * scale + padding * 2

        svg_parts = []
        coord_labels = []
        seq_num = 1

        # SVG header
        svg_parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" '
            f'width="{svg_width}" height="{svg_height}" style="background: {Colors.BACKGROUND};">'
        )

        # Draw background elements
        PreviewService._draw_material_outline(svg_parts, width, height, padding, scale)
        if wall_thickness:
            PreviewService._draw_tube_void(svg_parts, width, height, wall_thickness, padding, scale)
        PreviewService._draw_grid(svg_parts, width, height, padding, scale)
        PreviewService._draw_axis_labels(svg_parts, width, height, padding, scale)

        # Draw operations
        seq_num = PreviewService._draw_drill_points(
            svg_parts, coord_labels, drill_points, height, padding, scale, coords_mode, seq_num
        )
        seq_num = PreviewService._draw_circular_cuts(
            svg_parts, coord_labels, circular_cuts, height, padding, scale,
            tool_diameter, coords_mode, seq_num
        )
        seq_num = PreviewService._draw_hexagonal_cuts(
            svg_parts, coord_labels, hexagonal_cuts, height, padding, scale,
            tool_diameter, coords_mode, seq_num
        )
        seq_num = PreviewService._draw_line_cuts(
            svg_parts, coord_labels, line_cuts, height, padding, scale,
            tool_diameter, coords_mode, lead_in_settings, seq_num
        )

        # Draw coordinate labels on top
        for cx, cy, text, color in coord_labels:
            svg_parts.append(
                f'<text x="{cx}" y="{cy}" font-size="10" fill="{color}" '
                f'font-family="Arial, sans-serif">{text}</text>'
            )

        svg_parts.append('</svg>')
        return ''.join(svg_parts)

    @staticmethod
    def _draw_material_outline(
        svg_parts: List[str],
        width: float,
        height: float,
        padding: float,
        scale: float
    ) -> None:
        """Draw material outline rectangle."""
        svg_parts.append(
            f'<rect x="{padding}" y="{padding}" width="{width * scale}" height="{height * scale}" '
            f'fill="none" stroke="{Colors.MATERIAL_OUTLINE}" stroke-width="2"/>'
        )

    @staticmethod
    def _draw_tube_void(
        svg_parts: List[str],
        width: float,
        height: float,
        wall_thickness: float,
        padding: float,
        scale: float
    ) -> None:
        """Draw tube void rectangle for hollow tube materials."""
        wall = wall_thickness * scale
        inner_x = padding + wall
        inner_y = padding + wall
        inner_w = width * scale - wall * 2
        inner_h = height * scale - wall * 2
        if inner_w > 0 and inner_h > 0:
            svg_parts.append(
                f'<rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}" '
                f'fill="{Colors.TUBE_VOID_FILL}" stroke="{Colors.TUBE_VOID_STROKE}" '
                f'stroke-width="1" stroke-dasharray="4,4"/>'
            )

    @staticmethod
    def _draw_grid(
        svg_parts: List[str],
        width: float,
        height: float,
        padding: float,
        scale: float
    ) -> None:
        """Draw grid lines."""
        for x in range(int(width) + 1):
            px = padding + x * scale
            svg_parts.append(
                f'<line x1="{px}" y1="{padding}" x2="{px}" y2="{padding + height * scale}" '
                f'stroke="{Colors.GRID}" stroke-width="1"/>'
            )
        for y in range(int(height) + 1):
            py = padding + y * scale
            svg_parts.append(
                f'<line x1="{padding}" y1="{py}" x2="{padding + width * scale}" y2="{py}" '
                f'stroke="{Colors.GRID}" stroke-width="1"/>'
            )

    @staticmethod
    def _draw_axis_labels(
        svg_parts: List[str],
        width: float,
        height: float,
        padding: float,
        scale: float
    ) -> None:
        """Draw axis labels at 5-unit intervals."""
        label_interval = 5
        for x in range(0, int(width) + 1, label_interval):
            px = padding + x * scale
            svg_parts.append(
                f'<text x="{px}" y="{padding + height * scale + 15}" font-size="13" '
                f'fill="{Colors.AXIS_LABEL}" text-anchor="middle" font-family="Arial, sans-serif">{x}</text>'
            )
        for y in range(0, int(height) + 1, label_interval):
            py = padding + (height - y) * scale
            svg_parts.append(
                f'<text x="{padding - 5}" y="{py + 4}" font-size="13" '
                f'fill="{Colors.AXIS_LABEL}" text-anchor="end" font-family="Arial, sans-serif">{y}</text>'
            )

    @staticmethod
    def _draw_drill_points(
        svg_parts: List[str],
        coord_labels: List,
        drill_points: List,
        height: float,
        padding: float,
        scale: float,
        coords_mode: str,
        seq_num: int
    ) -> int:
        """Draw drill points as purple circles."""
        for x, y in drill_points:
            cx = padding + x * scale
            cy = padding + (height - y) * scale
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="4" fill="{Colors.DRILL}"/>'
            )
            svg_parts.append(
                f'<text x="{cx + 8}" y="{cy - 8}" font-size="14" font-weight="bold" '
                f'fill="{Colors.DRILL}" font-family="Arial, sans-serif">{seq_num}</text>'
            )
            if coords_mode != 'off':
                coord_labels.append((cx + 8, cy + 14, f'({x:.3f}, {y:.3f})', Colors.DRILL))
            seq_num += 1
        return seq_num

    @staticmethod
    def _draw_circular_cuts(
        svg_parts: List[str],
        coord_labels: List,
        circular_cuts: List,
        height: float,
        padding: float,
        scale: float,
        tool_diameter: Optional[float],
        coords_mode: str,
        seq_num: int
    ) -> int:
        """Draw circular cuts as teal circles."""
        for c in circular_cuts:
            cx = padding + c['center_x'] * scale
            cy = padding + (height - c['center_y']) * scale
            r = (c['diameter'] / 2) * scale
            compensation = c.get('compensation', 'none')

            # Feature geometry
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{Colors.CIRCLE}" stroke-width="2"/>'
            )

            # Compensated toolpath
            comp_radius = None
            if tool_diameter and compensation != 'none':
                comp_radius = calculate_cut_radius(c['diameter'], tool_diameter, compensation)
                comp_r = comp_radius * scale
                if comp_r > 0:
                    svg_parts.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{comp_r}" fill="none" stroke="{Colors.CIRCLE}" '
                        f'stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>'
                    )

            # Sequence number
            svg_parts.append(
                f'<text x="{cx}" y="{cy + 5}" font-size="16" font-weight="bold" '
                f'fill="{Colors.CIRCLE}" text-anchor="middle" font-family="Arial, sans-serif">{seq_num}</text>'
            )

            # Coordinate labels
            if coords_mode == 'feature':
                coord_labels.append((cx, cy + r + 14, f'({c["center_x"]:.3f}, {c["center_y"]:.3f}) d={c["diameter"]:.3f}', Colors.CIRCLE))
            elif coords_mode == 'toolpath':
                if comp_radius is not None:
                    coord_labels.append((cx, cy + r + 14, f'({c["center_x"]:.3f}, {c["center_y"]:.3f}) r={comp_radius:.3f}', Colors.CIRCLE))
                else:
                    coord_labels.append((cx, cy + r + 14, f'({c["center_x"]:.3f}, {c["center_y"]:.3f}) r={c["diameter"]/2:.3f}', Colors.CIRCLE))
            seq_num += 1
        return seq_num

    @staticmethod
    def _draw_hexagonal_cuts(
        svg_parts: List[str],
        coord_labels: List,
        hexagonal_cuts: List,
        height: float,
        padding: float,
        scale: float,
        tool_diameter: Optional[float],
        coords_mode: str,
        seq_num: int
    ) -> int:
        """Draw hexagonal cuts as amber hexagons."""
        for h in hexagonal_cuts:
            cx = padding + h['center_x'] * scale
            cy = padding + (height - h['center_y']) * scale
            ftf = h['flat_to_flat'] * scale / 2
            circumradius = ftf / math.cos(math.pi / 6)
            compensation = h.get('compensation', 'none')

            # Feature geometry
            points = []
            for i in range(6):
                angle = math.pi / 2 - i * math.pi / 3
                px = cx + circumradius * math.cos(angle)
                py = cy - circumradius * math.sin(angle)
                points.append(f"{px},{py}")
            svg_parts.append(
                f'<polygon points="{" ".join(points)}" fill="none" stroke="{Colors.HEXAGON}" stroke-width="2"/>'
            )

            # Compensated toolpath
            comp_vertices = None
            if tool_diameter and compensation != 'none':
                comp_vertices = calculate_hexagon_compensated_vertices(
                    h['center_x'], h['center_y'], h['flat_to_flat'],
                    tool_diameter, compensation
                )
                comp_points = []
                for vx, vy in comp_vertices:
                    svg_vx = padding + vx * scale
                    svg_vy = padding + (height - vy) * scale
                    comp_points.append(f"{svg_vx},{svg_vy}")
                svg_parts.append(
                    f'<polygon points="{" ".join(comp_points)}" fill="none" stroke="{Colors.HEXAGON}" '
                    f'stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>'
                )

            # Sequence number
            svg_parts.append(
                f'<text x="{cx}" y="{cy + 5}" font-size="16" font-weight="bold" '
                f'fill="{Colors.HEXAGON}" text-anchor="middle" font-family="Arial, sans-serif">{seq_num}</text>'
            )

            # Coordinate labels
            if coords_mode == 'feature':
                coord_labels.append((cx, cy + circumradius + 14, f'({h["center_x"]:.3f}, {h["center_y"]:.3f}) ftf={h["flat_to_flat"]:.3f}', Colors.HEXAGON))
            elif coords_mode == 'toolpath':
                if comp_vertices is not None:
                    comp_apothem = math.sqrt((comp_vertices[0][0] - h['center_x'])**2 + (comp_vertices[0][1] - h['center_y'])**2) * math.cos(math.pi / 6)
                    comp_ftf = comp_apothem * 2
                    coord_labels.append((cx, cy + circumradius + 14, f'({h["center_x"]:.3f}, {h["center_y"]:.3f}) ftf={comp_ftf:.3f}', Colors.HEXAGON))
                else:
                    coord_labels.append((cx, cy + circumradius + 14, f'({h["center_x"]:.3f}, {h["center_y"]:.3f}) ftf={h["flat_to_flat"]:.3f}', Colors.HEXAGON))
            seq_num += 1
        return seq_num

    @staticmethod
    def _points_to_svg_path(
        points_list: List[Dict],
        padding: float,
        scale: float,
        height: float
    ) -> str:
        """Convert a list of point dicts to SVG path string."""
        path_parts = []
        prev_px, prev_py = None, None

        for i, p in enumerate(points_list):
            px = padding + p['x'] * scale
            py = padding + (height - p['y']) * scale

            if i == 0:
                path_parts.append(f"M {px} {py}")
            else:
                line_type = p.get('line_type', 'straight')

                if line_type == 'arc' and 'arc_center_x' in p and 'arc_center_y' in p:
                    prev_cnc_x = points_list[i - 1]['x']
                    prev_cnc_y = points_list[i - 1]['y']

                    large_arc_flag, sweep_flag = calculate_svg_arc_flags(
                        start_x=prev_cnc_x, start_y=prev_cnc_y,
                        end_x=p['x'], end_y=p['y'],
                        center_x=p['arc_center_x'], center_y=p['arc_center_y'],
                        arc_direction=p.get('arc_direction')
                    )

                    arc_cx = padding + p['arc_center_x'] * scale
                    arc_cy = padding + (height - p['arc_center_y']) * scale
                    radius = calculate_arc_radius(prev_px, prev_py, arc_cx, arc_cy)

                    path_parts.append(
                        f"A {radius:.4f} {radius:.4f} 0 {large_arc_flag} {sweep_flag} {px:.4f} {py:.4f}"
                    )
                else:
                    path_parts.append(f"L {px} {py}")

            prev_px, prev_py = px, py

        # Auto-detect closed path
        if len(points_list) > 2:
            first_pt = points_list[0]
            last_pt = points_list[-1]
            is_closed = (
                abs(first_pt['x'] - last_pt['x']) < 0.0001 and
                abs(first_pt['y'] - last_pt['y']) < 0.0001
            )
            if is_closed:
                path_parts.append("Z")

        return " ".join(path_parts)

    @staticmethod
    def _draw_lead_in(
        svg_parts: List[str],
        lead_in_x: float,
        lead_in_y: float,
        start_x: float,
        start_y: float,
        height: float,
        padding: float,
        scale: float
    ) -> None:
        """Draw lead-in line and start point marker."""
        # Convert to SVG coordinates
        svg_lead_in_x = padding + lead_in_x * scale
        svg_lead_in_y = padding + (height - lead_in_y) * scale
        svg_start_x = padding + start_x * scale
        svg_start_y = padding + (height - start_y) * scale

        # Lead-in line (dashed orange)
        svg_parts.append(
            f'<line x1="{svg_lead_in_x}" y1="{svg_lead_in_y}" '
            f'x2="{svg_start_x}" y2="{svg_start_y}" '
            f'stroke="{Colors.LEAD_IN}" stroke-width="2" stroke-dasharray="3,2"/>'
        )
        # Lead-in start point (orange circle)
        svg_parts.append(
            f'<circle cx="{svg_lead_in_x}" cy="{svg_lead_in_y}" r="4" '
            f'fill="{Colors.LEAD_IN}" stroke="{Colors.LEAD_IN_STROKE}" stroke-width="1"/>'
        )

    @staticmethod
    def _draw_line_cuts(
        svg_parts: List[str],
        coord_labels: List,
        line_cuts: List,
        height: float,
        padding: float,
        scale: float,
        tool_diameter: Optional[float],
        coords_mode: str,
        lead_in_settings: Optional[Dict],
        seq_num: int
    ) -> int:
        """Draw line cuts as green paths with optional lead-in."""
        for lc in line_cuts:
            if not lc.get('points'):
                continue

            points = lc['points']
            compensation = lc.get('compensation', 'none')

            # Calculate centroid for label placement
            sum_x = sum(padding + p['x'] * scale for p in points)
            sum_y = sum(padding + (height - p['y']) * scale for p in points)

            # Feature geometry
            feature_path = PreviewService._points_to_svg_path(points, padding, scale, height)
            svg_parts.append(
                f'<path d="{feature_path}" fill="none" stroke="{Colors.LINE}" stroke-width="2"/>'
            )

            # Compensated toolpath
            comp_points = None
            if tool_diameter and compensation != 'none':
                try:
                    comp_points = compensate_line_path(points, tool_diameter, compensation)
                    comp_path = PreviewService._points_to_svg_path(comp_points, padding, scale, height)
                    svg_parts.append(
                        f'<path d="{comp_path}" fill="none" stroke="{Colors.LINE}" '
                        f'stroke-width="1.5" stroke-dasharray="5,3" opacity="0.7"/>'
                    )
                except ValueError:
                    pass

            # Lead-in visualization
            # Check for per-operation lead-in settings first, then fall back to global
            op_lead_in_mode = lc.get('lead_in_mode', 'auto')
            op_lead_in_type = lc.get('lead_in_type')
            op_approach_angle = lc.get('lead_in_approach_angle', 90)

            # Determine if lead-in should be shown
            show_lead_in = False
            lead_in_distance = 0

            if op_lead_in_mode == 'manual' and op_lead_in_type and op_lead_in_type != 'none':
                # Manual mode with non-none type - use global distance calculation
                if lead_in_settings and lead_in_settings.get('distance', 0) > 0:
                    show_lead_in = True
                    lead_in_distance = lead_in_settings['distance']
            elif op_lead_in_mode == 'auto' and lead_in_settings and lead_in_settings.get('distance', 0) > 0:
                # Auto mode - use global settings
                show_lead_in = True
                lead_in_distance = lead_in_settings['distance']
                op_approach_angle = 90  # Default angle for auto mode

            if show_lead_in:
                lead_in_path = comp_points if comp_points else points
                if len(lead_in_path) >= 2:
                    lead_in_x, lead_in_y = calculate_line_lead_in_point(
                        lead_in_path,
                        lead_in_distance,
                        compensation,
                        op_approach_angle
                    )
                    start_x = lead_in_path[0].get('x', 0)
                    start_y = lead_in_path[0].get('y', 0)
                    PreviewService._draw_lead_in(
                        svg_parts, lead_in_x, lead_in_y, start_x, start_y,
                        height, padding, scale
                    )

            # Sequence number
            centroid_x = sum_x / len(points)
            centroid_y = sum_y / len(points)
            svg_parts.append(
                f'<text x="{centroid_x}" y="{centroid_y + 5}" font-size="16" font-weight="bold" '
                f'fill="{Colors.LINE}" text-anchor="middle" font-family="Arial, sans-serif">{seq_num}</text>'
            )

            # Coordinate labels
            if coords_mode == 'feature':
                for p in points:
                    px = padding + p['x'] * scale
                    py = padding + (height - p['y']) * scale
                    coord_labels.append((px + 8, py + 14, f'({p["x"]:.3f}, {p["y"]:.3f})', Colors.LINE))
            elif coords_mode == 'toolpath':
                display_points = comp_points if comp_points else points
                for p in display_points:
                    px = padding + p['x'] * scale
                    py = padding + (height - p['y']) * scale
                    coord_labels.append((px + 8, py + 14, f'({p["x"]:.3f}, {p["y"]:.3f})', Colors.LINE))

            seq_num += 1
        return seq_num
