"""数据集文件存储客户端。"""

import os

from loguru import logger

from app.config import UPLOAD_FOLDER
from app.domain.errors import InvalidStateError
from app.utils.files import secure_filename


class DatasetStorageClient:
    """封装本地数据集文件的读写与删除。"""

    def save(self, file_path: str, content: bytes, dataset_id: int) -> None:
        """将上传内容写入目标路径。"""
        try:
            with open(file_path, "wb") as file:
                file.write(content)
        except OSError:
            logger.exception("保存数据集文件失败，数据集 ID：{}，路径：{}", dataset_id, file_path)
            raise

    def prepare_path(self, filename: str) -> tuple[str, str]:
        """校验文件名并创建数据集存储目录。"""
        safe_name = secure_filename(filename)
        if not safe_name:
            raise InvalidStateError("未选择数据集文件")
        folder = os.path.join(UPLOAD_FOLDER, "datasets")
        os.makedirs(folder, exist_ok=True)
        return safe_name, os.path.join(folder, safe_name)

    def delete(self, file_path: str, dataset_id: int) -> None:
        """删除存在的数据集文件。"""
        if not os.path.exists(file_path):
            return
        try:
            os.remove(file_path)
        except OSError:
            logger.exception("删除数据集文件失败，数据集 ID：{}，路径：{}", dataset_id, file_path)
            raise

    @staticmethod
    def exists(file_path: str) -> bool:
        """判断数据集文件是否存在。"""
        return os.path.isfile(file_path)
