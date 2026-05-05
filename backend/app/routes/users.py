"""사용자 설정 라우터 — 사정률 예측 설정 조회/저장.

server.py 의 `/api/v1/users/me/prediction-settings` 핸들러를 APIRouter 로 이전.
MIGRATION.md F4.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request

from app.core.database import SessionLocal
from app.core.security import require_auth
from app.models import PredictionSettings, User

router = APIRouter(prefix="/api/v1/users/me", tags=["사용자"])


def _rate_limit(spec: str):
    from server import rate_limit as _rl
    return _rl(spec)


@router.get("/prediction-settings")
@_rate_limit("60/minute")
def get_prediction_settings(request: Request, current_user: User = Depends(require_auth)):
    """현재 로그인 사용자의 사정률 예측 설정 조회 (없으면 기본값 반환)"""
    db = SessionLocal()
    try:
        s = db.query(PredictionSettings).filter(
            PredictionSettings.user_id == current_user.id
        ).first()
        if not s:
            return {
                "period_months": 6, "category_filter": "same",
                "bucket_mode": "A", "detail_rule": "max_gap",
                "rate_range_start": None, "rate_range_end": None,
                "confirmed_rate": None, "exists": False,
            }
        return {
            "period_months": s.period_months,
            "category_filter": s.category_filter,
            "bucket_mode": s.bucket_mode,
            "detail_rule": s.detail_rule,
            "rate_range_start": s.rate_range_start,
            "rate_range_end": s.rate_range_end,
            "confirmed_rate": s.confirmed_rate,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "exists": True,
        }
    finally:
        db.close()


@router.put("/prediction-settings")
@_rate_limit("30/minute")
def put_prediction_settings(
    request: Request,
    payload: dict,
    current_user: User = Depends(require_auth),
):
    """사정률 예측 설정 upsert"""
    db = SessionLocal()
    try:
        s = db.query(PredictionSettings).filter(
            PredictionSettings.user_id == current_user.id
        ).first()
        if not s:
            s = PredictionSettings(user_id=current_user.id)
            db.add(s)
        for field in ("period_months", "category_filter", "bucket_mode", "detail_rule",
                      "rate_range_start", "rate_range_end", "confirmed_rate"):
            if field in payload and payload[field] is not None:
                setattr(s, field, payload[field])
        s.updated_at = datetime.now()
        db.commit()
        return {"status": "ok", "updated_at": s.updated_at.isoformat()}
    finally:
        db.close()
