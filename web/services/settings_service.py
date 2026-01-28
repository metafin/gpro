"""Settings management service."""
from typing import Dict, List, Optional

from web.extensions import db
from web.models import Material, MachineSettings, GeneralSettings, Tool


class SettingsService:
    """Service for managing application settings."""

    # --- Material Methods ---

    @staticmethod
    def get_all_materials() -> List[Material]:
        """Get all materials, ordered by display_name."""
        return Material.query.order_by(Material.display_name).all()

    @staticmethod
    def get_material(material_id: str) -> Optional[Material]:
        """Get a single material by ID."""
        return Material.query.get(material_id)

    @staticmethod
    def get_materials_dict() -> Dict[str, Dict]:
        """Get all materials as dict for JSON serialization, keyed by ID."""
        materials = SettingsService.get_all_materials()
        result = {}
        for m in materials:
            result[m.id] = {
                'id': m.id,
                'display_name': m.display_name,
                'base_material': m.base_material,
                'form': m.form,
                'thickness': m.thickness,
                'outer_width': m.outer_width,
                'outer_height': m.outer_height,
                'wall_thickness': m.wall_thickness,
                'gcode_standards': m.gcode_standards or {}
            }
        return result

    @staticmethod
    def create_material(data: Dict) -> Material:
        """Create a new material from dict."""
        material = Material(
            id=data['id'],
            display_name=data['display_name'],
            base_material=data['base_material'],
            form=data['form'],
            thickness=data.get('thickness'),
            outer_width=data.get('outer_width'),
            outer_height=data.get('outer_height'),
            wall_thickness=data.get('wall_thickness'),
            gcode_standards=data.get('gcode_standards', {})
        )
        db.session.add(material)
        db.session.commit()
        return material

    @staticmethod
    def update_material(material_id: str, data: Dict) -> Optional[Material]:
        """Update an existing material."""
        material = Material.query.get(material_id)
        if not material:
            return None

        if 'display_name' in data:
            material.display_name = data['display_name']
        if 'base_material' in data:
            material.base_material = data['base_material']
        if 'form' in data:
            material.form = data['form']
        if 'thickness' in data:
            material.thickness = data['thickness']
        if 'outer_width' in data:
            material.outer_width = data['outer_width']
        if 'outer_height' in data:
            material.outer_height = data['outer_height']
        if 'wall_thickness' in data:
            material.wall_thickness = data['wall_thickness']
        if 'gcode_standards' in data:
            material.gcode_standards = data['gcode_standards']

        db.session.commit()
        return material

    @staticmethod
    def delete_material(material_id: str) -> bool:
        """Delete a material if not in use by any projects."""
        from web.models import Project
        material = Material.query.get(material_id)
        if not material:
            return False

        # Check if any projects use this material
        in_use = Project.query.filter_by(material_id=material_id).first()
        if in_use:
            return False

        db.session.delete(material)
        db.session.commit()
        return True

    # --- Machine Settings Methods ---

    @staticmethod
    def get_machine_settings() -> MachineSettings:
        """Get machine settings singleton, creating with defaults if missing."""
        settings = MachineSettings.query.get(1)
        if not settings:
            settings = MachineSettings(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings

    @staticmethod
    def get_machine_settings_dict() -> Dict:
        """Get machine settings as dict for JSON."""
        settings = SettingsService.get_machine_settings()
        return {
            'name': settings.name,
            'max_x': settings.max_x,
            'max_y': settings.max_y,
            'units': settings.units,
            'controller_type': settings.controller_type,
            'supports_subroutines': settings.supports_subroutines,
            'supports_canned_cycles': settings.supports_canned_cycles,
            'gcode_base_path': settings.gcode_base_path
        }

    @staticmethod
    def update_machine_settings(data: Dict) -> MachineSettings:
        """Update machine settings."""
        settings = SettingsService.get_machine_settings()

        if 'name' in data:
            settings.name = data['name']
        if 'max_x' in data:
            settings.max_x = float(data['max_x'])
        if 'max_y' in data:
            settings.max_y = float(data['max_y'])
        if 'units' in data:
            settings.units = data['units']
        if 'controller_type' in data:
            settings.controller_type = data['controller_type']
        if 'supports_subroutines' in data:
            settings.supports_subroutines = bool(data['supports_subroutines'])
        if 'supports_canned_cycles' in data:
            settings.supports_canned_cycles = bool(data['supports_canned_cycles'])
        if 'gcode_base_path' in data:
            settings.gcode_base_path = data['gcode_base_path']

        db.session.commit()
        return settings

    # --- General Settings Methods ---

    @staticmethod
    def get_general_settings() -> GeneralSettings:
        """Get general settings singleton, creating with defaults if missing."""
        settings = GeneralSettings.query.get(1)
        if not settings:
            settings = GeneralSettings(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings

    @staticmethod
    def get_general_settings_dict() -> Dict:
        """Get general settings as dict for JSON."""
        settings = SettingsService.get_general_settings()
        return {
            'safety_height': settings.safety_height,
            'travel_height': settings.travel_height,
            'spindle_warmup_seconds': settings.spindle_warmup_seconds,
            'circle_lead_in_type': settings.circle_lead_in_type,
            'hexagon_lead_in_type': settings.hexagon_lead_in_type,
            'line_lead_in_type': settings.line_lead_in_type,
            'ramp_angle': settings.ramp_angle,
            'helix_pitch': settings.helix_pitch,
            'first_pass_feed_factor': settings.first_pass_feed_factor,
            'max_stepdown_factor': settings.max_stepdown_factor,
            'corner_slowdown_enabled': settings.corner_slowdown_enabled,
            'corner_feed_factor': settings.corner_feed_factor,
            'cut_through_buffer': settings.cut_through_buffer
        }

    @staticmethod
    def update_general_settings(data: Dict) -> GeneralSettings:
        """Update general settings."""
        settings = SettingsService.get_general_settings()

        if 'safety_height' in data:
            settings.safety_height = float(data['safety_height'])
        if 'travel_height' in data:
            settings.travel_height = float(data['travel_height'])
        if 'spindle_warmup_seconds' in data:
            settings.spindle_warmup_seconds = int(data['spindle_warmup_seconds'])
        if 'circle_lead_in_type' in data:
            settings.circle_lead_in_type = data['circle_lead_in_type']
        if 'hexagon_lead_in_type' in data:
            settings.hexagon_lead_in_type = data['hexagon_lead_in_type']
        if 'line_lead_in_type' in data:
            settings.line_lead_in_type = data['line_lead_in_type']
        if 'ramp_angle' in data:
            settings.ramp_angle = float(data['ramp_angle'])
        if 'helix_pitch' in data:
            settings.helix_pitch = float(data['helix_pitch'])
        if 'first_pass_feed_factor' in data:
            settings.first_pass_feed_factor = float(data['first_pass_feed_factor'])
        if 'max_stepdown_factor' in data:
            settings.max_stepdown_factor = float(data['max_stepdown_factor'])
        if 'corner_slowdown_enabled' in data:
            settings.corner_slowdown_enabled = bool(data['corner_slowdown_enabled'])
        if 'corner_feed_factor' in data:
            settings.corner_feed_factor = float(data['corner_feed_factor'])
        if 'allow_negative_coordinates' in data:
            settings.allow_negative_coordinates = bool(data['allow_negative_coordinates'])
        if 'cut_through_buffer' in data:
            settings.cut_through_buffer = float(data['cut_through_buffer'])

        db.session.commit()
        return settings

    # --- Tool Methods ---

    @staticmethod
    def get_all_tools() -> List[Tool]:
        """Get all tools, ordered by tool_type then size."""
        return Tool.query.order_by(Tool.tool_type, Tool.size).all()

    @staticmethod
    def get_tool(tool_id: int) -> Optional[Tool]:
        """Get a single tool by ID."""
        return Tool.query.get(tool_id)

    @staticmethod
    def get_tools_by_type(tool_type: str) -> List[Tool]:
        """Get tools filtered by type, ordered by size."""
        return Tool.query.filter_by(tool_type=tool_type).order_by(Tool.size).all()

    @staticmethod
    def get_tools_as_list() -> List[Dict]:
        """Get all tools as list of dicts for JSON."""
        tools = SettingsService.get_all_tools()
        return [
            {
                'id': t.id,
                'tool_type': t.tool_type,
                'size': t.size,
                'size_unit': t.size_unit,
                'description': t.description
            }
            for t in tools
        ]

    @staticmethod
    def create_tool(data: Dict) -> Tool:
        """Create a new tool from dict."""
        tool = Tool(
            tool_type=data['tool_type'],
            size=float(data['size']),
            size_unit=data.get('size_unit', 'in'),
            description=data.get('description', ''),
            tip_compensation=float(data['tip_compensation']) if data.get('tip_compensation') else 0.0
        )
        db.session.add(tool)
        db.session.commit()
        return tool

    @staticmethod
    def update_tool(tool_id: int, data: Dict) -> Optional[Tool]:
        """Update an existing tool."""
        tool = Tool.query.get(tool_id)
        if not tool:
            return None

        if 'tool_type' in data:
            tool.tool_type = data['tool_type']
        if 'size' in data:
            tool.size = float(data['size'])
        if 'size_unit' in data:
            tool.size_unit = data['size_unit']
        if 'description' in data:
            tool.description = data['description']
        if 'tip_compensation' in data:
            tool.tip_compensation = float(data['tip_compensation']) if data['tip_compensation'] else 0.0

        db.session.commit()
        return tool

    @staticmethod
    def delete_tool(tool_id: int) -> bool:
        """Delete a tool."""
        tool = Tool.query.get(tool_id)
        if not tool:
            return False

        db.session.delete(tool)
        db.session.commit()
        return True
