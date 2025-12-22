import io
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
