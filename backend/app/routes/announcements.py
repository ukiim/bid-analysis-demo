"""공고 라우터 — 입찰 공고 목록/상세.

server.py 의 `@app.get("/api/v1/announcements*")` 핸들러를 APIRouter 로 이전.
MIGRATION.md F4.
"""
from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import case

from app.core.database import SessionLocal
from app.core.deps import require_auth
from app.models import BidAnnouncement, BidResult, User
from app.services.sync import get_announcement_url

router = APIRouter(prefix="/api/v1/announcements", tags=["공고"])


@router.get("")
def list_announcements(
    category: str = None, source: str = None, region: str = None,
    region_sido: str = None, region_sigungu: str = None,
    keyword: str = None, status: str = None,
    industry_code: str = None, license_category: str = None,
    date_from: str = None, date_to: str = None,
    is_defense: str = None,  # "true"/"false"/"all"
    page: int = 1, page_size: int = 20,
):
    db = SessionLocal()
    try:
        q = db.query(BidAnnouncement)

        # 용역/공사만, 취소·유찰·폐기·무효 공고 제외 (정밀 패턴)
        q = q.filter(BidAnnouncement.category.in_(["공사", "용역"]))
        q = q.filter(~BidAnnouncement.title.contains("취소"))
        for _p in ("[유찰", "(유찰", "유찰공고", "[폐기", "(폐기공고",
                   "폐기공고", "무효공고", "[연기공고", "(연기공고", "입찰취소"):
            q = q.filter(~BidAnnouncement.title.contains(_p))
        # 단가계약(다년 일괄) 차단 — "각 수요기관" 발주처는 분석 대상 아님
        q = q.filter(BidAnnouncement.ordering_org_name != "각 수요기관")

        if category and category != "all":
            cats = [c.strip() for c in category.split(",")]
            if len(cats) == 1:
                q = q.filter(BidAnnouncement.category == cats[0])
            else:
                q = q.filter(BidAnnouncement.category.in_(cats))
        if source and source != "all":
            q = q.filter(BidAnnouncement.source == source)
        if region and region != "all":
            q = q.filter(BidAnnouncement.region == region)
        # 시·도/시·군·구 2단계 필터 (KBID 동등성 §0 — 지역 세분화)
        # region 컬럼은 자유 텍스트 (예: "경기도 고양시", "서울특별시 강남구").
        # contains 매칭으로 광역 + 시군구를 모두 적용.
        if region_sido and region_sido != "all":
            q = q.filter(BidAnnouncement.region.contains(region_sido))
        if region_sigungu and region_sigungu != "all":
            q = q.filter(BidAnnouncement.region.contains(region_sigungu))
        if status and status != "all":
            q = q.filter(BidAnnouncement.status == status)
        if industry_code and industry_code != "all":
            q = q.filter(BidAnnouncement.industry_code == industry_code)
        if license_category and license_category != "all":
            q = q.filter(BidAnnouncement.license_category == license_category)
        if is_defense and is_defense != "all":
            q = q.filter(BidAnnouncement.is_defense == (is_defense.lower() == "true"))
        if date_from:
            try:
                q = q.filter(BidAnnouncement.announced_at >= datetime.strptime(date_from, "%Y-%m-%d"))
            except ValueError:
                pass
        if date_to:
            try:
                q = q.filter(BidAnnouncement.announced_at <= datetime.strptime(date_to, "%Y-%m-%d"))
            except ValueError:
                pass
        if keyword:
            q = q.filter(
                BidAnnouncement.title.contains(keyword) |
                BidAnnouncement.ordering_org_name.contains(keyword)
            )

        total = q.count()
        # 정렬: 마감일 기준 잔여일이 많은 공고 → 상단, 마감/만료 → 하단
        # 1순위: 활성(0) → 만료(1) → 미정/sentinel(2)
        # 2순위(활성): deadline_at ASC (가까운 마감이 위 = 잔여 14 → 30 → 90 ...)
        # 사용자 요구: "Day 많이 남은 게 상단, 마감은 뒤로"
        # → DESC 로 변경 (잔여 많은 순). 단 9999-12-31 sentinel 은 미정 처리.
        _now = datetime.now()
        _sentinel = datetime(9000, 1, 1)
        _sort_priority = case(
            (BidAnnouncement.deadline_at.is_(None), 2),
            (BidAnnouncement.deadline_at >= _sentinel, 2),  # 9999-12-31 등 미정 sentinel
            (BidAnnouncement.deadline_at < _now, 1),
            else_=0,
        )
        items = (
            q.order_by(_sort_priority.asc(), BidAnnouncement.deadline_at.desc())
             .offset((page - 1) * page_size).limit(page_size).all()
        )

        # N+1 해소 — BidResult 를 batch IN 절로 한 번에 조회
        ann_ids = [a.id for a in items]
        res_map: dict = {}
        if ann_ids:
            for r in db.query(BidResult).filter(BidResult.announcement_id.in_(ann_ids)).all():
                if r.announcement_id not in res_map:
                    res_map[r.announcement_id] = r

        result_items = []
        for ann in items:
            res = res_map.get(ann.id)
            result_items.append({
                "id": ann.id,
                "bid_number": ann.bid_number,
                "title": ann.title,
                "org": ann.ordering_org_name,
                "parent_org": ann.parent_org_name,  # KBID: 공고기관·수요기관 분리
                "type": ann.category,
                "area": ann.region,
                "budget": ann.base_amount,
                "estimated_price": ann.estimated_price,  # KBID: 추정가격
                "license_category": ann.license_category,  # KBID: 업종면허
                "deadline": ann.deadline_at.strftime("%Y-%m-%d %H:%M") if ann.deadline_at else "",
                "opening_at": ann.opening_at.strftime("%Y-%m-%d %H:%M") if ann.opening_at else None,  # KBID: 개찰일시
                "site_visit_at": ann.site_visit_at.strftime("%Y-%m-%d %H:%M") if ann.site_visit_at else None,  # KBID: 현설일
                "rate": round(res.assessment_rate, 2) if res and res.assessment_rate else None,
                "first_place_rate": round(res.first_place_rate, 4) if res and res.first_place_rate else None,
                "first_place_amount": res.first_place_amount if res else None,
                "status": ann.status,
                "source": ann.source,
                "bid_method": ann.bid_method,
                "num_bidders": res.num_bidders if res else None,
                "is_defense": bool(getattr(ann, "is_defense", False)),
                "external_url": get_announcement_url(ann),
            })

    finally:
        db.close()
    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get("/meta/regions")
def get_regions_meta():
    """공고 지역 메타데이터 — KBID 동등성을 위한 시·도/시·군·구 2단계 옵션.

    DB에 실제 존재하는 region 텍스트(자유포맷)에서 광역 + 하위 자치단체를 추출.
    예: "경기도 고양시" → sido="경기도", sigungu="고양시"
    """
    db = SessionLocal()
    try:
        # 카운트 많은 순으로 region distinct 추출
        from sqlalchemy import func
        rows = (
            db.query(BidAnnouncement.region, func.count().label("cnt"))
            .filter(BidAnnouncement.region.isnot(None))
            .group_by(BidAnnouncement.region)
            .order_by(func.count().desc())
            .limit(500)
            .all()
        )
        # 광역 키워드 — region 첫 단어와 매칭
        SIDO_KEYWORDS = [
            "서울특별시", "서울", "부산광역시", "부산", "대구광역시", "대구",
            "인천광역시", "인천", "광주광역시", "광주", "대전광역시", "대전",
            "울산광역시", "울산", "세종특별자치시", "세종",
            "경기도", "경기", "강원특별자치도", "강원", "충청북도", "충북",
            "충청남도", "충남", "전라북도", "전북", "전북특별자치도",
            "전라남도", "전남", "경상북도", "경북", "경상남도", "경남",
            "제주특별자치도", "제주",
        ]
        sido_map: dict[str, set[str]] = {}
        sido_counts: dict[str, int] = {}
        for region_text, cnt in rows:
            if not region_text:
                continue
            matched_sido = None
            for kw in SIDO_KEYWORDS:
                if region_text.startswith(kw):
                    matched_sido = kw
                    break
            if matched_sido is None:
                continue
            # 시·도 표기 정규화 (긴 형태 우선)
            normalized_sido = matched_sido
            for canon in ("서울특별시", "부산광역시", "대구광역시", "인천광역시",
                          "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
                          "경기도", "강원특별자치도", "충청북도", "충청남도",
                          "전라북도", "전북특별자치도", "전라남도", "경상북도",
                          "경상남도", "제주특별자치도"):
                if matched_sido in canon or canon.startswith(matched_sido):
                    normalized_sido = canon
                    break
            rest = region_text[len(matched_sido):].strip()
            sigungu = rest.split()[0] if rest else None
            if sigungu and len(sigungu) <= 10:
                sido_map.setdefault(normalized_sido, set()).add(sigungu)
            sido_counts[normalized_sido] = sido_counts.get(normalized_sido, 0) + cnt

        sido_list = sorted(sido_counts.items(), key=lambda x: -x[1])
        result = []
        for sido, _ in sido_list:
            result.append({
                "sido": sido,
                "sigungu_list": sorted(sido_map.get(sido, set())),
                "count": sido_counts[sido],
            })

        # license_category 옵션
        lic_rows = (
            db.query(BidAnnouncement.license_category, func.count().label("cnt"))
            .filter(BidAnnouncement.license_category.isnot(None))
            .group_by(BidAnnouncement.license_category)
            .order_by(func.count().desc())
            .limit(50)
            .all()
        )
        license_categories = [
            {"value": lc, "count": cnt} for lc, cnt in lic_rows if lc
        ]
        return {"regions": result, "license_categories": license_categories}
    finally:
        db.close()


@router.get("/{announcement_id}")
def get_announcement(announcement_id: str):
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}
        res = db.query(BidResult).filter(BidResult.announcement_id == ann.id).first()
    finally:
        db.close()
    return {
        "id": ann.id, "bid_number": ann.bid_number, "title": ann.title,
        "org": ann.ordering_org_name, "org_type": ann.ordering_org_type,
        "parent_org": ann.parent_org_name,
        "type": ann.category, "area": ann.region, "source": ann.source,
        "budget": ann.base_amount,
        "estimated_price": ann.estimated_price,
        "license_category": ann.license_category,
        "bid_method": ann.bid_method,
        "industry_code": ann.industry_code, "status": ann.status,
        "deadline": ann.deadline_at.strftime("%Y-%m-%d %H:%M") if ann.deadline_at else "",
        "opening_at": ann.opening_at.strftime("%Y-%m-%d %H:%M") if ann.opening_at else None,
        "site_visit_at": ann.site_visit_at.strftime("%Y-%m-%d %H:%M") if ann.site_visit_at else None,
        "announced_at": ann.announced_at.strftime("%Y-%m-%d") if ann.announced_at else "",
        "rate": round(res.assessment_rate, 4) if res and res.assessment_rate else None,
        "first_place_rate": round(res.first_place_rate, 4) if res and res.first_place_rate else None,
        "first_place_amount": res.first_place_amount if res else None,
        "num_bidders": res.num_bidders if res else None,
        "is_defense": bool(getattr(ann, "is_defense", False)),
        "external_url": get_announcement_url(ann),
    }


@router.get("/{announcement_id}/previous")
def get_previous_announcement(announcement_id: str,
                               current_user: User = Depends(require_auth)):
    """직전 공고 + 결과 비교 (Item 2).

    동일 category + industry_code + region 기준으로 announced_at 가 가장 가까운
    직전 공고 1건을 찾는다. 매칭이 없으면 단계적으로 조건을 완화:
      exact → no_region → no_industry → none
    """
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}
        if not ann.announced_at:
            return {"error": "공고일자가 없어 직전 공고를 검색할 수 없습니다."}

        base_q = db.query(BidAnnouncement).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.announced_at < ann.announced_at,
            BidAnnouncement.id != ann.id,
        )

        prev = None
        fallback_used = "none"
        # 1) 완전 일치
        cand = base_q.filter(
            BidAnnouncement.industry_code == ann.industry_code,
            BidAnnouncement.region == ann.region,
        ).order_by(BidAnnouncement.announced_at.desc()).first()
        if cand:
            prev = cand
            fallback_used = "exact"
        else:
            # 2) region 제외
            cand = base_q.filter(
                BidAnnouncement.industry_code == ann.industry_code,
            ).order_by(BidAnnouncement.announced_at.desc()).first()
            if cand:
                prev = cand
                fallback_used = "no_region"
            else:
                # 3) industry 도 제외 (category 만)
                cand = base_q.order_by(BidAnnouncement.announced_at.desc()).first()
                if cand:
                    prev = cand
                    fallback_used = "no_industry"

        if not prev:
            return {"prev": None, "fallback_used": "none"}

        res = db.query(BidResult).filter(BidResult.announcement_id == prev.id).first()
        result_payload = None
        if res:
            result_payload = {
                "winning_amount": res.winning_amount,
                "assessment_rate": round(res.assessment_rate, 4) if res.assessment_rate else None,
                "first_place_rate": round(res.first_place_rate, 4) if res.first_place_rate else None,
                "first_place_amount": res.first_place_amount,
                "winning_company": res.winning_company,
            }
        return {
            "prev": {
                "id": prev.id,
                "title": prev.title,
                "announced_at": prev.announced_at.strftime("%Y-%m-%d") if prev.announced_at else None,
                "base_amount": prev.base_amount,
                "category": prev.category,
                "industry_code": prev.industry_code,
                "region": prev.region,
                "ordering_org_name": prev.ordering_org_name,
                "result": result_payload,
            },
            "fallback_used": fallback_used,
        }
    finally:
        db.close()
