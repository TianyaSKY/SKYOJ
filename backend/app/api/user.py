import os
import uuid

from flask import Blueprint, jsonify, request, current_app, send_from_directory
from werkzeug.utils import secure_filename

from app.models.submission import Submission
from app.models.user import User, db
from app.utils.auth_tools import token_required

user_bp = Blueprint('user', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        "role": u.role,
        "avatar": u.avatar
    } for u in users]), 200


@user_bp.route('/<int:user_id>/profile', methods=['GET'])
@token_required
def get_user_profile(user_id):
    """
    获取指定用户资料
    """
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "avatar": user.avatar
    }), 200


@user_bp.route('/avatar', methods=['POST'])
@token_required
def upload_avatar():
    """
    上传头像
    """
    if 'avatar' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 使用 UUID 重命名文件以防止冲突
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{ext}"

        # 统一保存到 backend/uploads/avatars
        upload_folder = os.path.join(current_app.root_path, '..', 'uploads', 'avatars')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file.save(os.path.join(upload_folder, new_filename))

        # 更新用户头像路径
        user = request.current_user
        user.avatar = f"/api/user/avatars/{new_filename}"
        db.session.commit()

        return jsonify({"message": "Avatar uploaded successfully", "avatar": user.avatar}), 200

    return jsonify({"error": "Invalid file type"}), 400


@user_bp.route('/avatars/<filename>')
def get_avatar_file(filename):
    """
    获取头像文件
    """
    upload_folder = os.path.join(current_app.root_path, '..', 'uploads', 'avatars')
    return send_from_directory(upload_folder, filename)


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
            "exam_id": s.exam_id
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
