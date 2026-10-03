"""配置安全回归测试。"""

import pytest

from app.core.config import require_env, require_secret_key


def test_missing_required_environment_variable_is_rejected(monkeypatch):
    monkeypatch.delenv("MISSING_REQUIRED_VALUE", raising=False)

    with pytest.raises(RuntimeError, match="MISSING_REQUIRED_VALUE"):
        require_env("MISSING_REQUIRED_VALUE")


def test_default_secret_value_is_rejected(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "TianyaSKY")

    with pytest.raises(RuntimeError, match="默认值"):
        require_secret_key()


def test_relocated_config_keeps_project_dotenv_location():
    from pathlib import Path

    from app.core.config import BACKEND_ROOT, PROJECT_ROOT

    assert Path(BACKEND_ROOT) == Path(__file__).resolve().parents[1]
    assert Path(PROJECT_ROOT) == Path(__file__).resolve().parents[2]
