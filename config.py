import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Flask application configuration."""

    # Flask core
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Database
    # Heroku uses postgres:// but SQLAlchemy requires postgresql://
    _database_url = os.environ.get('DATABASE_URL', 'sqlite:///gcode.db')
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Authentication
    APP_PASSWORD = os.environ.get('APP_PASSWORD')  # None means no auth required
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 480))  # 8 hours

    # Session security
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
