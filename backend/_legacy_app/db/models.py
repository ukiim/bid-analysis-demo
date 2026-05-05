import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BidAnnouncement(Base):
    """입찰공고"""

    __tablename__ = "bid_announcements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="G2B 또는 D2B"
    )
    bid_number: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="입찰공고번호"
    )
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="공사/용역/물품/외자"
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="공고명")
    ordering_org_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="발주기관명"
    )
    ordering_org_type: Mapped[str | None] = mapped_column(
        String(50), comment="발주기관유형 (중앙부처/지자체/공기업 등)"
    )
    region: Mapped[str | None] = mapped_column(String(50), comment="지역")
    industry_code: Mapped[str | None] = mapped_column(String(50), comment="업종코드")
    industry_name: Mapped[str | None] = mapped_column(String(200), comment="업종명")
    base_amount: Mapped[int | None] = mapped_column(BigInteger, comment="기초금액 (원)")
    estimated_price: Mapped[int | None] = mapped_column(
        BigInteger, comment="예정가격 (원)"
    )
    bid_method: Mapped[str | None] = mapped_column(
        String(50), comment="입찰방식 (적격심사/최저가 등)"
    )
    announced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="공고일시"
    )
    bid_open_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="개찰일시"
    )
    deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="입찰마감일시"
    )
    status: Mapped[str | None] = mapped_column(
        String(20), default="진행중", comment="상태"
    )
    raw_json: Mapped[dict | None] = mapped_column(JSONB, comment="API 원본 응답")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    result: Mapped["BidResult | None"] = relationship(back_populates="announcement")

    __table_args__ = (
        # source + bid_number 조합으로 유니크
        {"comment": "입찰공고 정보"},
    )


class BidResult(Base):
    """낙찰결과"""

    __tablename__ = "bid_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bid_announcements.id", ondelete="CASCADE"),
        nullable=False,
    )
    winning_amount: Mapped[int | None] = mapped_column(
        BigInteger, comment="낙찰금액 (원)"
    )
    winning_rate: Mapped[float | None] = mapped_column(
        Numeric(8, 4), comment="낙찰률 (낙찰가/예정가*100)"
    )
    assessment_rate: Mapped[float | None] = mapped_column(
        Numeric(8, 4), comment="사정률 (예정가/기초금액*100)"
    )
    num_bidders: Mapped[int | None] = mapped_column(Integer, comment="참가업체수")
    winning_company: Mapped[str | None] = mapped_column(String(200), comment="낙찰업체명")
    preliminary_prices: Mapped[dict | None] = mapped_column(
        JSONB, comment="복수예비가격 (15개) 배열"
    )
    selected_price_indices: Mapped[list | None] = mapped_column(
        ARRAY(Integer), comment="추첨된 예비가격 번호"
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="개찰일시"
    )
    raw_json: Mapped[dict | None] = mapped_column(JSONB, comment="API 원본 응답")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    announcement: Mapped["BidAnnouncement"] = relationship(back_populates="result")

    __table_args__ = ({"comment": "낙찰결과 정보"},)


class User(Base):
    """사용자"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="무료", comment="무료/스탠다드/프리미엄")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    query_count: Mapped[int] = mapped_column(Integer, default=0, comment="조회 횟수")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = ({"comment": "사용자 정보"},)


class DataSyncLog(Base):
    """데이터 수집 로그"""

    __tablename__ = "data_sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, comment="G2B/D2B")
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="announcement/result/contract"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="success/failed/running"
    )
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = ({"comment": "데이터 수집 이력"},)
