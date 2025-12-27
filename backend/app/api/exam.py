import hashlib
import io
import csv
from datetime import datetime

from app.models.exam import Exam, ExamProblem
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import db, User
from app.services.plagiarism_service import plagiarism_service
from app.utils.auth_tools import token_required, encode_auth_token
from flask import Blueprint, request, jsonify, current_app, send_file
from sqlalchemy import func

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
    
    result = []
    for e in exams:
        d = e.to_dict()
        # 获取题目数
        d['problem_count'] = ExamProblem.query.filter_by(exam_id=e.id).count()
        # 获取提交次数
        d['submission_count'] = Submission.query.filter_by(exam_id=e.id).count()
        result.append(d)
        
    return jsonify(result), 200


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

    # 如果 Token 中的 exam_id 与当前考试 ID 一致，则跳过密码验证
    if getattr(request, 'exam_id', -1) != exam_id:
        # 验证密码
        if exam.password:
            data = request.get_json(silent=True) or {}
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


@exam_bp.route('/<int:exam_id>/monitor', methods=['GET'])
@token_required
def get_exam_monitor(exam_id):
    """
    获取考试监控数据（教师端）
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    exam = Exam.query.get_or_404(exam_id)

    # 1. 获取考试题目列表，用于表头
    exam_problems = ExamProblem.query.filter_by(exam_id=exam_id).all()
    problem_headers = [{
        "problem_id": ep.problem_id,
        "display_id": ep.display_id,
        "max_score": ep.score
    } for ep in exam_problems]

    # 2. 获取所有在该考试中有提交记录的用户
    user_ids = db.session.query(Submission.user_id).filter(Submission.exam_id == exam_id).distinct().all()
    user_ids = [uid[0] for uid in user_ids]

    monitor_data = []
    for uid in user_ids:
        user = User.query.get(uid)
        user_status = {
            "user_id": user.id,
            "username": user.username,
            "total_score": 0,
            "submissions": {}
        }

        for ep in exam_problems:
            # 获取该用户该题目的最后一次提交
            last_sub = Submission.query.filter_by(
                exam_id=exam_id,
                user_id=uid,
                problem_id=ep.problem_id
            ).order_by(Submission.created_at.desc()).first()

            if last_sub:
                user_status["submissions"][ep.problem_id] = {
                    "submission_id": last_sub.id,
                    "status": last_sub.status,
                    "score": last_sub.score,
                    "time": last_sub.created_at.isoformat()
                }
                # 累加得分（如果是 Accepted 或者是 Kaggle 模式的分数）
                user_status["total_score"] += last_sub.score
            else:
                user_status["submissions"][ep.problem_id] = {
                    "status": "Not Attempted",
                    "score": 0
                }

        monitor_data.append(user_status)

    # 按总分降序排列
    monitor_data.sort(key=lambda x: x['total_score'], reverse=True)

    return jsonify({
        "exam_title": exam.title,
        "problems": problem_headers,
        "users": monitor_data
    }), 200


@exam_bp.route('/<int:exam_id>/rank', methods=['GET'])
@token_required
def get_exam_rank(exam_id):
    """
    获取 ACM 模式滚榜数据
    """
    exam = Exam.query.get_or_404(exam_id)
    exam_problems = ExamProblem.query.filter_by(exam_id=exam_id).all()
    problem_ids = [ep.problem_id for ep in exam_problems]
    
    # 获取该考试的所有提交记录
    submissions = Submission.query.filter(
        Submission.exam_id == exam_id,
        Submission.problem_id.in_(problem_ids)
    ).order_by(Submission.created_at.asc()).all()

    rank_data = {}
    for sub in submissions:
        if sub.user_id not in rank_data:
            rank_data[sub.user_id] = {
                "user_id": sub.user_id,
                "username": sub.user.username,
                "solved": 0,
                "penalty": 0,
                "problems": {pid: {"solved": False, "failed_attempts": 0, "time": 0} for pid in problem_ids}
            }
        
        user_rank = rank_data[sub.user_id]
        prob_stats = user_rank["problems"].get(sub.problem_id)
        if not prob_stats or prob_stats["solved"]:
            continue

        if sub.status == 'Accepted':
            prob_stats["solved"] = True
            # 计算时间（秒）
            time_diff = int((sub.created_at - exam.start_time).total_seconds())
            prob_stats["time"] = time_diff
            user_rank["solved"] += 1
            # 罚时 = 通过时间 + 错误尝试次数 * 20分钟(1200秒)
            user_rank["penalty"] += time_diff + prob_stats["failed_attempts"] * 1200
        elif sub.status not in ['Pending', 'Compile Error']:
            # 编译错误通常不计入罚时
            prob_stats["failed_attempts"] += 1

    # 转换为列表并排序：解题数降序，罚时升序
    sorted_rank = list(rank_data.values())
    sorted_rank.sort(key=lambda x: (-x["solved"], x["penalty"]))

    return jsonify({
        "exam_title": exam.title,
        "problems": [{"problem_id": ep.problem_id, "display_id": ep.display_id} for ep in exam_problems],
        "rank": sorted_rank
    }), 200


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


@exam_bp.route('/<int:exam_id>/check_plagiarism', methods=['POST'])
@token_required
def check_exam_plagiarism(exam_id):
    """
    针对某场考试的所有人每一题的最后一次提交记录进行查重（教师手动触发）
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    # 获取该考试中每个用户对每个题目的最后一次提交 ID
    subquery = db.session.query(
        Submission.user_id,
        Submission.problem_id,
        func.max(Submission.id).label('max_id')
    ).filter(Submission.exam_id == exam_id).group_by(
        Submission.user_id,
        Submission.problem_id
    ).subquery()

    submission_ids = [row.max_id for row in db.session.query(subquery.c.max_id).all()]
    
    if not submission_ids:
        return jsonify({"message": "No submissions found for this exam"}), 200

    app = current_app._get_current_object()
    plagiarism_service.start_check_task(app, submission_ids)

    return jsonify({
        "message": f"Plagiarism check started for {len(submission_ids)} final submissions in exam #{exam_id}.",
        "count": len(submission_ids)
    }), 202


@exam_bp.route('/<int:exam_id>/export_scores', methods=['GET'])
@token_required
def export_exam_scores(exam_id):
    """
    导出考试成绩为 CSV 文件（教师权限）
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    exam = Exam.query.get_or_404(exam_id)
    exam_problems = ExamProblem.query.filter_by(exam_id=exam_id).order_by(ExamProblem.display_id).all()
    
    # 获取所有在该考试中有提交记录的用户
    user_ids = db.session.query(Submission.user_id).filter(Submission.exam_id == exam_id).distinct().all()
    user_ids = [uid[0] for uid in user_ids]

    # 准备 CSV 数据
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 表头
    header = ['User ID', 'Username']
    for ep in exam_problems:
        header.append(f'{ep.display_id} (Max: {ep.score})')
    header.append('Total Score')
    writer.writerow(header)

    # 数据行
    for uid in user_ids:
        user = User.query.get(uid)
        row = [user.id, user.username]
        total_score = 0
        
        for ep in exam_problems:
            last_sub = Submission.query.filter_by(
                exam_id=exam_id,
                user_id=uid,
                problem_id=ep.problem_id
            ).order_by(Submission.created_at.desc()).first()
            
            score = last_sub.score if last_sub else 0
            row.append(score)
            total_score += score
            
        row.append(total_score)
        writer.writerow(row)

    output.seek(0)
    filename = f"exam_{exam_id}_scores_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )
