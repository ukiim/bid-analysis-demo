"""메타 라우터 — 지역/공종 코드/기관 계층.

server.py 의 `@app.get("/api/v1/meta/...")`, `/api/v1/orgs/hierarchy`
핸들러를 APIRouter 로 이전 (MIGRATION.md F4).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.constants import ORG_HIERARCHY, REGIONS  # noqa: F401
from app.core.database import SessionLocal
from app.models import BidAnnouncement

router = APIRouter(prefix="/api/v1", tags=["메타"])


@router.get("/meta/industry-codes")
def get_industry_codes():
    """공종 코드 목록"""
    db = SessionLocal()
    try:
        codes = db.query(BidAnnouncement.industry_code).distinct().filter(
            BidAnnouncement.industry_code.isnot(None)
        ).all()
    finally:
        db.close()
    return {"codes": sorted([c[0] for c in codes if c[0]])}


@router.get("/meta/regions")
def get_regions():
    """지역(17개 시도) 목록"""
    return {"regions": REGIONS}


@router.get("/orgs/hierarchy")
def get_org_hierarchy():
    """발주기관 계층(부모) 매핑 — 프론트엔드에서 그룹화 표시용"""
    return {"hierarchy": ORG_HIERARCHY}
