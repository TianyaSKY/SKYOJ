"""判题基础设施故障须与学生程序的运行错误区分。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.judging import acm


@pytest.fixture
def cases(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(acm, 'ProblemRepository', lambda db: SimpleNamespace(
        get_by_id=lambda pid: SimpleNamespace(memory_limit=128, time_limit=1000),
    ))
    folder = tmp_path / 'uploads' / 'problems' / '1'
    return folder


@pytest.mark.parametrize('empty_directory', [False, True])
def test_missing_cases_are_system_error(cases, empty_directory):
    if empty_directory:
        cases.mkdir(parents=True)
    status, score, log, results = acm.run_acm_judge(1, 'print(1)', 1, 'python', db=object())
    assert status == 'System Error'
    assert score == 0 and results == []
    assert 'System Error' in log


@pytest.mark.parametrize('phase', ['launch', 'put_file', 'exec_run'])
def test_sandbox_infrastructure_failure_retains_diagnostic(cases, monkeypatch, phase):
    cases.mkdir(parents=True)
    (cases / '1.in').write_text('1')
    (cases / '1.out').write_text('1')
    runner = MagicMock()
    getattr(runner, phase).side_effect = ConnectionError('sandbox unavailable')
    monkeypatch.setattr(acm, 'SandboxRunner', lambda: runner)
    status, score, log, results = acm.run_acm_judge(1, 'print(1)', 1, 'python', db=object())
    assert status == 'System Error'
    assert score == 0
    assert 'sandbox unavailable' in log
    assert results[0]['status'] == 'system_error'
    assert results[0]['error_output'] == 'sandbox unavailable'
    runner.stop.assert_called_once()


def test_program_nonzero_exit_remains_runtime_error(cases, monkeypatch):
    cases.mkdir(parents=True)
    (cases / '1.in').write_text('1')
    (cases / '1.out').write_text('1')
    runner = MagicMock()
    runner.exec_run.return_value = (1, 'ZeroDivisionError')
    runner.is_tle.return_value = False
    monkeypatch.setattr(acm, 'SandboxRunner', lambda: runner)
    status, score, log, results = acm.run_acm_judge(1, '1/0', 1, 'python', db=object())
    assert status == 'Runtime Error'
    assert 'ZeroDivisionError' in log
    assert results[0]['status'] == 'runtime_error'
