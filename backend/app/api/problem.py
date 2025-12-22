import os
import shutil
import zipfile

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from app.models.problem import Problem
from app.models.user import db

problem_bp = Blueprint('problem', __name__)
UPLOAD_BASE_DIR = "uploads/problems"


@problem_bp.route('/', methods=['POST'])
def create_problem():
    data = request.get_json()

    # 提取字段
    new_problem = Problem(
        title=data.get('title'),
        content=data.get('content'),
        language=data.get('language'),
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
        "type": p.type
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
def update_problem(problem_id):
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
def delete_problem(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    
    # 删除关联的测试用例目录
    problem_dir = os.path.join(UPLOAD_BASE_DIR, str(problem_id))
    if os.path.exists(problem_dir):
        shutil.rmtree(problem_dir)
        
    db.session.delete(problem)
    db.session.commit()
    return jsonify({"message": "Problem deleted successfully"}), 200


@problem_bp.route('/<int:problem_id>/upload_files', methods=['POST'])
def upload_files(problem_id):
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
