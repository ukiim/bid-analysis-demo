from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import announcements, statistics, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시: 스케줄러 초기화 등
    yield
    # 종료 시: 리소스 정리


app = FastAPI(
    title="입찰 인사이트 API",
    description="공공데이터 기반 입찰가 산정 및 사정률 분석 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(announcements.router, prefix="/api/v1", tags=["공고 조회"])
app.include_router(statistics.router, prefix="/api/v1", tags=["통계 리포트"])
app.include_router(admin.router, prefix="/api/v1", tags=["관리자"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "입찰 인사이트 API"}
