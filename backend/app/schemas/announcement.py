from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnnouncementBase(BaseModel):
    source: str
    bid_number: str
    category: str
    title: str
    ordering_org_name: str
    ordering_org_type: str | None = None
    region: str | None = None
    industry_code: str | None = None
    industry_name: str | None = None
    base_amount: int | None = None
    estimated_price: int | None = None
    bid_method: str | None = None
    status: str | None = "진행중"


class AnnouncementResponse(AnnouncementBase):
    id: UUID
    announced_at: datetime | None = None
    bid_open_at: datetime | None = None
    deadline_at: datetime | None = None
    created_at: datetime

    # 연결된 낙찰결과 요약
    assessment_rate: float | None = None
    winning_amount: int | None = None

    model_config = {"from_attributes": True}


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AnnouncementFilter(BaseModel):
    category: str | None = None       # 공사/용역/물품
    source: str | None = None         # G2B/D2B
    region: str | None = None
    keyword: str | None = None
    date_from: str | None = None      # YYYY-MM-DD
    date_to: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    page: int = 1
    page_size: int = 20
