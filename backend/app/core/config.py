"""설정 / 환경변수 / 로거.

server.py 의 모듈 전역(`logger`, 경로 상수 등)을 재노출.
"""
from __future__ import annotations

import sys as _sys
import os as _os

# server.py 가 backend/ 직하에 있어야 한다. 호출자가 sys.path 에
# backend/ 를 넣지 않은 경우를 대비해 안전 장치.
_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

logger = _server.logger
DB_PATH = _server.DB_PATH
NAS_PATH = _server.NAS_PATH
SECRET_KEY = _server.SECRET_KEY
ALGORITHM = _server.ALGORITHM

__all__ = ["logger", "DB_PATH", "NAS_PATH", "SECRET_KEY", "ALGORITHM"]
