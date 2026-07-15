from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth_tools import encode_auth_token
from app.utils.passwords import check_password, hash_password

router = APIRouter()


class RegisterBody(BaseModel):
    username: str
    password: str
    role: str = Field(default="student")


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterBody, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(status_code=400, detail={"message": "User already exists"})

    hashed_password = hash_password(body.password)
    new_user = User(
        username=body.username,
        password_hash=hashed_password,
        role=body.role,
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()

    if user and check_password(user.password_hash, body.password):
        token = encode_auth_token(user.id, user.role)
        if not token:
            raise HTTPException(
                status_code=500, detail={"error": "Failed to generate token"}
            )
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return {
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
            },
        }
    raise HTTPException(status_code=401, detail={"error": "Invalid credentials"})
