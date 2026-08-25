"""ACM 模式并发判题实现：每个测试点独立容器并行执行。"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from loguru import logger

from app.repositories.problem_repository import ProblemRepository
from app.services.sandbox_runner import SandboxRunner


def natural_sort_key(value: str) -> list[int | str]:
    """按文件名中的数字自然排序。"""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"([0-9]+)", value)
    ]


@dataclass(frozen=True)
class SingleCaseResult:
    """单个测试点的执行结果，含完整 stdout/stderr/input/expected 用于调试展示。"""

    case_name: str
    status: str  # "passed" | "wrong_answer" | "tle" | "runtime_error" | "compile_error" | "system_error"
    input_data: str
    expected_output: str
    actual_output: str
    error_output: str = ""


def _prepare_and_run_case(
    lang_config: dict,
    user_code: str,
    case_name: str,
    input_data: str,
    expected_output: str,
    memory_limit_mb: int,
    time_limit_ms: int,
) -> tuple[str, str, str | None]:
    """启动独立容器，执行单个测试点，返回 (case_name, status, detail)。"""
    runner = None
    try:
        runner = SandboxRunner()
        runner.launch(
            pids_limit=50,
            mem_limit=f"{memory_limit_mb}m",
            nano_cpus=1000000000,
            workdir="/app",
        )
        runner.put_file(lang_config["src"], user_code)

        if lang_config["compile"]:
            exit_code, output = runner.exec_run(lang_config["compile"])
            if exit_code != 0:
                return case_name, "compile_error", output

        runner.put_file("input.txt", input_data)
        time_limit_s = max(1, int(time_limit_ms) // 1000)
        run_cmd = f"sh -c 'timeout {time_limit_s}s {lang_config['run']} < /app/input.txt'"
        exit_code, output = runner.exec_run(run_cmd)
        output = output.strip() if output else ""

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
        if runner:
            try:
                runner.stop()
            except Exception as exc:
                logger.warning("停止 ACM 测试容器失败 case_name={}: {}", case_name, exc)


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


def _judge_single_case_verbose(
    runner: SandboxRunner,
    case_name: str,
    input_data: str,
    expected_output: str,
    run_entry: str,
    time_limit_ms: int,
) -> SingleCaseResult:
    """单点执行并保留 stdout/stderr 等完整信息，供调试展示使用。"""
    try:
        runner.put_file("input.txt", input_data)
        time_limit_s = max(1, int(time_limit_ms) // 1000)
        run_cmd = f"sh -c 'timeout {time_limit_s}s {run_entry} < /app/input.txt'"
        exit_code, output = runner.exec_run(run_cmd)
        output_text = str(output) if output is not None else ""

        if runner.is_tle(exit_code):
            return SingleCaseResult(
                case_name=case_name,
                status="tle",
                input_data=input_data,
                expected_output=expected_output,
                actual_output="",
                error_output="Time Limit Exceeded",
            )
        if exit_code != 0:
            return SingleCaseResult(
                case_name=case_name,
                status="runtime_error",
                input_data=input_data,
                expected_output=expected_output,
                actual_output="",
                error_output=output_text,
            )
        # 调试场景保留原文，便于用户与期望对比
        if output_text == expected_output:
            return SingleCaseResult(
                case_name=case_name,
                status="passed",
                input_data=input_data,
                expected_output=expected_output,
                actual_output=output_text,
            )
        return SingleCaseResult(
            case_name=case_name,
            status="wrong_answer",
            input_data=input_data,
            expected_output=expected_output,
            actual_output=output_text,
        )
    except Exception as exc:
        return SingleCaseResult(
            case_name=case_name,
            status="runtime_error",
            input_data=input_data,
            expected_output=expected_output,
            actual_output="",
            error_output=str(exc),
        )
    finally:
        try:
            runner.exec_run("rm -f /app/input.txt")
        except Exception as exc:
            logger.warning("清理 ACM 测试输入失败 case_name={}: {}", case_name, exc)


_ACM_LANG_CONFIGS = {
    "c": {"src": "main.c", "compile": "gcc main.c -o main", "run": "./main"},
    "cpp": {"src": "main.cpp", "compile": "g++ main.cpp -o main", "run": "./main"},
    "java": {
        "src": "Main.java",
        "compile": "javac -encoding UTF-8 Main.java",
        "run": "java Main",
    },
    "python": {"src": "solution.py", "compile": None, "run": "python3 solution.py"},
}


def _resolve_problem(db, problem_id):
    """读取题目并返回 (memory_limit, time_limit)；题目不存在返回 None。"""
    if db is None:
        from app.database import SessionLocal

        temporary_db = SessionLocal()
        try:
            problem = ProblemRepository(temporary_db).get_by_id(problem_id)
            if not problem:
                return None
            return problem.memory_limit, problem.time_limit
        finally:
            temporary_db.close()
    problem = ProblemRepository(db).get_by_id(problem_id)
    if not problem:
        return None
    return problem.memory_limit, problem.time_limit


def run_acm_single_case(
    user_code: str,
    problem_id: int,
    language: str = "python",
    db=None,
) -> SingleCaseResult:
    """仅执行自然序第一个测试点，返回含 stdout/stderr/input/expected 的结果。

    - 失败优先返回 `Runtime Error` / `System Error`，附 error_output
    - 题目不存在、缺少测试数据时返回 status="system_error"
    """
    lang_config = _ACM_LANG_CONFIGS.get((language or "").lower())
    if not lang_config:
        return SingleCaseResult(
            case_name="",
            status="system_error",
            input_data="",
            expected_output="",
            actual_output="",
            error_output=f"Unsupported language: {language}",
        )

    limits = _resolve_problem(db, problem_id)
    if limits is None:
        return SingleCaseResult(
            case_name="",
            status="system_error",
            input_data="",
            expected_output="",
            actual_output="",
            error_output="Problem not found",
        )
    memory_limit, time_limit = limits

    test_case_dir = f"uploads/problems/{problem_id}"
    if not os.path.exists(test_case_dir):
        return SingleCaseResult(
            case_name="",
            status="runtime_error",
            input_data="",
            expected_output="",
            actual_output="",
            error_output="System Error: Test cases missing",
        )

    in_files = sorted(
        [name for name in os.listdir(test_case_dir) if name.endswith(".in")],
        key=natural_sort_key,
    )
    if not in_files:
        return SingleCaseResult(
            case_name="",
            status="runtime_error",
            input_data="",
            expected_output="",
            actual_output="",
            error_output="System Error: No .in files found",
        )

    first_in = in_files[0]
    case_name = first_in[: -len(".in")]
    out_file = os.path.join(test_case_dir, f"{case_name}.out")
    if not os.path.exists(out_file):
        return SingleCaseResult(
            case_name=case_name,
            status="system_error",
            input_data="",
            expected_output="",
            actual_output="",
            error_output=f"Missing output file for test case: {case_name}.out",
        )
    with open(os.path.join(test_case_dir, first_in), "r", encoding="utf-8") as source:
        input_data = source.read()
    with open(out_file, "r", encoding="utf-8") as source:
        expected_output = source.read().strip()

    try:
        memory_limit = max(16, int(memory_limit or 128))
    except (TypeError, ValueError):
        memory_limit = 128
    try:
        time_limit_ms = max(1, int(time_limit or 1000))
    except (TypeError, ValueError):
        time_limit_ms = 1000

    runner, prep_error_type, prep_error_message = _prepare_container(
        lang_config, user_code, memory_limit
    )
    if prep_error_type == "compile":
        return SingleCaseResult(
            case_name=case_name,
            status="compile_error",
            input_data=input_data,
            expected_output=expected_output,
            actual_output="",
            error_output=str(prep_error_message or ""),
        )
    if prep_error_type == "system":
        return SingleCaseResult(
            case_name=case_name,
            status="system_error",
            input_data=input_data,
            expected_output=expected_output,
            actual_output="",
            error_output=str(prep_error_message or ""),
        )
    if runner is None:
        return SingleCaseResult(
            case_name=case_name,
            status="system_error",
            input_data=input_data,
            expected_output=expected_output,
            actual_output="",
            error_output="Failed to prepare runtime container",
        )

    try:
        return _judge_single_case_verbose(
            runner,
            case_name,
            input_data,
            expected_output,
            lang_config["run"],
            time_limit_ms,
        )
    except Exception as exc:
        return SingleCaseResult(
            case_name=case_name,
            status="runtime_error",
            input_data=input_data,
            expected_output=expected_output,
            actual_output="",
            error_output=str(exc),
        )
    finally:
        runner.stop()


def run_acm_judge(submission_id, user_code, problem_id, language="python", db=None):
    """每个测试点独立容器并发执行，全部完成后汇总结果。

    并发上限为 8 个并行容器，超过 8 个测试点时多余排队。
    编译结果不跨容器复用，每次都重新编译（代码每次都不同，缓存收益低）。
    """
    del submission_id
    lang_config = _ACM_LANG_CONFIGS.get((language or "").lower())
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

    try:
        max_workers = min(len(case_payloads), 8)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _prepare_and_run_case,
                    lang_config,
                    user_code,
                    case_name,
                    input_data,
                    expected_output,
                    memory_limit,
                    time_limit_ms,
                ): case_name
                for case_name, input_data, expected_output in case_payloads
            }
            ordered_results = []
            for future in as_completed(futures):
                ordered_results.append(future.result())
    except Exception as exc:
        return "Runtime Error", 0, str(exc)

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
