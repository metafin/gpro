from datetime import datetime, UTC
import uuid

from web.extensions import db


class Material(db.Model):
    """Material type with G-code standards per tool size."""

    id = db.Column(db.String(50), primary_key=True)
    display_name = db.Column(db.String(100), nullable=False)
    base_material = db.Column(db.String(50), nullable=False)  # 'aluminum', 'polycarbonate'
    form = db.Column(db.String(20), nullable=False)  # 'sheet' or 'tube'

    # For sheets
    thickness = db.Column(db.Float, nullable=True)

    # For tubes
    outer_width = db.Column(db.Float, nullable=True)
    outer_height = db.Column(db.Float, nullable=True)
    wall_thickness = db.Column(db.Float, nullable=True)

    # G-code standards stored as JSON, keyed by tool_type then size (as string)
    # Format: {
    #   "drill": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pecking_depth": ...}},
    #   "end_mill_1flute": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pass_depth": ...}},
    #   "end_mill_2flute": {"0.125": {"spindle_speed": ..., "feed_rate": ..., "plunge_rate": ..., "pass_depth": ...}}
    # }
    # NOTE: Tool sizes are string keys in JSON. When looking up parameters, convert tool size to string:
    #   params = material.gcode_standards.get(tool_type, {}).get(str(tool.size))
    gcode_standards = db.Column(db.JSON, nullable=False, default=dict)


class MachineSettings(db.Model):
    """Machine configuration (singleton - one row)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    max_x = db.Column(db.Float)
    max_y = db.Column(db.Float)
    units = db.Column(db.String(10))  # 'inches' or 'mm'
    controller_type = db.Column(db.String(20))
    supports_subroutines = db.Column(db.Boolean)  # M98 subroutine calls
    supports_canned_cycles = db.Column(db.Boolean)  # G83 peck drilling
    gcode_base_path = db.Column(db.String(500))  # Where G-code directories are stored


class GeneralSettings(db.Model):
    """General G-code settings (singleton - one row)."""

    id = db.Column(db.Integer, primary_key=True)
    safety_height = db.Column(db.Float)
    travel_height = db.Column(db.Float)
    spindle_warmup_seconds = db.Column(db.Integer)

    # Per-cut-type lead-in settings
    # Circles and hexagons support: 'none', 'ramp', 'helical'
    # Lines only support: 'none', 'ramp' (no helical)
    circle_lead_in_type = db.Column(db.String(20))
    hexagon_lead_in_type = db.Column(db.String(20))
    line_lead_in_type = db.Column(db.String(20))

    # Shared lead-in parameters
    ramp_angle = db.Column(db.Float)  # Ramp entry angle in degrees (2-5° recommended)

    # Helical lead-in settings
    helix_pitch = db.Column(db.Float)  # Z drop per revolution (inches)

    # First pass feed reduction (reduces feed on first pass to reduce tool stress)
    first_pass_feed_factor = db.Column(db.Float)  # 70% of normal feed

    # Stepdown validation (warn if pass_depth exceeds this factor of tool diameter)
    max_stepdown_factor = db.Column(db.Float)  # 50% of tool diameter

    # Corner slowdown (reduce feed at sharp corners)
    corner_slowdown_enabled = db.Column(db.Boolean)
    corner_feed_factor = db.Column(db.Float)  # 50% of normal feed at corners

    # Arc slowdown (reduce feed on arc moves for improved cut quality)
    arc_slowdown_enabled = db.Column(db.Boolean)
    arc_feed_factor = db.Column(db.Float)  # 80% of normal feed on arcs

    # Bounds validation - allow toolpaths to extend past zero (for exterior cuts at origin)
    allow_negative_coordinates = db.Column(db.Boolean)

    # Cut-through buffer - extra Z depth for cut projects to ensure complete separation
    cut_through_buffer = db.Column(db.Float)


class Tool(db.Model):
    """Available tools (drill bits and end mills)."""

    id = db.Column(db.Integer, primary_key=True)
    tool_type = db.Column(db.String(20), nullable=False)  # 'drill', 'end_mill_1flute', 'end_mill_2flute'
    size = db.Column(db.Float, nullable=False)  # diameter
    size_unit = db.Column(db.String(5), nullable=False, default='in')  # 'in' or 'mm'
    description = db.Column(db.String(100))
    # Tip compensation for drills - extra depth to account for drill point geometry
    # Typical values: 0.03-0.05" for standard 118° drill points
    tip_compensation = db.Column(db.Float, nullable=True, default=0.0)


class Project(db.Model):
    """User project with operations."""

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    modified_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    project_type = db.Column(db.String(20), nullable=False)  # 'drill' or 'cut'
    material_id = db.Column(db.String(50), db.ForeignKey('material.id'))
    material = db.relationship('Material')

    # Tool references (foreign keys to Tool table)
    drill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=True)
    end_mill_tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=True)
    drill_tool = db.relationship('Tool', foreign_keys=[drill_tool_id])
    end_mill_tool = db.relationship('Tool', foreign_keys=[end_mill_tool_id])

    # Operations stored as JSON (flexible structure)
    # Format: {"drill_holes": [...], "circular_cuts": [...], "hexagonal_cuts": [...], "line_cuts": [...]}
    operations = db.Column(db.JSON, nullable=False, default=dict)

    # Tube settings
    tube_void_skip = db.Column(db.Boolean, default=False)
    working_length = db.Column(db.Float, nullable=True)  # Length of tube segment being machined
    tube_orientation = db.Column(db.String(10), nullable=True)  # 'wide' or 'narrow' - which face is up
    tube_axis = db.Column(db.String(1), nullable=True, default='x')  # 'x' or 'y' - tube placement on machine bed
