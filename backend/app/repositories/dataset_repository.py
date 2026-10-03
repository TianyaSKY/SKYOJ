"""数据集旧导入路径兼容层；新代码使用 app.persistence.dataset。"""

from app.persistence.dataset import (
    DatasetRepository,
)

__all__ = ['DatasetRepository']
