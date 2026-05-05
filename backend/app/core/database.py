"""DB 엔진 / SessionLocal / Base / 의존성.

server.py 의 SQLAlchemy 객체를 재노출 — 단일 진실 공급원 유지.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

engine = _server.engine
SessionLocal = _server.SessionLocal
Base = _server.Base
db_session = _server.db_session
get_db = _server.get_db

__all__ = ["engine", "SessionLocal", "Base", "db_session", "get_db"]
