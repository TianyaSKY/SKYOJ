import os
from datetime import datetime
from threading import Thread

from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import db
from app.services.judge_service import judge_submission
from app.utils.auth_tools import token_required
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

submission_bp = Blueprint('submission', __name__)

UPLOAD_SUBMISSION_DIR = "uploads/submissions"


@submission_bp.route('/submit', methods=['POST'])
@token_required
def submit_code():
    # 尝试获取 JSON 数据
    data = request.get_json(silent=True)

    if data:
        problem_id = data.get('problem_id')
        user_code = data.get('code')
        language = data.get('language')
        exam_id = data.get('exam_id', -1)
    else:
        problem_id = request.form.get('problem_id')
        language = request.form.get('language')
        user_code = request.form.get('code', '')
        exam_id = request.form.get('exam_id', -1)

        # 处理 Kaggle 模式的文件上传
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # 如果是 CSV 提交，保存文件
                if language == 'csv' or (file.filename and file.filename.endswith('.csv')):
                    if not os.path.exists(UPLOAD_SUBMISSION_DIR):
                        os.makedirs(UPLOAD_SUBMISSION_DIR)

                    filename = secure_filename(f"{request.current_user.id}_{problem_id}_{file.filename}")
                    file_path = os.path.join(UPLOAD_SUBMISSION_DIR, filename)
                    file.save(file_path)
                    user_code = file_path  # 在 Kaggle 模式下，code_content 存储文件路径
                else:
                    user_code = file.read().decode('utf-8')

    if not problem_id or not user_code:
        return jsonify({"error": "Missing problem_id or code/file"}), 400

    # 考试 ID 校验逻辑
    try:
        exam_id = int(exam_id)
    except (ValueError, TypeError):
        exam_id = -1

    if exam_id != -1:
        # 检测该考试是否存在且当前时间是否在考试时间内
        now = datetime.now()
        exam = Exam.query.filter(
            Exam.id == exam_id,
            Exam.start_time <= now,
            Exam.end_time >= now
        ).first()

        if not exam:
            # 如果考试不存在或不在时间内，强制设为 -1 (普通提交)
            exam_id = -1

    user_id = request.current_user.id
    # 如果是 -1，在数据库中存为 None
    db_exam_id = exam_id if exam_id != -1 else None

    problem = Problem.query.get(problem_id)
    if not problem:
        return jsonify({"error": "Problem not found"}), 404

    # 1. 记录初始提交
    new_submission = Submission(
        user_id=user_id,
        problem_id=problem_id,
        exam_id=db_exam_id,  # 自动关联当前考试
        language=language,
        code_content=user_code,
        status='Pending'
    )
    db.session.add(new_submission)
    db.session.commit()

    # 2. 使用线程异步执行判题
    app = current_app._get_current_object()
    Thread(target=judge_submission,
           args=(app, new_submission.id, str(problem.type), user_code, problem_id, language)).start()

    # 3. 立即返回
    return jsonify({
        "message": "Submission received, judging in background.",
        "submission_id": new_submission.id,
        "status": "Pending",
        "exam_id": db_exam_id
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
        "log": submission.output_log,
        "code": submission.code_content,
        "language": submission.language,
        "exam_id": submission.exam_id,
        "created_at": submission.created_at.isoformat()
    }), 200
