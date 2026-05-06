"""관리자 라우터 — 대시보드/모델 재학습/이상 공고/수집/스케줄/오류.

server.py 의 `/api/v1/admin/*` 핸들러를 APIRouter 로 이전 (MIGRATION.md F4).
스케줄러·NAS 상태 등 server.py 전역 상태에 의존하는 핸들러는
`from server import ...` 로 lazy 위임한다.
"""
from __future__ import annotations

import logging
import math
import os
import statistics
import urllib.error
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.security import require_admin
from app.models import (
    BidAnnouncement,
    BidResult,
    DataSyncLog,
    ModelMetric,
    QueryHistory,
    User,
)
from app.services.sync import (
    _build_sync_url,
    _extract_g2b_items,
    _http_fetch_with_retry,
    _normalize_item,
    _run_sync_for_source,
    get_announcement_url,
)

router = APIRouter(prefix="/api/v1/admin", tags=["관리자"])
logger = logging.getLogger("bid-insight")


def _rate_limit(spec: str):
    from server import rate_limit as _rl
    return _rl(spec)


@router.get("/models/history")
@_rate_limit("30/minute")
def admin_models_history(
    request: Request,
    limit: int = Query(30, ge=1, le=200),
    category: str = Query(None),
    current_user: User = Depends(require_admin),
):
    """모델 재학습 이력 조회 (정확도 추이)"""
    db = SessionLocal()
    try:
        q = db.query(ModelMetric).order_by(ModelMetric.trained_at.desc())
        if category:
            q = q.filter(ModelMetric.category == category)
        items = q.limit(limit).all()
        return {
            "items": [
                {
                    "id": m.id,
                    "trained_at": m.trained_at.isoformat() if m.trained_at else None,
                    "category": m.category,
                    "model_type": m.model_type,
                    "n_samples": m.n_samples,
                    "r_squared": m.r_squared,
                    "residual_std": m.residual_std,
                    "mae": m.mae,
                    "period_days": m.period_days,
                }
                for m in items
            ],
        }
    finally:
        db.close()


@router.post("/models/retrain")
@_rate_limit("5/minute")
def admin_models_retrain_now(request: Request, current_user: User = Depends(require_admin)):
    """수동 재학습 트리거 (스케줄 외 즉시 실행)"""
    from server import _scheduled_model_retrain
    _scheduled_model_retrain()
    return {"status": "ok", "message": "재학습 완료"}


@router.get("/anomalies")
@_rate_limit("30/minute")
def admin_anomalies(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    period_days: int = Query(30, ge=1, le=365),
    z_threshold: float = Query(2.0, ge=1.0, le=5.0),
    current_user: User = Depends(require_admin),
):
    """최근 N일 신규 공고 중 동종 분포 이상치(z>threshold) 자동 탐지."""
    db = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=period_days)
        recent = db.query(BidAnnouncement).filter(
            BidAnnouncement.announced_at >= since,
            BidAnnouncement.base_amount.isnot(None),
            BidAnnouncement.base_amount > 0,
            BidAnnouncement.category.in_(["공사", "용역"]),
        ).all()

        # 카테고리별 동종 표본 mean/std 1회만 계산 (성능 최적화)
        peer_stats = {}
        for cat in ("공사", "용역"):
            peers_q = db.query(BidAnnouncement.base_amount).filter(
                BidAnnouncement.category == cat,
                BidAnnouncement.base_amount.isnot(None),
                BidAnnouncement.base_amount > 0,
                BidAnnouncement.announced_at >= since - timedelta(days=180),
            )
            logs = [math.log(p[0]) for p in peers_q.all() if p[0]]
            if len(logs) >= 30:
                mean = sum(logs) / len(logs)
                std = statistics.stdev(logs)
                peer_stats[cat] = (mean, std, len(logs))

        anomalies = []
        for a in recent:
            stats_t = peer_stats.get(a.category)
            if not stats_t:
                continue
            mean, std, n = stats_t
            if std <= 0:
                continue
            log_amount = math.log(a.base_amount)
            z = (log_amount - mean) / std
            abs_z = abs(z)
            if abs_z > z_threshold:
                severity = "high" if abs_z > z_threshold * 1.5 else "medium"
                res = {"is_anomaly": True, "z_score": round(z, 3), "abs_z": round(abs_z, 3),
                       "peer_mean": round(mean, 4), "peer_std": round(std, 4),
                       "severity": severity}
            else:
                res = {"is_anomaly": False}
            if res.get("is_anomaly"):
                anomalies.append({
                    "id": a.id,
                    "bid_number": a.bid_number,
                    "title": a.title,
                    "ordering_org_name": a.ordering_org_name,
                    "category": a.category,
                    "base_amount": a.base_amount,
                    "announced_at": a.announced_at.isoformat() if a.announced_at else None,
                    "z_score": res.get("z_score"),
                    "abs_z": res.get("abs_z"),
                    "severity": res.get("severity"),
                    "external_url": get_announcement_url(a),
                })
        anomalies.sort(key=lambda x: -x["abs_z"])
        return {
            "items": anomalies[:limit],
            "total_scanned": len(recent),
            "params": {"period_days": period_days, "z_threshold": z_threshold},
        }
    finally:
        db.close()


@router.get("/dashboard")
def admin_dashboard(current_user: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712
        total_ann = db.query(BidAnnouncement).count()
        total_res = db.query(BidResult).count()
        avg_rate = db.query(func.avg(BidResult.assessment_rate)).scalar()
        avg_rate = round(avg_rate, 4) if avg_rate else 0
        rate_with_assessment = db.query(BidResult).filter(
            BidResult.assessment_rate.isnot(None)).count()
        matching_rate = round(rate_with_assessment / total_res * 100, 1) if total_res else 0
        analyzable_ann = db.query(BidResult.announcement_id).distinct().count()
        analyzable_rate = round(analyzable_ann / total_ann * 100, 1) if total_ann else 0

        logs = db.query(DataSyncLog).order_by(DataSyncLog.started_at.desc()).limit(10).all()
        pipelines = []
        seen = set()
        for log in logs:
            key = f"{log.source}_{log.sync_type}"
            if key in seen:
                continue
            seen.add(key)
            pipelines.append({
                "name": f"{log.source} {log.sync_type}",
                "status": log.status,
                "last": log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else "",
                "count": f"{log.records_fetched}건",
            })

        users = db.query(User).order_by(User.query_count.desc()).all()
        user_list = [
            {
                "id": u.id, "email": u.email,
                "joined": u.joined_at.strftime("%Y.%m.%d") if u.joined_at else "",
                "last": u.last_login_at.strftime("%Y-%m-%d") if u.last_login_at else "",
                "queries": u.query_count,
                "is_active": u.is_active if u.is_active is not None else True,
                "role": u.role,
            }
            for u in users
        ]

        g2b_count = db.query(BidAnnouncement).filter(BidAnnouncement.source == "G2B").count()
        d2b_count = db.query(BidAnnouncement).filter(BidAnnouncement.source == "D2B").count()
        upload_count = db.query(BidAnnouncement).filter(BidAnnouncement.source == "UPLOAD").count()

        total_analyses = db.query(QueryHistory).count()

    finally:
        db.close()
    return {
        "total_users": total_users, "active_users": active_users,
        "total_announcements": total_ann, "total_results": total_res,
        "avg_assessment_rate": avg_rate,
        "total_analyses": total_analyses,
        "matching_rate": matching_rate,
        "analyzable_announcements": analyzable_ann,
        "analyzable_rate": analyzable_rate,
        "source_ratio": {"G2B": g2b_count, "D2B": d2b_count, "UPLOAD": upload_count},
        "pipelines": pipelines,
        "users": user_list,
    }


@router.post("/sync")
def trigger_sync(current_user: User = Depends(require_admin)):
    """관리자 수동 수집 — 기본은 G2B만 실행 (국방부 데이터 포함).
    D2B 별도 호출이 필요한 경우 환경변수 ENABLE_D2B_SYNC=true 설정.
    """
    sources = ("G2B", "D2B") if os.environ.get("ENABLE_D2B_SYNC", "").lower() == "true" else ("G2B",)
    results = [_run_sync_for_source(src, trigger="manual") for src in sources]
    total = sum(r["records"] for r in results)
    failed = [r for r in results if r["status"] == "failed"]
    return {
        "message": f"{len(results) - len(failed)}/{len(results)} 소스 수집 완료 (총 {total}건)",
        "records": total,
        "results": results,
        "status": "failed" if failed and not total else "success",
    }


@router.post("/sync/diagnose")
def diagnose_sync(
    source: str = Query("G2B", pattern="^(G2B|D2B)$"),
    rows: int = Query(5, ge=1, le=50),
    current_user: User = Depends(require_admin),
):
    """수집 파이프라인 단계별 진단 — DB 변경 없이 키/네트워크/파싱만 검증"""
    api_key = os.environ.get(f"{source}_API_KEY", "").strip()
    steps: list[dict] = []

    def add(name: str, ok: bool, detail: str = "", **extra):
        steps.append({"step": name, "ok": ok, "detail": detail, **extra})

    if not api_key:
        add("api_key", False, f"{source}_API_KEY 환경변수 미설정")
        return {"source": source, "ok": False, "steps": steps,
                "guide": f"export {source}_API_KEY='발급받은_인증키' 후 재시도"}
    add("api_key", True, f"길이 {len(api_key)}, 마스킹 {api_key[:4]}…{api_key[-4:]}")

    try:
        url = _build_sync_url(source, api_key, rows=rows)
        add("build_url", True, f"길이 {len(url)}자")
    except Exception as e:
        add("build_url", False, str(e))
        return {"source": source, "ok": False, "steps": steps}

    import time as _t
    t0 = _t.perf_counter()
    try:
        payload = _http_fetch_with_retry(url, timeout=15, retries=1)
        elapsed_ms = round((_t.perf_counter() - t0) * 1000, 1)
        add("http_fetch", True, f"{len(payload)}바이트 / {elapsed_ms}ms",
            response_size=len(payload), elapsed_ms=elapsed_ms)
    except urllib.error.HTTPError as e:
        body = (e.read()[:300].decode("utf-8", errors="replace") if e.fp else "")
        add("http_fetch", False, f"HTTP {e.code} {e.reason}", body=body)
        return {"source": source, "ok": False, "steps": steps}
    except Exception as e:
        add("http_fetch", False, f"{type(e).__name__}: {str(e)[:150]}")
        return {"source": source, "ok": False, "steps": steps}

    items = _extract_g2b_items(payload)
    head = payload[:200].decode("utf-8", errors="replace")
    add("extract_items", len(items) > 0,
        f"{len(items)}건 추출 (응답 헤드: {head[:120]})", count=len(items))

    valid = []
    invalid = 0
    for it in items:
        n = _normalize_item(source, it)
        if n:
            valid.append({"bid_number": n["bid_number"], "title": n["title"][:60],
                          "org": n["ordering_org_name"], "amount": n["base_amount"]})
        else:
            invalid += 1
    add("normalize", len(valid) > 0 if items else True,
        f"유효 {len(valid)} / 무효 {invalid}",
        valid_count=len(valid), invalid_count=invalid)

    return {
        "source": source,
        "ok": all(s["ok"] for s in steps),
        "steps": steps,
        "sample_records": valid[:3],
        "note": "이 엔드포인트는 DB를 변경하지 않습니다. 실제 적재는 POST /api/v1/admin/sync 사용.",
    }


@router.get("/nas-status")
def nas_status(current_user: User = Depends(require_admin)):
    """NAS 마운트/용량 확인"""
    from server import NAS_PATH
    from app.core.database import DB_PATH
    nas_exists = os.path.exists(NAS_PATH)
    if nas_exists:
        try:
            stat = os.statvfs(NAS_PATH)
            total_gb = round(stat.f_frsize * stat.f_blocks / (1024 ** 3), 1)
            free_gb = round(stat.f_frsize * stat.f_bavail / (1024 ** 3), 1)
        except OSError as exc:
            logger.warning("NAS 디스크 정보 조회 실패 (%s): %s", NAS_PATH, exc)
            total_gb = 0
            free_gb = 0
    else:
        total_gb = 0
        free_gb = 0
    return {
        "mounted": nas_exists,
        "path": NAS_PATH,
        "total_gb": total_gb,
        "free_gb": free_gb,
        "db_path": DB_PATH,
        "db_size_mb": round(os.path.getsize(DB_PATH) / (1024 * 1024), 1) if os.path.exists(DB_PATH) else 0,
    }


@router.put("/users/{user_id}/status")
def toggle_user_status(user_id: str, current_user: User = Depends(require_admin)):
    """사용자 활성/비활성 토글"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            db.close()
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        if user.id == current_user.id:
            db.close()
            raise HTTPException(status_code=400, detail="자신의 상태는 변경할 수 없습니다.")
        user.is_active = not user.is_active
        db.commit()
        new_status = "활성" if user.is_active else "비활성"
    finally:
        db.close()
    return {"message": f"사용자 상태가 {new_status}(으)로 변경되었습니다.", "is_active": user.is_active}


@router.get("/sync/history")
def sync_history(page: int = 1, page_size: int = 20, current_user: User = Depends(require_admin)):
    """수집 히스토리 목록"""
    db = SessionLocal()
    try:
        q = db.query(DataSyncLog)
        total = q.count()
        items = q.order_by(DataSyncLog.started_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        result = [{
            "id": log.id, "source": log.source, "sync_type": log.sync_type,
            "status": log.status, "records_fetched": log.records_fetched,
            "inserted_count": getattr(log, "inserted_count", 0) or 0,
            "error_message": log.error_message,
            "started_at": log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else None,
            "finished_at": log.finished_at.strftime("%Y-%m-%d %H:%M") if log.finished_at else None,
            "duration_sec": int((log.finished_at - log.started_at).total_seconds()) if log.started_at and log.finished_at else None,
        } for log in items]
    finally:
        db.close()
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@router.get("/sync/progress")
def admin_sync_progress(current_user: User = Depends(require_admin)):
    """현재 진행 중인 수집의 진행률 반환 (Item 1).

    가장 최근 in_progress DataSyncLog 한 건을 돌려준다. 없으면 in_progress=False.
    """
    db = SessionLocal()
    try:
        log = (
            db.query(DataSyncLog)
            .filter(DataSyncLog.status == "in_progress")
            .order_by(DataSyncLog.started_at.desc())
            .first()
        )
        if not log:
            return {"in_progress": False}
        return {
            "in_progress": True,
            "sync_id": log.id,
            "source": log.source,
            "sync_type": log.sync_type,
            "progress_pct": round(log.progress_pct or 0.0, 2),
            "last_page": log.last_page or 0,
            "last_checkpoint": getattr(log, "last_checkpoint", None),
            "last_cursor_date": log.last_cursor_date.strftime("%Y-%m-%d") if log.last_cursor_date else None,
            "records_fetched": log.records_fetched or 0,
            "inserted_count": log.inserted_count or 0,
            "started_at": log.started_at.strftime("%Y-%m-%d %H:%M:%S") if log.started_at else None,
        }
    finally:
        db.close()


@router.post("/sync/{sync_id}/retry")
def retry_sync(sync_id: str, current_user: User = Depends(require_admin)):
    """실패한 수집 건 재시도 — 실 파이프라인 재실행

    Item 1 — last_checkpoint 또는 last_page>0 이면 그 위치 다음부터 chunk-level resume.
    """
    db = SessionLocal()
    resume_id = None
    try:
        log = db.query(DataSyncLog).filter(DataSyncLog.id == sync_id).first()
        if not log:
            db.close()
            raise HTTPException(status_code=404, detail="수집 이력을 찾을 수 없습니다.")
        source = log.source
        # Bug B 수정: last_checkpoint 가 있거나 (백워드 호환) last_page>0 이면 chunk-level resume 활성화
        if getattr(log, "last_checkpoint", None) or (log.last_page or 0) > 0:
            resume_id = sync_id
    finally:
        db.close()
    res = _run_sync_for_source(source, trigger="retry", resume_from_log_id=resume_id)
    return {
        "message": "재시도 완료",
        "status": res["status"],
        "records": res["records"],
        "inserted": res.get("inserted", 0),
        "error_message": res.get("error_message"),
        "new_sync_id": res["sync_id"],
    }


@router.get("/schedule")
def get_schedule(current_user: User = Depends(require_admin)):
    """자동 수집 스케줄 조회 — 다음 실행 시각 포함"""
    from server import _SCHEDULER_AVAILABLE, _scheduler, _schedule_config
    next_run = None
    if _SCHEDULER_AVAILABLE and _scheduler is not None:
        job = _scheduler.get_job("auto_sync")
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    return {**_schedule_config, "scheduler_running": _scheduler is not None, "next_run": next_run}


@router.put("/schedule")
def update_schedule(
    interval: str = Query(...),  # hourly / daily / weekly
    time: str = Query("02:00"),
    enabled: bool = Query(True),
    current_user: User = Depends(require_admin),
):
    """자동 수집 스케줄 설정 — 실 APScheduler 재등록"""
    from server import _SCHEDULER_AVAILABLE, _scheduler, _schedule_config, _apply_schedule_config
    if interval not in ("hourly", "daily", "weekly"):
        raise HTTPException(status_code=400, detail="interval은 hourly/daily/weekly 중 하나여야 합니다.")
    _schedule_config["interval"] = interval
    _schedule_config["time"] = time
    _schedule_config["enabled"] = enabled
    _apply_schedule_config(_schedule_config)
    next_run = None
    if _SCHEDULER_AVAILABLE and _scheduler is not None:
        job = _scheduler.get_job("auto_sync")
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    return {"message": "스케줄이 업데이트되었습니다.", **_schedule_config, "next_run": next_run}


@router.get("/errors")
def get_errors(current_user: User = Depends(require_admin)):
    """오류 모니터링 — 실패한 수집 로그 목록"""
    db = SessionLocal()
    try:
        fail_count = db.query(DataSyncLog).filter(DataSyncLog.status == "failed").count()
        recent_errors = db.query(DataSyncLog).filter(
            DataSyncLog.status == "failed"
        ).order_by(DataSyncLog.started_at.desc()).limit(20).all()
        result = [{
            "id": log.id, "source": log.source, "sync_type": log.sync_type,
            "started_at": log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else None,
            "error_message": log.error_message or f"{log.source} {log.sync_type} 수집 실패",
        } for log in recent_errors]
    finally:
        db.close()
    return {"fail_count": fail_count, "errors": result}
