"""FastAPI 라우터 — 현재 라우터 핸들러는 server.py 에 잔존.

각 도메인 서브모듈(`auth.py`, `announcements.py`, `analysis.py`,
`admin.py`, `sync.py`, `upload.py`, `history.py`, `meta.py`, `stats.py`)
은 향후 라우터 코드 이전을 위한 자리표시자로, 현재는 server.app
객체를 재노출한다. MIGRATION.md F4 단계 참조.
"""
from app.main import app  # noqa: F401

__all__ = ["app"]
