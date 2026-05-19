from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from sqlalchemy import text
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Ensure the SQLite directory exists (prevents "unable to open database file").
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if isinstance(uri, str) and uri.startswith("sqlite:///"):
        sqlite_path = uri.replace("sqlite:///", "", 1)
        sqlite_dir = os.path.dirname(sqlite_path)
        if sqlite_dir:
            os.makedirs(sqlite_dir, exist_ok=True)

    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(customer_bp, url_prefix="/")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    # Set MSSQL session context for Row-Level Security (RLS).
    # RLS predicates read SESSION_CONTEXT to decide which rows are visible.
    # This must run before every request so INSERT/SELECT/UPDATE all pass the predicate.
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "mssql" in uri:
        from flask_login import current_user

        @app.before_request
        def set_rls_session_context():
            try:
                if current_user.is_authenticated:
                    db.session.execute(
                        text("EXEC sp_set_session_context N'user_id', :uid, @read_only=0"),
                        {"uid": current_user.user_id},
                    )
                    db.session.execute(
                        text("EXEC sp_set_session_context N'user_role', :role, @read_only=0"),
                        {"role": current_user.role},
                    )
                else:
                    db.session.execute(
                        text("EXEC sp_set_session_context N'user_id', NULL, @read_only=0")
                    )
                    db.session.execute(
                        text("EXEC sp_set_session_context N'user_role', N'Guest', @read_only=0")
                    )
            except Exception:
                pass  # Non-MSSQL fallback or connection not yet ready

    # Custom error pages — never expose stack traces to users
    from flask import render_template as _rt

    @app.errorhandler(403)
    def forbidden(e):
        return _rt("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return _rt("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return _rt("errors/500.html"), 500

    return app
