"""FastAPI 의존성 주입 — 인증 가드, DB 세션, rate limit.

server.py 의 의존성 함수를 재노출.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

require_auth = _server.require_auth
require_admin = _server.require_admin
get_db = _server.get_db
rate_limit = _server.rate_limit

__all__ = ["require_auth", "require_admin", "get_db", "rate_limit"]
