"""Simple password authentication."""
from functools import wraps
from datetime import datetime, UTC, timedelta

from flask import current_app, session, redirect, url_for, request


def is_authenticated():
    """Check if the current session is authenticated."""
    if not current_app.config.get('APP_PASSWORD'):
        return True  # No password configured, allow access

    if not session.get('authenticated'):
        return False

    # Check session timeout
    auth_time = session.get('auth_time')
    if auth_time:
        timeout_minutes = current_app.config.get('SESSION_TIMEOUT_MINUTES', 480)
        expiry = datetime.fromisoformat(auth_time) + timedelta(minutes=timeout_minutes)
        if datetime.now(UTC) > expiry:
            session.clear()
            return False

    return True


def login_required(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def authenticate(password):
    """Attempt to authenticate with the given password."""
    app_password = current_app.config.get('APP_PASSWORD')
    if not app_password:
        return True  # No password configured
    if password == app_password:
        session['authenticated'] = True
        session['auth_time'] = datetime.now(UTC).isoformat()
        session.permanent = True
        return True
    return False


def logout():
    """Clear the authentication session."""
    session.pop('authenticated', None)
