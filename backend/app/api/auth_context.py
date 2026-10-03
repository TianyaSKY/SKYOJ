from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request
from loguru import logger
from sqlalchemy.orm import Session

from app.core.auth_tokens import decode_auth_token
from app.persistence.database import get_db
from app.persistence.user import User

if TYPE_CHECKING:
    from app.services.auth import AuthUserInfo


@dataclass
class AuthContext:
    user: AuthUserInfo
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
    request: Request = None,
) -> AuthContext:
    from app.services.auth import AuthUserInfo

    token = _extract_bearer(authorization)
    try:
        payload = decode_auth_token(token)
        current_user = db.get(User, int(payload["sub"]))
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail={"message": "User not found, token is invalid."},
            )
        ctx = AuthContext(
            user=AuthUserInfo(
                id=current_user.id,
                username=current_user.username,
                role=current_user.role,
            ),
            exam_id=payload.get("exam_id", -1),
        )
        if request is not None:
            request.state.auth_context = ctx
        return ctx
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"message": "Token has expired."})
    except jwt.InvalidTokenError as exc:
        logger.warning("认证令牌无效，原因：{}", exc)
        raise HTTPException(
            status_code=401, detail={"message": "Invalid token"}
        ) from exc
    except Exception:
        logger.exception("认证过程发生未处理异常")
        raise HTTPException(
            status_code=401, detail={"message": "Authentication failed"}
        )
