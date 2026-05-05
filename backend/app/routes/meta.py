"""메타 라우터 — 지역/공종 코드/기관 계층.

server.py 의 `@app.get("/api/v1/meta/...")`, `/api/v1/orgs/hierarchy`
핸들러를 APIRouter 로 이전 (MIGRATION.md F4).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.database import SessionLocal
from app.models import BidAnnouncement

router = APIRouter(prefix="/api/v1", tags=["메타"])


REGIONS = [
    "서울", "경기", "부산", "대전", "인천", "광주", "대구", "울산", "세종",
    "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]


# 발주기관 계층 매핑 — orgs/hierarchy 엔드포인트에서 사용
ORG_HIERARCHY = {
    "고양시": "경기도", "수원시": "경기도", "성남시": "경기도", "용인시": "경기도",
    "안양시": "경기도", "부천시": "경기도", "화성시": "경기도", "안산시": "경기도",
    "서울특별시 강남구": "서울특별시", "서울특별시 서초구": "서울특별시",
    "서울특별시 송파구": "서울특별시", "서울특별시 강동구": "서울특별시",
    "부산광역시 해운대구": "부산광역시", "부산광역시 사하구": "부산광역시",
    "대전광역시 유성구": "대전광역시", "인천광역시 남동구": "인천광역시",
    "고양시교육청": "경기도교육청", "수원시교육청": "경기도교육청",
    "국토교통부": "중앙부처", "환경부": "중앙부처", "교육부": "중앙부처",
    "행정안전부": "중앙부처", "국방부": "중앙부처",
    "한국도로공사": "공기업", "한국수자원공사": "공기업", "한국토지주택공사": "공기업",
    "부산항만공사": "공기업", "인천국제공항공사": "공기업",
    "서울대학교": "교육기관", "부산대학교": "교육기관", "충남대학교": "교육기관",
    "경기도": "경기도", "서울특별시": "서울특별시", "부산광역시": "부산광역시",
    "대전광역시": "대전광역시", "인천광역시": "인천광역시", "세종특별자치시": "세종특별자치시",
}


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
