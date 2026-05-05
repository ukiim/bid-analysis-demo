"""데이터 동기화 / 모델 메트릭 / 예측 설정 모델 — server.py L147-231 에서 분리."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models._base import Base


class DataSyncLog(Base):
    __tablename__ = "data_sync_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    records_fetched = Column(Integer, default=0)
    inserted_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class ModelMetric(Base):
    """매일 자동 재학습된 회귀 모델 성능 기록 — 정확도 추이 모니터링."""
    __tablename__ = "model_metrics"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trained_at = Column(DateTime, default=datetime.now, index=True)
    category = Column(String, index=True)         # "공사" / "용역" / "all"
    model_type = Column(String, default="ols")    # "ols" / "ensemble" 등 확장 대비
    n_samples = Column(Integer)
    r_squared = Column(Float)
    residual_std = Column(Float)
    mae = Column(Float)                            # 자체 학습 데이터 MAE (in-sample)
    coefficients_json = Column(Text)              # JSON 직렬화 계수 dump
    period_days = Column(Integer, default=180)


class PredictionSettings(Base):
    """사용자별 사정률 예측 학습 값 (스펙 §1 — 다음 공고 자동 적용)

    Tab1 에서 사용자가 마지막에 확정한 분석 옵션을 user_id 단위로 저장 →
    다음 공고 진입 시 같은 옵션으로 자동 적용.
    """
    __tablename__ = "prediction_settings"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, unique=True)
    period_months = Column(Integer, default=6)
    category_filter = Column(String, default="same")
    bucket_mode = Column(String, default="A")
    detail_rule = Column(String, default="max_gap")
    rate_range_start = Column(Float)
    rate_range_end = Column(Float)
    confirmed_rate = Column(Float)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


__all__ = ["DataSyncLog", "ModelMetric", "PredictionSettings"]
