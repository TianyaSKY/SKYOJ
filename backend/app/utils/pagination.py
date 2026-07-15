"""Simple offset pagination helper (Flask-SQLAlchemy paginate replacement)."""


def paginate(query, page: int = 1, per_page: int = 20):
    page = max(1, page or 1)
    per_page = max(1, per_page or 20)
    total = query.count()
    pages = (total + per_page - 1) // per_page if total else 0
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, pages
