"""评分脚本只能产生有限的 0–100 分，并保留有效部分分与诊断日志。"""

import math
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.judging import kaggle, oop


@pytest.fixture(params=['kaggle', 'oop'])
def grading(request, monkeypatch, tmp_path):
    module = kaggle if request.param == 'kaggle' else oop
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / 'uploads' / 'problems' / '1'
    folder.mkdir(parents=True)
    (folder / 'main.py').write_text('print(100)')
    (folder / 'truth.csv').write_text('id,value\n1,1')
    monkeypatch.setattr(module, 'ProblemRepository', lambda db: SimpleNamespace(
        get_by_id=lambda pid: SimpleNamespace(memory_limit=128, time_limit=1000),
    ))
    runner = MagicMock()
    runner.__enter__.return_value = runner
    monkeypatch.setattr(module, 'SandboxRunner', lambda: runner)

    def evaluate(output):
        runner.exec_run.return_value = (0, output)
        if request.param == 'kaggle':
            return module.run_kaggle_judge(1, 'id,value\n1,1', 1, db=object())
        return module.run_oop_judge(1, 'class Solution: pass', 1, 'python', db=object())

    return evaluate, runner


@pytest.mark.parametrize('value', ['nan', 'NaN', '-nan', 'inf', '-inf', '1e309', '-1', '101'])
def test_invalid_scores_never_leave_judge_as_nonfinite_or_out_of_range(grading, value):
    evaluate, runner = grading
    status, score, log = evaluate(f'grading details\n{value}')
    assert status == 'Runtime Error'
    assert score == 0 and math.isfinite(score)
    assert 'Invalid score' in log
    runner.__exit__.assert_called_once()


@pytest.mark.parametrize('value,expected_status', [(0, 'Wrong Answer'), (50.5, 'Wrong Answer'), (100, 'Accepted')])
def test_valid_score_boundaries_and_diagnostics_are_preserved(grading, value, expected_status):
    evaluate, _ = grading
    status, score, log = evaluate(f'grading details\n{value}')
    assert status == expected_status
    assert score == value
    assert log == 'grading details'
