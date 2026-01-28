from flask import Flask
from flask_cors import CORS

from config import Config
from web.extensions import db, migrate


def create_app(config_class=Config):
    """Application factory for creating Flask app instances."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure CORS - allow same origin by default
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Import and register blueprints inside factory to avoid circular imports
    from web.routes.main import main_bp
    from web.routes.projects import projects_bp
    from web.routes.settings import settings_bp
    from web.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app


# Create app instance for gunicorn and flask CLI
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
