import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))

load_dotenv(Path(PROJECT_ROOT) / ".env", override=False)

IN_DOCKER = os.path.exists("/.dockerenv")
db_host = "mysql" if IN_DOCKER else "127.0.0.1"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://root:root@{db_host}:3306/oj_db",
)
# 本地开发时把 Docker 主机名换成 127.0.0.1
if not IN_DOCKER:
    DATABASE_URL = DATABASE_URL.replace("@mysql:", "@127.0.0.1:")

SECRET_KEY = os.getenv("SECRET_KEY", "TianyaSKY")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
