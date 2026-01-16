import os
from datetime import datetime
from threading import Thread

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.models.exam import Exam
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import db, User
from app.services.judge_service import judge_submission
from app.services.plagiarism_service import plagiarism_service
from app.utils.auth_tools import token_required

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


@submission_bp.route('', methods=['GET'])
@token_required
def list_submissions():
    """
    获取提交列表，支持多种筛选
    """
    problem_id = request.args.get('problem_id', type=int)
    user_id = request.args.get('user_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    status = request.args.get('status')
    username = request.args.get('username')

    query = Submission.query

    # 权限控制：学生只能看自己的提交，除非是特定题目的公共提交（如果系统有此设定）
    # 这里默认教师可以看所有，学生只能看自己的
    if request.current_user.role == 'student':
        query = query.filter(Submission.user_id == request.current_user.id)
    elif user_id:
        query = query.filter(Submission.user_id == user_id)

    if username:
        query = query.join(User).filter(User.username.like(f"%{username}%"))

    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)

    if exam_id:
        query = query.filter(Submission.exam_id == exam_id)

    if status:
        query = query.filter(Submission.status == status)

    # 分页
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = query.order_by(Submission.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    submissions = pagination.items

    return jsonify({
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
        "submissions": [{
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.username,
            "problem_id": s.problem_id,
            "exam_id": s.exam_id,
            "status": s.status,
            "score": s.score,
            "language": s.language,
            "created_at": s.created_at.isoformat()
        } for s in submissions]
    }), 200


@submission_bp.route('/<int:submission_id>', methods=['GET'])
@token_required
def get_submission(submission_id, *args, **kwargs):
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # 权限检查
    if request.current_user.role == 'student' and submission.user_id != request.current_user.id:
        return jsonify({"error": "Permission denied"}), 403

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


@submission_bp.route('/<int:submission_id>/check_plagiarism', methods=['POST'])
@token_required
def check_single_submission_plagiarism(submission_id):
    """
    针对单个提交记录进行查重（教师手动触发）
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    submission = Submission.query.get_or_404(submission_id)

    app = current_app._get_current_object()
    plagiarism_service.start_check_task(app, [submission.id])

    return jsonify({
        "message": f"Plagiarism check started for submission #{submission_id}."
    }), 202
