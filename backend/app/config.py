import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))

load_dotenv(Path(PROJECT_ROOT) / ".env", override=False)

IN_DOCKER = os.path.exists("/.dockerenv")

_INSECURE_SECRET_VALUES = {
    "TianyaSKY",
    "change-me",
    "replace_with_random_secret",
}


def require_env(name: str) -> str:
    """读取必需环境变量；缺失或为空时拒绝启动。"""

    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"缺少必需环境变量：{name}")
    return value.strip()


def require_database_url() -> str:
    """读取数据库连接串，并禁止后端使用 MySQL root 用户。"""

    value = require_env("DATABASE_URL")
    if urlsplit(value).username == "root":
        raise RuntimeError("DATABASE_URL 不允许使用 MySQL root 用户")
    return value


def require_secret_key() -> str:
    """读取密钥并拒绝仓库中约定的默认占位值。"""

    value = require_env("SECRET_KEY")
    if value in _INSECURE_SECRET_VALUES:
        raise RuntimeError("SECRET_KEY 仍然是默认值，请重新生成")
    return value


DATABASE_URL = require_database_url()
SECRET_KEY = require_secret_key()

# 本地开发时把 Docker 主机名换成 127.0.0.1；容器内保留 mysql 服务名。
if not IN_DOCKER:
    DATABASE_URL = DATABASE_URL.replace("@mysql:", "@127.0.0.1:")

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
