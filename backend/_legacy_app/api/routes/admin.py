from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from _legacy_app.db.models import (
    BidAnnouncement,
    BidResult,
    DataSyncLog,
    User,
)
from _legacy_app.db.session import get_db
from _legacy_app.schemas.stats import AdminDashboard, PipelineStatus

router = APIRouter()


@router.get("/admin/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(db: AsyncSession = Depends(get_db)):
    """관리자 대시보드"""
    # 사용자 통계
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    premium_users = (
        await db.execute(
            select(func.count(User.id)).where(User.plan == "프리미엄")
        )
    ).scalar() or 0

    # 데이터 통계
    total_ann = (await db.execute(select(func.count(BidAnnouncement.id)))).scalar() or 0
    total_res = (await db.execute(select(func.count(BidResult.id)))).scalar() or 0

    # 파이프라인 상태 (최근 로그)
    pipeline_query = (
        select(DataSyncLog)
        .order_by(DataSyncLog.started_at.desc())
        .limit(10)
    )
    pipeline_result = await db.execute(pipeline_query)
    logs = pipeline_result.scalars().all()

    pipelines = []
    seen = set()
    for log in logs:
        key = f"{log.source}_{log.sync_type}"
        if key in seen:
            continue
        seen.add(key)
        pipelines.append(PipelineStatus(
            name=f"{log.source} {log.sync_type} 수집",
            source=log.source,
            sync_type=log.sync_type,
            status=log.status,
            last_run=log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else None,
            records_count=f"{log.records_fetched}건" if log.records_fetched else "0건",
        ))

    return AdminDashboard(
        total_users=total_users,
        premium_users=premium_users,
        today_api_calls=0,
        total_announcements=total_ann,
        total_results=total_res,
        pipelines=pipelines,
    )


@router.post("/admin/sync")
async def trigger_sync(
    source: str = "G2B",
    background_tasks: BackgroundTasks = None,
):
    """수동 데이터 수집 트리거"""
    from _legacy_app.etl.scheduler import run_sync
    background_tasks.add_task(run_sync, source)
    return {"message": f"{source} 데이터 수집이 시작되었습니다.", "status": "started"}
