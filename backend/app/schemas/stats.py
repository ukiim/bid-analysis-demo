from pydantic import BaseModel


class TrendDataPoint(BaseModel):
    period: str              # YYYY-MM 또는 YYYY-QN
    construction_rate: float | None = None
    service_rate: float | None = None
    total_rate: float | None = None
    count: int = 0


class RegionStat(BaseModel):
    region: str
    avg_rate: float
    count: int
    min_rate: float | None = None
    max_rate: float | None = None
    prev_rate: float | None = None  # 전기간 대비


class IndustryStat(BaseModel):
    industry_code: str
    industry_name: str
    avg_rate: float
    count: int


class TrendResponse(BaseModel):
    data: list[TrendDataPoint]
    period_type: str  # monthly/quarterly


class RegionStatsResponse(BaseModel):
    data: list[RegionStat]


class IndustryStatsResponse(BaseModel):
    data: list[IndustryStat]


class DashboardKPI(BaseModel):
    total_announcements: int
    today_announcements: int
    construction_count: int
    service_count: int
    defense_count: int
    avg_assessment_rate: float | None = None


class PipelineStatus(BaseModel):
    name: str
    source: str
    sync_type: str
    status: str       # success/failed/running/pending
    last_run: str | None = None
    records_count: str | None = None
    next_run: str | None = None


class AdminDashboard(BaseModel):
    total_users: int
    premium_users: int
    today_api_calls: int
    total_announcements: int
    total_results: int
    pipelines: list[PipelineStatus]
