import io
import os
import tarfile

import docker

from app.models.submission import Submission
from app.models.user import db

client = docker.from_env()
IMAGE_NAME = "skyoj-runner"


def create_tar_stream(filename, content):
    """创建一个包含单个文件的 tar 流，用于上传到容器"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        if isinstance(content, str):
            content = content.encode('utf-8')
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    tar_stream.seek(0)
    return tar_stream


def create_tar_from_path(local_path, remote_filename):
    """
    将宿主机的本地文件打包成 tar 流
    :param local_path: 宿主机上的文件绝对路径 (例如: /app/uploads/submissions/xxx.csv)
    :param remote_filename: 放入容器后的文件名 (例如: submission.csv)
    """
    tar_stream = io.BytesIO()

    # 检查文件是否存在
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"无法打包，找不到源文件: {local_path}")

    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        # arcname 决定了文件在 tar 包里的名字（即解压到容器后的文件名）
        tar.add(local_path, arcname=remote_filename)

    tar_stream.seek(0)
    return tar_stream


def judge_submission(app, submission_id, problem_type, user_code, problem_id, language):
    """
    执行判题逻辑 (替代原 Celery Task)
    """
    # 在线程中手动推入应用上下文，否则无法使用 db
    with app.app_context():
        # 避免循环引用，在函数内部导入具体判题服务
        from app.services.acm import run_acm_judge
        from app.services.oop import run_oop_judge
        from app.services.kaggle import run_kaggle_judge

        submission = Submission.query.get(submission_id)
        if not submission:
            return

        try:
            if problem_type == 'acm':
                status, score, log = run_acm_judge(submission_id, user_code, problem_id, language)
            elif problem_type == 'oop':
                status, score, log = run_oop_judge(submission_id, user_code, problem_id, language)
            elif problem_type == 'kaggle':
                status, score, log = run_kaggle_judge(submission_id, user_code, problem_id)
            else:
                status, score, log = 'System Error', 0, 'Unsupported problem type'

            submission.status = status
            submission.score = score
            submission.output_log = log
        except Exception as e:
            submission.status = 'System Error'
            submission.output_log = f"Judge Error: {str(e)}"

        db.session.commit()


def save_non_acm_script(problem_id, code, problem_type, language):
    """
    封装非 ACM 类型的脚本保存逻辑
    """
    problem_dir = os.path.join("uploads/problems", str(problem_id))
    os.makedirs(problem_dir, exist_ok=True)

    # 映射语言到文件名
    lang_map = {
        'python': 'main.py',
        'c': 'main.c',
        'cpp': 'main.cpp',
        'java': 'Main.java'
    }

    # 如果是 Kaggle 类型，通常固定为 score.py，但根据用户要求，这里优先遵循语言映射
    # 如果 language 没传或不在映射中，默认用 .py
    filename = lang_map.get(language.lower(), 'main.py')
    # 但用户明确要求保存为 main.cpp/main.c/main.py/Main.java

    file_path = os.path.join(problem_dir, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        return True, f"Script saved as {filename} for {problem_type} problem."
    except Exception as e:
        return False, str(e)
