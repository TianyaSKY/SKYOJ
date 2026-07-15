import os

if os.path.exists("/.dockerenv"):
    _db_host = "mysql"
else:
    _db_host = "127.0.0.1"

DEFAULT_DATABASE_URL = f"mysql+pymysql://root:root@{_db_host}:3306/oj_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
SECRET_KEY = os.getenv("SECRET_KEY", "TianyaSKY")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

# Absolute path to backend package root (backend/)
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
