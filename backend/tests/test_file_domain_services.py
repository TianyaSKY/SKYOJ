from types import SimpleNamespace

import pytest

from app.domain.dataset import UploadDatasetParams
from app.domain.errors import PermissionDeniedError, ResourceNotFoundError
from app.domain.problem import UploadTestCasesParams
from app.services.dataset_service import DatasetService
from app.services.problem_service import ProblemService


class FakeDatasetRepository:
    """用于验证数据集服务的内存仓储。"""

    def __init__(self) -> None:
        self.items = []

    def create(self, **values):
        item = SimpleNamespace(
            id=len(self.items) + 1,
            uploader=SimpleNamespace(username="teacher"),
            created_at=None,
            **values,
        )
        self.items.append(item)
        return item

    def get_by_id(self, dataset_id: int):
        return next((item for item in self.items if item.id == dataset_id), None)

    def list(self, page=None, page_size=None):
        return self.items, len(self.items)

    def delete(self, item) -> None:
        self.items.remove(item)


class FakeDatasetStorage:
    """记录数据集文件操作的存储客户端替身。"""

    def __init__(self) -> None:
        self.deleted = []

    def prepare_path(self, filename: str):
        return filename, f"uploads/datasets/{filename}"

    def stage_upload(self, content, file_path: str):
        return f"{file_path}.pending", len(content)

    def remove_staged(self, path: str) -> None:
        pass

    def delete(self, path: str, dataset_id: int) -> None:
        self.deleted.append((path, dataset_id))

    def exists(self, path: str) -> bool:
        return True


class FakeFileJobService:
    """记录 File Worker 任务。"""

    def __init__(self) -> None:
        self.calls = []

    def enqueue_finalize_dataset(self, dataset_id: int) -> None:
        self.calls.append(dataset_id)


def test_dataset_service_checks_role_and_submits_file_job() -> None:
    repository = FakeDatasetRepository()
    storage = FakeDatasetStorage()
    task = FakeFileJobService()
    service = DatasetService(repository, storage, task)

    with pytest.raises(PermissionDeniedError):
        service.upload_dataset(
            UploadDatasetParams("student", 1, "sample.csv", b"a,b\n1,2")
        )

    result = service.upload_dataset(
        UploadDatasetParams("teacher", 1, "sample.csv", b"a,b\n1,2")
    )

    assert result.name == "sample.csv"
    assert result.file_path == "uploads/datasets/sample.csv"
    assert task.calls == [result.id]


class FakeProblemRepository:
    """用于验证测试用例服务行为的题目仓储。"""

    def __init__(self) -> None:
        self.problem = SimpleNamespace(
            id=1,
            title="题目",
            content="内容",
            type="acm",
            language="python",
            time_limit=1000,
            memory_limit=256,
            template_code="",
            test_case_path=None,
            created_at=None,
        )

    def get_by_id(self, problem_id: int):
        return self.problem if problem_id == 1 else None


class FakeTestCaseStorage:
    """记录测试用例文件操作。"""

    def save_zip(self, problem_id: int, filename: str, content: bytes):
        return ["1.in", "1.out"]

    def delete_all(self, problem_id: int) -> None:
        pass

    def build_archive(self, problem_id: int) -> bytes:
        return b"zip"

    def delete_problem_directory(self, problem_id: int) -> None:
        pass


def test_problem_test_case_operations_require_teacher_and_problem() -> None:
    service = ProblemService(FakeProblemRepository(), FakeTestCaseStorage())

    with pytest.raises(PermissionDeniedError):
        service.upload_test_cases(
            "student", UploadTestCasesParams(1, "cases.zip", b"zip")
        )
    with pytest.raises(ResourceNotFoundError):
        service.upload_test_cases(
            "teacher", UploadTestCasesParams(2, "cases.zip", b"zip")
        )

    assert service.upload_test_cases(
        "teacher", UploadTestCasesParams(1, "cases.zip", b"zip")
    ) == ["1.in", "1.out"]
    assert service.download_test_cases("teacher", 1) == b"zip"
