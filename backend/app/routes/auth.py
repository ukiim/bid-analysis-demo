"""인증 라우터 — 회원가입/로그인/토큰 갱신/비밀번호 변경.

server.py 의 `@app.<method>("/api/v1/auth/...")` 핸들러를 APIRouter 기반으로
이전한다 (MIGRATION.md F4 단계).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.database import SessionLocal
from app.core.security import (
    create_access_token,
    get_password_hash,
    require_auth,
    verify_password,
)
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["인증"])


def _rate_limit(spec: str):
    """server.rate_limit 으로 lazy 위임 — slowapi 미설치 시 noop."""
    from server import rate_limit as _rl
    return _rl(spec)


@router.post("/register")
def register(
    username: str = Query(...),
    email: str = Query(...),
    password: str = Query(...),
    name: str = Query(None),
):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            db.close()
            raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
        if db.query(User).filter(User.email == email).first():
            db.close()
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            name=name or username,
            role="user",
            joined_at=datetime.now(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token({"sub": user.id})
    finally:
        db.close()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "username": user.username, "name": user.name,
            "email": user.email, "role": user.role, "plan": user.plan,
        },
    }


@router.post("/login")
@_rate_limit("10/minute")
def login(request: Request, username: str = Query(...), password: str = Query(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        if not user or not verify_password(password, user.hashed_password):
            db.close()
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
        user.last_login_at = datetime.now()
        db.commit()
        token = create_access_token({"sub": user.id})
    finally:
        db.close()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "username": user.username, "name": user.name,
            "email": user.email, "role": user.role, "plan": user.plan,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(require_auth)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "plan": current_user.plan,
        "query_count": current_user.query_count,
        "joined_at": current_user.joined_at.strftime("%Y-%m-%d") if current_user.joined_at else None,
    }


@router.post("/refresh")
def refresh_token(current_user: User = Depends(require_auth)):
    token = create_access_token({"sub": current_user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.put("/password")
def change_password(
    current_password: str = Query(...),
    new_password: str = Query(...),
    current_user: User = Depends(require_auth),
):
    """비밀번호 변경"""
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="새 비밀번호는 6자 이상이어야 합니다.")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        user.hashed_password = get_password_hash(new_password)
        db.commit()
    finally:
        db.close()
    return {"message": "비밀번호가 변경되었습니다."}
