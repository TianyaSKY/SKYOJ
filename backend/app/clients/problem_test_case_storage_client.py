"""题目测试用例文件存储客户端。"""

import io
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat
import uuid
import zipfile

from app.domain.errors import InvalidStateError, ResourceNotFoundError


MAX_ARCHIVE_SIZE = 100 * 1024 * 1024
MAX_EXTRACTED_SIZE = 500 * 1024 * 1024
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_FILE_COUNT = 2000
_COPY_BUFFER_SIZE = 1024 * 1024


class ProblemTestCaseStorageClient:
    """封装测试用例 ZIP 文件的安全写入、清理和打包下载。"""

    def __init__(self, base_dir: str = "uploads/problems") -> None:
        self._base_dir = Path(base_dir)

    def save_zip(self, problem_id: int, filename: str, content: bytes) -> list[str]:
        """安全保存并解压测试用例 ZIP，返回解压后的文件列表。"""

        if not filename or not filename.strip():
            raise InvalidStateError("未选择测试用例文件")
        if len(content) > MAX_ARCHIVE_SIZE:
            raise InvalidStateError("测试用例 ZIP 超过 100MB")

        target = self._folder(problem_id)
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)

        temporary = parent / f".{problem_id}-upload-{uuid.uuid4().hex}"
        backup = parent / f".{problem_id}-backup-{uuid.uuid4().hex}"
        temporary.mkdir()

        backup_created = False
        target_installed = False
        try:
            with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
                extracted_files = self._extract_archive(archive, temporary)

            if not extracted_files:
                raise InvalidStateError("ZIP 中没有有效测试文件")

            if self._path_exists(target):
                target.rename(backup)
                backup_created = True

            temporary.rename(target)
            target_installed = True

            if backup_created:
                self._remove_path(backup)

            return extracted_files
        except (
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
            NotImplementedError,
            RuntimeError,
        ) as exc:
            raise InvalidStateError("测试用例文件不是有效的 ZIP 文件") from exc
        except Exception:
            # 新目录已经安装但后续清理失败时，先删除新目录，再恢复旧目录。
            if target_installed and self._path_exists(target):
                self._remove_path(target)
            if (
                backup_created
                and self._path_exists(backup)
                and not self._path_exists(target)
            ):
                backup.rename(target)
            raise
        finally:
            if self._path_exists(temporary):
                self._remove_path(temporary)

    def delete_all(self, problem_id: int) -> None:
        """删除题目的所有测试用例文件。"""

        folder = self._folder(problem_id)
        if not self._path_exists(folder):
            raise ResourceNotFoundError("测试用例目录不存在")
        self._remove_path(folder)

    def has_test_cases(self, problem_id: int) -> bool:
        """题目是否已上传测试用例（目录存在且非空）。"""

        folder = self._folder(problem_id)
        return folder.is_dir() and any(folder.iterdir())

    def build_archive(self, problem_id: int) -> bytes:
        """将测试用例目录打包为 ZIP 字节流。"""

        folder = self._folder(problem_id)
        if not folder.is_dir() or not any(folder.iterdir()):
            raise ResourceNotFoundError("测试用例不存在")

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, directories, files in folder.walk():
                directories[:] = [
                    name for name in directories if not (root / name).is_symlink()
                ]
                for filename in files:
                    path = root / filename
                    if path.is_symlink():
                        continue
                    archive.write(path, path.relative_to(folder).as_posix())
        return output.getvalue()

    def delete_problem_directory(self, problem_id: int) -> None:
        """删除题目文件目录；目录不存在时不报错。"""

        folder = self._folder(problem_id)
        if self._path_exists(folder):
            self._remove_path(folder)

    def _extract_archive(
        self,
        archive: zipfile.ZipFile,
        destination: Path,
    ) -> list[str]:
        """逐文件校验并解压 ZIP，避免使用不受控的 extractall。"""

        members = archive.infolist()
        if len(members) > MAX_FILE_COUNT:
            raise InvalidStateError("ZIP 内文件数量过多")

        extracted_files: list[str] = []
        seen_paths: set[str] = set()
        total_size = 0

        for info in members:
            if self._is_symlink(info):
                raise InvalidStateError("ZIP 中不允许包含符号链接")

            target = self._validate_member_path(destination, info.filename)
            relative_path = target.relative_to(destination).as_posix()
            if relative_path in seen_paths:
                raise InvalidStateError("ZIP 中包含重复文件路径")
            seen_paths.add(relative_path)

            if info.is_dir():
                if target.exists() and not target.is_dir():
                    raise InvalidStateError("ZIP 中包含冲突路径")
                target.mkdir(parents=True, exist_ok=True)
                continue

            if info.file_size < 0 or info.file_size > MAX_FILE_SIZE:
                raise InvalidStateError(f"文件过大：{info.filename}")

            total_size += info.file_size
            if total_size > MAX_EXTRACTED_SIZE:
                raise InvalidStateError("ZIP 解压后的总大小超过限制")

            if target.parent.exists() and not target.parent.is_dir():
                raise InvalidStateError("ZIP 中包含冲突路径")
            if target.exists():
                raise InvalidStateError("ZIP 中包含冲突路径")
            target.parent.mkdir(parents=True, exist_ok=True)
            written_size = 0
            with archive.open(info, "r") as source, target.open("xb") as output:
                while True:
                    chunk = source.read(_COPY_BUFFER_SIZE)
                    if not chunk:
                        break
                    written_size += len(chunk)
                    if written_size > MAX_FILE_SIZE:
                        raise InvalidStateError(f"文件过大：{info.filename}")
                    output.write(chunk)

            if written_size != info.file_size:
                raise InvalidStateError(f"ZIP 文件大小校验失败：{info.filename}")

            extracted_files.append(relative_path)

        return extracted_files

    @staticmethod
    def _validate_member_path(root: Path, member_name: str) -> Path:
        """校验 ZIP 成员路径，并返回位于 root 下的目标路径。"""

        if not member_name or "\x00" in member_name:
            raise InvalidStateError("ZIP 中包含空或非法文件名")

        normalized = PurePosixPath(member_name.replace("\\", "/"))
        windows_path = PureWindowsPath(member_name)
        if (
            normalized.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
        ):
            raise InvalidStateError("ZIP 中包含绝对路径")
        if ".." in normalized.parts:
            raise InvalidStateError("ZIP 中包含非法上级路径")
        if not normalized.parts:
            raise InvalidStateError("ZIP 中包含空文件名")

        root_resolved = root.resolve()
        target = (root / Path(*normalized.parts)).resolve()
        try:
            target.relative_to(root_resolved)
        except ValueError as exc:
            raise InvalidStateError("ZIP 中包含目录穿越路径") from exc
        return target

    @staticmethod
    def _is_symlink(info: zipfile.ZipInfo) -> bool:
        """判断 ZIP 成员是否声明为符号链接。"""

        mode = info.external_attr >> 16
        return stat.S_ISLNK(mode)

    @staticmethod
    def _path_exists(path: Path) -> bool:
        """同时识别普通路径和悬空符号链接。"""

        return path.exists() or path.is_symlink()

    @staticmethod
    def _remove_path(path: Path) -> None:
        """安全删除目录、文件或符号链接本身。"""

        if path.is_symlink() or not path.is_dir():
            path.unlink()
            return
        shutil.rmtree(path)

    def _folder(self, problem_id: int) -> Path:
        return self._base_dir / str(problem_id)
