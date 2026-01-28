"""Main routes - home, login, logout."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import login_required, authenticate, logout as auth_logout
from web.services.project_service import ProjectService
from web.services.settings_service import SettingsService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """Home page - list all projects."""
    projects = ProjectService.get_all()
    materials = SettingsService.get_materials_dict()
    return render_template('index.html', projects=projects, materials=materials)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if authenticate(password):
            next_url = request.args.get('next') or url_for('main.index')
            return redirect(next_url)
        flash('Invalid password', 'error')
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    """Logout and redirect to login."""
    auth_logout()
    return redirect(url_for('main.login'))
