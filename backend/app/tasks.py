from app.extensions import celery
from app.models.submission import Submission
from app.models.user import db
from app.services.acm import run_acm_judge
from app.services.oop import run_oop_judge
from app.services.kaggle import run_kaggle_judge

@celery.task
def judge_submission_task(submission_id, problem_type, user_code, problem_id, language):
    """
    Celery 异步判题任务
    """
    # 在 Flask 上下文中获取提交记录
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