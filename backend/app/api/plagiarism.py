from flask import Blueprint, request, jsonify, current_app
from app.models.plagiarism import PlagiarismLog
from app.models.submission import Submission
from app.models.user import db
from app.utils.auth_tools import token_required
from app.services.plagiarism_service import plagiarism_service

plagiarism_bp = Blueprint('plagiarism', __name__)

@plagiarism_bp.route('/logs', methods=['GET'])
@token_required
def get_plagiarism_logs():
    """
    获取查重日志列表（仅限教师）
    支持按题目、考试、最低相似度过滤，并支持分页。
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    # 获取查询参数
    problem_id = request.args.get('problem_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    min_score = request.args.get('min_score', type=float, default=0.0)
    page = request.args.get('page', type=int, default=1)
    page_size = request.args.get('page_size', type=int, default=20)

    # 构建查询
    query = PlagiarismLog.query.join(Submission, PlagiarismLog.submission_id == Submission.id)
    
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    
    if exam_id:
        query = query.filter(Submission.exam_id == exam_id)
    
    if min_score > 0:
        query = query.filter(PlagiarismLog.similarity_score >= min_score)

    # 执行分页查询
    pagination = query.order_by(PlagiarismLog.similarity_score.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    
    # 格式化结果
    logs_data = []
    for log in pagination.items:
        logs_data.append({
            "id": log.id,
            "submission_id": log.submission_id,
            "target_submission_id": log.target_submission_id,
            "similarity_score": round(log.similarity_score, 2),
            "problem_id": log.submission.problem_id,
            "exam_id": log.submission.exam_id,
            "user_id": log.submission.user_id,
            "username": log.submission.user.username,
            "created_at": log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page,
        "page_size": pagination.per_page,
        "data": logs_data
    }), 200

@plagiarism_bp.route('/logs/<int:submission_id>', methods=['GET'])
@token_required
def get_submission_plagiarism_log(submission_id):
    """获取特定提交的查重详情"""
    log = PlagiarismLog.query.filter_by(submission_id=submission_id).first()
    if not log:
        return jsonify({"error": "Plagiarism log not found"}), 404
    
    # 权限检查：如果是学生，只能看自己的
    if request.current_user.role == 'student' and log.submission.user_id != request.current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    return jsonify({
        "id": log.id,
        "submission_id": log.submission_id,
        "target_submission_id": log.target_submission_id,
        "similarity_score": round(log.similarity_score, 2),
        "problem_id": log.submission.problem_id,
        "exam_id": log.submission.exam_id,
        "user_id": log.submission.user_id,
        "username": log.submission.user.username,
        "created_at": log.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@plagiarism_bp.route('/check_batch', methods=['POST'])
@token_required
def trigger_batch_check():
    """手动触发批量查重（仅限教师）"""
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    submission_ids = data.get('submission_ids', [])
    
    if not submission_ids:
        return jsonify({"error": "No submission_ids provided"}), 400

    app = current_app._get_current_object()
    plagiarism_service.start_check_task(app, submission_ids)
    
    return jsonify({"message": "Batch plagiarism check started"}), 202

@plagiarism_bp.route('/logs/<int:log_id>', methods=['DELETE'])
@token_required
def delete_plagiarism_log(log_id):
    """删除查重日志（仅限教师）"""
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    log = PlagiarismLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    
    return jsonify({"message": "Log deleted"}), 200
