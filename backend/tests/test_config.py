"""配置安全回归测试。"""

import pytest

from app.config import require_env, require_secret_key


def test_missing_required_environment_variable_is_rejected(monkeypatch):
    monkeypatch.delenv("MISSING_REQUIRED_VALUE", raising=False)

    with pytest.raises(RuntimeError, match="MISSING_REQUIRED_VALUE"):
        require_env("MISSING_REQUIRED_VALUE")


def test_default_secret_value_is_rejected(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "TianyaSKY")

    with pytest.raises(RuntimeError, match="默认值"):
        require_secret_key()
