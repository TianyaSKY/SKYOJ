import os
from flask import Blueprint, request, jsonify, send_from_directory, current_app

from app.models.dataset import Dataset
from app.models.user import db
from werkzeug.utils import secure_filename
from app.utils.auth_tools import token_required, decode_auth_token

dataset_bp = Blueprint('dataset', __name__)

@dataset_bp.route('', methods=['GET'])
def get_datasets():
    datasets = Dataset.query.all()
    return jsonify([d.to_dict() for d in datasets])

@dataset_bp.route('', methods=['POST'])
@token_required
def upload_dataset():
    # 权限校验：仅限教师上传
    if request.current_user.role != 'teacher':
        return jsonify({'error': 'Permission denied. Only teachers can upload datasets.'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    name = request.form.get('name')
    description = request.form.get('description')

    filename = secure_filename(file.filename)
    # 确保 UPLOAD_FOLDER 配置存在，或者使用默认路径
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    upload_dir = os.path.join(upload_folder, 'datasets')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Calculate file size
    size_bytes = os.path.getsize(file_path)
    if size_bytes < 1024:
        file_size = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        file_size = f"{size_bytes / 1024:.2f} KB"
    else:
        file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

    dataset = Dataset(
        name=name,
        description=description,
        file_path=file_path,
        file_size=file_size,
        uploader_id=request.current_user.id
    )
    db.session.add(dataset)
    db.session.commit()

    return jsonify(dataset.to_dict()), 201

@dataset_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_dataset(id):
    # 权限校验：仅限教师删除
    if request.current_user.role != 'teacher':
        return jsonify({'error': 'Permission denied. Only teachers can delete datasets.'}), 403

    dataset = Dataset.query.get_or_404(id)

    # 删除物理文件
    if os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except Exception as e:
            current_app.logger.error(f"Error deleting file {dataset.file_path}: {e}")

    db.session.delete(dataset)
    db.session.commit()

    return jsonify({'message': 'Dataset deleted successfully'}), 200

@dataset_bp.route('/<int:id>/download', methods=['GET'])
def download_dataset(id):
    # 支持 Header Token 或 Query Token (方便直接粘贴链接下载)
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:].strip()
    else:
        token = request.args.get('token')

    if not token:
        return jsonify({'message': 'Authentication required'}), 401

    try:
        decode_auth_token(token)
    except:
        return jsonify({'message': 'Invalid or expired token'}), 401

    dataset = Dataset.query.get_or_404(id)
    directory = os.path.dirname(dataset.file_path)
    filename = os.path.basename(dataset.file_path)
    return send_from_directory(directory, filename, as_attachment=True)
