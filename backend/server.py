"""통합 데모 서버 — KBID 스타일 1순위 예상 낙찰가 분석 시스템

SQLite + FastAPI로 백엔드 API 서빙 + 프론트엔드 정적 파일 서빙
단일 프로세스로 전체 데모 구동

실행: python3 server.py
"""

import os
import sys
import uuid
import json
import random
import math
import logging
import statistics
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


# ─── 로깅 설정 ──────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_file = os.environ.get("LOG_FILE", "").strip()

    root = logging.getLogger()
    root.setLevel(level)
    # 기존 핸들러 제거 (uvicorn reload 대응)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    if log_file:
        try:
            from logging.handlers import RotatingFileHandler
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            # 환경변수로 크기/보관 개수 조정 (기본 10MB × 7개 = 약 70MB 상한)
            max_bytes = int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
            backup_count = int(os.environ.get("LOG_BACKUP_COUNT", "7"))
            fh = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count,
                encoding="utf-8", delay=True,
            )
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception as e:
            sh.handle(logging.LogRecord(
                "server", logging.WARNING, __file__, 0,
                f"파일 로그 핸들러 구성 실패: {e}", None, None,
            ))

    return logging.getLogger("bid-insight")


logger = _setup_logging()

from fastapi import FastAPI, Query, Depends, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    func, text, Index,
)
from jose import JWTError, jwt
import bcrypt

# ─── DB 엔진 (app/core/database 에서 정의 — F2 분리) ───────────────────────

from app.core.database import engine, SessionLocal, DB_PATH  # noqa: E402

NAS_PATH = os.environ.get("NAS_MOUNT_PATH", os.path.join(os.path.dirname(__file__), "data"))


# ─── 모델 (app/models 에서 정의 — F1 분리) ────────────────────────────────

from app.models import (  # noqa: E402
    Base,
    BidAnnouncement,
    BidResult,
    CompanyBidRecord,
    DataSyncLog,
    ModelMetric,
    PredictionSettings,
    QueryHistory,
    UploadLog,
    User,
)


# ─── 발주기관 계층 매핑 ───────────────────────────────────────────────────

ORG_HIERARCHY = {
    "고양시": "경기도", "수원시": "경기도", "성남시": "경기도", "용인시": "경기도",
    "안양시": "경기도", "부천시": "경기도", "화성시": "경기도", "안산시": "경기도",
    "서울특별시 강남구": "서울특별시", "서울특별시 서초구": "서울특별시",
    "서울특별시 송파구": "서울특별시", "서울특별시 강동구": "서울특별시",
    "부산광역시 해운대구": "부산광역시", "부산광역시 사하구": "부산광역시",
    "대전광역시 유성구": "대전광역시", "인천광역시 남동구": "인천광역시",
    "고양시교육청": "경기도교육청", "수원시교육청": "경기도교육청",
    "국토교통부": "중앙부처", "환경부": "중앙부처", "교육부": "중앙부처",
    "행정안전부": "중앙부처", "국방부": "중앙부처",
    "한국도로공사": "공기업", "한국수자원공사": "공기업", "한국토지주택공사": "공기업",
    "부산항만공사": "공기업", "인천국제공항공사": "공기업",
    "서울대학교": "교육기관", "부산대학교": "교육기관", "충남대학교": "교육기관",
    "경기도": "경기도", "서울특별시": "서울특별시", "부산광역시": "부산광역시",
    "대전광역시": "대전광역시", "인천광역시": "인천광역시", "세종특별자치시": "세종특별자치시",
}

# ─── 메타 상수 (API 응답용) ────────────────────────────────────────────────

REGIONS = ["서울", "경기", "부산", "대전", "인천", "광주", "대구", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

# 시드 데이터 생성은 backend/seed.py 모듈로 분리됨.
# 운영 환경에서는 SKIP_SEED=true 로 비활성화.


# ─── FastAPI 앱 ────────────────────────────────────────────────────────────

# APScheduler 통합 (lifespan에서 시작/종료)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _scheduler: "BackgroundScheduler | None" = None
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _scheduler = None
    _SCHEDULER_AVAILABLE = False


def _send_alert_webhook(title: str, fields: dict):
    """Slack/Discord 호환 webhook 알림 + 옵션 SMTP 이메일.

    환경변수:
      ALERT_WEBHOOK_URL — Slack 호환 incoming webhook
      ALERT_EMAIL_TO   — 콤마 구분 수신자 (선택)
      SMTP_HOST/PORT/USER/PASS — SMTP 서버 (ALERT_EMAIL_TO 사용 시 필수)
    """
    text_lines = [f"*{title}*"]
    for k, v in fields.items():
        text_lines.append(f"• {k}: `{v}`")
    body_text = "\n".join(text_lines)

    # 1) Slack/Discord webhook
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    if url:
        try:
            import urllib.request
            payload = json.dumps({"text": body_text}).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 400:
                    logger.warning("alert webhook non-2xx status=%s", resp.status)
        except Exception as e:
            logger.warning("alert webhook failed: %s", e)

    # 2) SMTP Email (옵션)
    email_to = os.environ.get("ALERT_EMAIL_TO", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    if email_to and smtp_host:
        try:
            import smtplib
            from email.mime.text import MIMEText
            recipients = [e.strip() for e in email_to.split(",") if e.strip()]
            msg = MIMEText(body_text, "plain", "utf-8")
            msg["Subject"] = f"[비드스타] {title}"
            msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "noreply@bidstar"))
            msg["To"] = ", ".join(recipients)
            port = int(os.environ.get("SMTP_PORT", "587"))
            with smtplib.SMTP(smtp_host, port, timeout=10) as s:
                s.ehlo()
                if port == 587:
                    s.starttls()
                user = os.environ.get("SMTP_USER", "").strip()
                pwd = os.environ.get("SMTP_PASS", "").strip()
                if user and pwd:
                    s.login(user, pwd)
                s.sendmail(msg["From"], recipients, msg.as_string())
            logger.info("alert email sent to %s", email_to)
        except Exception as e:
            logger.warning("alert email failed: %s", e)


def _check_sync_failure_threshold():
    """최근 N회 수집 중 실패 비율이 임계치 초과 시 알림.

    환경변수:
      ALERT_FAILURE_THRESHOLD — 0.0~1.0 (기본 0.5 = 50%)
      ALERT_FAILURE_WINDOW    — 최근 N건 (기본 10)
    """
    try:
        threshold = float(os.environ.get("ALERT_FAILURE_THRESHOLD", "0.5"))
        window = int(os.environ.get("ALERT_FAILURE_WINDOW", "10"))
    except ValueError:
        return
    db = SessionLocal()
    try:
        recent = db.query(DataSyncLog).order_by(
            DataSyncLog.started_at.desc()
        ).limit(window).all()
        if len(recent) < window:
            return
        failed = sum(1 for r in recent if r.status == "failed")
        ratio = failed / len(recent)
        if ratio >= threshold:
            _send_alert_webhook(
                f"🚨 수집 실패 임계치 초과 ({failed}/{len(recent)}건, {int(ratio*100)}%)",
                {
                    "임계치": f"{int(threshold*100)}%",
                    "최근 실패": ", ".join(
                        f"{r.source} {r.started_at.strftime('%m/%d %H:%M')}"
                        for r in recent if r.status == "failed"
                    )[:200],
                },
            )
    finally:
        db.close()


def _scheduled_model_retrain():
    """매일 회귀 모델 재학습 — 카테고리별 OLS 적합 후 ModelMetric 저장.

    in-sample MAE/R² 만 기록 (out-of-sample 은 walk-forward 엔드포인트 활용).
    """
    import json as _json
    db = SessionLocal()
    try:
        period_days = int(os.environ.get("MODEL_RETRAIN_DAYS", "180"))
        cutoff = datetime.now() - timedelta(days=period_days)
        for category in ("공사", "용역", "all"):
            q = db.query(
                BidResult.assessment_rate, BidResult.opened_at,
                BidAnnouncement.base_amount, BidAnnouncement.category,
                BidAnnouncement.region, BidAnnouncement.industry_code,
                BidAnnouncement.ordering_org_type,
            ).join(BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id).filter(
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at >= cutoff,
            )
            if category in ("공사", "용역"):
                q = q.filter(BidAnnouncement.category == category)
            samples = []
            ref = datetime.now()
            for row in q.all():
                if not row[0]:
                    continue
                samples.append({
                    "rate": row[0],
                    "base_amount": row[2] or 0,
                    "category": row[3], "region": row[4],
                    "industry": row[5], "org_type": row[6],
                    "days_old": (ref - row[1]).days if row[1] else 0,
                })
            if len(samples) < 30:
                logger.info("model retrain skipped category=%s (n=%d, <30)", category, len(samples))
                continue
            # 자기 자신을 target 으로 → 평균값 회귀 결과
            target = {"base_amount": sum(s["base_amount"] for s in samples) / len(samples),
                      "category": category, "region": None, "industry": None,
                      "org_type": None, "days_old": 0}
            result = _ols_regression(samples, target)
            if result.get("predicted_rate") is None:
                continue
            # in-sample MAE 계산 (lstsq 가 다시 fit)
            import numpy as _np
            from collections import Counter as _Counter
            top_regions = [r for r, _ in _Counter(s.get("region") for s in samples
                                                    if s.get("region")).most_common(5)]

            def _featurize(s):
                ba = s.get("base_amount") or 1
                return [1.0, math.log(max(1, ba)), 1 if s.get("category") == "공사" else 0] + \
                       [1 if s.get("region") == r else 0 for r in top_regions] + \
                       [s.get("days_old", 0) or 0]
            X = _np.array([_featurize(s) for s in samples], dtype=float)
            y = _np.array([s["rate"] for s in samples], dtype=float)
            coef, *_ = _np.linalg.lstsq(X, y, rcond=None)
            y_pred = X @ coef
            mae = float(_np.mean(_np.abs(y - y_pred)))

            db.add(ModelMetric(
                category=category, model_type="ols",
                n_samples=len(samples),
                r_squared=result.get("r_squared"),
                residual_std=result.get("residual_std"),
                mae=round(mae, 4),
                coefficients_json=_json.dumps(
                    [(n, round(float(c), 4)) for n, c in zip(
                        ["intercept", "log_base", "is_construction"] + [f"region_{r}" for r in top_regions] + ["days_old"],
                        coef)],
                    ensure_ascii=False,
                ),
                period_days=period_days,
            ))
            logger.info("model retrain category=%s n=%d r²=%.4f mae=%.4f",
                        category, len(samples), result.get("r_squared") or 0, mae)
        db.commit()
    finally:
        db.close()


def _scheduled_sync_job():
    """스케줄러가 호출하는 수집 잡"""
    logger.info("scheduled sync job started")
    failures: list[dict] = []
    try:
        # G2B 키만으로 국방부·군 등 국방 발주 데이터까지 수집됨 → 기본은 G2B만 호출
        # D2B 별도 API를 사용할 경우 환경변수 ENABLE_D2B_SYNC=true 로 활성
        sources = ("G2B", "D2B") if os.environ.get("ENABLE_D2B_SYNC", "").lower() == "true" else ("G2B",)
        for src in sources:
            res = _run_sync_for_source(src, trigger="scheduled")
            logger.info(
                "sync result source=%s status=%s records=%s inserted=%s",
                res["source"], res["status"], res.get("records", 0),
                res.get("inserted", 0),
            )
            if res["status"] == "failed":
                failures.append({
                    "source": res["source"],
                    "error": res.get("error_message", "unknown"),
                })
        if failures:
            _send_alert_webhook(
                "🚨 자동 수집 실패",
                {
                    "실패 소스": ", ".join(f["source"] for f in failures),
                    "오류": "; ".join(f["error"][:80] for f in failures),
                    "서버시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        # 누적 실패율 임계치 점검
        _check_sync_failure_threshold()
    except Exception as e:
        logger.exception("scheduler job failed: %s", e)
        _send_alert_webhook("❗ 스케줄러 예외", {"error": str(e)[:200]})
        try:
            db = SessionLocal()
            try:
                db.add(DataSyncLog(
                    source="SCHEDULER", sync_type="자동 수집", status="failed",
                    records_fetched=0, error_message=str(e)[:500],
                    started_at=datetime.now(), finished_at=datetime.now(),
                ))
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.warning("DataSyncLog 저장 실패: %s", exc)


def _apply_schedule_config(config: dict):
    """_schedule_config에 따라 APScheduler 재설정"""
    global _scheduler
    if not _SCHEDULER_AVAILABLE or _scheduler is None:
        return
    # 기존 job 제거
    for job in _scheduler.get_jobs():
        job.remove()
    if not config.get("enabled", True):
        return
    interval = config.get("interval", "daily")
    time_str = config.get("time", "02:00")
    try:
        hour, minute = (int(x) for x in time_str.split(":"))
    except (ValueError, AttributeError) as exc:
        logger.warning("스케줄 시각 파싱 실패 (%s) — 기본값 02:00 사용: %s", time_str, exc)
        hour, minute = 2, 0

    if interval == "hourly":
        trigger = IntervalTrigger(hours=1)
    elif interval == "weekly":
        trigger = CronTrigger(day_of_week="mon", hour=hour, minute=minute)
    else:  # daily
        trigger = CronTrigger(hour=hour, minute=minute)
    _scheduler.add_job(_scheduled_sync_job, trigger=trigger, id="auto_sync", replace_existing=True)
    # 회귀 모델 재학습 — 매일 04:00 (수집 02:00 후)
    _scheduler.add_job(
        _scheduled_model_retrain,
        trigger=CronTrigger(hour=4, minute=0),
        id="auto_model_retrain", replace_existing=True,
    )


from contextlib import asynccontextmanager, contextmanager

# db_session / get_db 는 app/core/database 에서 재import (F2 분리)
from app.core.database import db_session, get_db  # noqa: E402, F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    if _SCHEDULER_AVAILABLE:
        try:
            _scheduler = BackgroundScheduler(timezone="Asia/Seoul")
            _scheduler.start()
            _apply_schedule_config(_schedule_config)
            logger.info("scheduler started config=%s", _schedule_config)
        except Exception as e:
            logger.exception("scheduler start failed: %s", e)
            _scheduler = None
    yield
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as exc:
            logger.warning("스케줄러 종료 실패: %s", exc)


# 스케줄 설정 (메모리 기반 — 재시작 시 환경변수에서 로드)
_schedule_config = {
    "interval": os.environ.get("SYNC_INTERVAL", "daily"),
    "time": os.environ.get("SYNC_TIME", "02:00"),
    "enabled": os.environ.get("SYNC_ENABLED", "true").lower() == "true",
}

app = FastAPI(
    title="비드스타 API",
    version="0.2.0",
    description=(
        "공공데이터 기반 입찰가 산정 및 사정률 분석 웹 서비스 API.\n\n"
        "**주요 기능**\n"
        "- 나라장터(G2B) 공고 수집 (국방부·군 발주 포함, 용역+공사 카테고리)\n"
        "- Tab1 빈도 분석 / Tab2 갭 분석 / Tab3 종합 분석\n"
        "- 사용자 마이페이지·데이터 업로드·관리자 대시보드\n"
        "- 자동 수집 스케줄러(APScheduler) + Prometheus 메트릭\n\n"
        "**인증**: JWT Bearer 토큰 (`POST /api/v1/auth/login` 으로 획득)\n"
        "**Rate Limit**: 로그인 10/min · 분석 30~60/min · 글로벌 300/min"
    ),
    contact={
        "name": "비드스타 지원팀",
        "email": "support@bid-insight.example.com",
    },
    license_info={"name": "Proprietary"},
    openapi_tags=[
        {"name": "인증", "description": "회원가입/로그인/토큰/비밀번호"},
        {"name": "메타", "description": "지역·공종 등 메타 데이터"},
        {"name": "공고", "description": "입찰 공고 조회 및 필터"},
        {"name": "분석", "description": "빈도·갭·종합·밀어내기식 검증"},
        {"name": "통계", "description": "KPI·추이·지역/업종별 통계"},
        {"name": "이력", "description": "조회 이력 (마이페이지)"},
        {"name": "데이터", "description": "Excel/CSV 업로드"},
        {"name": "관리자", "description": "사용자·수집·스케줄·NAS 상태 관리"},
        {"name": "운영", "description": "헬스체크·메트릭"},
    ],
    lifespan=lifespan,
)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Rate Limiting (slowapi) ──────────────────────────────────────
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from starlette.responses import JSONResponse

    limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request, exc):
        logger.warning("rate limit exceeded ip=%s path=%s", get_remote_address(request), request.url.path)
        return JSONResponse(
            status_code=429,
            content={"detail": f"요청 속도 제한을 초과했습니다. 잠시 후 다시 시도해주세요. (limit: {exc.detail})"},
        )

    _RATE_LIMIT_AVAILABLE = True
except ImportError:
    limiter = None
    _RATE_LIMIT_AVAILABLE = False
    logger.warning("slowapi 미설치 — Rate Limiting 비활성화")


def rate_limit(spec: str):
    """slowapi 설치 여부에 따라 조건부 적용 데코레이터"""
    if _RATE_LIMIT_AVAILABLE and limiter is not None:
        return limiter.limit(spec)

    def noop(fn):
        return fn

    return noop


# ─── 분석 결과 TTL 캐시 (app/services/cache 에서 정의 — F3 분리) ──────────
from app.services.cache import (  # noqa: E402, F401
    _cache_get,
    _cache_set,
    _cache_key,
    invalidate_analysis_cache,
)


# ─── 보안 헤더 미들웨어 ───────────────────────────────────────────
def _is_production() -> bool:
    return os.environ.get("APP_ENV", "development").lower() == "production"


@app.middleware("http")
async def _security_headers_middleware(request, call_next):
    response = await call_next(request)
    # XSS / Clickjacking 방어
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    # CSP — 단일 파일 SPA 특성상 inline script 허용 필요
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://apis.data.go.kr https://d2b.go.kr;",
    )
    if _is_production():
        # 프로덕션에서만 HSTS (HTTPS 강제)
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.middleware("http")
async def _access_log_middleware(request, call_next):
    import time as _time
    start = _time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as e:
        elapsed = (_time.perf_counter() - start) * 1000
        logger.exception(
            "request error method=%s path=%s duration_ms=%.1f err=%s",
            request.method, request.url.path, elapsed, e,
        )
        raise
    elapsed = (_time.perf_counter() - start) * 1000
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(
        level,
        "req method=%s path=%s status=%d duration_ms=%.1f",
        request.method, request.url.path, response.status_code, elapsed,
    )
    return response


# get_db 는 app/core/database 에서 이미 import 되어 있음 (F2)


# ─── 인증 설정 ──────────────────────────────────────────────────────────
_DEFAULT_SECRET = "bid-insight-secret-key-change-in-production"
SECRET_KEY = os.environ.get("SECRET_KEY", _DEFAULT_SECRET)
ALGORITHM = "HS256"

# 프로덕션 보안 검증: ENV=production일 때 기본 SECRET_KEY 거부
_RUNTIME_ENV = os.environ.get("APP_ENV", "development").lower()
if _RUNTIME_ENV == "production":
    if SECRET_KEY == _DEFAULT_SECRET:
        raise RuntimeError(
            "SECRET_KEY 환경변수가 설정되지 않았거나 기본값입니다. "
            "프로덕션 배포 시 `openssl rand -hex 32` 으로 생성한 키를 지정해야 합니다."
        )
    if len(SECRET_KEY) < 32:
        raise RuntimeError(
            f"SECRET_KEY 길이가 너무 짧습니다 ({len(SECRET_KEY)}자). 최소 32자 이상 권장."
        )
    if CORS_ORIGINS := os.environ.get("CORS_ORIGINS", "").strip():
        if "*" in CORS_ORIGINS.split(","):
            raise RuntimeError("프로덕션에서는 CORS_ORIGINS='*' 를 사용할 수 없습니다.")
    logger.info("production env validation passed")
else:
    if SECRET_KEY == _DEFAULT_SECRET:
        logger.warning("SECRET_KEY 기본값 사용 중 — 프로덕션 배포 전 반드시 변경 필요")
# ─── 인증 헬퍼 (app/core/security 에서 정의 — F2 분리) ──────────────────
# server.py 가 환경변수 검증 후 SECRET_KEY 를 주입한다.
import app.core.security as _sec_mod  # noqa: E402
_sec_mod.SECRET_KEY = SECRET_KEY

from app.core.security import (  # noqa: E402
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth2_scheme,
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_auth,
    require_admin,
)


# ─── API: 인증 (app/routes/auth 로 이전 — F4) ────────────────────────────
from app.routes.auth import router as _auth_router  # noqa: E402
app.include_router(_auth_router)


# ─── API: 메타·공고 (app/routes/meta, announcements 로 이전 — F4) ────────
from app.routes.meta import router as _meta_router  # noqa: E402
from app.routes.announcements import router as _anno_router  # noqa: E402
app.include_router(_meta_router)
app.include_router(_anno_router)


# ─── 사정률 예측 헬퍼 (app/services/analysis 에서 정의 — F3 분리) ──────────
from app.services.analysis import (  # noqa: E402, F401
    _remove_outliers_iqr,
    _time_weighted_rates,
    _confidence_interval,
    _homogeneity_score,
    _ensemble_predict,
    _trend_momentum,
    _walk_forward_validate,
    _bayesian_shrinkage,
    _apply_category_filter,
    _detect_anomaly,
    _kmeans_simple,
    _knn_similar_announcements,
    _ols_regression,
    _build_rate_histogram,
    _compute_rate_buckets,
    _extract_detail_rate,
    _compute_confidence,
)



# ─── API: 사정률 발생빈도 분석 ────────────────────────────────────────────

@app.get("/api/v1/analysis/frequency/{announcement_id}")
@rate_limit("60/minute")
def analysis_frequency(
    request: Request,
    announcement_id: str,
    period_months: int = Query(12, ge=1, le=24),
    org_scope: str = Query("specific"),  # specific | parent
    current_user: User = Depends(require_auth),
):
    """사정률 발생빈도 히스토그램 + 피크 구간 분석 (TTL 캐시)"""
    cache_key = _cache_key("freq", announcement_id, period_months, org_scope)
    cached = _cache_get(cache_key)
    if cached is not None:
        # 캐시 히트 시에도 인증 사용자의 이력은 저장
        if current_user:
            top_rate = cached.get("prediction_candidates", [{}])[0].get("rate") if cached.get("prediction_candidates") else None
            save_query_history(
                current_user.id, announcement_id, "frequency",
                parameters={"period_months": period_months, "org_scope": org_scope, "cached": True},
                result_summary={"top_predicted_rate": top_rate,
                                "data_count": cached.get("data_count", 0)},
            )
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 동일 카테고리 + 발주처 범위의 과거 사정률
        q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        if org_scope == "parent" and ann.parent_org_name:
            # 상위 기관 범위
            q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
        else:
            # 동일 발주기관
            q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

        rows = q.all()
        if not rows:
            # 폴백: 같은 카테고리+지역 전체
            q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.region == ann.region,
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at >= cutoff,
            )
            rows = q.all()

        rates = [r.assessment_rate for r in rows if r.assessment_rate]
        first_place_rates = [r.first_place_rate for r in rows if r.first_place_rate]

        if not rates:
            db.close()
            return {"bins": [], "peaks": [], "stats": {}, "data_count": 0}

        # 0.1% 단위 히스토그램
        min_r = math.floor(min(rates) * 10) / 10
        max_r = math.ceil(max(rates) * 10) / 10
        bin_size = 0.1
        bins = []
        current = min_r
        while current <= max_r + 0.001:
            count = sum(1 for r in rates if current - bin_size / 2 <= r < current + bin_size / 2)
            fp_count = sum(1 for r in first_place_rates if current - bin_size / 2 <= r < current + bin_size / 2)
            bins.append({
                "rate": round(current, 2),
                "count": count,
                "first_place_count": fp_count,
            })
            current = round(current + bin_size, 2)

        # 피크 구간 (상위 5개)
        sorted_bins = sorted(bins, key=lambda b: b["count"], reverse=True)
        peaks = []
        for b in sorted_bins[:5]:
            if b["count"] > 0:
                peaks.append({
                    "rate": b["rate"],
                    "range_start": round(b["rate"] - bin_size / 2, 2),
                    "range_end": round(b["rate"] + bin_size / 2, 2),
                    "count": b["count"],
                })

        # 1순위 예측 후보 (10개 이상) — 빈도 + 1순위 비율 점수
        total_fp = len(first_place_rates)
        prediction_candidates = []
        for b in bins:
            if b["count"] == 0:
                continue
            fp_ratio = round(b["first_place_count"] / b["count"] * 100, 1) if b["count"] > 0 else 0
            # 점수 = 빈도 비율(0.5) + 1순위 비율(0.5)
            freq_score = b["count"] / max(bb["count"] for bb in bins) if max(bb["count"] for bb in bins) > 0 else 0
            fp_score = b["first_place_count"] / max((max(bb["first_place_count"] for bb in bins), 1))
            combined_score = round(freq_score * 0.5 + fp_score * 0.5, 4)
            bid_amount = int(ann.base_amount * b["rate"] / 100) if ann.base_amount else 0
            prediction_candidates.append({
                "rate": b["rate"],
                "frequency": b["count"],
                "first_place_count": b["first_place_count"],
                "first_place_ratio": fp_ratio,
                "score": combined_score,
                "bid_amount": bid_amount,
                "is_recommended": False,
            })
        prediction_candidates.sort(key=lambda c: c["score"], reverse=True)
        # 상위 후보에 추천 마크
        for i, c in enumerate(prediction_candidates[:3]):
            c["is_recommended"] = True
        # 순위 부여
        for i, c in enumerate(prediction_candidates):
            c["rank"] = i + 1

        stat = {
            "mean": round(statistics.mean(rates), 4),
            "median": round(statistics.median(rates), 4),
            "std": round(statistics.stdev(rates), 4) if len(rates) > 1 else 0,
            "min": round(min(rates), 4),
            "max": round(max(rates), 4),
        }

    finally:
        db.close()
    result = {
        "bins": bins,
        "peaks": peaks,
        "stats": stat,
        "data_count": len(rates),
        "first_place_total": total_fp,
        "prediction_candidates": prediction_candidates[:15],
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "org": ann.ordering_org_name, "area": ann.region,
            "budget": ann.base_amount,
        },
    }
    _cache_set(cache_key, result)
    if current_user:
        top_rate = prediction_candidates[0]["rate"] if prediction_candidates else None
        save_query_history(
            current_user.id, announcement_id, "frequency",
            parameters={"period_months": period_months, "org_scope": org_scope},
            result_summary={"top_predicted_rate": top_rate, "data_count": len(rates),
                            "peak_count": len(peaks)},
        )
    return result


# ─── API: 사정률 구간 분석 (스펙 §1 — 3가지 모드 A/B/C) ──────────────────

@app.get("/api/v1/analysis/rate-buckets/{announcement_id}")
@rate_limit("60/minute")
def analysis_rate_buckets(
    request: Request,
    announcement_id: str,
    period_months: int = Query(6, ge=1, le=36, description="1/3/6/24개월 등 밀어내기식 분석 기간"),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    detail_rule: str = Query("max_gap", pattern="^(first_after|last_after|max_gap)$"),
    current_user: User = Depends(require_auth),
):
    """사정률 발생빈도 + 3가지 구간 알고리즘 (스펙 §1)

    - **mode A**: 빈도 최대 (막대 가장 큰 값 기준)
    - **mode B**: 공백 (막대 없는 값 기준)
    - **mode C**: 차이 최대 (인접 막대 차이가 가장 큰 값 기준)

    각 모드별로 100 기준 ±방향 정렬한 상위 5개 구간 반환 +
    detail_rule 에 따른 세부 사정률 값 1개.
    """
    cache_key = _cache_key("buckets", announcement_id, period_months, category_filter, detail_rule)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 카테고리 필터 적용
        q = db.query(BidResult.assessment_rate).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        q = _apply_category_filter(q, category_filter, ann)

        rates = [r[0] for r in q.all() if r[0] is not None]

        if not rates:
            result = {
                "announcement": {"id": ann.id, "title": ann.title, "category": ann.category},
                "params": {"period_months": period_months, "category_filter": category_filter,
                           "detail_rule": detail_rule},
                "data_count": 0,
                "histogram": [],
                "buckets": {"A": [], "B": [], "C": []},
                "detail_rate": None,
            }
        else:
            histogram = _build_rate_histogram(rates, bin_size=0.1)
            buckets = {
                "A": _compute_rate_buckets(histogram, mode="A", top_n=5),
                "B": _compute_rate_buckets(histogram, mode="B", top_n=5),
                "C": _compute_rate_buckets(histogram, mode="C", top_n=5),
            }
            # 표 = 빈도가 0보다 큰 bin 의 사정률 리스트
            table_rates = [b["rate"] for b in histogram if b["count"] > 0]
            detail_rate = _extract_detail_rate(table_rates, rule=detail_rule)
            bid_amount = (
                int(ann.base_amount * detail_rate / 100)
                if ann.base_amount and detail_rate else None
            )

            result = {
                "announcement": {
                    "id": ann.id, "title": ann.title, "category": ann.category,
                    "ordering_org_name": ann.ordering_org_name,
                    "base_amount": ann.base_amount,
                },
                "params": {
                    "period_months": period_months,
                    "category_filter": category_filter,
                    "detail_rule": detail_rule,
                },
                "data_count": len(rates),
                "histogram": histogram,
                "buckets": buckets,
                "detail_rate": round(detail_rate, 4) if detail_rate else None,
                "predicted_bid_amount": bid_amount,
            }
        _cache_set(cache_key, result)
        if current_user:
            top_a = buckets["A"][0]["rate"] if result.get("buckets", {}).get("A") else None
            save_query_history(
                current_user.id, announcement_id, "rate_buckets",
                parameters={"period_months": period_months, "category_filter": category_filter,
                            "detail_rule": detail_rule},
                result_summary={"top_A_rate": top_a, "detail_rate": result.get("detail_rate"),
                                "data_count": result["data_count"]},
            )
        return result
    finally:
        db.close()


# ─── API: 업체사정률 분석 (갭 분석) ───────────────────────────────────────

@app.get("/api/v1/analysis/company-rates/{announcement_id}")
@rate_limit("60/minute")
def analysis_company_rates(
    request: Request,
    announcement_id: str,
    rate_range_start: float = Query(99.0),
    rate_range_end: float = Query(100.0),
    period_months: int = Query(12, ge=1, le=36),
    # 사정률 예측 로직 §2 — 검색 5종
    org_search: str = Query("", description="발주처 부분 일치 검색"),
    price_volatility: float = Query(0.0, ge=0.0, description="예가 변동폭 % (assessment_rate 의 ± 범위)"),
    base_amount_min: int = Query(0, ge=0, description="기초금액 하한"),
    base_amount_max: int = Query(0, ge=0, description="기초금액 상한 (0 이면 무시)"),
    industry_filter: str = Query("", description="업종 코드 부분 일치"),
    current_user: User = Depends(require_auth),
):
    """선택 구간 내 업체 투찰률 분포 + 최대 갭 분석 + 검색 5종 (스펙 §2)

    Search params:
      - org_search        발주처명 LIKE
      - price_volatility  assessment_rate 가 (100 ± volatility) 범위인 결과만
      - base_amount_min/max  공고 기초금액 범위
      - industry_filter   업종 코드 LIKE
    """
    cache_key = _cache_key(
        "gap", announcement_id, rate_range_start, rate_range_end, period_months,
        org_search, price_volatility, base_amount_min, base_amount_max, industry_filter,
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        if current_user:
            save_query_history(
                current_user.id, announcement_id, "company-rates",
                parameters={"rate_range_start": rate_range_start,
                            "rate_range_end": rate_range_end,
                            "period_months": period_months, "cached": True},
                result_summary={"refined_rate": cached.get("refined_rate"),
                                "total_companies": cached.get("total_companies", 0)},
            )
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 선택 구간 내 업체 투찰률 (스펙 §2 검색 5종 적용)
        rec_q = db.query(CompanyBidRecord).join(
            BidAnnouncement, CompanyBidRecord.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.announced_at >= cutoff,
            CompanyBidRecord.bid_rate >= rate_range_start,
            CompanyBidRecord.bid_rate <= rate_range_end,
        )
        if org_search:
            rec_q = rec_q.filter(BidAnnouncement.ordering_org_name.like(f"%{org_search}%"))
        if base_amount_min > 0:
            rec_q = rec_q.filter(BidAnnouncement.base_amount >= base_amount_min)
        if base_amount_max > 0:
            rec_q = rec_q.filter(BidAnnouncement.base_amount <= base_amount_max)
        if industry_filter:
            rec_q = rec_q.filter(BidAnnouncement.industry_code.like(f"%{industry_filter}%"))
        if price_volatility > 0:
            # 예가 변동폭: 매칭되는 BidResult 의 assessment_rate 가 100 ± volatility 인 공고만
            ann_ids_in_volatility = db.query(BidResult.announcement_id).filter(
                BidResult.assessment_rate.isnot(None),
                BidResult.assessment_rate >= 100 - price_volatility,
                BidResult.assessment_rate <= 100 + price_volatility,
            )  # subquery() 없이 select 그대로 IN 절에 전달 → SAWarning 회피
            rec_q = rec_q.filter(CompanyBidRecord.announcement_id.in_(ann_ids_in_volatility))
        records = rec_q.order_by(CompanyBidRecord.bid_rate).all()

        company_rates = [
            {
                "company": r.company_name,
                "rate": round(r.bid_rate, 4),
                "amount": r.bid_amount,
                "ranking": r.ranking,
                "is_first_place": r.is_first_place,
            }
            for r in records
        ]

        # 갭 분석: 연속 투찰률 간 최대 빈 공간
        unique_rates = sorted(set(r.bid_rate for r in records))
        gaps = []
        if len(unique_rates) >= 2:
            for i in range(len(unique_rates) - 1):
                gap_size = round(unique_rates[i + 1] - unique_rates[i], 4)
                if gap_size > 0.01:  # 유의미한 갭만
                    gaps.append({
                        "start": round(unique_rates[i], 4),
                        "end": round(unique_rates[i + 1], 4),
                        "size": gap_size,
                        "midpoint": round((unique_rates[i] + unique_rates[i + 1]) / 2, 4),
                    })

        gaps.sort(key=lambda g: g["size"], reverse=True)
        largest_gap_midpoint = gaps[0]["midpoint"] if gaps else round((rate_range_start + rate_range_end) / 2, 4)
        refined_rate = largest_gap_midpoint

        # 1순위 예측 리스트 (해당 구간 내 과거 1순위 결과 + 검색 필터 적용)
        fp_q = db.query(BidResult, BidAnnouncement).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.first_place_rate >= rate_range_start,
            BidResult.first_place_rate <= rate_range_end,
            BidResult.opened_at >= cutoff,
        )
        if org_search:
            fp_q = fp_q.filter(BidAnnouncement.ordering_org_name.like(f"%{org_search}%"))
        if base_amount_min > 0:
            fp_q = fp_q.filter(BidAnnouncement.base_amount >= base_amount_min)
        if base_amount_max > 0:
            fp_q = fp_q.filter(BidAnnouncement.base_amount <= base_amount_max)
        if industry_filter:
            fp_q = fp_q.filter(BidAnnouncement.industry_code.like(f"%{industry_filter}%"))
        if price_volatility > 0:
            fp_q = fp_q.filter(
                BidResult.assessment_rate.isnot(None),
                BidResult.assessment_rate >= 100 - price_volatility,
                BidResult.assessment_rate <= 100 + price_volatility,
            )
        first_place_in_range = fp_q.order_by(BidResult.opened_at.desc()).limit(20).all()

        first_place_list = [
            {
                "title": a.title,
                "org": a.ordering_org_name,
                "area": a.region,
                "assessment_rate": round(r.assessment_rate, 4),
                "first_place_rate": round(r.first_place_rate, 4),
                "first_place_amount": r.first_place_amount,
                "date": r.opened_at.strftime("%Y-%m-%d") if r.opened_at else "",
            }
            for r, a in first_place_in_range
        ]

        # Phase 7: 갭 중간점 차기연도 검증
        next_year_validation = []
        if gaps:
            next_year_start = ref_date
            next_year_end = ref_date + timedelta(days=365)
            next_year_results = db.query(BidResult, BidAnnouncement).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidResult.assessment_rate.isnot(None),
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= next_year_start,
                BidResult.opened_at <= next_year_end,
            ).all()

            for g in gaps[:10]:
                mid = g["midpoint"]
                matches = []
                for res, past_ann in next_year_results:
                    diff = abs(mid - res.assessment_rate)
                    actual_diff = abs(res.first_place_rate - res.assessment_rate)
                    is_first = diff <= actual_diff + 0.02
                    matches.append({
                        "actual_rate": round(res.assessment_rate, 4),
                        "first_place_rate": round(res.first_place_rate, 4),
                        "diff": round(abs(mid - res.first_place_rate), 4),
                        "is_first_place": is_first,
                        "date": res.opened_at.strftime("%Y-%m-%d") if res.opened_at else "",
                    })
                match_count = sum(1 for m in matches if m["is_first_place"])
                next_year_validation.append({
                    "gap_midpoint": mid,
                    "gap_size": g["size"],
                    "total_cases": len(matches),
                    "match_count": match_count,
                    "match_rate": round(match_count / len(matches) * 100, 1) if matches else 0,
                    "cases": matches[:5],
                })

    finally:
        db.close()
    result = {
        "company_rates": company_rates[:100],  # 최대 100건
        "gaps": gaps[:10],
        "largest_gap_midpoint": largest_gap_midpoint,
        "refined_rate": refined_rate,
        "total_companies": len(company_rates),
        "unique_rate_count": len(unique_rates),
        "first_place_predictions": first_place_list,
        "next_year_validation": next_year_validation,
    }
    _cache_set(cache_key, result)
    if current_user:
        save_query_history(
            current_user.id, announcement_id, "company-rates",
            parameters={"rate_range_start": rate_range_start, "rate_range_end": rate_range_end,
                        "period_months": period_months},
            result_summary={"refined_rate": refined_rate,
                            "largest_gap_midpoint": largest_gap_midpoint,
                            "total_companies": len(company_rates)},
        )
    return result


# ─── API: 종합분석 ────────────────────────────────────────────────────────

@app.get("/api/v1/analysis/comprehensive/{announcement_id}")
@rate_limit("60/minute")
def analysis_comprehensive(
    request: Request,
    announcement_id: str,
    confirmed_rate: float = Query(99.5),
    period_months: int = Query(12, ge=1, le=24),
    org_scope: str = Query("specific"),
    current_user: User = Depends(require_auth),
):
    """확정사정률 기반 과거 1순위 비교 + 종합 분석 (TTL 캐시)"""
    cache_key = _cache_key("comp", announcement_id, confirmed_rate, period_months, org_scope)
    cached = _cache_get(cache_key)
    if cached is not None:
        if current_user:
            save_query_history(
                current_user.id, announcement_id, "comprehensive",
                parameters={"confirmed_rate": confirmed_rate, "period_months": period_months,
                            "org_scope": org_scope, "cached": True},
                result_summary={"confirmed_rate": cached.get("confirmed_rate"),
                                "predicted_first_place_amount":
                                    cached.get("predicted_first_place", {}).get("amount")},
            )
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        # 기간별 분석 (밀어내기식)
        ref_date = ann.announced_at or datetime.now()
        periods = [1, 3, 6, 12, 24]
        period_results = {}

        for pm in periods:
            if pm > period_months:
                continue
            cutoff = ref_date - timedelta(days=pm * 30)

            q = db.query(BidResult, BidAnnouncement).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidResult.assessment_rate.isnot(None),
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= cutoff,
            )

            if org_scope == "parent" and ann.parent_org_name:
                q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
            elif org_scope == "specific":
                q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

            past_data = q.order_by(BidResult.opened_at.desc()).all()

            match_count = 0
            comparisons = []
            for res, past_ann in past_data:
                # 예측사정률(confirmed_rate)로 1순위 되었을지 확인
                diff = abs(confirmed_rate - res.assessment_rate)
                actual_diff = abs(res.first_place_rate - res.assessment_rate)
                is_match = diff <= actual_diff + 0.02  # 오차범위 0.02%

                if is_match:
                    match_count += 1

                comparisons.append({
                    "id": past_ann.id,
                    "title": past_ann.title,
                    "org": past_ann.ordering_org_name,
                    "area": past_ann.region,
                    "date": res.opened_at.strftime("%Y-%m-%d") if res.opened_at else "",
                    "assessment_rate": round(res.assessment_rate, 4),
                    "first_place_rate": round(res.first_place_rate, 4),
                    "predicted_rate": round(confirmed_rate, 4),
                    "predicted_diff": round(diff, 4),
                    "actual_first_diff": round(actual_diff, 4),
                    "is_match": is_match,
                    "first_place_amount": res.first_place_amount,
                })

            total = len(comparisons)
            period_results[f"{pm}m"] = {
                "period_months": pm,
                "match_count": match_count,
                "total": total,
                "match_rate": round(match_count / total * 100, 1) if total > 0 else 0,
                "comparisons": comparisons[:30],  # 최대 30건
            }

        # 1순위 예상 낙찰가
        predicted_first_place_amount = int(ann.base_amount * confirmed_rate / 100) if ann.base_amount else 0

        # 상위기관 동시 분석
        parent_analysis = None
        if ann.parent_org_name and org_scope == "specific":
            cutoff = ref_date - timedelta(days=period_months * 30)
            parent_q = db.query(BidResult, BidAnnouncement).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.parent_org_name == ann.parent_org_name,
                BidResult.assessment_rate.isnot(None),
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= cutoff,
            )
            parent_data = parent_q.all()
            parent_match = sum(
                1 for res, _ in parent_data
                if abs(confirmed_rate - res.assessment_rate) <= abs(res.first_place_rate - res.assessment_rate) + 0.02
            )
            parent_analysis = {
                "parent_org": ann.parent_org_name,
                "match_count": parent_match,
                "total": len(parent_data),
                "match_rate": round(parent_match / len(parent_data) * 100, 1) if parent_data else 0,
            }

    finally:
        db.close()
    result = {
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "org": ann.ordering_org_name, "parent_org": ann.parent_org_name,
            "area": ann.region, "budget": ann.base_amount,
        },
        "confirmed_rate": round(confirmed_rate, 4),
        "predicted_first_place": {
            "rate": round(confirmed_rate, 4),
            "amount": predicted_first_place_amount,
        },
        "period_results": period_results,
        "parent_analysis": parent_analysis,
    }
    _cache_set(cache_key, result)
    if current_user:
        save_query_history(
            current_user.id, announcement_id, "comprehensive",
            parameters={"confirmed_rate": confirmed_rate, "period_months": period_months,
                        "org_scope": org_scope},
            result_summary={"confirmed_rate": round(confirmed_rate, 4),
                            "predicted_first_place_amount": predicted_first_place_amount,
                            "period_result_count": len(period_results) if period_results else 0},
        )
    return result


# ─── API: 결합 예측 (빈도 + 갭 결합) ─────────────────────────────────────

@app.get("/api/v1/analysis/combined-prediction/{announcement_id}")
def analysis_combined_prediction(
    announcement_id: str,
    period_months: int = Query(12, ge=1, le=24),
    org_scope: str = Query("specific"),
):
    """빈도분석 피크 + 갭분석 중간점을 결합하여 최적 후보 10개 이상 산출"""
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 1) 빈도분석: 사정률 히스토그램 피크
        q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        if org_scope == "parent" and ann.parent_org_name:
            q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
        else:
            q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)
        rows = q.all()

        if not rows:
            q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.region == ann.region,
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at >= cutoff,
            )
            rows = q.all()

        rates = [r.assessment_rate for r in rows if r.assessment_rate]
        first_place_rates = [r.first_place_rate for r in rows if r.first_place_rate]

        # 빈도 히스토그램 (0.1% 단위)
        freq_map = {}
        if rates:
            bin_size = 0.1
            for r in rates:
                key = round(round(r / bin_size) * bin_size, 2)
                freq_map[key] = freq_map.get(key, 0) + 1
        fp_map = {}
        for r in first_place_rates:
            key = round(round(r / 0.1) * 0.1, 2)
            fp_map[key] = fp_map.get(key, 0) + 1
        max_freq = max(freq_map.values()) if freq_map else 1

        # 상위 빈도 피크 10개
        freq_peaks = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)[:10]

        # 2) 갭분석: 업체 투찰률 빈 공간 중간점
        mean_rate = statistics.mean(rates) if rates else 99.5
        gap_range_start = round(mean_rate - 0.5, 2)
        gap_range_end = round(mean_rate + 0.5, 2)
        company_records = db.query(CompanyBidRecord).join(
            BidAnnouncement, CompanyBidRecord.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.announced_at >= cutoff,
            CompanyBidRecord.bid_rate >= gap_range_start,
            CompanyBidRecord.bid_rate <= gap_range_end,
        ).order_by(CompanyBidRecord.bid_rate).all()

        unique_rates = sorted(set(r.bid_rate for r in company_records))
        gap_midpoints = []
        if len(unique_rates) >= 2:
            for i in range(len(unique_rates) - 1):
                gap_size = unique_rates[i + 1] - unique_rates[i]
                if gap_size > 0.01:
                    gap_midpoints.append({
                        "rate": round((unique_rates[i] + unique_rates[i + 1]) / 2, 4),
                        "gap_size": round(gap_size, 4),
                    })
        gap_midpoints.sort(key=lambda g: g["gap_size"], reverse=True)

        # 3) 결합 점수 산출
        candidates = {}
        # 빈도 피크에서 후보 추가
        for rate_val, count in freq_peaks:
            fp_cnt = fp_map.get(rate_val, 0)
            freq_score = count / max_freq
            fp_score = fp_cnt / max(max(fp_map.values(), default=1), 1)
            candidates[rate_val] = {
                "rate": rate_val,
                "source": "빈도",
                "freq_count": count,
                "first_place_count": fp_cnt,
                "freq_score": round(freq_score, 4),
                "gap_score": 0,
                "combined_score": 0,
            }

        # 갭 중간점에서 후보 추가/보강
        max_gap = gap_midpoints[0]["gap_size"] if gap_midpoints else 1
        for gm in gap_midpoints[:15]:
            rate_val = round(gm["rate"], 2)
            gap_s = gm["gap_size"] / max_gap
            if rate_val in candidates:
                candidates[rate_val]["source"] = "빈도+갭"
                candidates[rate_val]["gap_score"] = round(gap_s, 4)
            else:
                # 근접 빈도 구간 찾기
                nearest_freq = 0
                nearest_fp = 0
                for fr, fc in freq_map.items():
                    if abs(fr - rate_val) <= 0.15:
                        nearest_freq = max(nearest_freq, fc)
                        nearest_fp = max(nearest_fp, fp_map.get(fr, 0))
                candidates[rate_val] = {
                    "rate": rate_val,
                    "source": "갭",
                    "freq_count": nearest_freq,
                    "first_place_count": nearest_fp,
                    "freq_score": round(nearest_freq / max_freq, 4) if max_freq > 0 else 0,
                    "gap_score": round(gap_s, 4),
                    "combined_score": 0,
                }

        # 결합 점수 = 빈도(0.4) + 갭(0.4) + 1순위 이력(0.2)
        max_fp_score = max((c["first_place_count"] for c in candidates.values()), default=1) or 1
        for c in candidates.values():
            fp_s = c["first_place_count"] / max_fp_score
            c["combined_score"] = round(
                c["freq_score"] * 0.4 + c["gap_score"] * 0.4 + fp_s * 0.2, 4
            )
            c["bid_amount"] = int(ann.base_amount * c["rate"] / 100) if ann.base_amount else 0

        result_list = sorted(candidates.values(), key=lambda c: c["combined_score"], reverse=True)
        for i, c in enumerate(result_list):
            c["rank"] = i + 1
            c["is_recommended"] = i < 3
            c["confidence"] = "높음" if c["combined_score"] > 0.6 else "보통" if c["combined_score"] > 0.3 else "낮음"

    finally:
        db.close()
    return {
        "candidates": result_list[:15],
        "total_candidates": len(result_list),
        "data_summary": {
            "freq_data_count": len(rates),
            "gap_data_count": len(company_records),
            "first_place_count": len(first_place_rates),
        },
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "org": ann.ordering_org_name, "area": ann.region,
            "budget": ann.base_amount,
        },
    }


# ─── API: 상관관계 분석 (스펙 §3.11 — 3가지 방법 종합 1순위) ─────────────

@app.get("/api/v1/analysis/correlation/{announcement_id}")
@rate_limit("30/minute")
def analysis_correlation(
    request: Request,
    announcement_id: str,
    period_months: int = Query(6, ge=1, le=36),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    bucket_mode: str = Query("A", pattern="^(A|B|C)$"),
    detail_rule: str = Query("max_gap", pattern="^(first_after|last_after|max_gap)$"),
    rate_range_start: float = Query(99.0),
    rate_range_end: float = Query(101.0),
    current_user: User = Depends(require_auth),
):
    """스펙 §3.11 — 3가지 분석 방법별 1순위 + 종합 상관관계 1순위.

    Methods:
      1) 사정률 발생빈도 분석 (Tab1 모드)
      2) 업체사정률 갭 분석 (Tab2)
      3) 빈도+갭 결합 분석

    Returns:
      methods: [{name, top1_rate, top1_score, count}, ...]
      correlation: {agreement, final_top1, final_score, methods_aligned}
    """
    cache_key = _cache_key(
        "correlation", announcement_id, period_months, category_filter,
        bucket_mode, detail_rule, rate_range_start, rate_range_end,
    )
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 카테고리 필터 — 공통 헬퍼 alias (analysis_correlation 내부 사용)
        _apply_category = lambda q: _apply_category_filter(q, category_filter, ann)

        # ── Method 1: 사정률 발생빈도 (정확도 강화 적용) ───────────
        # 표본 수집 — 사정률·날짜·발주처·업종 동시 조회 (정확도 분석용 메타)
        rate_q = db.query(
            BidResult.assessment_rate,
            BidResult.opened_at,
            BidAnnouncement.ordering_org_name,
            BidAnnouncement.industry_code,
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        rate_q = _apply_category(rate_q)
        raw_samples = [(r[0], r[1], r[2], r[3]) for r in rate_q.all() if r[0] is not None]
        raw_rates = [s[0] for s in raw_samples]

        # ① IQR 이상치 제거 (분포 안정화)
        clean_rates = _remove_outliers_iqr(raw_rates)
        outliers_removed = len(raw_rates) - len(clean_rates)

        # ② 동종성 점수 (대상 공고 발주처/업종과 표본 유사도)
        homogeneity = _homogeneity_score(
            ann.ordering_org_name, ann.industry_code,
            [s[2] for s in raw_samples], [s[3] for s in raw_samples],
        )

        # ③ 시계열 가중치 (최근 6개월 데이터 더 높게)
        rates_with_dates = [(s[0], s[1]) for s in raw_samples if s[0] in clean_rates]
        rates_m1 = _time_weighted_rates(rates_with_dates, half_life_days=180, ref_date=ref_date)
        if not rates_m1:  # fallback
            rates_m1 = clean_rates

        method1 = {
            "name": "1) 사정률 발생빈도 분석",
            "top1_rate": None,
            "top1_score": 0,
            "count": len(raw_rates),  # 원 표본 수 (사용자 노출용)
            "weighted_count": len(rates_m1),
            "outliers_removed": outliers_removed,
            "homogeneity": homogeneity,
            "mode": bucket_mode,
        }
        if rates_m1:
            hist = _build_rate_histogram(rates_m1)
            buckets = _compute_rate_buckets(hist, mode=bucket_mode, top_n=1)
            if buckets:
                method1["top1_rate"] = round(buckets[0]["rate"], 4)
                method1["top1_score"] = buckets[0]["score"]

        # ── Method 2: 업체사정률 갭 분석 ─────────────────────────
        # 1차: CompanyBidRecord (업로드 데이터)
        gap_q = db.query(CompanyBidRecord.bid_rate).join(
            BidAnnouncement, CompanyBidRecord.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.announced_at >= cutoff,
            CompanyBidRecord.bid_rate >= rate_range_start,
            CompanyBidRecord.bid_rate <= rate_range_end,
        )
        gap_q = _apply_category(gap_q)
        bid_rates = sorted({round(r[0], 4) for r in gap_q.all() if r[0] is not None})
        gap_source = "company_records"
        # Fallback: G2B 자동 수집은 CompanyBidRecord 가 비어 있으므로
        # BidResult.first_place_rate (1순위 낙찰률) 분포로 대체
        if not bid_rates:
            fp_q = db.query(BidResult.first_place_rate).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= cutoff,
                BidResult.first_place_rate >= rate_range_start,
                BidResult.first_place_rate <= rate_range_end,
            )
            fp_q = _apply_category(fp_q)
            bid_rates = sorted({round(r[0], 4) for r in fp_q.all() if r[0] is not None})
            gap_source = "first_place_rate"
        method2 = {
            "name": "2) 업체사정률 갭 분석",
            "top1_rate": None,
            "top1_score": 0,
            "count": len(bid_rates),
            "source": gap_source,
        }
        if len(bid_rates) >= 2:
            best_gap = 0
            best_mid = None
            for i in range(len(bid_rates) - 1):
                gap = round(bid_rates[i + 1] - bid_rates[i], 4)
                if gap > best_gap:
                    best_gap = gap
                    best_mid = round((bid_rates[i] + bid_rates[i + 1]) / 2, 4)
            if best_mid is not None:
                method2["top1_rate"] = best_mid
                method2["top1_score"] = best_gap

        # ── Method 3: 빈도+갭 결합 (양쪽 후보 중 100 가까운 + 양쪽에 모두 등장) ──
        method3 = {
            "name": "3) 빈도+갭 결합 분석",
            "top1_rate": None,
            "top1_score": 0,
            "count": 0,
        }
        if rates_m1 and bid_rates:
            hist = _build_rate_histogram(rates_m1)
            top5_freq = [b["rate"] for b in _compute_rate_buckets(hist, mode=bucket_mode, top_n=5)]
            # 갭 후보 (상위 5)
            gap_candidates = []
            for i in range(len(bid_rates) - 1):
                gap = round(bid_rates[i + 1] - bid_rates[i], 4)
                mid = round((bid_rates[i] + bid_rates[i + 1]) / 2, 4)
                gap_candidates.append((mid, gap))
            gap_candidates.sort(key=lambda x: -x[1])
            top5_gap = [round(m, 1) for m, _ in gap_candidates[:5]]
            # 교집합 (소수 1자리 반올림 기준) → 100 기준 가까운 순
            top5_freq_round = {round(r, 1) for r in top5_freq}
            top5_gap_round = set(top5_gap)
            common = sorted(top5_freq_round & top5_gap_round, key=lambda r: abs(r - 100))
            method3["count"] = len(common)
            if common:
                method3["top1_rate"] = round(common[0], 4)
                method3["top1_score"] = len(common)
            elif method1["top1_rate"] and method2["top1_rate"]:
                # 교집합 없으면 두 1순위의 평균
                method3["top1_rate"] = round(
                    (method1["top1_rate"] + method2["top1_rate"]) / 2, 4
                )
                method3["top1_score"] = 0

        # ── 종합 상관관계 ──────────────────────────────────────────
        rates_predicted = [m["top1_rate"] for m in [method1, method2, method3] if m["top1_rate"] is not None]
        agreement = 0.0
        final_top1 = None
        methods_aligned = []
        if rates_predicted:
            # 각 방법 1순위가 ±0.2% 이내면 합치 (agreement) — 단순 카운트 기반 점수
            from collections import Counter
            rounded = [round(r, 1) for r in rates_predicted]
            counter = Counter(rounded)
            most_common, freq = counter.most_common(1)[0]
            agreement = round(freq / len(rates_predicted), 2)
            # 정렬: 가장 많이 등장한 값을 가진 방법들
            methods_aligned = [
                m["name"] for m in [method1, method2, method3]
                if m["top1_rate"] is not None and round(m["top1_rate"], 1) == most_common
            ]
            # 최종 1순위: 합치된 값들의 평균 (없으면 method1 우선)
            aligned_rates = [
                m["top1_rate"] for m in [method1, method2, method3]
                if m["top1_rate"] is not None and round(m["top1_rate"], 1) == most_common
            ]
            final_top1 = round(sum(aligned_rates) / len(aligned_rates), 4)

        bid_amount = (
            int(ann.base_amount * final_top1 / 100)
            if ann.base_amount and final_top1 else None
        )

        result = {
            "announcement": {
                "id": ann.id, "title": ann.title, "category": ann.category,
                "ordering_org_name": ann.ordering_org_name,
                "base_amount": ann.base_amount,
            },
            "params": {
                "period_months": period_months,
                "category_filter": category_filter,
                "bucket_mode": bucket_mode,
                "detail_rule": detail_rule,
                "rate_range_start": rate_range_start,
                "rate_range_end": rate_range_end,
            },
            "methods": [method1, method2, method3],
            "correlation": {
                "agreement": agreement,         # 0.0 ~ 1.0
                "final_top1": final_top1,
                "predicted_bid_amount": bid_amount,
                "methods_aligned": methods_aligned,
                # 신뢰도: 1) 데이터 표본 크기 2) 합치도 3) 표준편차 + 동종성 종합
                "confidence": _compute_confidence(rates_m1, agreement, len(methods_aligned)),
                "sample_size": len(rates_m1),
                "raw_sample_size": len(raw_rates),
                "outliers_removed": outliers_removed,
                "homogeneity": homogeneity,
                "std_deviation": (round(statistics.stdev(rates_m1), 4)
                                  if len(rates_m1) > 1 else None),
                # 신뢰구간 (95%) — final_top1 ± margin
                "confidence_interval": (lambda ci: {
                    "mean": ci[0], "lower": ci[1], "upper": ci[2], "margin": ci[3],
                })(_confidence_interval(rates_m1, confidence=0.95)),
            },
        }

        # ── 앙상블 + 모멘텀 보정 ──────────────────────────────────
        # 각 방법의 표본 크기를 가중치로 사용 (큰 표본 = 높은 신뢰)
        ensemble = _ensemble_predict([
            {"name": "빈도분석", "rate": method1["top1_rate"], "weight": method1["count"]},
            {"name": "갭분석", "rate": method2["top1_rate"], "weight": method2["count"]},
            {"name": "결합분석", "rate": method3["top1_rate"], "weight": max(1, method3["count"])},
        ])

        # 시계열 모멘텀 — 최근 6개월 월별 평균 추세
        from collections import defaultdict
        recent_cutoff = ref_date - timedelta(days=180)
        monthly_buckets = defaultdict(list)
        for s in raw_samples:
            if s[1] and s[1] >= recent_cutoff:
                monthly_buckets[s[1].strftime("%Y-%m")].append(s[0])
        monthly_series = [
            {"period": k, "avg_rate": sum(v) / len(v), "count": len(v)}
            for k, v in sorted(monthly_buckets.items())
        ]
        momentum = _trend_momentum(monthly_series)

        # 모멘텀 보정 — slope 의 30%만 반영 (과보정 방지)
        ensemble_corrected = ensemble.get("final_rate")
        if ensemble_corrected is not None and momentum.get("slope") is not None:
            correction = momentum["slope"] * 0.3
            ensemble_corrected = round(ensemble_corrected + correction, 4)

        # ── Bayesian Shrinkage (소표본 발주처 보정) ────────────────
        same_org_rates = [s[0] for s in raw_samples if s[2] == ann.ordering_org_name]
        bayesian = _bayesian_shrinkage(same_org_rates, raw_rates, prior_strength=10)

        # ── 이상 탐지 (대상 공고 기초금액 vs 동종 공고) ─────────────
        anomaly = {"is_anomaly": False}
        if ann.base_amount and ann.base_amount > 0:
            peer_q = db.query(BidAnnouncement.base_amount).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.base_amount.isnot(None),
                BidAnnouncement.base_amount > 0,
                BidAnnouncement.announced_at >= cutoff,
            )
            peer_amounts = [math.log(p[0]) for p in peer_q.all() if p[0]]
            if peer_amounts:
                anomaly = _detect_anomaly(math.log(ann.base_amount), peer_amounts, z_threshold=2.0)

        result["ensemble"] = {
            **ensemble,
            "momentum": momentum,
            "final_rate_corrected": ensemble_corrected,
            "predicted_bid_amount": (
                int(ann.base_amount * ensemble_corrected / 100)
                if ann.base_amount and ensemble_corrected else None
            ),
        }
        result["bayesian_shrinkage"] = bayesian
        result["anomaly"] = anomaly
        _cache_set(cache_key, result)
        if current_user:
            save_query_history(
                current_user.id, announcement_id, "correlation",
                parameters=result["params"],
                result_summary={
                    "final_top1": final_top1,
                    "agreement": agreement,
                    "methods_aligned_count": len(methods_aligned),
                },
            )
        return result
    finally:
        db.close()


# ─── API: 사용자 예측 설정 (app/routes/users 로 이전 — F4) ──────────
from app.routes.users import router as _users_router  # noqa: E402
app.include_router(_users_router)


# ─── API: 분석 결과 엑셀 export (스펙 §3.8/3.9) ──────────────────────────

@app.get("/api/v1/analysis/export/{export_type}")
@rate_limit("10/minute")
def analysis_export_xlsx(
    request: Request,
    export_type: str,
    announcement_id: str = Query(...),
    period_months: int = Query(6, ge=1, le=36),
    category_filter: str = Query("same"),
    bucket_mode: str = Query("A"),
    detail_rule: str = Query("max_gap"),
    rate_range_start: float = Query(99.0),
    rate_range_end: float = Query(101.0),
    current_user: User = Depends(require_auth),
):
    """엑셀(.xlsx) 분석 결과 다운로드.

    export_type: buckets / company / correlation / bid_list
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    import io

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

        wb = Workbook()
        ws = wb.active
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="0066CC", end_color="0066CC", fill_type="solid")
        center = Alignment(horizontal="center", vertical="center")

        def write_header(row_idx, headers):
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=row_idx, column=col, value=h)
                c.font = header_font
                c.fill = header_fill
                c.alignment = center

        # ── 공고 메타 ────────────────────────────────────────
        ws.title = export_type[:31]
        ws.cell(row=1, column=1, value="공고명").font = Font(bold=True)
        ws.cell(row=1, column=2, value=ann.title)
        ws.cell(row=2, column=1, value="공고번호").font = Font(bold=True)
        ws.cell(row=2, column=2, value=ann.bid_number)
        ws.cell(row=3, column=1, value="발주기관").font = Font(bold=True)
        ws.cell(row=3, column=2, value=ann.ordering_org_name)
        ws.cell(row=4, column=1, value="기초금액").font = Font(bold=True)
        ws.cell(row=4, column=2, value=ann.base_amount)

        if export_type == "buckets":
            # 3가지 모드 결과
            ref_date = ann.announced_at or datetime.now()
            cutoff = ref_date - timedelta(days=period_months * 30)
            q = db.query(BidResult.assessment_rate).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at >= cutoff,
                BidAnnouncement.category == ann.category,
            )
            rates = [r[0] for r in q.all() if r[0] is not None]
            hist = _build_rate_histogram(rates)
            write_header(6, ["모드", "순위", "사정률(%)", "방향", "점수", "구간시작", "구간끝"])
            row = 7
            for mode in ["A", "B", "C"]:
                for b in _compute_rate_buckets(hist, mode=mode, top_n=5):
                    ws.cell(row=row, column=1, value=mode)
                    ws.cell(row=row, column=2, value=b["rank"])
                    ws.cell(row=row, column=3, value=b["rate"])
                    ws.cell(row=row, column=4, value=b["side"])
                    ws.cell(row=row, column=5, value=b["score"])
                    ws.cell(row=row, column=6, value=b["range_start"])
                    ws.cell(row=row, column=7, value=b["range_end"])
                    row += 1

        elif export_type == "company":
            # 업체 투찰 + 갭
            ref_date = ann.announced_at or datetime.now()
            cutoff = ref_date - timedelta(days=period_months * 30)
            recs = db.query(CompanyBidRecord, BidAnnouncement).join(
                BidAnnouncement, CompanyBidRecord.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.announced_at >= cutoff,
                CompanyBidRecord.bid_rate >= rate_range_start,
                CompanyBidRecord.bid_rate <= rate_range_end,
            ).order_by(CompanyBidRecord.bid_rate).all()
            write_header(6, ["업체명", "투찰률(%)", "투찰금액", "순위", "1순위", "공고명", "발주기관"])
            for i, (r, a) in enumerate(recs, start=7):
                ws.cell(row=i, column=1, value=r.company_name)
                ws.cell(row=i, column=2, value=round(r.bid_rate, 4))
                ws.cell(row=i, column=3, value=r.bid_amount)
                ws.cell(row=i, column=4, value=r.ranking)
                ws.cell(row=i, column=5, value="O" if r.is_first_place else "")
                ws.cell(row=i, column=6, value=a.title)
                ws.cell(row=i, column=7, value=a.ordering_org_name)

        elif export_type == "correlation":
            # 3가지 방법 + 종합
            corr = analysis_correlation(
                request, announcement_id, period_months=period_months,
                category_filter=category_filter, bucket_mode=bucket_mode,
                detail_rule=detail_rule, rate_range_start=rate_range_start,
                rate_range_end=rate_range_end, current_user=current_user,
            )
            write_header(6, ["분석 방법", "1순위 사정률(%)", "점수", "데이터 수", "합치 여부"])
            aligned_set = set(corr.get("correlation", {}).get("methods_aligned", []))
            for i, m in enumerate(corr.get("methods", []), start=7):
                ws.cell(row=i, column=1, value=m["name"])
                ws.cell(row=i, column=2, value=m["top1_rate"])
                ws.cell(row=i, column=3, value=m["top1_score"])
                ws.cell(row=i, column=4, value=m["count"])
                ws.cell(row=i, column=5, value="합치" if m["name"] in aligned_set else "")
            # 종합 결과
            row = 7 + len(corr.get("methods", [])) + 1
            ws.cell(row=row, column=1, value="종합 1순위").font = Font(bold=True, color="DC2626")
            ws.cell(row=row, column=2, value=corr.get("correlation", {}).get("final_top1"))
            ws.cell(row=row, column=3, value=f"합치도 {round((corr.get('correlation', {}).get('agreement') or 0) * 100)}%")
            ws.cell(row=row, column=4, value=corr.get("correlation", {}).get("predicted_bid_amount"))

        elif export_type == "bid_list":
            # 투찰 리스트 (최근 100건 — 카테고리 동일)
            ref_date = ann.announced_at or datetime.now()
            cutoff = ref_date - timedelta(days=period_months * 30)
            anns = db.query(BidAnnouncement).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.announced_at >= cutoff,
            ).order_by(BidAnnouncement.announced_at.desc()).limit(100).all()
            write_header(6, ["공고일", "공고번호", "공고명", "발주기관", "기초금액", "예상 투찰률(%)", "예상 투찰금액"])
            # 종합 1순위 사용
            corr = analysis_correlation(
                request, announcement_id, period_months=period_months,
                category_filter=category_filter, bucket_mode=bucket_mode,
                detail_rule=detail_rule, rate_range_start=rate_range_start,
                rate_range_end=rate_range_end, current_user=current_user,
            )
            top1 = corr.get("correlation", {}).get("final_top1") or 100
            for i, a in enumerate(anns, start=7):
                ws.cell(row=i, column=1, value=a.announced_at.strftime("%Y-%m-%d") if a.announced_at else "")
                ws.cell(row=i, column=2, value=a.bid_number)
                ws.cell(row=i, column=3, value=a.title)
                ws.cell(row=i, column=4, value=a.ordering_org_name)
                ws.cell(row=i, column=5, value=a.base_amount)
                ws.cell(row=i, column=6, value=top1)
                ws.cell(row=i, column=7, value=int((a.base_amount or 0) * top1 / 100))
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 export_type")

        # 컬럼 너비 자동
        for col_letter in ["A", "B", "C", "D", "E", "F", "G"]:
            ws.column_dimensions[col_letter].width = 18

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f"bidstar_{export_type}_{ann.bid_number}.xlsx"
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        db.close()


# ─── API: 회귀 분석 — 다중 선형 회귀로 사정률 예측 ─────────────────────────

@app.get("/api/v1/analysis/regression/{announcement_id}")
@rate_limit("30/minute")
def analysis_regression(
    request: Request,
    announcement_id: str,
    period_months: int = Query(12, ge=1, le=36),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    current_user: User = Depends(require_auth),
):
    """기초금액·공사여부·지역·경과일수를 독립변수로 한 사정률 다중 선형 회귀.

    Returns:
      - predicted_rate: 모델이 예측한 사정률
      - r_squared: 모델 설명력 (0~1)
      - top_features: 영향도 큰 5개 변수 (계수)
      - n: 학습 표본 수
    """
    cache_key = _cache_key("regression", announcement_id, period_months, category_filter)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        # 표본 수집 — 사정률 + feature 동시
        q = db.query(
            BidResult.assessment_rate,
            BidResult.opened_at,
            BidAnnouncement.base_amount,
            BidAnnouncement.category,
            BidAnnouncement.region,
            BidAnnouncement.industry_code,
            BidAnnouncement.ordering_org_type,
        ).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        q = _apply_category_filter(q, category_filter, ann)

        samples = []
        for row in q.all():
            if not row[0]:
                continue
            days_old = (ref_date - row[1]).days if row[1] else 0
            samples.append({
                "rate": row[0],
                "base_amount": row[2] or 0,
                "category": row[3],
                "region": row[4],
                "industry": row[5],
                "org_type": row[6],
                "days_old": days_old,
            })

        target = {
            "base_amount": ann.base_amount or 0,
            "category": ann.category,
            "region": ann.region,
            "industry": ann.industry_code,
            "org_type": ann.ordering_org_type,
            "days_old": 0,
        }

        result = _ols_regression(samples, target)
        result["announcement"] = {
            "id": ann.id, "title": ann.title,
            "base_amount": ann.base_amount, "region": ann.region,
            "category": ann.category,
        }
        result["params"] = {"period_months": period_months, "category_filter": category_filter}
        if result.get("predicted_rate") and ann.base_amount:
            result["predicted_bid_amount"] = int(ann.base_amount * result["predicted_rate"] / 100)

        _cache_set(cache_key, result)
        if current_user:
            save_query_history(
                current_user.id, announcement_id, "regression",
                parameters=result["params"],
                result_summary={"predicted_rate": result.get("predicted_rate"),
                                "r_squared": result.get("r_squared"),
                                "n": result.get("n")},
            )
        return result
    finally:
        db.close()


# ─── API: 시계열 추세 — 월별/분기별 사정률 평균 ─────────────────────────────

@app.get("/api/v1/analysis/trend/{announcement_id}")
@rate_limit("60/minute")
def analysis_trend(
    request: Request,
    announcement_id: str,
    granularity: str = Query("month", pattern="^(month|quarter|year)$"),
    period_months: int = Query(24, ge=3, le=84),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    current_user: User = Depends(require_auth),
):
    """월/분기/연 단위 평균 사정률 추이 (시계열 차트용)."""
    cache_key = _cache_key("trend", announcement_id, granularity, period_months, category_filter)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}
        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        q = db.query(BidResult.assessment_rate, BidResult.opened_at).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        q = _apply_category_filter(q, category_filter, ann)

        # 그룹핑 키 생성
        from collections import defaultdict
        buckets = defaultdict(list)
        for rate, dt in q.all():
            if not dt or rate is None:
                continue
            if granularity == "month":
                key = dt.strftime("%Y-%m")
            elif granularity == "quarter":
                key = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
            else:
                key = str(dt.year)
            buckets[key].append(rate)

        series = []
        for key in sorted(buckets.keys()):
            rates = buckets[key]
            series.append({
                "period": key,
                "avg_rate": round(sum(rates) / len(rates), 4),
                "min_rate": round(min(rates), 4),
                "max_rate": round(max(rates), 4),
                "count": len(rates),
            })

        result = {
            "announcement": {"id": ann.id, "title": ann.title, "category": ann.category},
            "params": {"granularity": granularity, "period_months": period_months,
                       "category_filter": category_filter},
            "series": series,
        }
        _cache_set(cache_key, result)
        return result
    finally:
        db.close()


# ─── API: 백테스트 — 과거 공고 대상 알고리즘 정확도 측정 ──────────────────

@app.get("/api/v1/analysis/backtest/{announcement_id}")
@rate_limit("10/minute")
def analysis_backtest(
    request: Request,
    announcement_id: str,
    sample_size: int = Query(30, ge=5, le=100),
    period_months: int = Query(24, ge=6, le=60),
    bucket_mode: str = Query("A", pattern="^(A|B|C)$"),
    current_user: User = Depends(require_auth),
):
    """A/B 백테스트 — 과거 공고 N건에 대해 알고리즘 예측 vs 실제 사정률 비교.

    각 과거 공고마다:
      1) 그 공고가 발생한 시점의 데이터로만 (이전 데이터) 빈도 분석
      2) 알고리즘 1순위 예측 사정률 산출
      3) 실제 사정률과 절대 오차 계산
    Returns:
      - mae: 평균 절대 오차 (Mean Absolute Error)
      - mape: 평균 절대 비율 오차 (%)
      - within_05: ±0.5% 이내 적중률
      - within_10: ±1.0% 이내 적중률
      - samples: 샘플별 (실제, 예측, 오차) 리스트
    """
    cache_key = _cache_key("backtest", announcement_id, sample_size, period_months, bucket_mode)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        # 과거 N건의 동일 카테고리 결과 (대상 공고 직전까지)
        past_results = (
            db.query(BidResult, BidAnnouncement)
            .join(BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id)
            .filter(
                BidAnnouncement.category == ann.category,
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at < ref_date,
                BidResult.opened_at >= ref_date - timedelta(days=period_months * 30),
            )
            .order_by(BidResult.opened_at.desc())
            .limit(sample_size * 3)  # 후보 풀
            .all()
        )

        # 무작위 sample_size 건 추출 (재현성 위해 고정 seed)
        import random as _rand
        _rand.seed(42)
        if len(past_results) > sample_size:
            past_results = _rand.sample(past_results, sample_size)

        comparisons = []
        for past_res, past_ann in past_results:
            # 그 공고 시점 이전 90일 데이터로만 분석
            train_cutoff = past_ann.announced_at - timedelta(days=1) if past_ann.announced_at else past_res.opened_at
            train_q = db.query(BidResult.assessment_rate).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidResult.assessment_rate.isnot(None),
                BidResult.opened_at < train_cutoff,
                BidResult.opened_at >= train_cutoff - timedelta(days=180),
            )
            train_rates = [r[0] for r in train_q.all() if r[0] is not None]
            if len(train_rates) < 5:
                continue

            # 알고리즘 적용 (IQR + 가중치 없음 — 단순 빈도 모드)
            clean = _remove_outliers_iqr(train_rates)
            hist = _build_rate_histogram(clean)
            buckets = _compute_rate_buckets(hist, mode=bucket_mode, top_n=1)
            if not buckets:
                continue

            predicted = buckets[0]["rate"]
            actual = past_res.assessment_rate
            error = abs(predicted - actual)
            comparisons.append({
                "title": past_ann.title[:40],
                "actual": round(actual, 4),
                "predicted": round(predicted, 4),
                "error": round(error, 4),
                "opened_at": past_res.opened_at.strftime("%Y-%m-%d") if past_res.opened_at else "",
            })

        if not comparisons:
            return {"error": "백테스트 가능한 표본이 부족합니다.",
                    "n": 0, "params": {"sample_size": sample_size}}

        errors = [c["error"] for c in comparisons]
        actuals = [c["actual"] for c in comparisons]
        mae = round(sum(errors) / len(errors), 4)
        mape = round(sum(e / max(0.01, a) for e, a in zip(errors, actuals)) / len(errors) * 100, 4)
        within_05 = round(sum(1 for e in errors if e <= 0.5) / len(errors) * 100, 1)
        within_10 = round(sum(1 for e in errors if e <= 1.0) / len(errors) * 100, 1)

        result = {
            "announcement": {"id": ann.id, "title": ann.title},
            "params": {"sample_size": sample_size, "period_months": period_months,
                       "bucket_mode": bucket_mode},
            "n": len(comparisons),
            "mae": mae,                        # 평균 절대 오차 (사정률 %)
            "mape": mape,                      # 평균 절대 비율 오차 (%)
            "within_05": within_05,            # ±0.5%p 적중률
            "within_10": within_10,            # ±1.0%p 적중률
            "samples": comparisons[:10],       # 상위 10건만 노출 (응답 크기)
        }
        _cache_set(cache_key, result)
        return result
    finally:
        db.close()


# ─── API: 관리자(모델/이상 공고) (app/routes/admin 로 이전 — F4) ──


# ─── API: K-means 공고 클러스터링 ────────────────────────────────────────

@app.get("/api/v1/analysis/clusters")
@rate_limit("10/minute")
def analysis_clusters(
    request: Request,
    period_months: int = Query(12, ge=1, le=36),
    k: int = Query(5, ge=2, le=10),
    category_filter: str = Query("all", pattern="^(all|construction|service)$"),
    current_user: User = Depends(require_auth),
):
    """K-means 자동 군집화 — 기초금액·지역·카테고리 기반 공고 그룹.

    각 군집에 대해 표본 평균 사정률·대표 공고 5건 노출.
    """
    cache_key = _cache_key("clusters", period_months, k, category_filter)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(days=period_months * 30)
        q = db.query(BidAnnouncement, BidResult).join(
            BidResult, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidAnnouncement.base_amount.isnot(None),
            BidAnnouncement.base_amount > 0,
            BidAnnouncement.announced_at >= cutoff,
            BidAnnouncement.category.in_(["공사", "용역"]),
        )
        q = _apply_category_filter(q, category_filter)
        rows = q.limit(2000).all()
        if len(rows) < k * 5:
            return {"clusters": [], "n": len(rows),
                    "reason": f"표본 부족 (k×5={k*5} 필요, 현재 {len(rows)})"}

        # 지역 인코딩 (top 5)
        from collections import Counter as _C
        top_regions = [r for r, _ in _C(a.region for a, _ in rows if a.region).most_common(5)]

        def featurize(a):
            return [
                math.log(max(1, a.base_amount or 1)),
                1.0 if a.category == "공사" else 0.0,
            ] + [1.0 if a.region == r else 0.0 for r in top_regions]

        features = [featurize(a) for a, _ in rows]
        labels, centroids = _kmeans_simple(features, k=k)

        # 군집별 집계
        clusters = []
        for cluster_idx in range(k):
            members = [(a, r, lbl) for (a, r), lbl in zip(rows, labels) if lbl == cluster_idx]
            if not members:
                continue
            rates = [r.assessment_rate for _, r, _ in members if r.assessment_rate]
            amounts = [a.base_amount for a, _, _ in members if a.base_amount]
            cats = _C(a.category for a, _, _ in members)
            regs = _C(a.region for a, _, _ in members if a.region)

            samples = [
                {
                    "id": a.id, "title": a.title[:60],
                    "ordering_org_name": a.ordering_org_name,
                    "base_amount": a.base_amount,
                    "assessment_rate": round(r.assessment_rate, 4) if r.assessment_rate else None,
                    "external_url": get_announcement_url(a),
                }
                for a, r, _ in members[:5]
            ]
            clusters.append({
                "cluster_id": cluster_idx,
                "size": len(members),
                "avg_assessment_rate": round(sum(rates) / len(rates), 4) if rates else None,
                "avg_base_amount": int(sum(amounts) / len(amounts)) if amounts else None,
                "category_dist": dict(cats),
                "top_regions": dict(regs.most_common(3)),
                "samples": samples,
            })
        clusters.sort(key=lambda x: -x["size"])

        result = {
            "params": {"period_months": period_months, "k": k, "category_filter": category_filter},
            "n_total": len(rows),
            "clusters": clusters,
        }
        _cache_set(cache_key, result)
        return result
    finally:
        db.close()


# ─── API: K-NN 유사 공고 추천 ──────────────────────────────────────────

@app.get("/api/v1/analysis/similar/{announcement_id}")
@rate_limit("30/minute")
def analysis_similar(
    request: Request,
    announcement_id: str,
    k: int = Query(5, ge=1, le=20),
    period_months: int = Query(12, ge=1, le=36),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    current_user: User = Depends(require_auth),
):
    """대상 공고와 가장 유사한 과거 공고 K건 추천 (사정률 포함).

    유사도 = 1 / (1 + 가중 거리)
    거리 = 0.4×|log(기초금액)차이| + 0.3×지역 불일치 + 0.2×업종 불일치 + 0.1×경과/365
    """
    cache_key = _cache_key("similar", announcement_id, k, period_months, category_filter)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        q = db.query(BidAnnouncement, BidResult).join(
            BidResult, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidAnnouncement.announced_at >= cutoff,
            BidAnnouncement.id != announcement_id,
        )
        q = _apply_category_filter(q, category_filter, ann)

        candidates = []
        for c_ann, c_res in q.limit(2000).all():  # 후보 풀 제한
            days_old = (ref_date - c_ann.announced_at).days if c_ann.announced_at else 0
            candidates.append({
                "id": c_ann.id,
                "bid_number": c_ann.bid_number,
                "title": c_ann.title,
                "category": c_ann.category,
                "ordering_org_name": c_ann.ordering_org_name,
                "region": c_ann.region,
                "industry": c_ann.industry_code,
                "base_amount": c_ann.base_amount,
                "assessment_rate": round(c_res.assessment_rate, 4) if c_res.assessment_rate else None,
                "days_old": days_old,
                "external_url": get_announcement_url(c_ann),
            })

        target = {
            "base_amount": ann.base_amount,
            "region": ann.region,
            "industry": ann.industry_code,
            "category": ann.category,
        }
        similar = _knn_similar_announcements(target, candidates, k=k)

        # 유사 공고 평균 사정률
        rates = [s["assessment_rate"] for s in similar if s.get("assessment_rate") is not None]
        avg_similar_rate = round(sum(rates) / len(rates), 4) if rates else None
        predicted_amount = (
            int(ann.base_amount * avg_similar_rate / 100)
            if ann.base_amount and avg_similar_rate else None
        )

        result = {
            "announcement": {"id": ann.id, "title": ann.title, "category": ann.category,
                             "base_amount": ann.base_amount, "region": ann.region},
            "params": {"k": k, "period_months": period_months, "category_filter": category_filter},
            "similar": similar,
            "avg_similar_rate": avg_similar_rate,
            "predicted_bid_amount": predicted_amount,
            "candidate_pool_size": len(candidates),
        }
        _cache_set(cache_key, result)
        return result
    finally:
        db.close()


# ─── API: Walk-forward Validation (시계열 rolling 정확도) ────────────

@app.get("/api/v1/analysis/walk-forward/{announcement_id}")
@rate_limit("10/minute")
def analysis_walk_forward(
    request: Request,
    announcement_id: str,
    period_months: int = Query(24, ge=6, le=60),
    window_days: int = Query(90, ge=30, le=365),
    stride_days: int = Query(30, ge=7, le=90),
    category_filter: str = Query("same", pattern="^(same|all|construction|service|industry)$"),
    current_user: User = Depends(require_auth),
):
    """Walk-forward Validation — 시간순 rolling window 백테스트.

    각 시점마다 [t-window, t] 데이터로 학습 → 다음 stride 예측 → 실제값 비교.
    백테스트보다 robust 한 시계열 정확도 평가.
    """
    cache_key = _cache_key("walkfwd", announcement_id, period_months, window_days, stride_days, category_filter)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)

        q = db.query(BidResult.assessment_rate, BidResult.opened_at).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        q = _apply_category_filter(q, category_filter, ann)

        samples = [(r[0], r[1]) for r in q.all() if r[0] is not None and r[1] is not None]

        result = _walk_forward_validate(samples, window_days=window_days, stride_days=stride_days)
        result["announcement"] = {"id": ann.id, "title": ann.title, "category": ann.category}
        result["params"] = {
            "period_months": period_months, "window_days": window_days,
            "stride_days": stride_days, "category_filter": category_filter,
        }

        _cache_set(cache_key, result)
        return result
    finally:
        db.close()


# ─── API: 밀어내기식 검토 (Sliding Window Backtesting) ────────────────────

@app.get("/api/v1/analysis/sliding-review/{announcement_id}")
@rate_limit("30/minute")
def analysis_sliding_review(
    request: Request,
    announcement_id: str,
    window_size: str = Query("3m"),
    confirmed_rate: float = Query(99.5),
    org_scope: str = Query("specific"),
    current_user: User = Depends(require_auth),
):
    """밀어내기식 검토: 윈도우를 이동하며 예측 vs 실제 비교"""
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()

        # 윈도우 크기 → 일수 변환
        window_days_map = {"1d": 1, "5d": 5, "1m": 30, "3m": 90, "6m": 180, "1y": 365}
        w_days = window_days_map.get(window_size, 90)

        # 전체 과거 데이터 가져오기 (최대 7년)
        full_cutoff = ref_date - timedelta(days=2650)
        q = db.query(BidResult, BidAnnouncement).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.assessment_rate.isnot(None),
            BidResult.first_place_rate.isnot(None),
            BidResult.opened_at >= full_cutoff,
            BidResult.opened_at < ref_date,
        )
        if org_scope == "parent" and ann.parent_org_name:
            q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
        elif org_scope == "specific":
            q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

        all_data = q.order_by(BidResult.opened_at).all()
        if not all_data:
            # 폴백: 동일 카테고리+지역으로 범위 확대
            all_data = db.query(BidResult, BidAnnouncement).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.region == ann.region,
                BidResult.assessment_rate.isnot(None),
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= full_cutoff,
                BidResult.opened_at < ref_date,
            ).order_by(BidResult.opened_at).all()

        # 슬라이딩 윈도우: 각 시점에서 window 크기만큼의 데이터로 예측
        timeline = []
        match_count = 0
        step_days = max(w_days // 3, 1)  # 스텝 크기

        current_date = full_cutoff + timedelta(days=w_days)
        while current_date < ref_date:
            window_start = current_date - timedelta(days=w_days)
            window_data = [
                (r, a) for r, a in all_data
                if r.opened_at and window_start <= r.opened_at < current_date
            ]

            if len(window_data) >= 3:
                # 윈도우 내 사정률 평균/중앙값으로 예측
                window_rates = [r.assessment_rate for r, a in window_data]
                predicted_rate = round(statistics.median(window_rates), 4)

                # 해당 시점 이후 가장 가까운 실제 결과 찾기
                next_results = [
                    (r, a) for r, a in all_data
                    if r.opened_at and current_date <= r.opened_at < current_date + timedelta(days=step_days)
                ]

                for res, res_ann in next_results:
                    diff = abs(confirmed_rate - res.assessment_rate)
                    actual_diff = abs(res.first_place_rate - res.assessment_rate)
                    is_first = diff <= actual_diff + 0.02

                    if is_first:
                        match_count += 1

                    timeline.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "window_start": window_start.strftime("%Y-%m-%d"),
                        "predicted_rate": predicted_rate,
                        "actual_rate": round(res.assessment_rate, 4),
                        "first_place_rate": round(res.first_place_rate, 4),
                        "confirmed_rate": round(confirmed_rate, 4),
                        "was_first_place": is_first,
                        "diff": round(diff, 4),
                        "data_count": len(window_data),
                    })

            current_date += timedelta(days=step_days)

        total = len(timeline)
        hit_rate = round(match_count / total * 100, 1) if total > 0 else 0

    finally:
        db.close()
    result = {
        "timeline": timeline[-60:],  # 최근 60개 포인트
        "summary": {
            "total_points": total,
            "match_count": match_count,
            "hit_rate": hit_rate,
            "window_size": window_size,
            "window_days": w_days,
        },
        "announcement": {
            "id": ann.id, "title": ann.title,
            "org": ann.ordering_org_name,
        },
    }
    if current_user:
        save_query_history(
            current_user.id, announcement_id, "sliding-review",
            parameters={"window_size": window_size, "confirmed_rate": confirmed_rate,
                        "org_scope": org_scope},
            result_summary={"hit_rate": hit_rate, "total_points": total,
                            "match_count": match_count},
        )
    return result


# ─── API: 연도별 낙찰확률 검증 ──────────────────────────────────────────

@app.get("/api/v1/analysis/yearly-validation/{announcement_id}")
@rate_limit("30/minute")
def analysis_yearly_validation(
    request: Request,
    announcement_id: str,
    confirmed_rate: float = Query(99.5),
    org_scope: str = Query("specific"),
    current_user: User = Depends(require_auth),
):
    """연도별(2020~2026) 낙찰확률 검증"""
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        years_result = []
        for year in range(2020, 2027):
            year_start = datetime(year, 1, 1)
            year_end = datetime(year, 12, 31)
            prev_cutoff = datetime(year - 1, 1, 1)

            # 해당 연도 실제 낙찰 데이터
            q = db.query(BidResult, BidAnnouncement).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidResult.assessment_rate.isnot(None),
                BidResult.first_place_rate.isnot(None),
                BidResult.opened_at >= year_start,
                BidResult.opened_at <= year_end,
            )
            if org_scope == "parent" and ann.parent_org_name:
                q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
            elif org_scope == "specific":
                q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

            year_data = q.all()
            if not year_data:
                continue

            match_count = 0
            cases = []
            for res, past_ann in year_data:
                diff = abs(confirmed_rate - res.assessment_rate)
                actual_diff = abs(res.first_place_rate - res.assessment_rate)
                is_match = diff <= actual_diff + 0.02

                if is_match:
                    match_count += 1

                cases.append({
                    "title": past_ann.title,
                    "org": past_ann.ordering_org_name,
                    "predicted_rate": round(confirmed_rate, 4),
                    "actual_rate": round(res.assessment_rate, 4),
                    "first_place_rate": round(res.first_place_rate, 4),
                    "is_match": is_match,
                    "date": res.opened_at.strftime("%Y-%m-%d") if res.opened_at else "",
                })

            total = len(cases)
            years_result.append({
                "year": year,
                "total": total,
                "first_place_count": match_count,
                "match_rate": round(match_count / total * 100, 1) if total > 0 else 0,
                "cases": cases[:20],
            })

    finally:
        db.close()
    result = {
        "years": years_result,
        "confirmed_rate": round(confirmed_rate, 4),
        "announcement": {
            "id": ann.id, "title": ann.title,
            "org": ann.ordering_org_name,
        },
    }
    if current_user:
        avg_match = round(sum(y["match_rate"] for y in years_result) / len(years_result), 1) if years_result else 0
        save_query_history(
            current_user.id, announcement_id, "yearly-validation",
            parameters={"confirmed_rate": confirmed_rate, "org_scope": org_scope},
            result_summary={"avg_match_rate": avg_match, "year_count": len(years_result)},
        )
    return result


# ─── API: 추첨예가 빈도수 분석 ────────────────────────────────────────────

@app.get("/api/v1/analysis/preliminary-frequency/{announcement_id}")
def analysis_preliminary_frequency(
    announcement_id: str,
    period_months: int = Query(12, ge=1, le=24),
    org_scope: str = Query("specific"),
):
    """복수예비가격 15개 번호 중 추첨 빈도 분석"""
    db = SessionLocal()
    try:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
        if not ann:
            db.close()
            return {"error": "공고를 찾을 수 없습니다."}

        ref_date = ann.announced_at or datetime.now()
        cutoff = ref_date - timedelta(days=period_months * 30)
        q = db.query(BidResult).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.selected_price_indices.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        if org_scope == "parent" and ann.parent_org_name:
            q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
        else:
            q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

        results = q.all()
        if not results:
            # 폴백: 같은 카테고리+지역
            q = db.query(BidResult).join(
                BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
            ).filter(
                BidAnnouncement.category == ann.category,
                BidAnnouncement.region == ann.region,
                BidResult.selected_price_indices.isnot(None),
                BidResult.opened_at >= cutoff,
            )
            results = q.all()

        # 15개 번호별 추첨 횟수 집계
        freq = {i: 0 for i in range(1, 16)}
        total_cases = 0
        for res in results:
            try:
                indices = json.loads(res.selected_price_indices) if isinstance(res.selected_price_indices, str) else res.selected_price_indices
                if indices:
                    total_cases += 1
                    for idx in indices:
                        if 1 <= idx <= 15:
                            freq[idx] += 1
            except (json.JSONDecodeError, TypeError):
                continue

        bins = [{"number": i, "count": freq[i], "percentage": round(freq[i] / total_cases * 100, 1) if total_cases > 0 else 0} for i in range(1, 16)]
        max_count = max(b["count"] for b in bins) if bins else 0
        peak_numbers = [b["number"] for b in bins if b["count"] == max_count and max_count > 0]

    finally:
        db.close()
    return {
        "bins": bins,
        "total_cases": total_cases,
        "peak_numbers": peak_numbers,
        "selected_per_case": 4,
    }


# ─── API: 통계·예측(호환) (app/routes/stats 로 이전 — F4) ──────────
from app.routes.stats import router as _stats_router  # noqa: E402
app.include_router(_stats_router)


# ─── API: 관리자(대시보드/수집/스케줄) (app/routes/admin 로 이전 — F4) ──
# G2B 동기화 헬퍼는 app/services/sync 에서 정의 (F3)
from app.services.sync import (  # noqa: E402, F401
    _parse_date,
    _extract_g2b_items,
    _detect_defense,
    get_announcement_url,
    build_g2b_url,
    _normalize_item,
    _upsert_announcements,
    _windows_iter,
    _record_sync_error,
    _build_sync_url,
    _build_result_url,
    _normalize_result_item,
    _aggregate_prelim_prices,
    _upsert_results,
    _http_fetch_with_retry,
    _run_sync_for_source,
)
from app.routes.admin import router as _admin_router  # noqa: E402
app.include_router(_admin_router)


# ─── API: 조회 이력 (app/routes/history 로 이전 — F4) ────────────────────
from app.routes.history import router as _history_router  # noqa: E402
app.include_router(_history_router)

# save_query_history 는 다른 분석 핸들러에서도 호출되므로
# app/services/history 에서 재export 하여 backwards-compat 유지.
from app.services.history import save_query_history  # noqa: E402, F401


# ─── API: 데이터 업로드 (app/routes/upload 로 이전 — F4) ──────────
from app.routes.upload import router as _upload_router  # noqa: E402
app.include_router(_upload_router)


# ─── 프론트엔드 서빙 ──────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


# ─── 헬스체크 + 메트릭 ───────────────────────────────────────────
@app.get("/healthz", tags=["운영"])
def healthz():
    """컨테이너 헬스체크 — DB 연결 + 스케줄러 상태"""
    ok = True
    checks = {}
    try:
        db = SessionLocal()
        try:
            db.query(User).limit(1).all()
        finally:
            db.close()
        checks["db"] = "ok"
    except Exception as e:
        ok = False
        checks["db"] = f"error: {str(e)[:80]}"

    checks["scheduler"] = "running" if (_scheduler is not None) else "stopped"
    checks["env"] = _RUNTIME_ENV
    status_code = 200 if ok else 503
    from starlette.responses import JSONResponse as _JR
    return _JR({"status": "ok" if ok else "degraded", "checks": checks}, status_code=status_code)


@app.get("/metrics", tags=["운영"])
def metrics():
    """경량 운영 메트릭 — Prometheus 파싱 호환 형식.

    외부 노출 전에 인증/ACL 제어 필요 시 reverse-proxy에서 제한할 것.
    """
    db = SessionLocal()
    lines: list[str] = []

    def _m(name: str, value, help_text: str, mtype: str = "gauge"):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {mtype}")
        lines.append(f"{name} {value}")

    try:
        _m("bid_announcements_total", db.query(BidAnnouncement).count(),
           "등록된 공고 수")
        _m("bid_results_total", db.query(BidResult).count(),
           "낙찰 결과 수")
        _m("users_total", db.query(User).count(),
           "가입 사용자 수")
        _m("users_active_total", db.query(User).filter(User.is_active == True).count(),  # noqa: E712
           "활성 사용자 수")
        _m("sync_success_total",
           db.query(DataSyncLog).filter(DataSyncLog.status == "success").count(),
           "누적 성공 수집 건수", "counter")
        _m("sync_failed_total",
           db.query(DataSyncLog).filter(DataSyncLog.status == "failed").count(),
           "누적 실패 수집 건수", "counter")
        _m("query_history_total", db.query(QueryHistory).count(),
           "누적 분석 조회 수", "counter")
        _m("upload_logs_total", db.query(UploadLog).count(),
           "누적 업로드 건수", "counter")
        # 캐시/스케줄러 상태 (F3: 캐시 lock/store 가 app.services.cache 로 이동)
        from app.services.cache import _cache_lock as _cl, _cache_store as _cs  # noqa: E402
        with _cl:
            cache_size = len(_cs)
        _m("analysis_cache_entries", cache_size, "분석 캐시 엔트리 수")
        _m("scheduler_running", 1 if _scheduler is not None else 0,
           "스케줄러 실행 여부 (1=running)")
    finally:
        db.close()

    from starlette.responses import Response as _Resp
    return _Resp("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/proposal")
def serve_proposal():
    return FileResponse(os.path.join(DOCS_DIR, "기술제안서.html"))


# SPA catchall — path 기반 라우팅(/admin, /announcements 등) 새로고침/북마크 지원
# API/메타 prefix 는 흡수하지 않도록 화이트리스트 명시.
_API_PREFIXES = ("api/", "docs", "redoc", "openapi", "metrics", "healthz", "static")


@app.get("/{full_path:path}")
def spa_catchall(full_path: str):
    if not full_path or full_path.startswith(_API_PREFIXES):
        raise HTTPException(status_code=404)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ─── 시작 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(engine)
    # SKIP_SEED=true 면 시드 데이터 자동 생성 비활성화 (운영 모드)
    if os.environ.get("SKIP_SEED", "").lower() not in ("true", "1", "yes"):
        try:
            from seed import seed_database  # lazy import (운영 시 임포트도 안 함)
            seed_database()
        except Exception as e:
            print(f"⚠️ 시드 데이터 생성 중 오류 (무시하고 계속): {e}")
    else:
        logger.info("SKIP_SEED=true — 시드 데이터 생성 건너뜀")
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🚀 서버 시작: http://0.0.0.0:{port}")
    print(f"   API 문서: http://localhost:{port}/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
