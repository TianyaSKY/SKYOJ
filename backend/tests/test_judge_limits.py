"""判题时限换算与 ACM 状态汇总回归测试。"""

from app.services.judge_service import aggregate_acm_results, time_limit_seconds


def test_time_limit_seconds_converts_milliseconds() -> None:
    assert time_limit_seconds(1000) == 1
    assert time_limit_seconds(1500) == 2
    assert time_limit_seconds(30000) == 30
    assert time_limit_seconds(50) == 1
    assert time_limit_seconds(None) == 1
    assert time_limit_seconds("bad") == 1


def test_aggregate_acm_results_prefers_runtime_error_over_wrong_answer() -> None:
    status, score, log = aggregate_acm_results(
        [
            ("1", "passed", None),
            ("2", "runtime_error", "segfault"),
            ("3", "wrong_answer", None),
        ],
        3,
    )
    assert status == "Runtime Error"
    assert score == (1 / 3) * 100
    assert "Runtime Error" in log
    assert "Wrong Answer" in log


def test_aggregate_acm_results_prefers_tle() -> None:
    status, score, _log = aggregate_acm_results(
        [
            ("1", "tle", None),
            ("2", "runtime_error", "boom"),
        ],
        2,
    )
    assert status == "Time Limit Exceeded"
    assert score == 0
