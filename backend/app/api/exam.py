import hashlib
from flask import Blueprint, request, jsonify, current_app
from app.models.exam import Exam, ExamProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import db
from app.utils.auth_tools import token_required, encode_auth_token
from datetime import datetime

exam_bp = Blueprint('exam', __name__)

def hash_exam_password(password):
    """使用 SECRET_KEY 对考试密码进行简单哈希"""
    if not password:
        return None
    secret = current_app.config.get('SECRET_KEY', 'skyoj_secret_key')
    return hashlib.sha256((password + secret).encode()).hexdigest()

# --- 考试管理 (CRUD) ---

@exam_bp.route('/', methods=['POST'])
@token_required
def create_exam():
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.get_json()
    try:
        raw_password = data.get('password')
        hashed_password = hash_exam_password(raw_password) if raw_password else None

        new_exam = Exam(
            title=data['title'],
            description=data.get('description', ''),
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            password=hashed_password,
            is_visible=data.get('is_visible', False),
            created_by=request.current_user.id
        )
        db.session.add(new_exam)
        db.session.commit()
        return jsonify(new_exam.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@exam_bp.route('/', methods=['GET'])
@token_required
def get_exams():
    if request.current_user.role == 'teacher':
        exams = Exam.query.all()
    else:
        exams = Exam.query.filter_by(is_visible=True).all()
    return jsonify([e.to_dict() for e in exams]), 200

@exam_bp.route('/<int:exam_id>', methods=['GET'])
@token_required
def get_exam_detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    data = exam.to_dict()
    data['has_password'] = bool(exam.password)
    
    problems = ExamProblem.query.filter_by(exam_id=exam_id).all()
    data['problems'] = [{
        "problem_id": p.problem_id,
        "display_id": p.display_id,
        "score": p.score,
        "title": p.problem.title
    } for p in problems]
    return jsonify(data), 200

@exam_bp.route('/<int:exam_id>/enter', methods=['POST'])
@token_required
def enter_exam(exam_id):
    """
    进入考试接口：验证密码并返回带有 exam_id 的新 Token
    """
    exam = Exam.query.get_or_404(exam_id)
    
    # 检查考试是否已开始
    now = datetime.utcnow()
    if now < exam.start_time:
        return jsonify({"error": "Exam has not started yet"}), 403
    if now > exam.end_time:
        return jsonify({"error": "Exam has already ended"}), 403

    # 验证密码
    if exam.password:
        data = request.get_json()
        input_password = data.get('password')
        if hash_exam_password(input_password) != exam.password:
            return jsonify({"error": "Incorrect password"}), 401
    
    # 生成包含 exam_id 的新 Token
    new_token = encode_auth_token(
        user_id=request.current_user.id,
        role=request.current_user.role,
        exam_id=exam_id
    )
    
    return jsonify({
        "message": "Successfully entered exam",
        "token": new_token,
        "exam_id": exam_id
    }), 200

@exam_bp.route('/exit', methods=['POST'])
@token_required
def exit_exam():
    """
    退出考试接口：返回不带 exam_id 的普通 Token
    """
    new_token = encode_auth_token(
        user_id=request.current_user.id,
        role=request.current_user.role,
        exam_id=-1
    )
    return jsonify({
        "message": "Successfully exited exam",
        "token": new_token
    }), 200

@exam_bp.route('/status', methods=['GET'])
@token_required
def get_my_exam_status():
    """
    通过 Token 自动获取 exam_id 和 user_id，查询当前考试中所有题目的最后一次提交状态
    """
    user_id = request.current_user.id
    exam_id = getattr(request, 'exam_id', -1)

    if exam_id == -1:
        return jsonify({"error": "You are not in an active exam session"}), 400

    # 1. 获取考试中的所有题目
    exam_problems = ExamProblem.query.filter_by(exam_id=exam_id).all()
    if not exam_problems:
        return jsonify([]), 200

    # 2. 组装结果
    result = []
    for ep in exam_problems:
        # 获取该用户对该题目的最后一次提交记录
        last_submission = Submission.query.filter_by(
            exam_id=exam_id, 
            user_id=user_id, 
            problem_id=ep.problem_id
        ).order_by(Submission.created_at.desc()).first()

        result.append({
            "problem_id": ep.problem_id,
            "display_id": ep.display_id,
            "title": ep.problem.title,
            "max_score": ep.score,
            "status": last_submission.status if last_submission else "Not Attempted",
            "current_score": last_submission.score if last_submission else 0,
            "last_submitted_at": last_submission.created_at.isoformat() if last_submission else None
        })

    return jsonify(result), 200

@exam_bp.route('/<int:exam_id>', methods=['PUT'])
@token_required
def update_exam(exam_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    exam = Exam.query.get_or_404(exam_id)
    data = request.get_json()
    
    if 'title' in data: exam.title = data['title']
    if 'description' in data: exam.description = data['description']
    if 'start_time' in data: exam.start_time = datetime.fromisoformat(data['start_time'])
    if 'end_time' in data: exam.end_time = datetime.fromisoformat(data['end_time'])
    if 'is_visible' in data: exam.is_visible = data['is_visible']
    
    if 'password' in data:
        raw_password = data['password']
        exam.password = hash_exam_password(raw_password) if raw_password else None
    
    db.session.commit()
    return jsonify(exam.to_dict()), 200

@exam_bp.route('/<int:exam_id>', methods=['DELETE'])
@token_required
def delete_exam(exam_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    return jsonify({"message": "Exam deleted"}), 200

# --- 考试题目管理 ---

@exam_bp.route('/<int:exam_id>/problems', methods=['POST'])
@token_required
def add_problem_to_exam(exam_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.get_json()
    new_ep = ExamProblem(
        exam_id=exam_id,
        problem_id=data['problem_id'],
        display_id=data.get('display_id'),
        score=data.get('score', 100)
    )
    db.session.add(new_ep)
    db.session.commit()
    return jsonify({"message": "Problem added to exam"}), 201

@exam_bp.route('/<int:exam_id>/problems/<int:problem_id>', methods=['DELETE'])
@token_required
def remove_problem_from_exam(exam_id, problem_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    ep = ExamProblem.query.filter_by(exam_id=exam_id, problem_id=problem_id).first_or_404()
    db.session.delete(ep)
    db.session.commit()
    return jsonify({"message": "Problem removed from exam"}), 200
