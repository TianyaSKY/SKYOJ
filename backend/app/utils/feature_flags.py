import os


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# 临时开关：默认关闭深度学习语义搜索与判重
ENABLE_SEMANTIC_SEARCH = _env_bool("ENABLE_SEMANTIC_SEARCH", False)
ENABLE_PLAGIARISM = _env_bool("ENABLE_PLAGIARISM", False)
