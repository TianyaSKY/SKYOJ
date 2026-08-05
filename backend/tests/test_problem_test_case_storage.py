"""测试用例 ZIP 存储安全回归测试。"""

from io import BytesIO
from pathlib import Path
import stat
import zipfile

import pytest

from app.clients import problem_test_case_storage_client as storage_module
from app.clients.problem_test_case_storage_client import (
    ProblemTestCaseStorageClient,
)
from app.domain.errors import InvalidStateError


def make_zip(*members: tuple[str, bytes]) -> bytes:
    """构造测试用 ZIP。"""

    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in members:
            archive.writestr(filename, content)
    return output.getvalue()


def test_valid_zip_replaces_existing_cases_atomically(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))
    old_folder = tmp_path / "problems" / "1"
    old_folder.mkdir(parents=True)
    (old_folder / "old.in").write_text("old", encoding="utf-8")

    files = client.save_zip(
        1,
        "cases.zip",
        make_zip(("1.in", b"input"), ("1.out", b"output")),
    )

    assert files == ["1.in", "1.out"]
    assert not (old_folder / "old.in").exists()
    assert (old_folder / "1.in").read_bytes() == b"input"
    assert (old_folder / "1.out").read_bytes() == b"output"
    assert not list((tmp_path / "problems").glob(".*-upload-*"))
    assert not list((tmp_path / "problems").glob(".*-backup-*"))


def test_path_traversal_member_is_rejected_and_old_cases_remain(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))
    old_folder = tmp_path / "problems" / "1"
    old_folder.mkdir(parents=True)
    old_file = old_folder / "old.in"
    old_file.write_text("old", encoding="utf-8")

    with pytest.raises(InvalidStateError, match="上级路径"):
        client.save_zip(1, "cases.zip", make_zip(("../../outside.txt", b"bad")))

    assert old_file.read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "outside.txt").exists()


def test_absolute_member_is_rejected(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    with pytest.raises(InvalidStateError, match="绝对路径"):
        client.save_zip(1, "cases.zip", make_zip(("/etc/passwd", b"bad")))


def test_windows_absolute_member_is_rejected(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    with pytest.raises(InvalidStateError, match="绝对路径"):
        client.save_zip(1, "cases.zip", make_zip((r"C:\\outside.txt", b"bad")))


def test_symlink_member_is_rejected(tmp_path: Path):
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "../../outside.txt")

    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))
    with pytest.raises(InvalidStateError, match="符号链接"):
        client.save_zip(1, "cases.zip", output.getvalue())


def test_empty_zip_is_rejected(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    with pytest.raises(InvalidStateError, match="没有有效"):
        client.save_zip(1, "cases.zip", make_zip())


def test_corrupt_zip_does_not_delete_existing_cases(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))
    old_folder = tmp_path / "problems" / "1"
    old_folder.mkdir(parents=True)
    old_file = old_folder / "1.in"
    old_file.write_text("old", encoding="utf-8")

    with pytest.raises(InvalidStateError, match="有效的 ZIP"):
        client.save_zip(1, "cases.zip", b"not a zip")

    assert old_file.read_text(encoding="utf-8") == "old"
    assert not list((tmp_path / "problems").glob(".*-upload-*"))


def test_file_count_limit_is_enforced(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(storage_module, "MAX_FILE_COUNT", 1)
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    with pytest.raises(InvalidStateError, match="文件数量"):
        client.save_zip(
            1,
            "cases.zip",
            make_zip(("1.in", b"input"), ("1.out", b"output")),
        )


def test_extracted_size_limit_is_enforced(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(storage_module, "MAX_EXTRACTED_SIZE", 4)
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    with pytest.raises(InvalidStateError, match="总大小"):
        client.save_zip(1, "cases.zip", make_zip(("1.in", b"input")))


def test_has_test_cases_tracks_upload_and_delete(tmp_path: Path):
    client = ProblemTestCaseStorageClient(str(tmp_path / "problems"))

    assert client.has_test_cases(1) is False

    client.save_zip(1, "cases.zip", make_zip(("1.in", b"input")))
    assert client.has_test_cases(1) is True

    client.delete_all(1)
    assert client.has_test_cases(1) is False
