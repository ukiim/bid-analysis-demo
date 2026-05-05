#!/usr/bin/env python3
"""오래된 공공데이터 보존기간 초과분 정리 스크립트

`announced_at` 기준 N년 초과 BidAnnouncement + 종속 BidResult 를 일괄 삭제한다.
DataSyncLog 도 동일 정책으로 정리.

기본 정책 (사정률 예측 로직 스펙 §3.10):
- 공고/낙찰결과: 10년 (DATA_RETAIN_YEARS=10)
- 수집 로그: 1년 (SYNC_LOG_RETAIN_DAYS=365)

사용법:
    python3 scripts/purge_old_data.py                       # 기본값 (10년/365일)
    python3 scripts/purge_old_data.py --retain-years 3      # 3년만 보관
    python3 scripts/purge_old_data.py --dry-run             # 삭제 없이 영향 행수만 출력
    python3 scripts/purge_old_data.py --logs-only           # 수집 로그만 정리

cron 등록:
    0 4 * * 0  /usr/bin/python3 /app/scripts/purge_old_data.py >> /app/data/purge.log 2>&1
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS_DIR))


def main() -> int:
    p = argparse.ArgumentParser(description="오래된 공공데이터 정리")
    p.add_argument("--retain-years", type=int,
                   default=int(os.environ.get("DATA_RETAIN_YEARS", "10")),
                   help="공고/낙찰결과 보관 연수 (기본 10년 또는 DATA_RETAIN_YEARS env)")
    p.add_argument("--retain-log-days", type=int,
                   default=int(os.environ.get("SYNC_LOG_RETAIN_DAYS", "365")),
                   help="수집 로그 보관 일수 (기본 365일)")
    p.add_argument("--logs-only", action="store_true",
                   help="공고는 건드리지 않고 DataSyncLog 만 정리")
    p.add_argument("--dry-run", action="store_true",
                   help="실제 DELETE 없이 영향 행수만 출력")
    args = p.parse_args()

    from server import (  # noqa: E402
        SessionLocal, BidAnnouncement, BidResult, DataSyncLog, invalidate_analysis_cache,
    )

    now = datetime.now()
    ann_floor = now - timedelta(days=365 * args.retain_years)
    log_floor = now - timedelta(days=args.retain_log_days)
    print(f"[INFO] 현재 시각: {now.isoformat(timespec='seconds')}")
    print(f"[INFO] 공고/결과 삭제 기준: announced_at < {ann_floor.date()}  (보관 {args.retain_years}년)")
    print(f"[INFO] 수집 로그 삭제 기준: finished_at < {log_floor.date()}  (보관 {args.retain_log_days}일)")
    if args.dry_run:
        print("[INFO] --dry-run 모드 — 실제 삭제는 수행하지 않음")

    db = SessionLocal()
    try:
        # ── 공고/결과 카운트 ─────────────────────────────────────
        if not args.logs_only:
            old_ann_q = db.query(BidAnnouncement).filter(BidAnnouncement.announced_at < ann_floor)
            old_ann_count = old_ann_q.count()
            print(f"[INFO] 삭제 대상 공고: {old_ann_count:,} 건")

            if old_ann_count and not args.dry_run:
                # 종속 BidResult 먼저 삭제 (FK 제약 회피)
                old_ids = [a.id for a in old_ann_q.with_entities(BidAnnouncement.id).all()]
                # 큰 IN 절 회피 — 1000개 단위로 chunk
                CHUNK = 1000
                deleted_results = 0
                for i in range(0, len(old_ids), CHUNK):
                    chunk = old_ids[i:i + CHUNK]
                    n = db.query(BidResult).filter(BidResult.announcement_id.in_(chunk)).delete(
                        synchronize_session=False)
                    deleted_results += n
                print(f"[OK]   삭제된 BidResult: {deleted_results:,} 건")

                deleted_ann = old_ann_q.delete(synchronize_session=False)
                print(f"[OK]   삭제된 BidAnnouncement: {deleted_ann:,} 건")
                db.commit()
                invalidate_analysis_cache()

        # ── 수집 로그 정리 ──────────────────────────────────────
        old_log_q = db.query(DataSyncLog).filter(DataSyncLog.finished_at < log_floor)
        old_log_count = old_log_q.count()
        print(f"[INFO] 삭제 대상 수집 로그: {old_log_count:,} 건")

        if old_log_count and not args.dry_run:
            deleted_logs = old_log_q.delete(synchronize_session=False)
            print(f"[OK]   삭제된 DataSyncLog: {deleted_logs:,} 건")
            db.commit()

        print("[OK]   정리 완료" if not args.dry_run else "[OK]   dry-run 분석 완료")
        return 0
    except Exception as e:
        db.rollback()
        print(f"[FAIL] {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
