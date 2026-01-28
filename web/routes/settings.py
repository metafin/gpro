"""Settings routes - materials, machine, general settings, tools."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import login_required
from web.services.settings_service import SettingsService

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
@login_required
def index():
    """Settings dashboard."""
    return render_template('settings/index.html')


# --- Materials ---

@settings_bp.route('/materials')
@login_required
def materials():
    """List all materials."""
    materials_list = SettingsService.get_all_materials()
    return render_template('settings/materials.html', materials=materials_list)


@settings_bp.route('/materials/create', methods=['POST'])
@login_required
def create_material():
    """Create a new material."""
    data = {
        'id': request.form.get('id'),
        'display_name': request.form.get('display_name'),
        'base_material': request.form.get('base_material'),
        'form': request.form.get('form'),
        'thickness': float(request.form.get('thickness')) if request.form.get('thickness') else None,
        'outer_width': float(request.form.get('outer_width')) if request.form.get('outer_width') else None,
        'outer_height': float(request.form.get('outer_height')) if request.form.get('outer_height') else None,
        'wall_thickness': float(request.form.get('wall_thickness')) if request.form.get('wall_thickness') else None,
        'gcode_standards': {}
    }
    SettingsService.create_material(data)
    flash('Material created', 'success')
    return redirect(url_for('settings.materials'))


@settings_bp.route('/materials/<material_id>/edit')
@login_required
def edit_material(material_id):
    """Edit material form."""
    material = SettingsService.get_material(material_id)
    if not material:
        flash('Material not found', 'error')
        return redirect(url_for('settings.materials'))

    # Fetch tools for G-Code standards configuration
    drills = SettingsService.get_tools_by_type('drill')
    end_mills_1flute = SettingsService.get_tools_by_type('end_mill_1flute')
    end_mills_2flute = SettingsService.get_tools_by_type('end_mill_2flute')

    return render_template(
        'settings/material_edit.html',
        material=material,
        drills=drills,
        end_mills_1flute=end_mills_1flute,
        end_mills_2flute=end_mills_2flute
    )


@settings_bp.route('/materials/<material_id>/update', methods=['POST'])
@login_required
def update_material(material_id):
    """Update a material."""
    # Parse G-code standards from form fields
    gcode_standards = {}
    tool_types = ['drill', 'end_mill_1flute', 'end_mill_2flute']
    drill_params = ['spindle_speed', 'feed_rate', 'plunge_rate', 'pecking_depth']
    endmill_params = ['spindle_speed', 'feed_rate', 'plunge_rate', 'pass_depth']

    for key in request.form:
        for tool_type in tool_types:
            if key.startswith(f'{tool_type}_'):
                # Parse field name: e.g., "drill_0.125_spindle_speed"
                params = drill_params if tool_type == 'drill' else endmill_params
                for param in params:
                    if key.endswith(f'_{param}'):
                        # Extract size from between tool_type and param
                        size_key = key[len(tool_type) + 1:-(len(param) + 1)]
                        value = request.form.get(key)
                        if value:
                            if tool_type not in gcode_standards:
                                gcode_standards[tool_type] = {}
                            if size_key not in gcode_standards[tool_type]:
                                gcode_standards[tool_type][size_key] = {}
                            # Convert to appropriate type
                            if param == 'spindle_speed':
                                gcode_standards[tool_type][size_key][param] = int(float(value))
                            else:
                                gcode_standards[tool_type][size_key][param] = float(value)
                        break

    data = {
        'display_name': request.form.get('display_name'),
        'base_material': request.form.get('base_material'),
        'form': request.form.get('form'),
        'thickness': float(request.form.get('thickness')) if request.form.get('thickness') else None,
        'outer_width': float(request.form.get('outer_width')) if request.form.get('outer_width') else None,
        'outer_height': float(request.form.get('outer_height')) if request.form.get('outer_height') else None,
        'wall_thickness': float(request.form.get('wall_thickness')) if request.form.get('wall_thickness') else None,
        'gcode_standards': gcode_standards,
    }
    if SettingsService.update_material(material_id, data):
        flash('Material updated', 'success')
    else:
        flash('Material not found', 'error')
    return redirect(url_for('settings.materials'))


@settings_bp.route('/materials/<material_id>/delete', methods=['POST'])
@login_required
def delete_material(material_id):
    """Delete a material."""
    if SettingsService.delete_material(material_id):
        flash('Material deleted', 'success')
    else:
        flash('Cannot delete material - it may be in use by projects', 'error')
    return redirect(url_for('settings.materials'))


# --- Machine Settings ---

@settings_bp.route('/machine')
@login_required
def machine():
    """Machine settings form."""
    machine_settings = SettingsService.get_machine_settings()
    return render_template('settings/machine.html', settings=machine_settings)


@settings_bp.route('/machine/save', methods=['POST'])
@login_required
def machine_save():
    """Save machine settings."""
    data = {
        'name': request.form.get('name'),
        'max_x': float(request.form.get('max_x', 15.0)),
        'max_y': float(request.form.get('max_y', 15.0)),
        'units': request.form.get('units', 'inches'),
        'controller_type': request.form.get('controller_type', 'mach3'),
        'supports_subroutines': request.form.get('supports_subroutines') == 'on',
        'supports_canned_cycles': request.form.get('supports_canned_cycles') == 'on',
        'gcode_base_path': request.form.get('gcode_base_path', 'C:\\Mach3\\GCode'),
    }
    SettingsService.update_machine_settings(data)
    flash('Machine settings saved', 'success')
    return redirect(url_for('settings.machine'))


# --- General Settings ---

@settings_bp.route('/general')
@login_required
def general():
    """General settings form."""
    general_settings = SettingsService.get_general_settings()
    return render_template('settings/general.html', settings=general_settings)


@settings_bp.route('/general/save', methods=['POST'])
@login_required
def save_general():
    """Save general settings."""
    data = {
        'safety_height': float(request.form.get('safety_height', 0.5)),
        'travel_height': float(request.form.get('travel_height', 0.2)),
        'spindle_warmup_seconds': int(request.form.get('spindle_warmup_seconds', 2)),
        'circle_lead_in_type': request.form.get('circle_lead_in_type', 'helical'),
        'hexagon_lead_in_type': request.form.get('hexagon_lead_in_type', 'helical'),
        'line_lead_in_type': request.form.get('line_lead_in_type', 'ramp'),
        'ramp_angle': float(request.form.get('ramp_angle', 3.0)),
        'helix_pitch': float(request.form.get('helix_pitch', 0.04)),
        'first_pass_feed_factor': float(request.form.get('first_pass_feed_factor', 0.7)),
        'max_stepdown_factor': float(request.form.get('max_stepdown_factor', 0.5)),
        'corner_slowdown_enabled': request.form.get('corner_slowdown_enabled') == 'on',
        'corner_feed_factor': float(request.form.get('corner_feed_factor', 0.5)),
        'arc_slowdown_enabled': request.form.get('arc_slowdown_enabled') == 'on',
        'arc_feed_factor': float(request.form.get('arc_feed_factor', 0.8)),
        'allow_negative_coordinates': request.form.get('allow_negative_coordinates') == 'on',
        'cut_through_buffer': float(request.form.get('cut_through_buffer', 0.01)),
    }
    SettingsService.update_general_settings(data)
    flash('General settings saved', 'success')
    return redirect(url_for('settings.general'))


# --- Tools ---

@settings_bp.route('/tools')
@login_required
def tools():
    """List all tools."""
    drills = SettingsService.get_tools_by_type('drill')
    end_mills_1flute = SettingsService.get_tools_by_type('end_mill_1flute')
    end_mills_2flute = SettingsService.get_tools_by_type('end_mill_2flute')
    return render_template(
        'settings/tools.html',
        drills=drills,
        end_mills_1flute=end_mills_1flute,
        end_mills_2flute=end_mills_2flute
    )


@settings_bp.route('/tools/create', methods=['POST'])
@login_required
def create_tool():
    """Add a new tool."""
    data = {
        'tool_type': request.form.get('tool_type'),
        'size': float(request.form.get('size')),
        'size_unit': request.form.get('size_unit', 'in'),
        'description': request.form.get('description'),
        'tip_compensation': request.form.get('tip_compensation'),
    }
    SettingsService.create_tool(data)
    flash('Tool added', 'success')
    return redirect(url_for('settings.tools'))


@settings_bp.route('/tools/<int:tool_id>/update', methods=['POST'])
@login_required
def update_tool(tool_id):
    """Update an existing tool."""
    data = {
        'description': request.form.get('description'),
        'tip_compensation': request.form.get('tip_compensation'),
    }
    if SettingsService.update_tool(tool_id, data):
        flash('Tool updated', 'success')
    else:
        flash('Tool not found', 'error')
    return redirect(url_for('settings.tools'))


@settings_bp.route('/tools/<int:tool_id>/delete', methods=['POST'])
@login_required
def delete_tool(tool_id):
    """Delete a tool."""
    if SettingsService.delete_tool(tool_id):
        flash('Tool deleted', 'success')
    else:
        flash('Tool not found', 'error')
    return redirect(url_for('settings.tools'))
