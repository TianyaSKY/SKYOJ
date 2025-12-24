import os
import shutil
import zipfile
import io

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from app.models.problem import Problem
from app.models.user import db
from app.utils.auth_tools import token_required

problem_bp = Blueprint('problem', __name__)
UPLOAD_BASE_DIR = "uploads/problems"


@problem_bp.route('/', methods=['POST'])
@token_required
def create_problem():
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    data = request.get_json()

    # 提取字段
    new_problem = Problem(
        title=data.get('title'),
        content=data.get('content'),
        language=data.get('language'), # 前端传过来的是逗号分隔的字符串
        type=data.get('type'),  # 'acm', 'oop', 'kaggle'
        time_limit=data.get('time_limit', 1000),
        memory_limit=data.get('memory_limit', 128),
        template_code=data.get('template_code', '')
    )

    db.session.add(new_problem)
    db.session.commit()

    return jsonify({
        "message": "Problem created successfully",
        "problem_id": new_problem.id
    }), 201


@problem_bp.route('/', methods=['GET'])
def get_problems():
    problems = Problem.query.all()
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "type": p.type,
        "language": p.language,
        "time_limit": p.time_limit,
        "memory_limit": p.memory_limit
    } for p in problems]), 200


@problem_bp.route('/<int:problem_id>', methods=['GET'])
def get_problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    return jsonify({
        "id": problem.id,
        "title": problem.title,
        "content": problem.content,
        "type": problem.type,
        "language": problem.language,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "template_code": problem.template_code
    }), 200


@problem_bp.route('/<int:problem_id>', methods=['PUT'])
@token_required
def update_problem(problem_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    problem = Problem.query.get_or_404(problem_id)
    data = request.get_json()

    problem.title = data.get('title', problem.title)
    problem.content = data.get('content', problem.content)
    problem.language = data.get('language', problem.language)
    problem.type = data.get('type', problem.type)
    problem.time_limit = data.get('time_limit', problem.time_limit)
    problem.memory_limit = data.get('memory_limit', problem.memory_limit)
    problem.template_code = data.get('template_code', problem.template_code)

    db.session.commit()
    return jsonify({"message": "Problem updated successfully"}), 200


@problem_bp.route('/<int:problem_id>', methods=['DELETE'])
@token_required
def delete_problem(problem_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    problem = Problem.query.get_or_404(problem_id)
    
    # 删除关联的测试用例目录
    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)
        
    db.session.delete(problem)
    db.session.commit()
    return jsonify({"message": "Problem deleted successfully"}), 200


@problem_bp.route('/<int:problem_id>/upload_files', methods=['POST'])
@token_required
def upload_files(problem_id):
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    # 1. 检查是否有文件
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 2. 确保目标目录存在
    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)  # 如果已存在则清空旧数据
    os.makedirs(problem_dir)

    # 3. 保存并解压
    filename = secure_filename(file.filename)
    zip_path = os.path.join(problem_dir, filename)
    file.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(problem_dir)

        # 删除原始压缩包
        os.remove(zip_path)

        return jsonify({
            "message": f"Test cases for problem {problem_id} uploaded and extracted successfully.",
            "files": os.listdir(problem_dir)
        }), 200
    except zipfile.BadZipFile:
        return jsonify({"error": "Invalid zip file"}), 400


@problem_bp.route('/<int:problem_id>/test_cases', methods=['DELETE'])
@token_required
def delete_test_cases(problem_id):
    """
    删除某题的所有测试点文件
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403
    
    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        # 清空目录下的所有内容，但保留目录本身
        for filename in os.listdir(problem_dir):
            file_path = os.path.join(problem_dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        return jsonify({"message": f"All test cases for problem {problem_id} deleted."}), 200
    else:
        return jsonify({"error": "Test cases directory not found"}), 404


@problem_bp.route('/<int:problem_id>/test_cases', methods=['GET'])
@token_required
def download_test_cases(problem_id):
    """
    将某题的所有测试点打包为压缩包下载
    """
    if request.current_user.role != 'teacher':
        return jsonify({"error": "Permission denied"}), 403

    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if not os.path.exists(problem_dir) or not os.listdir(problem_dir):
        return jsonify({"error": "No test cases found for this problem"}), 404

    # 在内存中创建压缩包
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(problem_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # 计算在压缩包内的相对路径
                arcname = os.path.relpath(file_path, problem_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'problem_{problem_id}_test_cases.zip'
    )
