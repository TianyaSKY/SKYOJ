import os
import threading

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename

from app.models.dataset import Dataset
from app.models.user import db
from app.utils.auth_tools import token_required, decode_auth_token

dataset_bp = Blueprint('dataset', __name__)

# 限制最大上传大小为 500MB
MAX_DATASET_SIZE = 500 * 1024 * 1024


def async_save_file(app_context, file_data, file_path, dataset_id):
    """异步保存文件并更新数据库状态（如果需要）"""
    with app_context:
        try:
            with open(file_path, 'wb') as f:
                f.write(file_data)
            # 这里可以添加后续处理逻辑，如解压、校验等
        except Exception as e:
            print(f"Error in async_save_file: {e}")


@dataset_bp.route('', methods=['GET'])
def get_datasets():
    page = request.args.get('page', type=int)
    page_size = request.args.get('page_size', type=int)

    if page and page_size:
        pagination = Dataset.query.order_by(Dataset.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        datasets = pagination.items
        return jsonify({
            "total": pagination.total,
            "page": pagination.page,
            "page_size": pagination.per_page,
            "datasets": [d.to_dict() for d in datasets]
        }), 200

    datasets = Dataset.query.order_by(Dataset.id.desc()).all()
    return jsonify([d.to_dict() for d in datasets]), 200


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

    # 检查文件大小 (从 Content-Length 获取，或者读取一部分检查)
    # 注意：request.content_length 可能不可靠，取决于客户端
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)  # 重置指针

    if size_bytes > MAX_DATASET_SIZE:
        return jsonify({
                           'error': f'File too large. Maximum size is {MAX_DATASET_SIZE // (1024 * 1024)}MB.You file size is {size_bytes // (1024 * 1024)}'}), 413

    name = request.form.get('name')
    description = request.form.get('description')

    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    upload_dir = os.path.join(upload_folder, 'datasets')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_path = os.path.join(upload_dir, filename)

    # 格式化文件大小显示
    if size_bytes < 1024:
        file_size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        file_size_str = f"{size_bytes / 1024:.2f} KB"
    else:
        file_size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

    # 先创建数据库记录
    dataset = Dataset(
        name=name,
        description=description,
        file_path=file_path,
        file_size=file_size_str,
        uploader_id=request.current_user.id
    )
    db.session.add(dataset)
    db.session.commit()

    # 异步保存文件
    file_data = file.read()
    thread = threading.Thread(
        target=async_save_file,
        args=(current_app.app_context(), file_data, file_path, dataset.id)
    )
    thread.start()

    return jsonify({
        "message": "Upload started",
        "dataset": dataset.to_dict()
    }), 202


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
