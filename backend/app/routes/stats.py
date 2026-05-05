"""통계·예측(호환) 라우터.

server.py 의 `/api/v1/stats/*` 및 `/api/v1/predictions/*` 핸들러를
APIRouter 로 이전 (MIGRATION.md F4).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models import BidAnnouncement, BidResult

router = APIRouter(prefix="/api/v1", tags=["통계"])


@router.get("/stats/kpi")
def get_kpi():
    db = SessionLocal()
    try:
        total = db.query(BidAnnouncement).filter(BidAnnouncement.category.in_(["공사", "용역"])).count()
        today = db.query(BidAnnouncement).filter(
            func.date(BidAnnouncement.announced_at) == func.date(datetime.now())
        ).count()
        construction = db.query(BidAnnouncement).filter(BidAnnouncement.category == "공사").count()
        service = db.query(BidAnnouncement).filter(BidAnnouncement.category == "용역").count()
        avg_rate = db.query(func.avg(BidResult.assessment_rate)).scalar()
        avg_fp_rate = db.query(func.avg(BidResult.first_place_rate)).scalar()
    finally:
        db.close()
    return {
        "total_announcements": total,
        "today_announcements": today,
        "construction_count": construction,
        "service_count": service,
        "avg_assessment_rate": round(float(avg_rate), 2) if avg_rate else 0,
        "avg_first_place_rate": round(float(avg_fp_rate), 4) if avg_fp_rate else 0,
    }


@router.get("/stats/trends")
def get_trends(months: int = 6, category: str = None):
    db = SessionLocal()
    try:
        q = db.query(
            func.strftime("%Y-%m", BidResult.opened_at).label("period"),
            BidAnnouncement.category,
            func.avg(BidResult.assessment_rate).label("avg_rate"),
            func.count(BidResult.id).label("cnt"),
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at.isnot(None),
            BidAnnouncement.category.in_(["공사", "용역"]),
        )
        if category and category != "all":
            q = q.filter(BidAnnouncement.category == category)
        rows = q.group_by(
            func.strftime("%Y-%m", BidResult.opened_at),
            BidAnnouncement.category,
        ).order_by("period").all()

        period_data: dict = {}
        for row in rows:
            p = row.period
            if p not in period_data:
                period_data[p] = {"period": p, "construction": None, "service": None, "total": None, "count": 0}
            if row.category == "공사":
                period_data[p]["construction"] = round(row.avg_rate, 2)
            elif row.category == "용역":
                period_data[p]["service"] = round(row.avg_rate, 2)
            period_data[p]["count"] += row.cnt

        for p in period_data:
            vals = [v for v in [period_data[p]["construction"], period_data[p]["service"]] if v]
            period_data[p]["total"] = round(sum(vals) / len(vals), 2) if vals else None

        data = sorted(period_data.values(), key=lambda x: x["period"])[-months:]
    finally:
        db.close()
    return {"data": data}


@router.get("/stats/by-region")
def get_region_stats():
    db = SessionLocal()
    try:
        rows = db.query(
            BidAnnouncement.region,
            func.avg(BidResult.assessment_rate).label("avg_rate"),
            func.count(BidResult.id).label("count"),
            func.min(BidResult.assessment_rate).label("min_rate"),
            func.max(BidResult.assessment_rate).label("max_rate"),
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidAnnouncement.region.isnot(None),
            BidAnnouncement.category.in_(["공사", "용역"]),
        ).group_by(BidAnnouncement.region).order_by(func.count(BidResult.id).desc()).all()

        data = [
            {
                "region": r.region,
                "rate": round(r.avg_rate, 2),
                "count": r.count,
                "min_rate": round(r.min_rate, 2) if r.min_rate else None,
                "max_rate": round(r.max_rate, 2) if r.max_rate else None,
            }
            for r in rows
        ]
    finally:
        db.close()
    return {"data": data}


@router.get("/predictions/{announcement_id}")
def predict(announcement_id: str):
    """실시간 사정률 예측 (통계 기반 간이 모델, 기존 호환 엔드포인트)"""
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        stats = db.query(
            func.avg(BidResult.assessment_rate).label("avg"),
            func.min(BidResult.assessment_rate).label("min"),
            func.max(BidResult.assessment_rate).label("max"),
            func.count(BidResult.id).label("cnt"),
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.region == ann.region,
            BidResult.assessment_rate.isnot(None),
        ).first()

        org_stats = db.query(
            func.avg(BidResult.assessment_rate)
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.ordering_org_type == ann.ordering_org_type,
            BidResult.assessment_rate.isnot(None),
        ).scalar()

        if stats and stats.avg and stats.cnt >= 5:
            pred_rate = round(stats.avg * 0.7 + (org_stats or stats.avg) * 0.3, 2)
            ci_width = max(1.0, (stats.max - stats.min) * 0.3)
            confidence = min(95, 50 + stats.cnt * 0.5)
        else:
            pred_rate = 99.3 if ann.category == "공사" else 99.5
            ci_width = 3.0
            confidence = 30

        pred_min = round(pred_rate - ci_width, 2)
        pred_max = round(pred_rate + ci_width, 2)
        bid_pred = int(ann.base_amount * pred_rate / 100) if ann.base_amount else 0
        bid_min = int(ann.base_amount * pred_min / 100) if ann.base_amount else 0
        bid_max = int(ann.base_amount * pred_max / 100) if ann.base_amount else 0

        similar = db.query(BidAnnouncement, BidResult).join(
            BidResult, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.assessment_rate.isnot(None),
        ).order_by(BidResult.opened_at.desc()).limit(10).all()

        similar_list = [
            {
                "title": s[0].title, "area": s[0].region,
                "rate": round(s[1].assessment_rate, 2),
                "first_place_rate": round(s[1].first_place_rate, 4) if s[1].first_place_rate else None,
                "amount": s[1].winning_amount,
                "date": s[1].opened_at.strftime("%Y-%m") if s[1].opened_at else "",
            }
            for s in similar
        ]

    finally:
        db.close()
    return {
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "area": ann.region, "budget": ann.base_amount,
            "org": ann.ordering_org_name, "org_type": ann.ordering_org_type,
            "bid_method": ann.bid_method,
        },
        "prediction": {
            "predRate": round(pred_rate, 2),
            "predMin": pred_min, "predMax": pred_max,
            "bidAmountPred": bid_pred, "bidMin": bid_min, "bidMax": bid_max,
            "confidence": round(confidence),
            "dataPoints": stats.cnt if stats else 0,
        },
        "similar": similar_list,
    }
