import os

from app.models.problem import Problem
from app.services.judge_service import client, IMAGE_NAME, create_tar_stream


def run_oop_judge(submission_id, user_code, problem_id, language='python'):
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

    problem = Problem.query.get(problem_id)
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
            mem_limit=f"{problem.memory_limit}m",
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
        run_cmd = f"sh -c 'timeout {time_limit}s {lang_config['run']}'"
        run_result = container.exec_run(run_cmd)
        output = run_result.output.decode('utf-8')

        # 5. 判定结果 (约定：教师程序最后一行输出分数 0-100)
        lines = output.strip().splitlines()
        if run_result.exit_code == 0 and lines:
            try:
                # 尝试解析最后一行作为分数
                final_score = float(lines[-1].strip())
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
            except:
                pass
