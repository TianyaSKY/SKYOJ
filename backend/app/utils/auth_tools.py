import datetime
from functools import wraps

import jwt
from app.models.user import User
from flask import current_app, request, jsonify


def encode_auth_token(user_id, role, exam_id=-1):
    """
    生成加密的 Token
    :param user_id: 用户ID
    :param role: 用户角色
    :param exam_id: 正在进行的考试ID，-1表示不在考试中
    """
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            'sub': str(user_id),
            'role': role,
            'exam_id': exam_id
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

        try:
            payload = decode_auth_token(token)
            current_user = User.query.get(payload['sub'])

            if not current_user:
                return jsonify({'message': 'User not found, token is invalid.'}), 401

            # 将用户信息和考试状态存入 request 对象
            request.current_user = current_user
            request.exam_id = payload.get('exam_id', -1)

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
