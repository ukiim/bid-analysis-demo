"""공고 관련 모델 — server.py L93-116 에서 분리."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text

from app.models._base import Base


class BidAnnouncement(Base):
    __tablename__ = "bid_announcements"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    bid_number = Column(String, nullable=False, index=True)            # 매칭 조회용
    category = Column(String, nullable=False, index=True)              # 공사 / 용역
    title = Column(String, nullable=False)
    ordering_org_name = Column(String, nullable=False)
    ordering_org_type = Column(String)
    parent_org_name = Column(String)                    # 상위 발주기관 (경기도 등)
    region = Column(String, index=True)
    industry_code = Column(String, index=True)
    base_amount = Column(Integer)
    estimated_price = Column(Integer)                   # 추정가격 (KBID: 1차 데모 검토 §0)
    bid_method = Column(String)
    license_category = Column(String, index=True)       # 업종면허 (예: 토건/전기/통신/소방)
    announced_at = Column(DateTime, index=True)        # 정렬·범위 필터 핵심
    deadline_at = Column(DateTime)
    opening_at = Column(DateTime)                       # 개찰일시 (공고 단계, BidResult.opened_at과 분리)
    site_visit_at = Column(DateTime)                    # 현설일 (현장설명회 일시)
    status = Column(String, default="진행중", index=True)
    is_defense = Column(Boolean, default=False, index=True)  # 국방부/군 발주 자동 태깅
    external_url = Column(Text)  # 원본 공고 상세 페이지 URL (G2B 응답의 bidNtceDtlUrl)
    bid_ord = Column(String, default="000")  # 차수 (URL fallback 생성 시 필요)
    # 복합 인덱스 — 공고 목록의 (category 필터 + announced_at 정렬) 조합 가속
    __table_args__ = (
        Index("ix_bid_ann_cat_announced", "category", "announced_at"),
    )


__all__ = ["BidAnnouncement"]
