import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def build_database_uri():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    db_engine = os.environ.get("DB_ENGINE", "").lower()
    if db_engine in {"mssql", "sqlserver"} or os.environ.get("MSSQL_SERVER"):
        server = os.environ.get("MSSQL_SERVER", "localhost")
        database = os.environ.get("MSSQL_DATABASE", "FoodOrderingDB")
        driver = os.environ.get("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
        encrypt = os.environ.get("MSSQL_ENCRYPT", "no")
        trust_server_certificate = os.environ.get("MSSQL_TRUST_SERVER_CERTIFICATE", "yes")

        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={database}",
            f"Encrypt={encrypt}",
            f"TrustServerCertificate={trust_server_certificate}",
        ]

        username = os.environ.get("MSSQL_USERNAME")
        password = os.environ.get("MSSQL_PASSWORD")
        if username and password:
            parts.extend([f"UID={username}", f"PWD={password}"])
        else:
            parts.append("Trusted_Connection=yes")

        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(";".join(parts))

    return "sqlite:///" + os.path.join(basedir, "instance", "food_ordering.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is required. Set it in your environment or .env")

    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Session hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
