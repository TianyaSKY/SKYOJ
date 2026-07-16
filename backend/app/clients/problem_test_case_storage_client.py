"""题目测试用例文件存储客户端。"""

import io
import os
import shutil
import zipfile

from app.domain.errors import InvalidStateError, ResourceNotFoundError
from app.utils.files import secure_filename


class ProblemTestCaseStorageClient:
    """封装测试用例 ZIP 文件的写入、清理和打包下载。"""

    def __init__(self, base_dir: str = "uploads/problems") -> None:
        self._base_dir = base_dir

    def save_zip(self, problem_id: int, filename: str, content: bytes) -> list[str]:
        """保存并解压测试用例 ZIP，返回解压后的文件列表。"""
        safe_name = secure_filename(filename)
        if not safe_name:
            raise InvalidStateError("未选择测试用例文件")
        folder = self._folder(problem_id)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)
        zip_path = os.path.join(folder, safe_name)
        with open(zip_path, "wb") as output:
            output.write(content)
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(folder)
            os.remove(zip_path)
        except zipfile.BadZipFile as exc:
            shutil.rmtree(folder, ignore_errors=True)
            raise InvalidStateError("测试用例文件不是有效的 ZIP 文件") from exc
        return os.listdir(folder)

    def delete_all(self, problem_id: int) -> None:
        """删除题目的所有测试用例文件。"""
        folder = self._folder(problem_id)
        if not os.path.exists(folder):
            raise ResourceNotFoundError("测试用例目录不存在")
        shutil.rmtree(folder)

    def build_archive(self, problem_id: int) -> bytes:
        """将测试用例目录打包为 ZIP 字节流。"""
        folder = self._folder(problem_id)
        if not os.path.isdir(folder) or not os.listdir(folder):
            raise ResourceNotFoundError("测试用例不存在")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, _directories, files in os.walk(folder):
                for filename in files:
                    path = os.path.join(root, filename)
                    archive.write(path, os.path.relpath(path, folder))
        return output.getvalue()

    def delete_problem_directory(self, problem_id: int) -> None:
        """删除题目文件目录；目录不存在时不报错。"""
        folder = self._folder(problem_id)
        if os.path.exists(folder):
            shutil.rmtree(folder)

    def _folder(self, problem_id: int) -> str:
        return os.path.join(self._base_dir, str(problem_id))
