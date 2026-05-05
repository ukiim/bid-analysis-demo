"""ORM 모델 패키지 — server.py 모놀리스에서 분리된 단일 진실 공급원.

신규 코드는 `from app.models import BidAnnouncement` 등을 사용.
server.py 는 이 모듈에서 모든 모델/Base 를 재import 한다.
Alembic autogenerate 는 Base.metadata 를 통해 모든 테이블을 인식한다.
"""
from __future__ import annotations

from app.models._base import Base
from app.models.announcement import BidAnnouncement
from app.models.bid import BidResult, CompanyBidRecord
from app.models.sync import DataSyncLog, ModelMetric, PredictionSettings
from app.models.user import QueryHistory, UploadLog, User

__all__ = [
    "Base",
    "BidAnnouncement",
    "BidResult",
    "CompanyBidRecord",
    "DataSyncLog",
    "ModelMetric",
    "PredictionSettings",
    "QueryHistory",
    "UploadLog",
    "User",
]
