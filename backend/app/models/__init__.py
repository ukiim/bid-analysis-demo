"""ORM 모델 — server.py 정의를 재노출.

신규 코드는 `from app.models import BidAnnouncement` 형태 사용 가능.
Alembic autogenerate 는 여전히 server.py 의 Base 를 참조한다.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

# 모델 클래스 8종
BidAnnouncement = _server.BidAnnouncement
BidResult = _server.BidResult
CompanyBidRecord = _server.CompanyBidRecord
DataSyncLog = _server.DataSyncLog
User = _server.User
QueryHistory = _server.QueryHistory
UploadLog = _server.UploadLog
ModelMetric = _server.ModelMetric
PredictionSettings = _server.PredictionSettings

# Base 도 함께 노출 — Alembic 등에서 참조
Base = _server.Base

__all__ = [
    "BidAnnouncement",
    "BidResult",
    "CompanyBidRecord",
    "DataSyncLog",
    "User",
    "QueryHistory",
    "UploadLog",
    "ModelMetric",
    "PredictionSettings",
    "Base",
]
