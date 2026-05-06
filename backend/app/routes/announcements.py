"""공고 라우터 — 입찰 공고 목록/상세.

server.py 의 `@app.get("/api/v1/announcements*")` 핸들러를 APIRouter 로 이전.
MIGRATION.md F4.
"""
from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.database import SessionLocal
from app.core.deps import require_auth
from app.models import BidAnnouncement, BidResult, User
from app.services.sync import get_announcement_url

router = APIRouter(prefix="/api/v1/announcements", tags=["공고"])


@router.get("")
def list_announcements(
    category: str = None, source: str = None, region: str = None,
    keyword: str = None, status: str = None,
    industry_code: str = None, date_from: str = None, date_to: str = None,
    is_defense: str = None,  # "true"/"false"/"all"
    page: int = 1, page_size: int = 20,
):
    db = SessionLocal()
    try:
        q = db.query(BidAnnouncement)

        # 용역/공사만
        q = q.filter(BidAnnouncement.category.in_(["공사", "용역"]))

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
        if status and status != "all":
            q = q.filter(BidAnnouncement.status == status)
        if industry_code and industry_code != "all":
            q = q.filter(BidAnnouncement.industry_code == industry_code)
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
        items = q.order_by(BidAnnouncement.announced_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

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
                "type": ann.category,
                "area": ann.region,
                "budget": ann.base_amount,
                "deadline": ann.deadline_at.strftime("%Y-%m-%d") if ann.deadline_at else "",
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
        "budget": ann.base_amount, "bid_method": ann.bid_method,
        "industry_code": ann.industry_code, "status": ann.status,
        "deadline": ann.deadline_at.strftime("%Y-%m-%d") if ann.deadline_at else "",
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
