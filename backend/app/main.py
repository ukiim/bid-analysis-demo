"""FastAPI 앱 진입점 — server.app 을 재노출.

uvicorn 으로 `app.main:app` 도, `server:app` 도 모두 동일한 인스턴스를 가리킨다.
향후 PR 에서 라우터/미들웨어 등록을 본 파일로 이전 예정 (MIGRATION.md F5).
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

app = _server.app

__all__ = ["app"]
