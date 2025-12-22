from threading import Thread
from flask import Blueprint, request, jsonify, current_app

from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import db
from app.services.judge_service import judge_submission
from app.utils.auth_tools import token_required

submission_bp = Blueprint('submission', __name__)


@submission_bp.route('/submit', methods=['POST'])
@token_required
def submit_code(*args, **kwargs):
    data = request.get_json()
    problem_id = data.get('problem_id')
    user_code = data.get('code')
    language = data.get('language')  # 获取语言，默认为 python

    # CRITICAL SECURITY FIX: Get user_id from the validated token, not the request body.
    user_id = request.current_user.id

    problem = Problem.query.get(problem_id)
    if not problem:
        return jsonify({"error": "Problem not found"}), 404

    # 1. 记录初始提交
    new_submission = Submission(user_id=user_id, problem_id=problem_id, language=language, status='Pending')
    db.session.add(new_submission)
    db.session.commit()

    # 2. 使用线程异步执行判题 (替代 Celery)
    # 获取当前 app 的真实对象传入线程
    app = current_app._get_current_object()
    Thread(target=judge_submission, args=(app, new_submission.id, str(problem.type), user_code, problem_id, language)).start()

    # 3. 立即返回，告知前端已接收
    return jsonify({
        "message": "Submission received, judging in background.",
        "submission_id": new_submission.id,
        "status": "Pending"
    }), 202


@submission_bp.route('/<int:submission_id>', methods=['GET'])
@token_required
def get_submission(submission_id, *args, **kwargs):
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    return jsonify({
        "id": submission.id,
        "status": submission.status,
        "score": submission.score,
        "log": submission.output_log
    }), 200
