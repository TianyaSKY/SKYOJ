from app.models.user import db, User
from app.utils.auth_tools import encode_auth_token
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt, check_password_hash

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')  # 默认为学生

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 400

    # 对密码进行哈希处理
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(username=username, password_hash=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()

    if user and check_password_hash(user.password_hash, data.get('password')):
        token = encode_auth_token(user.id, user.role)

        if not token:
            return jsonify({"error": "Failed to generate token"}), 500

        # PyJWT < 2.0 returns bytes, ensure it's a string
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({
            "message": "Login successful",
            "token": token,  # 返回给前端
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401
