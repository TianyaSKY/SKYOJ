"""JWT 编解码，不依赖 HTTP 或数据库。"""

import datetime

import jwt
from loguru import logger

from app.core.config import SECRET_KEY


def encode_auth_token(user_id, role, exam_id=-1):
    """
    生成加密的 Token
    :param user_id: 用户ID
    :param role: 用户角色
    :param exam_id: 正在进行的考试ID，-1表示不在考试中
    """
    try:
        now = datetime.datetime.now(datetime.UTC)
        payload = {
            "exp": now + datetime.timedelta(days=1),
            "iat": now,
            "sub": str(user_id),
            "role": role,
            "exam_id": exam_id,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    except Exception:
        logger.exception("生成认证令牌失败，用户 ID：{}", user_id)
        return None


def decode_auth_token(auth_token):
    """验证并解析 Token"""
    return jwt.decode(
        auth_token,
        SECRET_KEY,
        algorithms=["HS256"],
        leeway=10,
    )
