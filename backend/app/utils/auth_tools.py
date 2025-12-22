import jwt
import datetime
from functools import wraps
from flask import current_app, request, jsonify
from app.models.user import User


def encode_auth_token(user_id, role):
    """
    生成加密的 Token
    """
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            # ---------------------------------------------------------
            # [关键修复] PyJWT 要求 sub 必须是字符串，必须使用 str() 转换
            # ---------------------------------------------------------
            'sub': str(user_id),
            'role': role
        }
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY', 'skyoj_secret_key'),
            algorithm='HS256'
        )
    except Exception as e:
        print(f"Error encoding token: {e}")
        return None


def decode_auth_token(auth_token):
    """
    验证并解析 Token
    """
    return jwt.decode(
        auth_token,
        current_app.config.get('SECRET_KEY', 'skyoj_secret_key'),
        algorithms=['HS256'],
        # 保留这个以防止 "ImmatureSignatureError"
        leeway=10
    )


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if token is None:
            return jsonify({'message': 'Token 丢失'}), 401

        if token.startswith('Bearer '):
            token = token[7:].strip()
        elif ' ' in token:
            token = token.split()[-1]

        current_user = None

        try:
            payload = decode_auth_token(token)

            # payload['sub'] 现在是字符串，SQLAlchemy 通常能自动处理字符串转数字的主键查询
            # 如果报错，可以改写为 User.query.get(int(payload['sub']))
            current_user = User.query.get(payload['sub'])

            if not current_user:
                return jsonify({'message': 'User not found, token is invalid.'}), 401

            request.current_user = current_user

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired.'}), 401
        except jwt.InvalidTokenError as e:
            print(f"DEBUG: Invalid Token Error: {e}")
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        except Exception as e:
            print(f"DEBUG: Unknown Auth Error: {e}")
            return jsonify({'message': 'Authentication failed'}), 401

        return f(*args, **kwargs)

    return decorated