from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from _legacy_app.db.models import BidAnnouncement, BidResult
from _legacy_app.db.session import get_db
from _legacy_app.schemas.announcement import (
    AnnouncementFilter,
    AnnouncementListResponse,
    AnnouncementResponse,
)

router = APIRouter()


@router.get("/announcements", response_model=AnnouncementListResponse)
async def list_announcements(
    category: str | None = None,
    source: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """공고 목록 조회 (필터, 페이지네이션)"""
    query = select(BidAnnouncement).options(joinedload(BidAnnouncement.result))

    # 필터 적용
    if category:
        query = query.where(BidAnnouncement.category == category)
    if source:
        query = query.where(BidAnnouncement.source == source)
    if region:
        query = query.where(BidAnnouncement.region == region)
    if keyword:
        query = query.where(
            or_(
                BidAnnouncement.title.ilike(f"%{keyword}%"),
                BidAnnouncement.ordering_org_name.ilike(f"%{keyword}%"),
            )
        )
    if date_from:
        query = query.where(BidAnnouncement.announced_at >= date_from)
    if date_to:
        query = query.where(BidAnnouncement.announced_at <= date_to)
    if budget_min:
        query = query.where(BidAnnouncement.base_amount >= budget_min)
    if budget_max:
        query = query.where(BidAnnouncement.base_amount <= budget_max)

    # 전체 개수
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 페이지네이션
    query = (
        query.order_by(BidAnnouncement.announced_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    announcements = result.unique().scalars().all()

    items = []
    for ann in announcements:
        item = AnnouncementResponse.model_validate(ann)
        if ann.result:
            item.assessment_rate = float(ann.result.assessment_rate) if ann.result.assessment_rate else None
            item.winning_amount = ann.result.winning_amount
        items.append(item)

    total_pages = (total + page_size - 1) // page_size

    return AnnouncementListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """공고 상세 조회"""
    query = (
        select(BidAnnouncement)
        .options(joinedload(BidAnnouncement.result))
        .where(BidAnnouncement.id == announcement_id)
    )
    result = await db.execute(query)
    ann = result.unique().scalar_one_or_none()

    if not ann:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="해당 공고를 찾을 수 없습니다.")

    item = AnnouncementResponse.model_validate(ann)
    if ann.result:
        item.assessment_rate = float(ann.result.assessment_rate) if ann.result.assessment_rate else None
        item.winning_amount = ann.result.winning_amount

    return item
