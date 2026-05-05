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



# ─── API: 분석 (16개 엔드포인트 → app/routes/analysis 로 이전 — F4) ─
from app.routes.analysis import router as _analysis_router  # noqa: E402
app.include_router(_analysis_router)


# ─── API: 사용자 예측 설정 (app/routes/users 로 이전 — F4) ──────────
from app.routes.users import router as _users_router  # noqa: E402
app.include_router(_users_router)


# ─── API: 관리자(모델/이상 공고) (app/routes/admin 로 이전 — F4) ──


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
