"""API routes - AJAX endpoints for the frontend."""
from flask import Blueprint, request, send_file
import io

from web.auth import login_required
from web.services.project_service import ProjectService
from web.services.settings_service import SettingsService
from web.services.gcode_service import GCodeService
from web.utils.responses import success_response, error_response, validation_response

api_bp = Blueprint('api', __name__)


@api_bp.route('/projects/<project_id>/save', methods=['POST'])
@login_required
def save_project(project_id):
    """Save project data from the editor."""
    data = request.get_json()
    if not data:
        return error_response('No data provided')

    project = ProjectService.save(project_id, data)
    if not project:
        return error_response('Project not found', 404)

    return success_response(data={'modified_at': project.modified_at.isoformat()})


@api_bp.route('/projects/<project_id>/preview', methods=['POST'])
@login_required
def preview_project(project_id):
    """Generate SVG preview. Can preview unsaved changes by passing operations in body."""
    project = ProjectService.get(project_id)
    if not project:
        return error_response('Project not found', 404)

    # Get operations from request body, or use project's saved operations
    data = request.get_json() or {}
    operations = data.get('operations', project.operations)
    coords_mode = data.get('coords_mode', 'off')  # 'off', 'feature', or 'toolpath'

    try:
        svg = GCodeService.generate_preview_svg(project, operations, coords_mode)
        return success_response(data={'svg': svg})
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/projects/<project_id>/download')
@login_required
def download_gcode(project_id):
    """Download generated G-code file."""
    project = ProjectService.get(project_id)
    if not project:
        return error_response('Project not found', 404)

    if not project.material_id:
        return error_response('No material selected', 400)

    # Check for appropriate tool
    if project.project_type == 'drill' and not project.drill_tool_id:
        return error_response('No drill tool selected', 400)
    if project.project_type == 'cut' and not project.end_mill_tool_id:
        return error_response('No end mill tool selected', 400)

    try:
        zip_bytes, filename = GCodeService.generate_download(project)

        # Create file-like object for download
        buffer = io.BytesIO(zip_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/projects/<project_id>/validate', methods=['POST'])
@login_required
def validate_project(project_id):
    """Validate project configuration before generating G-code."""
    project = ProjectService.get(project_id)
    if not project:
        return error_response('Project not found', 404)

    errors = GCodeService.validate(project)
    return validation_response(errors)


@api_bp.route('/projects/multi-preview', methods=['POST'])
@login_required
def multi_preview():
    """Generate SVG previews for multiple projects (for overlay comparison)."""
    data = request.get_json() or {}
    project_ids = data.get('project_ids', [])

    if not project_ids:
        return error_response('No projects selected')

    results = []
    for pid in project_ids:
        project = ProjectService.get(pid)
        if not project:
            continue
        try:
            svg = GCodeService.generate_preview_svg(project)
            results.append({
                'project_id': project.id,
                'name': project.name,
                'svg': svg
            })
        except Exception as e:
            results.append({
                'project_id': pid,
                'name': project.name if project else str(pid),
                'error': str(e)
            })

    return success_response(data={'previews': results})


@api_bp.route('/materials/<material_id>/gcode-params')
@login_required
def get_gcode_params(material_id):
    """Get G-code parameters for a material."""
    material = SettingsService.get_material(material_id)
    if not material:
        return error_response('Material not found', 404)

    return success_response(data={
        'id': material.id,
        'gcode_standards': material.gcode_standards
    })
