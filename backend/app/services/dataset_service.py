"""数据集旧导入路径兼容层；新代码使用 app.services.dataset。"""

from app.services.dataset import (
    DatasetService,
)

__all__ = ['DatasetService']
