import datetime
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import SECRET_KEY
from app.database import get_db
from app.models.user import User


def encode_auth_token(user_id, role, exam_id=-1):
    """
    生成加密的 Token
    :param user_id: 用户ID
    :param role: 用户角色
    :param exam_id: 正在进行的考试ID，-1表示不在考试中
    """
    try:
        payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
            "iat": datetime.datetime.utcnow(),
            "sub": str(user_id),
            "role": role,
            "exam_id": exam_id,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    except Exception as e:
        print(f"Error encoding token: {e}")
        return None


def decode_auth_token(auth_token):
    """验证并解析 Token"""
    return jwt.decode(
        auth_token,
        SECRET_KEY,
        algorithms=["HS256"],
        leeway=10,
    )


@dataclass
class AuthContext:
    user: User
    exam_id: int = -1


def _extract_bearer(authorization: Optional[str]) -> str:
    if authorization is None:
        raise HTTPException(status_code=401, detail={"message": "Token 丢失"})

    token = authorization
    if token.startswith("Bearer "):
        token = token[7:].strip()
    elif " " in token:
        token = token.split()[-1]
    return token


def get_current_auth(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthContext:
    token = _extract_bearer(authorization)
    try:
        payload = decode_auth_token(token)
        current_user = db.get(User, int(payload["sub"]))
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail={"message": "User not found, token is invalid."},
            )
        return AuthContext(
            user=current_user,
            exam_id=payload.get("exam_id", -1),
        )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail={"message": "Token has expired."}
        )
    except jwt.InvalidTokenError as e:
        print(f"DEBUG: Invalid Token Error: {e}")
        raise HTTPException(
            status_code=401, detail={"message": f"Invalid token: {str(e)}"}
        )
    except Exception as e:
        print(f"DEBUG: Unknown Auth Error: {e}")
        raise HTTPException(
            status_code=401, detail={"message": "Authentication failed"}
        )
