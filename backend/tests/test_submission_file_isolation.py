"""每次提交保存独立附件，异步判题不能读到后续同名上传的内容。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.clients.submission_storage_client import SubmissionStorageClient
from app.persistence.submission import SubmissionRepository
from app.persistence.unit_of_work import UnitOfWork
from app.services.submission import SubmissionService, SubmitParams


def test_repeated_csv_submissions_keep_their_own_contents(db_session, student_user, sample_problem, tmp_path):
    sample_problem.type = 'kaggle'
    db_session.commit()
    repo = SubmissionRepository(db_session)
    jobs = MagicMock()
    service = SubmissionService(repo, jobs, SubmissionStorageClient(str(tmp_path)), uow=UnitOfWork(db_session))
    results = []
    for value in [b'id,value\n1,10\n', b'id,value\n1,20\n']:
        results.append(service.submit(SubmitParams(
            user_id=student_user.id, problem_id=sample_problem.id, code='__file_upload__', language='csv',
            is_file_upload=True, filename='prediction.csv', file_content=value,
        ), requester_role='student'))
        db_session.commit()
    paths = [Path(repo.get_by_id(result.submission_id).code_content) for result in results]
    assert paths[0] != paths[1]
    assert [path.read_bytes() for path in paths] == [b'id,value\n1,10\n', b'id,value\n1,20\n']
    assert jobs.enqueue_judge_submission.call_count == 2


def test_concurrent_uploads_with_sanitized_identical_names_do_not_collide(tmp_path):
    storage = SubmissionStorageClient(str(tmp_path))

    def upload(index):
        content = str(index).encode()
        name = 'answer?.csv' if index % 2 else 'answer*.csv'
        return Path(storage.save(1, 1, name, content)), content

    with ThreadPoolExecutor(max_workers=4) as workers:
        files = list(workers.map(upload, range(8)))
    assert len({path for path, _ in files}) == 8
    assert all(path.read_bytes() == content for path, content in files)
    assert all(path.is_relative_to(tmp_path) for path, _ in files)


def test_failed_upload_does_not_leave_new_directory(tmp_path, monkeypatch):
    from app.clients import submission_storage_client

    def fail_open(*args, **kwargs):
        raise PermissionError('write denied')

    monkeypatch.setattr(submission_storage_client, 'open', fail_open, raising=False)
    with pytest.raises(PermissionError, match='write denied'):
        SubmissionStorageClient(str(tmp_path)).save(1, 1, 'answer.csv', b'csv')
    assert list(tmp_path.iterdir()) == []
