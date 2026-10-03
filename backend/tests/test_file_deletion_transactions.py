"""删除记录失败时恢复文件，数据库成功提交后才最终删除。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.clients.dataset_storage_client import DatasetStorageClient
from app.clients.file_deletion import stage_file_deletion
from app.clients.problem_test_case_storage_client import ProblemTestCaseStorageClient
from app.persistence.database import Base
from app.persistence.dataset import Dataset, DatasetRepository
from app.persistence.problem import Problem, ProblemRepository
from app.persistence.unit_of_work import UnitOfWork
from app.persistence.user import User
from app.services.dataset import DatasetService
from app.services.judge import save_non_acm_script
from app.services.problem import ProblemService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.mark.parametrize("resource", ["problem", "dataset"])
@pytest.mark.parametrize("failure", [None, "flush", "commit"])
def test_deletion_compensates_database_failure(
    tmp_path, monkeypatch, resource, failure
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        uow = UnitOfWork(db)
        if resource == "problem":
            db.add(
                Problem(
                    id=1, title="题目", content="内容", type="acm", language="python"
                )
            )
            folder = tmp_path / "1"
            folder.mkdir()
            files = [folder / "1.in", folder / "1.out"]
            service = ProblemService(
                ProblemRepository(db),
                ProblemTestCaseStorageClient(str(tmp_path)),
                uow=uow,
            )
            delete = service.delete_problem
            model = Problem
        else:
            db.add(User(id=1, username="teacher", password_hash="hash", role="teacher"))
            db.flush()
            files = [tmp_path / "data.csv", tmp_path / "data.csv.pending"]
            db.add(
                Dataset(
                    id=1,
                    name="数据",
                    file_path=str(files[0]),
                    temp_path=str(files[1]),
                    uploader_id=1,
                    status="pending",
                )
            )
            service = DatasetService(
                DatasetRepository(db),
                DatasetStorageClient(str(tmp_path)),
                MagicMock(),
                uow=uow,
            )
            delete = service.delete_dataset
            model = Dataset
        for file in files:
            file.write_text(f"保留 {file.name}")
        db.commit()
        if failure:

            def fail(*args, **kwargs):
                raise RuntimeError("注入数据库失败")

            monkeypatch.setattr(db, failure, fail)
            with pytest.raises(RuntimeError, match="注入数据库失败"):
                delete("teacher", 1)
            monkeypatch.undo()
            assert db.get(model, 1) is not None
            assert all(file.read_text() == f"保留 {file.name}" for file in files)
        else:
            delete("teacher", 1)
            assert db.get(model, 1) is None
            assert all(not file.exists() for file in files)
        assert not list(tmp_path.rglob(".trash/*"))
    engine.dispose()


def test_partial_staging_failure_restores_already_moved_file(tmp_path, monkeypatch):
    files = [tmp_path / "first", tmp_path / "second"]
    for file in files:
        file.write_text(file.name)
    rename = Path.rename

    def fail_second(self, target):
        if self == files[1]:
            raise OSError("暂存失败")
        return rename(self, target)

    monkeypatch.setattr(Path, "rename", fail_second)
    with pytest.raises(OSError, match="暂存失败"), stage_file_deletion(files):
        pytest.fail("文件尚未全部暂存，不能进入数据库删除")
    assert [file.read_text() for file in files] == ["first", "second"]


def test_cleanup_failure_keeps_trash_after_committed_delete(tmp_path, monkeypatch):
    import app.clients.file_deletion as deletion

    folder = tmp_path / "problem"
    folder.mkdir()
    (folder / "1.in").write_text("内容")
    monkeypatch.setattr(
        deletion.shutil, "rmtree", MagicMock(side_effect=OSError("清理失败"))
    )
    with stage_file_deletion([folder]):
        assert not folder.exists()
    assert not folder.exists()
    assert next((tmp_path / ".trash").glob("*/1.in")).read_text() == "内容"


@pytest.mark.parametrize(
    "language,filename",
    [
        (None, "main.py"),
        ("PYTHON", "main.py"),
        ("c", "main.c"),
        ("cpp", "main.cpp"),
        ("java", "Main.java"),
    ],
)
def test_script_storage_preserves_judge_filename(tmp_path, language, filename):
    storage = ProblemTestCaseStorageClient(str(tmp_path))
    success, message = save_non_acm_script(
        1, "脚本内容", "oop", language, storage=storage
    )
    assert success and filename in message
    assert (tmp_path / "1" / filename).read_text() == "脚本内容"


def test_script_storage_failure_returns_public_error():
    storage = MagicMock(spec=ProblemTestCaseStorageClient)
    storage.save_script.side_effect = PermissionError("private-storage-path")
    success, message = save_non_acm_script(1, "code", "oop", "python", storage=storage)
    assert not success
    assert "private-storage-path" not in message
