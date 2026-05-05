"""입찰 결과 / 업체별 투찰 기록 모델 — server.py L119-144 에서 분리."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.models._base import Base


class BidResult(Base):
    __tablename__ = "bid_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    announcement_id = Column(String, nullable=False, index=True)        # batch 조회·매칭 가속
    winning_amount = Column(Integer)
    winning_rate = Column(Float)
    assessment_rate = Column(Float)
    first_place_rate = Column(Float)                    # 1순위 사정률
    first_place_amount = Column(Integer)                # 1순위 낙찰가
    num_bidders = Column(Integer)
    winning_company = Column(String)
    preliminary_prices = Column(Text)                   # JSON: 복수예비가격 15개
    selected_price_indices = Column(Text)               # JSON: 추첨된 4개 인덱스
    opened_at = Column(DateTime)


class CompanyBidRecord(Base):
    """업체별 투찰 기록"""
    __tablename__ = "company_bid_records"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    announcement_id = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    bid_amount = Column(Integer)
    bid_rate = Column(Float)                            # 업체 투찰률
    ranking = Column(Integer)
    is_first_place = Column(Boolean, default=False)


__all__ = ["BidResult", "CompanyBidRecord"]
