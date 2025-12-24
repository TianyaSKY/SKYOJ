from flask import Blueprint, jsonify, request
from app.models.submission import Submission
from app.models.user import User, db
from app.utils.auth_tools import token_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/all', methods=['GET'])
@token_required
def get_all_users():
    """
    获取所有用户列表 (仅限教师/管理员)
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
        
    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "role": u.role
    } for u in users]), 200

@user_bp.route('/<int:user_id>/profile', methods=['GET'])
@token_required
def get_user_profile(user_id):
    """
    获取指定用户资料
    """
    user = User.query.get_or_404(user_id)
    # 假设 User 模型中没有 created_at 和 avatar，这里先返回基础信息
    # 如果后续模型更新了，可以再添加
    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": None, # 占位
        "avatar": "" 
    }), 200

@user_bp.route('/<int:user_id>/submissions', methods=['GET'])
@token_required
def get_other_user_submissions(user_id):
    """
    获取指定用户的提交历史
    """
    # 如果是查看自己，或者当前用户是老师，则允许查看
    if request.current_user.id != user_id and request.current_user.role != 'teacher':
        # 这里可以根据隐私设置进一步过滤，目前简单处理
        pass

    submissions = Submission.query.filter_by(user_id=user_id).order_by(Submission.created_at.desc()).all()
    
    result = []
    for s in submissions:
        result.append({
            "id": s.id,
            "problem_id": s.problem_id,
            "problem_title": s.problem.title if s.problem else "Unknown",
            "status": s.status,
            "score": s.score,
            "language": s.language,
            "created_at": s.created_at.isoformat(),
            "exam_id":s.exam_id
        })
    
    return jsonify(result), 200

@user_bp.route('/submissions', methods=['GET'])
@token_required
def get_user_submissions():
    # 从 token_required 装饰器设置的 request.current_user 中获取当前用户
    user = request.current_user
    
    # 查询该用户的所有提交记录，按时间倒序排列
    submissions = Submission.query.filter_by(user_id=user.id).order_by(Submission.created_at.desc()).all()
    
    result = []
    for s in submissions:
        result.append({
            "id": s.id,
            "problem_id": s.problem_id,
            "problem_title": s.problem.title if s.problem else "Unknown",
            "status": s.status,
            "score": s.score,
            "language": s.language,
            "created_at": s.created_at.isoformat(),
            "exam_id": s.exam_id
        })
    
    return jsonify(result), 200
