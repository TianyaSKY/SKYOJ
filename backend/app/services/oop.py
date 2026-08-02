import os
import re

from loguru import logger

from app.models.problem import Problem
from app.services.judge_service import client, IMAGE_NAME, create_tar_stream


FORBIDDEN_EXIT_PATTERNS = {
    'python': [
        (r"\bsys\s*\.\s*exit\s*\(", "sys.exit"),
        (r"\bos\s*\.\s*_exit\s*\(", "os._exit"),
    ],
    'c': [
        (r"\b(exit|_Exit|quick_exit|abort)\s*\(", "exit/_Exit/quick_exit/abort"),
    ],
    'cpp': [
        (r"\b(exit|_Exit|quick_exit|abort)\s*\(", "exit/_Exit/quick_exit/abort"),
    ],
    'java': [
        (r"\bSystem\s*\.\s*exit\s*\(", "System.exit"),
        (r"\bRuntime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*halt\s*\(", "Runtime.getRuntime().halt"),
    ],
}


def _detect_forbidden_exit_apis(code, language):
    patterns = FORBIDDEN_EXIT_PATTERNS.get(language.lower(), [])
    hits = []
    for pattern, label in patterns:
        if re.search(pattern, code):
            hits.append(label)
    return sorted(set(hits))


PYTHON_OOP_GUARD_RUNNER = """import runpy
import sys
import traceback


def _system_exit_from_solution(tb):
    while tb:
        filename = tb.tb_frame.f_code.co_filename.replace("\\\\", "/")
        if filename.endswith("/solution.py"):
            return True
        tb = tb.tb_next
    return False


try:
    runpy.run_path("/app/main.py", run_name="__main__")
except SystemExit as ex:
    if _system_exit_from_solution(ex.__traceback__):
        exit_code = ex.code if isinstance(ex.code, int) else 1
        if exit_code == 0:
            exit_code = 91
        print(f"[SKYOJ] Forbidden SystemExit detected in solution.py: {ex.code}", file=sys.stderr)
        sys.exit(exit_code)
    raise
except Exception:
    traceback.print_exc()
    sys.exit(1)
"""


def run_oop_judge(submission_id, user_code, problem_id, language='python', db=None):
    """
    OOP 模式判题逻辑，支持多种语言。
    约定:
    - C/C++: 教师提供 main.c/main.cpp, 学生实现 solution.c/solution.cpp。
    - Java: 教师提供 Main.java (测试主类), 学生实现 Solution.java。
    - Python: 教师提供 test_runner.py, 学生实现 solution.py。
    教师的测试文件需要和题目的其他测试用例一起上传。
    """
    configs = {
        'c': {
            'student_file': 'solution.c',
            'teacher_files': ['main.c'],
            'compile': 'gcc main.c solution.c -o main',
            'run': './main'
        },
        'cpp': {
            'student_file': 'solution.cpp',
            'teacher_files': ['main.cpp'],
            'compile': 'g++ main.cpp solution.cpp -o main -std=c++11',
            'run': './main'
        },
        'java': {
            'student_file': 'Solution.java',
            'teacher_files': ['Main.java'],
            'compile': 'javac -encoding UTF-8 Main.java Solution.java',
            'run': 'java Main'
        },
        'python': {
            'student_file': 'solution.py',
            'teacher_files': ['main.py'],
            'compile': None,
            'run': 'python3 main.py'
        }
    }

    lang_config = configs.get(language.lower())
    if not lang_config:
        return "System Error", 0, f"Unsupported language for OOP mode: {language}"

    forbidden_hits = _detect_forbidden_exit_apis(user_code or "", language)
    if forbidden_hits:
        return "Runtime Error", 0, (
            "Forbidden API usage detected: "
            + ", ".join(forbidden_hits)
            + ". Do not terminate the judge process directly."
        )

    if db is None:
        from app.database import SessionLocal
        _db = SessionLocal()
        try:
            problem = _db.get(Problem, problem_id)
            if not problem:
                return "System Error", 0, "Problem not found"
            memory_limit = problem.memory_limit
        finally:
            _db.close()
    else:
        problem = db.get(Problem, problem_id)
        if not problem:
            return "System Error", 0, "Problem not found"
        memory_limit = problem.memory_limit
    problem_dir = f"uploads/problems/{problem_id}"

    # 检查教师的测试文件是否存在
    for teacher_file in lang_config['teacher_files']:
        teacher_file_path = os.path.join(problem_dir, teacher_file)
        if not os.path.exists(teacher_file_path):
            return "System Error", 0, f"Teacher's test file '{teacher_file}' is missing."

    container = None
    try:
        # 启动容器
        container = client.containers.run(
            image=IMAGE_NAME,
            command="sleep 600",
            detach=True,
            network_mode="none",
            mem_limit=f"{memory_limit}m",
            nano_cpus=1000000000,
            remove=True
        )

        # 1. 上传学生代码
        student_code_tar = create_tar_stream(lang_config['student_file'], user_code)
        container.put_archive('/app', student_code_tar)

        # 2. 上传教师的测试文件
        for teacher_file in lang_config['teacher_files']:
            teacher_file_path = os.path.join(problem_dir, teacher_file)
            with open(teacher_file_path, 'rb') as f:
                content = f.read()
            container.put_archive('/app', create_tar_stream(teacher_file, content))

        # 3. 编译 (如果需要)
        if lang_config['compile']:
            compile_result = container.exec_run(lang_config['compile'])
            if compile_result.exit_code != 0:
                return "Compile Error", 0, compile_result.output.decode('utf-8')

        # 4. 运行
        # 使用 timeout 防止死循环
        time_limit = getattr(problem, 'time_limit', 5)
        run_entry = lang_config['run']
        if language.lower() == 'python':
            guard_filename = "__skyoj_oop_guard_runner.py"
            guard_tar = create_tar_stream(guard_filename, PYTHON_OOP_GUARD_RUNNER)
            container.put_archive('/app', guard_tar)
            run_entry = f"python3 {guard_filename}"

        run_cmd = f"sh -c 'timeout {time_limit}s {run_entry}'"
        run_result = container.exec_run(run_cmd)
        output = run_result.output.decode('utf-8')

        # 5. 判定结果 (约定：教师程序最后一行输出分数 0-100)
        lines = output.strip().splitlines()
        if run_result.exit_code == 0 and lines:
            try:
                # 尝试解析最后一行作为分数
                final_score = float(lines[-1].strip())
                if final_score < 0 or final_score > 100:
                    return "Runtime Error", 0, f"Invalid score out of range [0, 100]: {final_score}"
                log_output = "\n".join(lines[:-1])
                # 只有满分才显示 Accepted，否则显示 Wrong Answer (带部分分)
                final_status = "Accepted" if final_score == 100 else "Wrong Answer"
                return final_status, final_score, log_output
            except ValueError:
                # 如果最后一行不是数字，且不是 "OK"，则视为格式错误
                if lines[-1].strip() == "OK":
                    return "Accepted", 100, "\n".join(lines[:-1])
                return "Runtime Error", 0, f"Teacher's script did not return a valid score.\nOutput:\n{output}"
        else:
            if run_result.exit_code == 124:
                return "Time Limit Exceeded", 0, "Execution timed out."
            error_msg = f"Execution Failed\nExit Code: {run_result.exit_code}\n---\nOutput:\n{output}"
            return "Wrong Answer", 0, error_msg

    except Exception as e:
        return "System Error", 0, str(e)
    finally:
        if container:
            try:
                container.stop()
            except Exception as exc:
                logger.warning("停止 OOP 沙箱失败: {}", exc)
