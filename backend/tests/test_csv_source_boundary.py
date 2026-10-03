"""CSV 文本与服务器附件路径必须明确区分，并约束旧记录的兼容范围。"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.clients.submission_storage_client import SubmissionStorageClient, legacy_submission_path
from app.judging import kaggle
from app.persistence.submission import Submission, SubmissionRepository
from app.persistence.unit_of_work import UnitOfWork
from app.services import judge
from app.services.submission import SubmissionService, SubmitParams


def test_csv_text_matching_existing_server_file_is_not_read(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    folder = Path('uploads/problems/1')
    folder.mkdir(parents=True)
    for name in ['main.py', 'truth.csv']:
        (folder / name).write_text('private teacher data')
    runner = MagicMock()
    runner.__enter__.return_value = runner
    runner.exec_run.return_value = (0, '100')
    monkeypatch.setattr(kaggle, 'SandboxRunner', lambda: runner)
    monkeypatch.setattr(kaggle, 'ProblemRepository', lambda db: SimpleNamespace(
        get_by_id=lambda pid: SimpleNamespace(memory_limit=128, time_limit=1000),
    ))
    source = str(folder / 'truth.csv')
    assert kaggle.run_kaggle_judge(1, source, 1, db=object())[:2] == ('Accepted', 100)
    runner.put_file_from_path.assert_not_called()
    assert runner.put_file.call_args_list[0].args == ('submission.csv', source)

    runner.reset_mock()
    assert kaggle.run_kaggle_judge(1, '', 1, db=object(), source_path=source)[:2] == ('Accepted', 100)
    runner.put_file_from_path.assert_called_once_with(str(Path(source).resolve()), 'submission.csv')


@pytest.mark.parametrize('source', [
    'uploads/problems/1/truth.csv', '/etc/passwd',
    'uploads/submissions/2_1_answer.csv', 'uploads/submissions/1_2_answer.csv',
    'uploads/submissions/1_1_dir/../../problems/1/truth.csv',
])
def test_legacy_paths_cannot_read_outside_owned_submission(source, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert legacy_submission_path(source, 1, 1) is None


def test_legacy_owned_uploads_remain_supported_but_symlinks_do_not(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = Path('uploads/submissions')
    root.mkdir(parents=True)
    for source in ['uploads/submissions/1_1_answer.csv', 'uploads/submissions/1_1_unique/answer.csv']:
        assert legacy_submission_path(source, 1, 1) == source
    private = tmp_path / 'private.csv'
    private.write_text('private')
    (root / '1_1_link.csv').symlink_to(private)
    assert legacy_submission_path(str(root / '1_1_link.csv'), 1, 1) is None
    other = root / '2_1_answer.csv'
    other.write_text('another student')
    (root / '1_1_other.csv').symlink_to(other.resolve())
    assert legacy_submission_path(str(root / '1_1_other.csv'), 1, 1) is None


@pytest.mark.parametrize('kind', ['text', 'upload', 'legacy'])
def test_submission_source_marker_survives_storage_and_judge_dispatch(
    kind, db_session, student_user, sample_problem, tmp_path, monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    sample_problem.type = 'kaggle'
    db_session.commit()
    repo = SubmissionRepository(db_session)
    service = SubmissionService(repo, MagicMock(), SubmissionStorageClient(), uow=UnitOfWork(db_session))
    # 文本刻意使用合法旧附件路径，确保新的文本记录仍不会被当作附件。
    text = f'uploads/submissions/{student_user.id}_{sample_problem.id}_answer.csv'
    result = service.submit(SubmitParams(
        user_id=student_user.id, problem_id=sample_problem.id, code=text, language='csv',
        is_file_upload=kind == 'upload', filename='answer.csv', file_content=b'id,value\n1,2',
    ), requester_role='student')
    if kind == 'legacy':
        db_session.get(Submission, result.submission_id).code_path = None
    db_session.commit()
    snapshot = repo.get_by_id(result.submission_id)
    if kind == 'text':
        assert snapshot.code_path == ''
    elif kind == 'upload':
        assert snapshot.code_path == snapshot.code_content
        assert Path(snapshot.code_path).read_bytes() == b'id,value\n1,2'
    evaluator = MagicMock(return_value=('Wrong Answer', 50, 'partial'))
    monkeypatch.setattr(judge, 'run_kaggle_judge', evaluator)
    monkeypatch.setattr(judge, '_publish_realtime_result', MagicMock())
    judge.judge_submission(result.submission_id, db_session)
    expected_path = None if kind == 'text' else snapshot.code_content
    assert evaluator.call_args.kwargs['source_path'] == expected_path
    assert repo.get_by_id(result.submission_id).score == 50
