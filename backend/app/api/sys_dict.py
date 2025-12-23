from flask import Blueprint, jsonify, request
from app.models.sysdict import SysDict
from app.models.user import db
from app.utils.auth_tools import token_required

sys_dict_bp = Blueprint('sys_dict', __name__)

@sys_dict_bp.route('/info', methods=['GET'])
def get_sys_info():
    """
    获取系统级常量配置
    """
    dicts = SysDict.query.all()
    # 将数据库中的键值对转换为字典格式返回
    config = {d.key: d.val for d in dicts}
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
            item.val = str(val)
        else:
            # 如果不存在则新增
            item = SysDict(key=key, val=str(val))
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
