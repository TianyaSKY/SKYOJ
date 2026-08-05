"""ACM 模式串行判题实现。"""

import os
import re

from loguru import logger

from app.repositories.problem_repository import ProblemRepository
from app.services.sandbox_runner import SandboxRunner


def natural_sort_key(value: str) -> list[int | str]:
    """按文件名中的数字自然排序。"""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"([0-9]+)", value)
    ]


def _prepare_container(lang_config, user_code, memory_limit):
    """创建一个提交专用容器并完成源码上传与编译。"""
    runner = None
    try:
        runner = SandboxRunner()
        runner.launch(
            pids_limit=50,
            mem_limit=f"{memory_limit}m",
            nano_cpus=1000000000,
            workdir="/app",
        )
        runner.put_file(lang_config["src"], user_code)

        if lang_config["compile"]:
            exit_code, output = runner.exec_run(lang_config["compile"])
            if exit_code != 0:
                runner.stop()
                return None, "compile", output
        return runner, None, None
    except Exception as exc:
        if runner is not None:
            runner.stop()
        return None, "system", str(exc)


def _judge_single_case(
    runner: SandboxRunner,
    case_name,
    input_data,
    expected_output,
    run_entry,
    time_limit_ms,
):
    """在同一个提交容器中串行执行一个测试点。"""
    try:
        runner.put_file("input.txt", input_data)
        time_limit_s = max(1, int(time_limit_ms) // 1000)
        run_cmd = f"sh -c 'timeout {time_limit_s}s {run_entry} < /app/input.txt'"
        exit_code, output = runner.exec_run(run_cmd)
        output = output.strip()

        if runner.is_tle(exit_code):
            return case_name, "tle", None
        if exit_code != 0:
            return case_name, "runtime_error", output
        if output == expected_output:
            return case_name, "passed", None
        return case_name, "wrong_answer", None
    except Exception as exc:
        return case_name, "runtime_error", str(exc)
    finally:
        try:
            runner.exec_run("rm -f /app/input.txt")
        except Exception as exc:
            logger.warning("清理 ACM 测试输入失败 case_name={}: {}", case_name, exc)


def run_acm_judge(submission_id, user_code, problem_id, language="python", db=None):
    """编译一次，并在一个沙箱容器中按顺序执行全部测试点。"""
    del submission_id
    configs = {
        "c": {"src": "main.c", "compile": "gcc main.c -o main", "run": "./main"},
        "cpp": {"src": "main.cpp", "compile": "g++ main.cpp -o main", "run": "./main"},
        "java": {
            "src": "Main.java",
            "compile": "javac -encoding UTF-8 Main.java",
            "run": "java Main",
        },
        "python": {"src": "solution.py", "compile": None, "run": "python3 solution.py"},
    }

    lang_config = configs.get((language or "").lower())
    if not lang_config:
        return "System Error", 0, f"Unsupported language: {language}"

    if db is None:
        from app.database import SessionLocal

        temporary_db = SessionLocal()
        try:
            problem = ProblemRepository(temporary_db).get_by_id(problem_id)
            if not problem:
                return "System Error", 0, "Problem not found"
            memory_limit = problem.memory_limit
            time_limit = problem.time_limit
        finally:
            temporary_db.close()
    else:
        problem = ProblemRepository(db).get_by_id(problem_id)
        if not problem:
            return "System Error", 0, "Problem not found"
        memory_limit = problem.memory_limit
        time_limit = problem.time_limit

    test_case_dir = f"uploads/problems/{problem_id}"
    if not os.path.exists(test_case_dir):
        return "Runtime Error", 0, "System Error: Test cases missing"

    in_files = sorted(
        [name for name in os.listdir(test_case_dir) if name.endswith(".in")],
        key=natural_sort_key,
    )
    total_cases = len(in_files)
    if total_cases == 0:
        return "Runtime Error", 0, "System Error: No .in files found"

    case_payloads = []
    for in_file in in_files:
        case_name = in_file[: -len(".in")]
        out_file = os.path.join(test_case_dir, f"{case_name}.out")
        if not os.path.exists(out_file):
            return "System Error", 0, f"Missing output file for test case: {case_name}.out"
        with open(os.path.join(test_case_dir, in_file), "r", encoding="utf-8") as source:
            input_data = source.read()
        with open(out_file, "r", encoding="utf-8") as source:
            expected_output = source.read().strip()
        case_payloads.append((case_name, input_data, expected_output))

    try:
        memory_limit = max(16, int(memory_limit or 128))
    except (TypeError, ValueError):
        memory_limit = 128
    try:
        time_limit_ms = max(1, int(time_limit or 1000))
    except (TypeError, ValueError):
        time_limit_ms = 1000

    runner, prep_error_type, prep_error_message = _prepare_container(
        lang_config,
        user_code,
        memory_limit,
    )
    if prep_error_type == "compile":
        return "Compile Error", 0, prep_error_message
    if prep_error_type == "system":
        return "System Error", 0, prep_error_message
    if runner is None:
        return "System Error", 0, "Failed to prepare runtime container"

    try:
        ordered_results = [
            _judge_single_case(
                runner,
                case_name,
                input_data,
                expected_output,
                lang_config["run"],
                time_limit_ms,
            )
            for case_name, input_data, expected_output in case_payloads
        ]
    except Exception as exc:
        return "Runtime Error", 0, str(exc)
    finally:
        runner.stop()

    passed_count = 0
    has_tle = False
    logs = []
    for case_name, result_type, detail in ordered_results:
        if result_type == "passed":
            passed_count += 1
            logs.append(f"Test Case {case_name}: Passed")
        elif result_type == "tle":
            has_tle = True
            logs.append(f"Test Case {case_name}: Time Limit Exceeded")
        elif result_type == "runtime_error":
            logs.append(
                f"Test Case {case_name}: Runtime Error"
                + (f"\n{detail}" if detail else "")
            )
        else:
            logs.append(f"Test Case {case_name}: Wrong Answer")

    final_score = (passed_count / total_cases) * 100
    if has_tle:
        final_status = "Time Limit Exceeded"
    elif passed_count == total_cases:
        final_status = "Accepted"
    else:
        final_status = "Wrong Answer"
    return final_status, final_score, "\n".join(logs)
