from flask import Blueprint, request, jsonify
from app.services.search_service import search_service
from app.utils.auth_tools import token_required

search_bp = Blueprint('search', __name__)

@search_bp.route('', methods=['GET'])
@token_required
def search_problems():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])

    top_k = request.args.get('top_k', 5, type=int)
    results = search_service.search(query, top_k=top_k)

    return jsonify(results)

@search_bp.route('/rebuild', methods=['POST'])
@token_required
def rebuild_index():
    # Only teachers or admins should be able to rebuild the index
    if request.current_user.role != 'teacher':
        return jsonify({'error': 'Permission denied'}), 403

    search_service.rebuild_index()
    return jsonify({'message': 'Index rebuilt successfully'})
