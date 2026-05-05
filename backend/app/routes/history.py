"""조회 이력 라우터 — 사용자별 분석 이력 목록/상세.

server.py 의 `@app.get("/api/v1/history*")` 핸들러를 APIRouter 로 이전 (F4).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import SessionLocal
from app.core.security import require_auth
from app.models import BidAnnouncement, QueryHistory, User

router = APIRouter(prefix="/api/v1/history", tags=["이력"])


@router.get("")
def list_history(
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(require_auth),
):
    """현재 사용자의 분석 조회 이력"""
    db = SessionLocal()
    try:
        q = db.query(QueryHistory).filter(QueryHistory.user_id == current_user.id)
        total = q.count()
        items = q.order_by(QueryHistory.queried_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for h in items:
            ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == h.announcement_id).first()
            result.append({
                "id": h.id,
                "announcement_id": h.announcement_id,
                "announcement_title": ann.title if ann else None,
                "analysis_type": h.analysis_type,
                "parameters": json.loads(h.parameters) if h.parameters else None,
                "result_summary": json.loads(h.result_summary) if h.result_summary else None,
                "queried_at": h.queried_at.strftime("%Y-%m-%d %H:%M") if h.queried_at else None,
            })

    finally:
        db.close()
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/{history_id}")
def get_history(history_id: str, current_user: User = Depends(require_auth)):
    db = SessionLocal()
    try:
        h = db.query(QueryHistory).filter(
            QueryHistory.id == history_id, QueryHistory.user_id == current_user.id
        ).first()
        if not h:
            db.close()
            raise HTTPException(status_code=404, detail="조회 이력을 찾을 수 없습니다.")
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == h.announcement_id).first()
    finally:
        db.close()
    return {
        "id": h.id,
        "announcement_id": h.announcement_id,
        "announcement_title": ann.title if ann else None,
        "analysis_type": h.analysis_type,
        "parameters": json.loads(h.parameters) if h.parameters else None,
        "result_summary": json.loads(h.result_summary) if h.result_summary else None,
        "queried_at": h.queried_at.strftime("%Y-%m-%d %H:%M") if h.queried_at else None,
    }
