"""인증 / 보안 — JWT, bcrypt 패스워드 해시, OAuth2 스키마.

server.py 의 보안 함수를 재노출.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

verify_password = _server.verify_password
get_password_hash = _server.get_password_hash
create_access_token = _server.create_access_token
get_current_user = _server.get_current_user
oauth2_scheme = _server.oauth2_scheme

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "get_current_user",
    "oauth2_scheme",
]
