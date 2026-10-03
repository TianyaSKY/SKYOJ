"""提交附件文件存储客户端。"""

import os
import shutil
import tempfile
from pathlib import Path

from loguru import logger

from app.core.files import secure_filename


def legacy_submission_path(content: str, user_id: int, problem_id: int) -> str | None:
    """旧记录未标记附件，只兼容当前用户及题目在提交目录内的历史路径。"""
    root = Path("uploads/submissions")
    candidate = Path(content)
    try:
        relative = candidate.relative_to(root)
        prefix = f"{user_id}_{problem_id}_"
        if len(relative.parts) not in (1, 2) or not relative.parts[0].startswith(prefix):
            return None
        resolved = candidate.resolve().relative_to(root.resolve())
        if len(resolved.parts) not in (1, 2) or not resolved.parts[0].startswith(prefix):
            return None
    except (ValueError, OSError):
        return None
    return str(candidate)


class SubmissionStorageClient:
    """封装 CSV 等提交附件的本地文件保存。"""

    def __init__(self, base_dir: str = "uploads/submissions") -> None:
        self._base_dir = base_dir

    def save(self, user_id: int, problem_id: int, filename: str, content: bytes) -> str:
        """保存附件并返回判题服务可使用的本地路径。"""
        safe_name = secure_filename(filename)
        if not safe_name:
            raise ValueError("提交文件名无效")
        os.makedirs(self._base_dir, exist_ok=True)
        # 目录由操作系统原子分配，同名及并发上传均不能覆盖其他提交。
        upload_dir = tempfile.mkdtemp(prefix=f"{user_id}_{problem_id}_", dir=self._base_dir)
        path = os.path.join(upload_dir, safe_name)
        try:
            with open(path, "xb") as output:
                output.write(content)
        except OSError:
            try:
                shutil.rmtree(upload_dir)
            except OSError:
                logger.exception("清理失败的提交附件目录失败 path={}", upload_dir)
            raise
        return path
