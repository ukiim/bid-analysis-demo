"""인증 / 보안 — JWT, bcrypt 패스워드 해시, OAuth2 스키마.

server.py L679-727 에서 분리. SECRET_KEY/ALGORITHM 는 환경변수 검증
부수효과 때문에 server.py 가 module-load 시 설정한 후 본 모듈로 주입.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.database import SessionLocal
from app.models import User


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# server.py 가 module-load 시 환경 검증 후 SECRET_KEY 를 주입한다.
# 본 모듈 단독 import 시에도 동작하도록 환경변수 폴백 제공.
SECRET_KEY = os.environ.get("SECRET_KEY", "bid-insight-secret-key-change-in-production")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    """JWT 토큰에서 현재 사용자 조회. 토큰 없으면 None 반환."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()
    return user


def require_auth(current_user: User = Depends(get_current_user)):
    """인증 필수 의존성"""
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return current_user


def require_admin(current_user: User = Depends(require_auth)):
    """관리자 권한 필수 의존성"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


__all__ = [
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "oauth2_scheme",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "get_current_user",
    "require_auth",
    "require_admin",
]
