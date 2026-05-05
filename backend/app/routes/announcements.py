"""공고 라우터 — 입찰 공고 목록/상세.

server.py 의 `@app.get("/api/v1/announcements*")` 핸들러를 APIRouter 로 이전.
MIGRATION.md F4.
"""
from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter

from app.core.database import SessionLocal
from app.models import BidAnnouncement, BidResult
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
