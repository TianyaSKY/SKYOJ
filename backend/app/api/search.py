from flask import Blueprint, request, jsonify

from app.models.problem import Problem
from app.models.search_history import SearchHistory
from app.models.user import db
from app.services.search_service import search_service
from app.utils.auth_tools import token_required

search_bp = Blueprint('search', __name__)


@search_bp.route('', methods=['GET'])
@token_required
def search_problems():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])

    mode = request.args.get('mode', 'semantic')
    top_k = request.args.get('top_k', 5, type=int)

    # Save search history
    try:
        search_history = SearchHistory(
            user_id=request.current_user.id,
            query=query
        )
        db.session.add(search_history)
        db.session.commit()
    except Exception as e:
        print(f"Error saving search history: {e}")
        db.session.rollback()

    if mode == 'normal':
        # Normal search using SQL LIKE
        problems = Problem.query.filter(
            (Problem.title.like(f'%{query}%')) |
            (Problem.content.like(f'%{query}%'))
        ).limit(top_k).all()

        results = [{
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "type": p.type,
            "language": p.language,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit
        } for p in problems]
    else:
        # Semantic search
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
