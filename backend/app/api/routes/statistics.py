from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BidAnnouncement, BidResult
from app.db.session import get_db
from app.schemas.stats import (
    DashboardKPI,
    IndustryStat,
    IndustryStatsResponse,
    RegionStat,
    RegionStatsResponse,
    TrendDataPoint,
    TrendResponse,
)

router = APIRouter()


@router.get("/stats/kpi", response_model=DashboardKPI)
async def get_dashboard_kpi(db: AsyncSession = Depends(get_db)):
    """대시보드 KPI 지표"""
    total = (await db.execute(select(func.count(BidAnnouncement.id)))).scalar() or 0

    today_count = (
        await db.execute(
            select(func.count(BidAnnouncement.id)).where(
                func.date(BidAnnouncement.created_at) == func.current_date()
            )
        )
    ).scalar() or 0

    construction = (
        await db.execute(
            select(func.count(BidAnnouncement.id)).where(
                BidAnnouncement.category == "공사"
            )
        )
    ).scalar() or 0

    service = (
        await db.execute(
            select(func.count(BidAnnouncement.id)).where(
                BidAnnouncement.category == "용역"
            )
        )
    ).scalar() or 0

    defense = (
        await db.execute(
            select(func.count(BidAnnouncement.id)).where(
                BidAnnouncement.source == "D2B"
            )
        )
    ).scalar() or 0

    avg_rate = (
        await db.execute(select(func.avg(BidResult.assessment_rate)))
    ).scalar()

    return DashboardKPI(
        total_announcements=total,
        today_announcements=today_count,
        construction_count=construction,
        service_count=service,
        defense_count=defense,
        avg_assessment_rate=round(float(avg_rate), 2) if avg_rate else None,
    )


@router.get("/stats/trends", response_model=TrendResponse)
async def get_trends(
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    """사정률 월별 추이"""
    query = (
        select(
            func.to_char(BidResult.opened_at, "YYYY-MM").label("period"),
            func.avg(
                case(
                    (BidAnnouncement.category == "공사", BidResult.assessment_rate),
                )
            ).label("construction_rate"),
            func.avg(
                case(
                    (BidAnnouncement.category == "용역", BidResult.assessment_rate),
                )
            ).label("service_rate"),
            func.avg(BidResult.assessment_rate).label("total_rate"),
            func.count(BidResult.id).label("count"),
        )
        .join(BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id)
        .where(BidResult.assessment_rate.isnot(None))
        .group_by(func.to_char(BidResult.opened_at, "YYYY-MM"))
        .order_by(func.to_char(BidResult.opened_at, "YYYY-MM").desc())
        .limit(months)
    )

    result = await db.execute(query)
    rows = result.all()

    data = []
    for row in reversed(rows):
        data.append(
            TrendDataPoint(
                period=row.period or "",
                construction_rate=round(float(row.construction_rate), 2) if row.construction_rate else None,
                service_rate=round(float(row.service_rate), 2) if row.service_rate else None,
                total_rate=round(float(row.total_rate), 2) if row.total_rate else None,
                count=row.count,
            )
        )

    return TrendResponse(data=data, period_type="monthly")


@router.get("/stats/by-region", response_model=RegionStatsResponse)
async def get_region_stats(db: AsyncSession = Depends(get_db)):
    """지역별 사정률 통계"""
    query = (
        select(
            BidAnnouncement.region,
            func.avg(BidResult.assessment_rate).label("avg_rate"),
            func.count(BidResult.id).label("count"),
            func.min(BidResult.assessment_rate).label("min_rate"),
            func.max(BidResult.assessment_rate).label("max_rate"),
        )
        .join(BidResult, BidResult.announcement_id == BidAnnouncement.id)
        .where(
            BidResult.assessment_rate.isnot(None),
            BidAnnouncement.region.isnot(None),
        )
        .group_by(BidAnnouncement.region)
        .order_by(func.count(BidResult.id).desc())
    )

    result = await db.execute(query)
    data = [
        RegionStat(
            region=row.region,
            avg_rate=round(float(row.avg_rate), 2),
            count=row.count,
            min_rate=round(float(row.min_rate), 2) if row.min_rate else None,
            max_rate=round(float(row.max_rate), 2) if row.max_rate else None,
        )
        for row in result.all()
    ]

    return RegionStatsResponse(data=data)


@router.get("/stats/by-industry", response_model=IndustryStatsResponse)
async def get_industry_stats(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """업종별 사정률 통계"""
    query = (
        select(
            BidAnnouncement.industry_code,
            BidAnnouncement.industry_name,
            func.avg(BidResult.assessment_rate).label("avg_rate"),
            func.count(BidResult.id).label("count"),
        )
        .join(BidResult, BidResult.announcement_id == BidAnnouncement.id)
        .where(
            BidResult.assessment_rate.isnot(None),
            BidAnnouncement.industry_code.isnot(None),
        )
        .group_by(BidAnnouncement.industry_code, BidAnnouncement.industry_name)
        .order_by(func.count(BidResult.id).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    data = [
        IndustryStat(
            industry_code=row.industry_code or "",
            industry_name=row.industry_name or "",
            avg_rate=round(float(row.avg_rate), 2),
            count=row.count,
        )
        for row in result.all()
    ]

    return IndustryStatsResponse(data=data)
