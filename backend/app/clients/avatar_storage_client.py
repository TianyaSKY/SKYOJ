"""用户头像文件存储客户端。"""

import os
import uuid

from app.config import BACKEND_ROOT
from app.domain.errors import ResourceNotFoundError
from app.utils.files import secure_filename


class AvatarStorageClient:
    """封装本地头像文件的保存和读取。"""

    _allowed_extensions = {"png", "jpg", "jpeg", "gif"}

    def save(self, filename: str, content: bytes) -> str:
        """校验并保存头像，返回 API 可访问路径。"""
        safe_name = secure_filename(filename)
        if "." not in safe_name:
            raise ValueError("头像文件类型不受支持")
        extension = safe_name.rsplit(".", 1)[1].lower()
        if extension not in self._allowed_extensions:
            raise ValueError("头像文件类型不受支持")

        stored_name = f"{uuid.uuid4().hex}.{extension}"
        folder = self._folder()
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, stored_name), "wb") as output:
            output.write(content)
        return f"/api/user/avatars/{stored_name}"

    def get_path(self, filename: str) -> str:
        """返回存在的头像文件路径。"""
        safe_name = secure_filename(filename)
        path = os.path.join(self._folder(), safe_name)
        if not os.path.isfile(path):
            raise ResourceNotFoundError("头像文件不存在")
        return path

    @staticmethod
    def _folder() -> str:
        return os.path.join(BACKEND_ROOT, "uploads", "avatars")
