"""DB 엔진 / SessionLocal / Base / 의존성.

server.py 모놀리스에서 분리된 단일 진실 공급원 (F2).
Base 자체는 app/models/_base.py 에 있으며 본 모듈은 그것을 re-export.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models._base import Base


# ─── DB 설정 (SQLite) ──────────────────────────────────────────────────────
# server.py 와 동일 경로를 가리켜야 한다 — backend/demo.db
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_BACKEND_DIR, "demo.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI 의존성 — 요청 단위 DB 세션."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """SessionLocal 컨텍스트 매니저 — 헬퍼/스크립트 용.

    예외 발생 시도 자동 close. 명시적 commit 은 호출 측 책임.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["engine", "SessionLocal", "Base", "DB_PATH", "get_db", "db_session"]
