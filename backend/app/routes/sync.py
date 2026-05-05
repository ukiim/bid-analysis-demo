"""sync 라우터 — 사용처 없음 (placeholder).

원래는 `/api/v1/sync/*` 전용 라우터로 계획되었으나,
실제 동기화 엔드포인트는 모두 관리자 전용(`/api/v1/admin/sync/*`)이므로
`app/routes/admin.py` 에 통합되었다. 본 모듈은 추후 일반 사용자용
동기화 엔드포인트가 추가될 경우를 위해 유지한다.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/sync", tags=["동기화"])
