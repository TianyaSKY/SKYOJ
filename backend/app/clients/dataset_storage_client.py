"""数据集文件存储客户端。"""

import hashlib
import os
from pathlib import Path
from typing import BinaryIO
import uuid

from loguru import logger

from app.config import UPLOAD_FOLDER
from app.domain.errors import InvalidStateError
from app.utils.files import secure_filename


class DatasetStorageClient:
    """封装本地数据集文件的暂存、校验、落盘与删除。"""

    MAX_FILE_SIZE = 500 * 1024 * 1024
    COPY_BUFFER_SIZE = 1024 * 1024

    def save(self, file_path: str, content: bytes, dataset_id: int) -> None:
        """将上传内容写入目标路径。"""
        try:
            with open(file_path, "wb") as file:
                file.write(content)
        except OSError:
            logger.exception("保存数据集文件失败，数据集 ID：{}，路径：{}", dataset_id, file_path)
            raise

    def stage_upload(
        self,
        content: bytes | BinaryIO,
        file_path: str,
    ) -> tuple[str, int]:
        """将上传流写入临时文件，返回临时路径和字节数。"""
        parent = Path(file_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        temporary_path = f"{file_path}.pending-{uuid.uuid4().hex}"
        total_size = 0
        try:
            with open(temporary_path, "wb") as output:
                if isinstance(content, bytes):
                    chunks = (content,)
                else:
                    try:
                        content.seek(0)
                    except (AttributeError, OSError):
                        pass
                    chunks = iter(lambda: content.read(self.COPY_BUFFER_SIZE), b"")

                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise InvalidStateError("上传文件流必须返回字节")
                    total_size += len(chunk)
                    if total_size > self.MAX_FILE_SIZE:
                        raise InvalidStateError("数据集文件超过 500MB 限制")
                    output.write(chunk)
        except Exception:
            self.remove_staged(temporary_path)
            raise
        return temporary_path, total_size

    def finalize(
        self,
        temporary_path: str,
        file_path: str,
        dataset_id: int,
    ) -> tuple[int, str]:
        """校验临时文件并原子移动到正式路径，返回大小和 SHA-256。"""
        if not os.path.isfile(temporary_path):
            raise InvalidStateError("数据集临时文件不存在")

        digest = hashlib.sha256()
        total_size = 0
        try:
            with open(temporary_path, "rb") as source:
                while True:
                    chunk = source.read(self.COPY_BUFFER_SIZE)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.MAX_FILE_SIZE:
                        raise InvalidStateError("数据集文件超过 500MB 限制")
                    digest.update(chunk)

            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary_path, file_path)
        except OSError:
            logger.exception("数据集文件落盘失败，数据集 ID：{}，路径：{}", dataset_id, file_path)
            raise
        return total_size, digest.hexdigest()

    @staticmethod
    def remove_staged(file_path: str) -> None:
        """删除尚未落盘的临时文件。"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            logger.exception("删除数据集临时文件失败，路径：{}", file_path)

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
