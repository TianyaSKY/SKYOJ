from flask import Blueprint, jsonify, request
from app.models.submission import Submission
from app.utils.auth_tools import token_required

user_bp = Blueprint('user', __name__)

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
            "created_at": s.created_at.isoformat()
        })
    
    return jsonify(result), 200
