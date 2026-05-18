from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
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

    return app
