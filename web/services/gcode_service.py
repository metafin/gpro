"""G-code generation service."""
from typing import Dict, List, Optional, Tuple
import os

from web.models import Project, Material, Tool
from web.services.settings_service import SettingsService

from src.gcode_generator import (
    WebGCodeGenerator,
    GenerationSettings,
    ToolParams,
    GenerationResult
)
from src.pattern_expander import expand_all_operations
from src.tube_void_checker import filter_operations_for_tube
from src.utils.multipass import get_material_depth
from src.utils.gcode_format import sanitize_project_name
from src.utils.file_manager import (
    create_output_directory,
    write_main_file,
    write_subroutine_file,
    package_for_download
)
from src.utils.config_writer import write_config_file
from src.utils.tool_compensation import compensate_line_path
from src.utils.validators import validate_stepdown, validate_feed_rates
from web.services.preview_service import PreviewService


class GCodeService:
    """Service for G-code generation and validation."""

    @staticmethod
    def get_gcode_params(material: Material, tool_size: float, tool_type: str) -> Optional[Dict]:
        """
        Get G-code parameters for a material/tool combination.

        Returns dict with spindle_speed, feed_rate, plunge_rate, and
        pecking_depth (drill) or pass_depth (end mills).
        """
        if not material or not material.gcode_standards:
            return None

        # Tool sizes are stored as string keys in JSON
        size_key = str(tool_size)
        tool_standards = material.gcode_standards.get(tool_type, {})
        params = tool_standards.get(size_key)

        if not params:
            return None

        # Get material depth
        material_depth = get_material_depth(material)

        return {
            'spindle_speed': params.get('spindle_speed'),
            'feed_rate': params.get('feed_rate'),
            'plunge_rate': params.get('plunge_rate'),
            'pecking_depth': params.get('pecking_depth'),
            'pass_depth': params.get('pass_depth'),
            'material_depth': material_depth
        }

    @staticmethod
    def expand_operations(operations: Dict) -> Tuple[List, List, List, List]:
        """
        Expand all pattern types to individual coordinates.

        Returns: (drill_points, circular_cuts, hexagonal_cuts, line_cuts)
        """
        expanded = expand_all_operations(operations)
        return (
            expanded['drill_points'],
            expanded['circular_cuts'],
            expanded['hexagonal_cuts'],
            expanded['line_cuts']
        )

    @staticmethod
    def validate(project: Project) -> List[str]:
        """
        Validate a project configuration before generating G-code.

        Returns list of error messages (empty if valid).
        """
        errors = []
        machine = SettingsService.get_machine_settings()
        general = SettingsService.get_general_settings()

        # Check required fields
        if not project.material_id:
            errors.append("No material selected")

        if project.project_type == 'drill':
            if not project.drill_tool_id:
                errors.append("No drill tool selected")
        else:
            if not project.end_mill_tool_id:
                errors.append("No end mill tool selected")

        # Validate stepdown for cutting operations (blocking errors)
        if project.project_type != 'drill' and project.end_mill_tool_id and project.material_id:
            end_mill = Tool.query.get(project.end_mill_tool_id)
            material = Material.query.get(project.material_id)
            if end_mill and material:
                # Get pass_depth from G-code standards
                params = GCodeService.get_gcode_params(material, end_mill.size, end_mill.tool_type)
                if params and params.get('pass_depth'):
                    stepdown_errors, _ = validate_stepdown(
                        params['pass_depth'],
                        end_mill.size,
                        general.max_stepdown_factor or 0.5
                    )
                    errors.extend(stepdown_errors)

        # Check operations exist
        operations = project.operations or {}
        has_operations = False

        if project.project_type == 'drill':
            if operations.get('drill_holes'):
                has_operations = True
        else:
            if (operations.get('circular_cuts') or
                operations.get('hexagonal_cuts') or
                operations.get('line_cuts')):
                has_operations = True

        if not has_operations:
            errors.append("Project has no operations")

        # Validate coordinates are within machine bounds
        expanded = expand_all_operations(operations)

        max_x = machine.max_x
        max_y = machine.max_y
        general = SettingsService.get_general_settings()
        allow_negative = general.allow_negative_coordinates

        for x, y in expanded['drill_points']:
            if x > max_x or y > max_y:
                errors.append(f"Drill point ({x}, {y}) exceeds machine bounds")
            elif not allow_negative and (x < 0 or y < 0):
                errors.append(f"Drill point ({x}, {y}) is outside machine bounds (negative coordinate)")

        for c in expanded['circular_cuts']:
            radius = c['diameter'] / 2
            if c['center_x'] + radius > max_x or c['center_y'] + radius > max_y:
                errors.append(f"Circle at ({c['center_x']}, {c['center_y']}) extends outside machine bounds")
            elif not allow_negative and (c['center_x'] - radius < 0 or c['center_y'] - radius < 0):
                errors.append(f"Circle at ({c['center_x']}, {c['center_y']}) extends past zero")

        for h in expanded['hexagonal_cuts']:
            # Hex extends apothem in X, circumradius in Y (point-up orientation)
            import math
            apothem = h['flat_to_flat'] / 2
            circumradius = h['flat_to_flat'] / math.sqrt(3)
            if h['center_x'] + apothem > max_x or h['center_y'] + circumradius > max_y:
                errors.append(f"Hexagon at ({h['center_x']}, {h['center_y']}) extends outside machine bounds")
            elif not allow_negative and (h['center_x'] - apothem < 0 or h['center_y'] - circumradius < 0):
                errors.append(f"Hexagon at ({h['center_x']}, {h['center_y']}) extends past zero")

        # Get end mill tool for line cut compensation validation
        end_mill_tool = None
        if project.project_type != 'drill' and project.end_mill_tool_id:
            end_mill_tool = Tool.query.get(project.end_mill_tool_id)

        for lc in expanded['line_cuts']:
            compensation = lc.get('compensation', 'none')
            points_to_check = lc.get('points', [])

            # Apply compensation for validation if applicable
            if compensation != 'none' and end_mill_tool:
                from src.utils.tool_compensation import compensate_line_path
                try:
                    points_to_check = compensate_line_path(
                        points_to_check,
                        end_mill_tool.size,
                        compensation
                    )
                except ValueError as e:
                    errors.append(str(e))
                    continue

            for p in points_to_check:
                if p['x'] > max_x or p['y'] > max_y:
                    errors.append(f"Line point ({p['x']:.3f}, {p['y']:.3f}) exceeds machine bounds")
                elif not allow_negative and (p['x'] < 0 or p['y'] < 0):
                    errors.append(f"Line point ({p['x']:.3f}, {p['y']:.3f}) has negative coordinate")

        return errors

    @staticmethod
    def get_validation_warnings(project: Project) -> List[str]:
        """
        Get non-blocking warnings for a project configuration.

        These warnings don't prevent generation but inform the user
        of potential issues or risky configurations.

        Returns list of warning messages.
        """
        warnings = []
        general = SettingsService.get_general_settings()

        # Get tool and material for parameter checks
        if project.project_type != 'drill' and project.end_mill_tool_id and project.material_id:
            end_mill = Tool.query.get(project.end_mill_tool_id)
            material = Material.query.get(project.material_id)

            if end_mill and material:
                params = GCodeService.get_gcode_params(material, end_mill.size, end_mill.tool_type)
                if params:
                    # Stepdown warnings (non-blocking)
                    if params.get('pass_depth'):
                        _, stepdown_warnings = validate_stepdown(
                            params['pass_depth'],
                            end_mill.size,
                            general.max_stepdown_factor or 0.5
                        )
                        warnings.extend(stepdown_warnings)

                    # Feed rate warnings
                    if params.get('feed_rate') and params.get('plunge_rate'):
                        feed_warnings = validate_feed_rates(
                            params['feed_rate'],
                            params['plunge_rate']
                        )
                        warnings.extend(feed_warnings)

        # Warn if lead-in is disabled for profile cuts (non-drill projects)
        if project.project_type != 'drill':
            operations = project.operations or {}
            disabled_lead_ins = []

            if operations.get('circular_cuts') and (general.circle_lead_in_type or 'helical') == 'none':
                disabled_lead_ins.append('circle')
            if operations.get('hexagonal_cuts') and (general.hexagon_lead_in_type or 'helical') == 'none':
                disabled_lead_ins.append('hexagon')
            if operations.get('line_cuts') and (general.line_lead_in_type or 'ramp') == 'none':
                disabled_lead_ins.append('line')

            if disabled_lead_ins:
                cut_types = ', '.join(disabled_lead_ins)
                warnings.append(
                    f"Lead-in is disabled for {cut_types} cuts. "
                    "This increases risk of end mill breakage from vertical plunge. "
                    "Consider enabling 'Helical' or 'Ramp' lead-in in General Settings."
                )

        return warnings

    @staticmethod
    def generate_preview_svg(
        project: Project,
        operations: Optional[Dict] = None,
        coords_mode: str = 'off'
    ) -> str:
        """
        Generate an SVG preview of the project toolpaths.

        Args:
            project: The project to preview
            operations: Optional operations dict (for previewing unsaved changes)
            coords_mode: 'off', 'feature' (show feature coords), or 'toolpath' (show compensated coords)
        """
        ops = operations if operations else project.operations
        if not ops:
            ops = {'drill_holes': [], 'circular_cuts': [], 'hexagonal_cuts': [], 'line_cuts': []}

        expanded = expand_all_operations(ops)

        machine = SettingsService.get_machine_settings()

        # Get material dimensions for display
        material = project.material if project.material_id else None
        wall_thickness = None
        if material and material.form == 'tube':
            # Tube laid flat: X = working_length, Y = selected face dimension
            width = project.working_length or 12.0  # Default 12" if not set
            if project.tube_orientation == 'narrow':
                height = material.outer_height
            else:
                height = material.outer_width  # Default to wide face
            wall_thickness = material.wall_thickness
        else:
            width = machine.max_x
            height = machine.max_y

        # Get tool diameter for compensation preview
        tool_diameter = None
        if project.project_type != 'drill' and project.end_mill_tool:
            tool_diameter = project.end_mill_tool.size

        # Get lead-in settings for preview
        general = SettingsService.get_general_settings()
        lead_in_settings = None
        ramp_angle = general.ramp_angle or 3.0  # Default to 3° if not set
        if general.line_lead_in_type == 'ramp' and ramp_angle > 0:
            # Estimate pass depth for preview lead-in calculation
            import math
            estimated_pass_depth = 0.1  # Default estimate
            if material and tool_diameter:
                # Try to get actual pass depth from material/tool params
                gcode_params = GCodeService.get_gcode_params(
                    material, tool_diameter, 'end_mill_2flute'
                )
                if gcode_params and gcode_params.get('pass_depth'):
                    estimated_pass_depth = gcode_params['pass_depth']

            # Calculate lead-in distance from ramp angle
            ramp_radians = math.radians(ramp_angle)
            lead_in_distance = estimated_pass_depth / math.tan(ramp_radians)

            lead_in_settings = {
                'type': general.line_lead_in_type,
                'distance': lead_in_distance
            }

        # Generate SVG using PreviewService
        svg = PreviewService.generate_svg(
            width, height,
            expanded['drill_points'],
            expanded['circular_cuts'],
            expanded['hexagonal_cuts'],
            expanded['line_cuts'],
            wall_thickness,
            tool_diameter,
            coords_mode,
            lead_in_settings
        )
        return svg

    @staticmethod
    def build_generation_settings() -> GenerationSettings:
        """
        Build GenerationSettings from machine and general settings.

        Returns GenerationSettings configured from database settings.
        """
        general = SettingsService.get_general_settings()
        machine = SettingsService.get_machine_settings()

        return GenerationSettings(
            safety_height=general.safety_height,
            travel_height=general.travel_height,
            spindle_warmup_seconds=general.spindle_warmup_seconds,
            supports_subroutines=machine.supports_subroutines,
            supports_canned_cycles=machine.supports_canned_cycles,
            gcode_base_path=machine.gcode_base_path,
            max_x=machine.max_x,
            max_y=machine.max_y,
            circle_lead_in_type=general.circle_lead_in_type or 'helical',
            hexagon_lead_in_type=general.hexagon_lead_in_type or 'helical',
            line_lead_in_type=general.line_lead_in_type or 'ramp',
            ramp_angle=general.ramp_angle or 3.0,
            helix_pitch=general.helix_pitch or 0.04,
            first_pass_feed_factor=general.first_pass_feed_factor or 0.7,
            max_stepdown_factor=general.max_stepdown_factor or 0.5,
            corner_slowdown_enabled=general.corner_slowdown_enabled if general.corner_slowdown_enabled is not None else True,
            corner_feed_factor=general.corner_feed_factor or 0.5,
            arc_slowdown_enabled=general.arc_slowdown_enabled if general.arc_slowdown_enabled is not None else True,
            arc_feed_factor=general.arc_feed_factor or 0.8
        )

    @staticmethod
    def build_tool_params(
        material: Material,
        tool: Tool,
        tool_type: str = None
    ) -> Optional[ToolParams]:
        """
        Build ToolParams from material and tool.

        Args:
            material: Material to get G-code standards from
            tool: Tool to get parameters for
            tool_type: Override tool type (defaults to tool.tool_type or 'drill')

        Returns ToolParams or None if no parameters found.
        """
        if not tool or not material:
            return None

        effective_tool_type = tool_type or tool.tool_type
        params = GCodeService.get_gcode_params(material, tool.size, effective_tool_type)

        if not params:
            return None

        return ToolParams(
            spindle_speed=params['spindle_speed'],
            feed_rate=params['feed_rate'],
            plunge_rate=params['plunge_rate'],
            pecking_depth=params.get('pecking_depth'),
            pass_depth=params.get('pass_depth'),
            tool_diameter=tool.size
        )

    @staticmethod
    def prepare_operations(project: Project) -> Dict:
        """
        Expand and filter operations for a project.

        Returns expanded operations dict ready for generation.
        """
        material = project.material
        drill_tool = project.drill_tool if project.project_type == 'drill' else None
        end_mill_tool = project.end_mill_tool if project.project_type != 'drill' else None

        # Expand operations
        expanded = expand_all_operations(project.operations or {})

        # Filter for tube void if applicable
        if material and material.form == 'tube' and project.tube_void_skip:
            drill_diameter = drill_tool.size if drill_tool else None
            end_mill_diameter = end_mill_tool.size if end_mill_tool else None

            expanded = filter_operations_for_tube(
                expanded, material, drill_diameter, end_mill_diameter
            )

        return expanded

    @staticmethod
    def generate_with_params(
        project: Project,
        cut_params: Optional[ToolParams] = None,
        drill_params: Optional[ToolParams] = None,
        project_name_suffix: str = '',
        skip_validation: bool = False
    ) -> GenerationResult:
        """
        Generate G-code for a project with custom tool parameters.

        This method allows overriding the tool parameters that would normally
        be derived from the material's gcode_standards. Useful for testing
        different cutting parameters.

        Args:
            project: Project to generate G-code for
            cut_params: Custom cutting parameters (overrides material standards)
            drill_params: Custom drilling parameters (overrides material standards)
            project_name_suffix: Suffix to append to project name (e.g., '_very_safe')
            skip_validation: Skip project validation (useful for parameter testing)

        Returns GenerationResult with main_gcode, subroutines dict, and warnings.
        """
        # Validate first (unless skipped)
        if not skip_validation:
            errors = GCodeService.validate(project)
            if errors:
                raise ValueError(f"Project validation failed: {'; '.join(errors)}")

        # Get material
        material = project.material
        if not material:
            raise ValueError("No material selected")

        material_depth = get_material_depth(material)

        # Add tip compensation for drill projects
        drill_tool = project.drill_tool if project.project_type == 'drill' else None
        if drill_tool and drill_tool.tip_compensation:
            material_depth += drill_tool.tip_compensation

        # Add cut-through buffer for cut projects to ensure complete separation
        if project.project_type != 'drill':
            general = SettingsService.get_general_settings()
            if general.cut_through_buffer:
                material_depth += general.cut_through_buffer

        # Build generation settings
        gen_settings = GCodeService.build_generation_settings()

        # Use provided params or build from material/tool
        if cut_params is None and project.project_type != 'drill':
            end_mill_tool = project.end_mill_tool
            if end_mill_tool:
                cut_params = GCodeService.build_tool_params(
                    material, end_mill_tool, end_mill_tool.tool_type
                )

        if drill_params is None and project.project_type == 'drill':
            if drill_tool:
                drill_params = GCodeService.build_tool_params(
                    material, drill_tool, 'drill'
                )

        # Check we have at least one set of params
        if not drill_params and not cut_params:
            raise ValueError("No G-code parameters provided or found for tool/material")

        # Prepare operations
        expanded = GCodeService.prepare_operations(project)

        # Create generator with optional name suffix
        project_name = project.name + project_name_suffix

        generator = WebGCodeGenerator(
            settings=gen_settings,
            project_name=project_name,
            material_depth=material_depth
        )

        # Generate G-code
        result = generator.generate(
            expanded_ops=expanded,
            drill_params=drill_params,
            cut_params=cut_params,
            original_operations=project.operations
        )

        return result

    @staticmethod
    def generate(project: Project) -> GenerationResult:
        """
        Generate G-code for a project.

        Returns GenerationResult with main_gcode, subroutines dict, and warnings.
        """
        # Use the parameterized version with default behavior
        result = GCodeService.generate_with_params(project)

        # Add validation warnings to result
        validation_warnings = GCodeService.get_validation_warnings(project)
        result.warnings.extend(validation_warnings)

        return result

    @staticmethod
    def generate_and_save(project: Project) -> Dict:
        """
        Generate G-code and save to filesystem.

        Returns dict with file paths and download info.
        """
        result = GCodeService.generate(project)

        machine = SettingsService.get_machine_settings()
        general = SettingsService.get_general_settings()

        # Create output directory
        directory = create_output_directory(
            machine.gcode_base_path,
            result.project_name
        )

        # Write main file
        main_path = write_main_file(directory, result.main_gcode)

        # Write subroutines
        subroutine_paths = []
        for number, content in result.subroutines.items():
            path = write_subroutine_file(directory, number, content)
            subroutine_paths.append(path)

        # Write config file for debugging
        config_data = GCodeService._build_config_data(project, machine, general)
        write_config_file(directory, config_data)

        return {
            'directory': directory,
            'main_file': main_path,
            'subroutines': subroutine_paths,
            'project_name': result.project_name,
            'warnings': result.warnings
        }

    @staticmethod
    def _build_config_data(project: Project, machine, general) -> Dict:
        """Build config data dict for debugging output."""
        material = project.material
        tool = project.drill_tool if project.project_type == 'drill' else project.end_mill_tool

        # Get G-code params for the tool/material combo
        gcode_params = {}
        if tool and material:
            tool_type = 'drill' if project.project_type == 'drill' else tool.tool_type
            params = GCodeService.get_gcode_params(material, tool.size, tool_type)
            if params:
                gcode_params = params

        return {
            'project': {
                'name': project.name,
                'type': project.project_type,
                'tube_void_skip': project.tube_void_skip,
                'working_length': project.working_length,
                'tube_orientation': project.tube_orientation,
                'tube_axis': project.tube_axis
            },
            'material': {
                'display_name': material.display_name if material else None,
                'base_material': material.base_material if material else None,
                'form': material.form if material else None,
                'thickness': material.thickness if material else None,
                'outer_width': material.outer_width if material else None,
                'outer_height': material.outer_height if material else None,
                'wall_thickness': material.wall_thickness if material else None
            } if material else {},
            'tool': {
                'tool_type': tool.tool_type if tool else None,
                'size': tool.size if tool else None,
                'size_unit': tool.size_unit if tool else 'in',
                'description': tool.description if tool else None,
                'tip_compensation': tool.tip_compensation if tool and tool.tool_type == 'drill' else None
            } if tool else {},
            'gcode_params': gcode_params,
            'machine': {
                'name': machine.name,
                'max_x': machine.max_x,
                'max_y': machine.max_y,
                'units': machine.units,
                'controller_type': machine.controller_type,
                'supports_subroutines': machine.supports_subroutines,
                'supports_canned_cycles': machine.supports_canned_cycles,
                'gcode_base_path': machine.gcode_base_path
            },
            'general': {
                'safety_height': general.safety_height,
                'travel_height': general.travel_height,
                'spindle_warmup_seconds': general.spindle_warmup_seconds,
                'circle_lead_in_type': general.circle_lead_in_type,
                'hexagon_lead_in_type': general.hexagon_lead_in_type,
                'line_lead_in_type': general.line_lead_in_type,
                'ramp_angle': general.ramp_angle,
                'helix_pitch': general.helix_pitch,
                'first_pass_feed_factor': general.first_pass_feed_factor,
                'max_stepdown_factor': general.max_stepdown_factor,
                'corner_slowdown_enabled': general.corner_slowdown_enabled,
                'corner_feed_factor': general.corner_feed_factor,
                'arc_slowdown_enabled': general.arc_slowdown_enabled,
                'arc_feed_factor': general.arc_feed_factor,
                'allow_negative_coordinates': general.allow_negative_coordinates,
                'cut_through_buffer': general.cut_through_buffer
            },
            'operations': project.operations or {}
        }

    @staticmethod
    def generate_download(project: Project) -> Tuple[bytes, str]:
        """
        Generate G-code and package for download.

        Returns tuple of (zip_bytes, filename).
        """
        save_result = GCodeService.generate_and_save(project)

        # Package as zip
        zip_bytes = package_for_download(save_result['directory'])
        filename = f"{save_result['project_name']}.zip"

        return zip_bytes, filename

    @staticmethod
    def get_gcode_preview(project: Project) -> Dict:
        """
        Generate G-code and return as preview (not saved to filesystem).

        Returns dict with main_gcode and subroutines for display.
        """
        result = GCodeService.generate(project)

        return {
            'main_gcode': result.main_gcode,
            'subroutines': {
                f"{num}.nc": content
                for num, content in result.subroutines.items()
            },
            'project_name': result.project_name,
            'warnings': result.warnings
        }
