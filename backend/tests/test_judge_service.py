"""判题子系统重构测试：分发→update_result、SandboxRunner 参数透传、无 import 环。"""

from types import SimpleNamespace

import pytest

from app.services import acm, judge_service, sandbox_runner


class _StubSubmission:
    def __init__(self, problem_type, language="python", problem_id=1):
        self.problem = SimpleNamespace(type=problem_type)
        self.language = language
        self.problem_id = problem_id
        self.code_content = "print(1)"


class _StubDb:
    def __init__(self):
        self.committed = 0

    def commit(self):
        self.committed += 1


def make_repo_factory(problem_type):
    """构造注入 judge_service 的假 SubmissionRepository 工厂。"""

    class _FakeSubmissionRepository:
        last = None

        def __init__(self, db):
            self.db = db
            self.submission = _StubSubmission(problem_type)
            self.updates = []
            type(self).last = self

        def get_by_id(self, submission_id):
            return self.submission

        def update_result(self, submission_id, *, status, score, output_log):
            self.updates.append((submission_id, status, score, output_log))

    return _FakeSubmissionRepository


def test_judge_submission_dispatches_acm_and_updates_result(monkeypatch):
    calls = {}

    def fake_acm_judge(submission_id, user_code, problem_id, language, db=None):
        calls["args"] = (submission_id, user_code, problem_id, language, db)
        return "Accepted", 100.0, "Test Case 1: Passed"

    repo_factory = make_repo_factory("acm")
    monkeypatch.setattr(judge_service, "run_acm_judge", fake_acm_judge)
    monkeypatch.setattr(judge_service, "SubmissionRepository", repo_factory)

    db = _StubDb()
    judge_service.judge_submission(7, db)

    assert calls["args"] == (7, "print(1)", 1, "python", db)
    assert repo_factory.last.updates == [(7, "Accepted", 100.0, "Test Case 1: Passed")]
    assert db.committed == 1


def test_judge_submission_unsupported_type_marks_system_error(monkeypatch):
    repo_factory = make_repo_factory("text")
    monkeypatch.setattr(judge_service, "SubmissionRepository", repo_factory)

    db = _StubDb()
    judge_service.judge_submission(7, db)

    assert repo_factory.last.updates == [(7, "System Error", 0, "Unsupported problem type")]
    assert db.committed == 1


def test_judge_submission_marks_system_error_on_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("sandbox exploded")

    repo_factory = make_repo_factory("acm")
    monkeypatch.setattr(judge_service, "run_acm_judge", boom)
    monkeypatch.setattr(judge_service, "SubmissionRepository", repo_factory)

    db = _StubDb()
    judge_service.judge_submission(7, db)

    assert repo_factory.last.updates == [
        (7, "System Error", 0, "Judge Error: sandbox exploded")
    ]
    assert db.committed == 1


def test_judge_submission_missing_submission_skips(monkeypatch):
    class _EmptyRepo:
        last = None

        def __init__(self, db):
            self.db = db
            type(self).last = self

        def get_by_id(self, submission_id):
            return None

        def update_result(self, submission_id, *, status, score, output_log):
            raise AssertionError("不应更新不存在的提交")

    monkeypatch.setattr(judge_service, "SubmissionRepository", _EmptyRepo)

    db = _StubDb()
    judge_service.judge_submission(7, db)

    assert db.committed == 0


def test_acm_judge_runs_cases_through_runner(monkeypatch, tmp_path):
    """真实 run_acm_judge + 假 runner/仓库：验证编排与参数逐字透传。"""

    class FakeProblem:
        memory_limit = 128
        time_limit = 1000

    class FakeProblemRepo:
        last = None

        def __init__(self, db):
            type(self).last = self

        def get_by_id(self, problem_id):
            return FakeProblem()

    class FakeRunner:
        last = None

        def __init__(self, image="skyoj-runner"):
            self.image = image
            self.files = []
            self.launch_kwargs = None
            self.exec_calls = []
            self.stopped = False
            type(self).last = self

        def launch(self, **kwargs):
            self.launch_kwargs = kwargs

        def put_file(self, name, content):
            self.files.append(name)

        def exec_run(self, cmd, **kwargs):
            self.exec_calls.append((cmd, kwargs))
            if "input.txt" in cmd:
                return 0, "5"
            return 0, ""

        def is_tle(self, exit_code):
            return exit_code == 124

        def stop(self):
            self.stopped = True

    monkeypatch.setattr(acm, "SandboxRunner", FakeRunner)
    monkeypatch.setattr(acm, "ProblemRepository", FakeProblemRepo)
    monkeypatch.chdir(tmp_path)

    problem_dir = tmp_path / "uploads" / "problems" / "1"
    problem_dir.mkdir(parents=True)
    (problem_dir / "1.in").write_text("5\n", encoding="utf-8")
    (problem_dir / "1.out").write_text("5", encoding="utf-8")

    status, score, log = acm.run_acm_judge(1, "print(5)", 1, "python", db=object())

    assert (status, score) == ("Accepted", 100.0)
    assert log == "Test Case 1: Passed"
    assert FakeRunner.last.launch_kwargs == {
        "pids_limit": 50,
        "mem_limit": "128m",
        "nano_cpus": 1000000000,
        "workdir": "/app",
    }
    assert FakeRunner.last.files == ["solution.py", "input.txt"]
    run_cmd, kwargs = FakeRunner.last.exec_calls[0]
    assert "timeout 1s" in run_cmd
    assert kwargs == {}
    assert FakeRunner.last.stopped is True


def test_sandbox_runner_launch_forwards_limits(monkeypatch):
    class FakeContainer:
        def __init__(self):
            self.exec_kwargs = []
            self.stopped = False
            self.removed = False

        def put_archive(self, *args):
            pass

        def exec_run(self, cmd, **kwargs):
            self.exec_kwargs.append((cmd, kwargs))
            return SimpleNamespace(exit_code=0, output=b"out")

        def get_archive(self, path):
            return (b"bits", {"stat": 1})

        def stop(self):
            self.stopped = True

        def remove(self, force=False):
            self.removed = True

    class FakeContainers:
        def __init__(self):
            self.run_kwargs = None
            self.last_container = None

        def run(self, image, command, **kwargs):
            self.run_kwargs = {"image": image, "command": command, **kwargs}
            self.last_container = FakeContainer()
            return self.last_container

    fake = FakeContainers()
    monkeypatch.setattr(sandbox_runner, "client", SimpleNamespace(containers=fake))

    runner = sandbox_runner.SandboxRunner(image="skyoj-generator")
    runner.launch(pids_limit=50, mem_limit="128m", nano_cpus=1000000000, workdir="/app")

    assert fake.run_kwargs == {
        "image": "skyoj-generator",
        "command": ["sleep", "600"],
        "detach": True,
        "remove": True,
        "network_mode": "none",
        "pids_limit": 50,
        "mem_limit": "128m",
        "nano_cpus": 1000000000,
        "working_dir": "/app",
    }

    exit_code, output = runner.exec_run("ls", timeout=5)
    assert exit_code == 0
    assert output == "out"
    assert fake.last_container.exec_kwargs == [("ls", {"timeout": 5})]

    assert runner.is_tle(124) is True
    assert runner.is_tle(0) is False

    runner.stop()
    assert fake.last_container.stopped is True
    assert fake.last_container.removed is True
    # 幂等：再次 stop 不抛错
    runner.stop()


def test_sandbox_runner_context_manager_stops(monkeypatch):
    class FakeContainer:
        def __init__(self):
            self.stopped = False
            self.removed = False

        def stop(self):
            self.stopped = True

        def remove(self, force=False):
            self.removed = True

    class FakeContainers:
        def run(self, image, command, **kwargs):
            return FakeContainer()

    monkeypatch.setattr(sandbox_runner, "client", SimpleNamespace(containers=FakeContainers()))

    with sandbox_runner.SandboxRunner() as runner:
        runner.launch()
        container = runner._container

    assert container.stopped is True
    assert container.removed is True


def test_no_import_cycle_between_judge_modules():
    """judge_service 与模式模块可以以任意顺序导入。"""
    import importlib

    for module_name in ("app.services.acm", "app.services.judge_service"):
        importlib.import_module(module_name)
    import app.services.judge_service  # noqa: F401
    import app.services.acm  # noqa: F401
    import app.services.oop  # noqa: F401
    import app.services.kaggle  # noqa: F401
    import app.services.test_gen_service  # noqa: F401
