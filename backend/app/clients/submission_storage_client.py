"""提交附件文件存储客户端。"""

import os

from app.utils.files import secure_filename


class SubmissionStorageClient:
    """封装 CSV 等提交附件的本地文件保存。"""

    def __init__(self, base_dir: str = "uploads/submissions") -> None:
        self._base_dir = base_dir

    def save(
        self, user_id: int, problem_id: int, filename: str, content: bytes
    ) -> str:
        """保存附件并返回判题服务可使用的本地路径。"""
        safe_name = secure_filename(filename)
        if not safe_name:
            raise ValueError("提交文件名无效")
        os.makedirs(self._base_dir, exist_ok=True)
        path = os.path.join(self._base_dir, f"{user_id}_{problem_id}_{safe_name}")
        with open(path, "wb") as output:
            output.write(content)
        return path
