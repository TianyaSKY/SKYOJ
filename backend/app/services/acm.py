import io
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.problem import Problem
from app.services.judge_service import client, IMAGE_NAME, create_tar_stream

DEFAULT_CASE_PARALLELISM = 2
MAX_CASE_PARALLELISM = 8


def natural_sort_key(s):
    """
    实现自然排序的 key 函数，将字符串中的数字部分转换为整数进行比较。
    例如: '1.in', '2.in', '10.in'
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]


def _resolve_case_parallelism(total_cases):
    raw_value = os.getenv('ACM_CASE_PARALLELISM', str(DEFAULT_CASE_PARALLELISM))
    try:
        workers = int(raw_value)
    except (TypeError, ValueError):
        workers = DEFAULT_CASE_PARALLELISM

    workers = max(1, min(workers, MAX_CASE_PARALLELISM))
    cpu_count = os.cpu_count() or 1
    workers = min(workers, cpu_count, total_cases)
    return max(1, workers)


def _prepare_workspace(lang_config, user_code, memory_limit):
    """
    在预热容器中准备好运行环境（源码 + 编译产物），并导出 /app 的 tar 快照。
    """
    container = None
    try:
        container = client.containers.run(
            image=IMAGE_NAME,
            command="sleep 600",
            detach=True,
            network_mode="none",
            mem_limit=f"{memory_limit}m",
            nano_cpus=1000000000,
            remove=True,
            pids_limit=50
        )

        container.put_archive('/app', create_tar_stream(lang_config['src'], user_code))

        if lang_config['compile']:
            exec_result = container.exec_run(lang_config['compile'])
            if exec_result.exit_code != 0:
                return None, 'compile', exec_result.output.decode('utf-8')

        bits, _ = container.get_archive('/app')
        workspace_tar = b''.join(bits)
        return workspace_tar, None, None
    except Exception as e:
        return None, 'system', str(e)
    finally:
        if container:
            try:
                container.stop()
            except:
                pass


def _judge_single_case(case_name, input_data, expected_output, run_entry, workspace_tar, memory_limit, time_limit_ms):
    """
    每个测试点使用独立容器执行，避免并行时相互污染。
    """
    container = None
    try:
        container = client.containers.run(
            image=IMAGE_NAME,
            command="sleep 600",
            detach=True,
            network_mode="none",
            mem_limit=f"{memory_limit}m",
            nano_cpus=1000000000,
            remove=True,
            pids_limit=50
        )

        container.put_archive('/', io.BytesIO(workspace_tar))
        container.put_archive('/app', create_tar_stream('input.txt', input_data))

        time_limit_s = max(1, int(time_limit_ms) // 1000)
        run_cmd = f"sh -c 'timeout {time_limit_s}s {run_entry} < input.txt'"
        result = container.exec_run(run_cmd)

        if result.exit_code == 124:
            return case_name, 'tle', None

        actual_output = result.output.decode('utf-8').strip()

        if result.exit_code != 0:
            return case_name, 'runtime_error', actual_output
        if actual_output == expected_output:
            return case_name, 'passed', None
        return case_name, 'wrong_answer', None
    except Exception as e:
        return case_name, 'runtime_error', str(e)
    finally:
        if container:
            try:
                container.stop()
            except:
                pass


def run_acm_judge(submission_id, user_code, problem_id, language='python'):
    # 多语言配置
    configs = {
        'c': {'src': 'main.c', 'compile': 'gcc main.c -o main', 'run': './main'},
        'cpp': {'src': 'main.cpp', 'compile': 'g++ main.cpp -o main', 'run': './main'},
        'java': {'src': 'Main.java', 'compile': 'javac -encoding UTF-8 Main.java', 'run': 'java Main'},
        'python': {'src': 'solution.py', 'compile': None, 'run': 'python3 solution.py'}
    }

    lang_config = configs.get(language.lower())
    if not lang_config:
        return "System Error", 0, f"Unsupported language: {language}"

    problem = Problem.query.get(problem_id)
    if not problem:
        return "System Error", 0, "Problem not found"

    test_case_dir = f"uploads/problems/{problem_id}"
    if not os.path.exists(test_case_dir):
        return "Runtime Error", 0, "System Error: Test cases missing"

    in_files = [f for f in os.listdir(test_case_dir) if f.endswith('.in')]
    total_cases = len(in_files)
    if total_cases == 0:
        return "Runtime Error", 0, "System Error: No .in files found"

    in_files.sort(key=natural_sort_key)

    case_payloads = []
    for in_file in in_files:
        case_name = in_file.replace('.in', '')
        out_file = os.path.join(test_case_dir, f"{case_name}.out")
        if not os.path.exists(out_file):
            return "System Error", 0, f"Missing output file for test case: {case_name}.out"

        with open(os.path.join(test_case_dir, in_file), 'r') as f:
            input_data = f.read()
        with open(out_file, 'r') as f:
            expected_output = f.read().strip()

        case_payloads.append((case_name, input_data, expected_output))

    try:
        memory_limit = int(getattr(problem, 'memory_limit', 128) or 128)
    except (TypeError, ValueError):
        memory_limit = 128
    memory_limit = max(16, memory_limit)

    try:
        time_limit_ms = int(getattr(problem, 'time_limit', 1000) or 1000)
    except (TypeError, ValueError):
        time_limit_ms = 1000
    time_limit_ms = max(1, time_limit_ms)

    workspace_tar, prep_error_type, prep_error_msg = _prepare_workspace(lang_config, user_code, memory_limit)
    if prep_error_type == 'compile':
        return "Compile Error", 0, prep_error_msg
    if prep_error_type == 'system':
        return "System Error", 0, prep_error_msg
    if not workspace_tar:
        return "System Error", 0, "Failed to prepare runtime workspace"

    case_parallelism = _resolve_case_parallelism(total_cases)
    ordered_results = [None] * total_cases

    try:
        with ThreadPoolExecutor(max_workers=case_parallelism) as executor:
            future_to_idx = {
                executor.submit(
                    _judge_single_case,
                    case_name,
                    input_data,
                    expected_output,
                    lang_config['run'],
                    workspace_tar,
                    memory_limit,
                    time_limit_ms
                ): idx
                for idx, (case_name, input_data, expected_output) in enumerate(case_payloads)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                case_name = case_payloads[idx][0]
                try:
                    ordered_results[idx] = future.result()
                except Exception as e:
                    ordered_results[idx] = (case_name, 'runtime_error', str(e))
    except Exception as e:
        return "Runtime Error", 0, str(e)

    passed_count = 0
    has_tle = False
    logs = []

    for case_name, result_type, detail in ordered_results:
        if result_type == 'passed':
            passed_count += 1
            logs.append(f"Test Case {case_name}: Passed")
        elif result_type == 'tle':
            has_tle = True
            logs.append(f"Test Case {case_name}: Time Limit Exceeded")
        elif result_type == 'runtime_error':
            if detail:
                logs.append(f"Test Case {case_name}: Runtime Error\n{detail}")
            else:
                logs.append(f"Test Case {case_name}: Runtime Error")
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
