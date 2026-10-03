"""数据集收拢回归：快照边界、HTTP 契约和兼容导出。"""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from app.api.deps import get_dataset_service
from app.persistence.dataset import Dataset, DatasetRepository
from app.services.dataset import DatasetRecord, DatasetService, PaginatedDatasets


def create_dataset(repository, uploader_id):
    return repository.create(
        name="data.csv",
        description="",
        file_path="uploads/datasets/data.csv",
        file_size="1 KB",
        uploader_id=uploader_id,
        temp_path="tmp/data.pending",
    )


def test_repository_returns_snapshots_and_updates_file_state(db_session, teacher_user):
    repository = DatasetRepository(db_session)
    record = create_dataset(repository, teacher_user.id)
    assert isinstance(record, DatasetRecord)
    assert record.uploader == teacher_user.username
    with pytest.raises(FrozenInstanceError):
        record.status = "ready"

    ready = repository.mark_ready(record.id, file_size="2 KB", file_hash="abc")
    assert ready.status == "ready"
    assert ready.temp_path is None
    assert record.status == "pending"
    failed = repository.mark_failed(record.id, "x" * 2100)
    assert failed.status == "failed"
    assert len(failed.error_message) == 2000
    db_session.expunge_all()
    assert ready.uploader == teacher_user.username
    assert ready.file_hash == "abc"


def test_service_lists_and_deletes_snapshots(db_session, teacher_user):
    repository = DatasetRepository(db_session)
    record = create_dataset(repository, teacher_user.id)
    storage = MagicMock()
    service = DatasetService(repository, storage, MagicMock())
    result = service.list_datasets(page=1, page_size=1)
    assert isinstance(result, PaginatedDatasets)
    assert result.total == 1
    assert result.datasets[0].uploader == teacher_user.username
    assert service.list_datasets(page=2, page_size=1).datasets == []
    assert service.get_dataset(record.id).temp_path == "tmp/data.pending"
    service.delete_dataset("teacher", record.id)
    storage.delete.assert_called_once_with(record.file_path, record.id)
    storage.remove_staged.assert_called_once_with(record.temp_path)
    assert repository.get_by_id(record.id) is None


def test_dataset_api_keeps_list_and_download_contracts(client, teacher_token, db_session, teacher_user):
    repository = DatasetRepository(db_session)
    record = create_dataset(repository, teacher_user.id)
    repository.mark_ready(record.id, file_size="2 KB", file_hash="abc")
    service = DatasetService(repository, MagicMock(), MagicMock())
    from app.main import app

    app.dependency_overrides[get_dataset_service] = lambda: service
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = client.get("/api/datasets", headers=headers)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["uploader"] == teacher_user.username
    assert item["status"] == "ready"
    assert item["download_url"] == f"/api/datasets/{record.id}/download"
    paginated = client.get("/api/datasets?page=1&page_size=1", headers=headers)
    assert paginated.status_code == 200
    assert paginated.json()["datasets"] == [item]
    assert paginated.json()["total"] == 1
    assert service.download_dataset(record.id).filename == "data.csv"
    deleted = client.delete(f"/api/datasets/{record.id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Dataset deleted successfully"}
    assert client.get(f"/api/datasets/{record.id}/download", headers=headers).status_code == 404
