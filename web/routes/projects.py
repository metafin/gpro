"""Project routes - CRUD operations."""
import json

from flask import Blueprint, render_template, request, redirect, url_for, abort, flash

from web.auth import login_required
from web.services.project_service import ProjectService
from web.services.settings_service import SettingsService

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/new')
@login_required
def new():
    """New project form."""
    materials = SettingsService.get_all_materials()
    return render_template('project/new.html', materials=materials)


@projects_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create a new project and redirect to edit."""
    name = request.form.get('name', 'Untitled Project')
    project_type = request.form.get('project_type', 'drill')
    material_id = request.form.get('material_id')

    project = ProjectService.create({
        'name': name,
        'project_type': project_type,
        'material_id': material_id if material_id else None
    })

    return redirect(url_for('projects.edit', project_id=project.id))


@projects_bp.route('/<project_id>')
@login_required
def edit(project_id):
    """Project editor page."""
    project = ProjectService.get(project_id)
    if not project:
        abort(404)

    return render_template('project/edit.html',
        project=project,
        project_json=json.dumps(ProjectService.get_as_dict(project_id)),
        materials_json=json.dumps(SettingsService.get_materials_dict()),
        tools_json=json.dumps(SettingsService.get_tools_as_list()),
        machine_json=json.dumps(SettingsService.get_machine_settings_dict())
    )


@projects_bp.route('/<project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    """Delete a project."""
    if ProjectService.delete(project_id):
        flash('Project deleted', 'success')
    else:
        flash('Project not found', 'error')
    return redirect(url_for('main.index'))


@projects_bp.route('/<project_id>/duplicate', methods=['POST'])
@login_required
def duplicate(project_id):
    """Duplicate a project."""
    new_name = request.form.get('name')
    new_project = ProjectService.duplicate(project_id, new_name)

    if new_project:
        flash('Project duplicated', 'success')
        return redirect(url_for('projects.edit', project_id=new_project.id))
    else:
        flash('Project not found', 'error')
        return redirect(url_for('main.index'))
