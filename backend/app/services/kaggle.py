import os

from app.models.problem import Problem
from app.services.judge_service import client, IMAGE_NAME, create_tar_stream, create_tar_from_path


def run_kaggle_judge(submission_id, user_csv_content, problem_id):
    """
    Kaggle 模式判题逻辑
    约定:
    - 教师提供: main.py (评分脚本) 和 truth.csv (标准答案)
    - 学生提供: CSV 内容
    - 评分脚本需读取 truth.csv 和 submission.csv，并将最终分数打印到标准输出的最后一行
    """
    problem = Problem.query.get(problem_id)
    problem_dir = f"uploads/problems/{problem_id}"

    teacher_files = ['main.py', 'truth.csv']
    for f_name in teacher_files:
        if not os.path.exists(os.path.join(problem_dir, f_name)):
            return "System Error", 0, f"Missing teacher file: {f_name}"

    container = None
    try:
        container = client.containers.run(
            image=IMAGE_NAME,
            command="sleep 600",
            detach=True,
            network_mode="none",
            mem_limit=f"{problem.memory_limit}m",
            nano_cpus=1000000000,
            remove=True
        )

        # 1. 上传学生提交的 CSV
        student_tar = create_tar_from_path(os.path.abspath(user_csv_content), 'submission.csv')
        container.put_archive('/app', student_tar)

        # 2. 上传教师的评分脚本和真值表
        for f_name in teacher_files:
            with open(os.path.join(problem_dir, f_name), 'rb') as f:
                content = f.read()
            container.put_archive('/app', create_tar_stream(f_name, content))

        # 3. 运行评分脚本
        # Kaggle 评分脚本可能涉及大量计算，给予较长超时
        time_limit = getattr(problem, 'time_limit', 30)
        run_result = container.exec_run(f"sh -c 'timeout {time_limit}s python3 main.py'")
        output = run_result.output.decode('utf-8').strip()

        if run_result.exit_code != 0:
            if run_result.exit_code == 124:
                return "Time Limit Exceeded", 0, "Scoring script timed out."
            return "Runtime Error", 0, f"Scoring script failed:\n{output}"

        # 4. 解析分数 (取输出的最后一行)
        lines = output.splitlines()
        if not lines:
            return "Runtime Error", 0, "Scoring script produced no output"

        try:
            final_score = float(lines[-1])
            log_output = "\n".join(lines[:-1]) if len(lines) > 1 else "Score calculated."
            return "Accepted" if final_score == 100 else "Wrong Answer", final_score, log_output
        except ValueError:
            return "Runtime Error", 0, f"Scoring script did not return a valid number at the last line.\nOutput: {output}"

    except Exception as e:
        return "System Error", 0, str(e)
    finally:
        if container:
            try:
                container.stop()
            except:
                pass
