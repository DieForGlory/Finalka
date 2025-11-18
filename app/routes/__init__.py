# app/routes/__init__.py
from .main import main_bp
from .auth import auth_bp
from .admin import admin_bp
from .templates import templates_bp
from .dictionaries import dictionaries_bp

def register_routes(app):
    """
    Регистрирует все Blueprint'ы в приложении Flask.
    """
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(templates_bp, url_prefix='/templates')
    app.register_blueprint(dictionaries_bp, url_prefix='/dictionaries')