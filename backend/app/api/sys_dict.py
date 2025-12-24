from flask import Blueprint, jsonify, request
from app.models.sysdict import SysDict
from app.models.user import db, User
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.exam import Exam
from app.utils.auth_tools import token_required
from datetime import datetime, timedelta

sys_dict_bp = Blueprint('sys_dict', __name__)

@sys_dict_bp.route('/info', methods=['GET'])
def get_sys_info():
    """
    获取系统级常量配置
    """
    dicts = SysDict.query.all()
    # 将数据库中的键值对转换为字典格式返回
    config = {d.key: d.val for d in dicts}
    
    # 确保前端需要的字段存在，如果不存在则返回默认值
    required_fields = {
        "title": "SKYOJ",
        "info": "",
        "warning": "false",
        "practice": "true",
        "llm_api_url": "",
        "llm_model_name": "",
        "llm_api_key": ""
    }
    
    for key, default in required_fields.items():
        if key not in config:
            config[key] = default
            
    # 转换布尔字符串
    if "warning" in config:
        config["warning"] = config["warning"].lower() == "true"
    if "practice" in config:
        config["practice"] = config["practice"].lower() == "true"
            
    return jsonify(config), 200

@sys_dict_bp.route('/info', methods=[ 'PUT'])
@token_required
def update_sys_info():
    """
    更新或新增系统级常量配置 (仅限教师/管理员)
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid data format"}), 400

    updated_keys = []
    for key, val in data.items():
        # 查找是否存在该键
        item = SysDict.query.filter_by(key=key).first()
        if item:
            item.val = str(val).lower() if isinstance(val, bool) else str(val)
        else:
            # 如果不存在则新增
            item = SysDict(key=key, val=str(val).lower() if isinstance(val, bool) else str(val))
            db.session.add(item)
        updated_keys.append(key)

    db.session.commit()
    return jsonify({
        "message": "System configuration updated successfully",
        "updated_keys": updated_keys
    }), 200

@sys_dict_bp.route('/info/<string:key>', methods=['DELETE'])
@token_required
def delete_sys_info(key):
    """
    删除指定的系统级常量配置 (仅限教师/管理员)
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    item = SysDict.query.filter_by(key=key).first()
    if not item:
        return jsonify({"error": "Key not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": f"Key '{key}' deleted successfully"}), 200

@sys_dict_bp.route('/statistics', methods=['GET'])
@token_required
def get_statistics():
    """
    获取今日提交量、总题目数、一年前到六个月范围内的考试数量、用户数量
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
        
    # 1. 今日提交量
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_submissions = Submission.query.filter(Submission.created_at >= today_start).count()

    # 2. 总题目数
    total_problems = Problem.query.count()

    # 3. 用户数量
    total_users = User.query.count()

    # 4. 一年前到六个月范围内的考试数量
    now = datetime.utcnow()
    one_year_ago = now - timedelta(days=365)
    six_months_ago = now + timedelta(days=180)
    
    exams_in_range = Exam.query.filter(
        Exam.start_time >= one_year_ago,
        Exam.start_time <= six_months_ago
    ).count()

    return jsonify({
        "today_submissions": today_submissions,
        "total_problems": total_problems,
        "total_users": total_users,
        "exams_in_period": exams_in_range
    }), 200
