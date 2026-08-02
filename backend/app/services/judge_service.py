import io
import os
import tarfile

from app.models.submission import Submission
from loguru import logger

IMAGE_NAME = "skyoj-runner"
_client = None


def _get_docker_client():
    global _client
    if _client is None:
        import docker

        _client = docker.from_env()
    return _client


# Backwards-compatible attribute used by acm/oop/kaggle
class _ClientProxy:
    def __getattr__(self, name):
        return getattr(_get_docker_client(), name)


client = _ClientProxy()


def create_tar_stream(filename, content):
    """创建一个包含单个文件的 tar 流，用于上传到容器"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        if isinstance(content, str):
            content = content.encode("utf-8")
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    tar_stream.seek(0)
    return tar_stream


def create_tar_from_path(local_path, remote_filename):
    """
    将宿主机的本地文件打包成 tar 流
    :param local_path: 宿主机上的文件绝对路径
    :param remote_filename: 放入容器后的文件名
    """
    tar_stream = io.BytesIO()

    if not os.path.exists(local_path):
        raise FileNotFoundError(f"无法打包，找不到源文件: {local_path}")

    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar.add(local_path, arcname=remote_filename)

    tar_stream.seek(0)
    return tar_stream


def judge_submission(submission_id: int, db=None) -> None:
    """读取提交并执行判题；该函数只在 Judge Worker 中调用。"""
    owns_session = db is None
    if owns_session:
        from app.database import SessionLocal

        db = SessionLocal()
    try:
        from app.services.acm import run_acm_judge
        from app.services.oop import run_oop_judge
        from app.services.kaggle import run_kaggle_judge

        submission = db.get(Submission, submission_id)
        if not submission:
            logger.warning("提交记录不存在，跳过判题 submission_id={}", submission_id)
            return

        try:
            problem_type = str(submission.problem.type or "acm").lower()
            user_code = submission.code_content or ""
            problem_id = submission.problem_id
            language = submission.language or "python"
            if problem_type == "acm":
                status, score, log = run_acm_judge(
                    submission_id, user_code, problem_id, language, db=db
                )
            elif problem_type == "oop":
                status, score, log = run_oop_judge(
                    submission_id, user_code, problem_id, language, db=db
                )
            elif problem_type == "kaggle":
                status, score, log = run_kaggle_judge(
                    submission_id, user_code, problem_id, db=db
                )
            else:
                status, score, log = "System Error", 0, "Unsupported problem type"

            submission.status = status
            submission.score = score
            submission.output_log = log
        except Exception as exc:
            submission.status = "System Error"
            submission.output_log = f"Judge Error: {str(exc)}"
            logger.exception("判题业务执行异常 submission_id={}", submission_id)

        db.commit()
    finally:
        if owns_session:
            db.close()


def save_non_acm_script(problem_id, code, problem_type, language):
    """封装非 ACM 类型的脚本保存逻辑"""
    problem_dir = os.path.join("uploads/problems", str(problem_id))
    os.makedirs(problem_dir, exist_ok=True)

    lang_map = {
        "python": "main.py",
        "c": "main.c",
        "cpp": "main.cpp",
        "java": "Main.java",
    }

    filename = lang_map.get((language or "python").lower(), "main.py")
    file_path = os.path.join(problem_dir, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return True, f"Script saved as {filename} for {problem_type} problem."
    except Exception as exc:
        logger.exception(
            "保存非 ACM 测试脚本失败 problem_id={} problem_type={}",
            problem_id,
            problem_type,
        )
        return False, str(exc)
