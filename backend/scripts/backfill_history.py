#!/usr/bin/env python3
"""공공데이터 G2B 전체 기간(2019년~) 백필 수집 스크립트

`server.py` 의 `_run_sync_for_source()` 를 SYNC_START_DATE 환경변수와 함께 호출해
오늘부터 지정 일자(기본 2019-01-01) 까지 7일 단위 슬라이딩 윈도우로 전 구간 수집한다.

사용법:
    export G2B_API_KEY="발급받은_인증키"
    python3 scripts/backfill_history.py                  # 2019-01-01 ~ 오늘
    python3 scripts/backfill_history.py --from 2024-01-01
    python3 scripts/backfill_history.py --pages 10        # 윈도우당 페이지 수 상향
    python3 scripts/backfill_history.py --dry-run         # API 호출 없이 윈도우 목록만 출력

주의:
- 2019-01-01 부터 오늘까지 약 380주(7일 윈도우) × 카테고리 2종 = 약 760회 페이지 호출
  (페이지당 최대 100건). API 호출 간 슬립을 두어 Rate Limit 회피.
- 중복은 bid_number+bid_ord 기준 자동 dedup → 재실행해도 안전.
- 백업 권장: scripts/backup_db.py 먼저 실행.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS_DIR))


def main() -> int:
    p = argparse.ArgumentParser(description="G2B 전체 기간 백필 수집")
    p.add_argument("--from", dest="start", default="2019-01-01",
                   help="백필 시작일 YYYY-MM-DD (기본 2019-01-01)")
    p.add_argument("--source", default="G2B", choices=["G2B", "D2B"],
                   help="수집 소스 (기본 G2B)")
    p.add_argument("--pages", type=int, default=None,
                   help="윈도우당 최대 페이지 수 override (기본: SYNC_MAX_PAGES_ANN=5)")
    p.add_argument("--dry-run", action="store_true",
                   help="실제 호출 없이 윈도우 분할 결과만 출력")
    args = p.parse_args()

    # 시작일 검증
    try:
        start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    except ValueError:
        print(f"[FAIL] --from 형식 오류: {args.start} (YYYY-MM-DD)")
        return 2
    if start_dt > datetime.now():
        print(f"[FAIL] --from 이 미래입니다: {args.start}")
        return 2

    # 환경변수 주입 (server.py 가 읽음)
    os.environ["SYNC_START_DATE"] = args.start
    if args.pages:
        os.environ["SYNC_MAX_PAGES_ANN"] = str(args.pages)
        os.environ["SYNC_MAX_PAGES_RES"] = str(args.pages)

    # API 키 확인
    key = os.environ.get(f"{args.source}_API_KEY", "").strip()
    if not key:
        print(f"[FAIL] {args.source}_API_KEY 환경변수가 비어 있습니다.")
        return 2
    masked = key[:6] + "…" + key[-4:] if len(key) > 12 else "***"
    print(f"[OK]   {args.source}_API_KEY 감지 ({masked})")
    print(f"[INFO] 백필 시작일: {args.start} ~ {datetime.now().strftime('%Y-%m-%d')}")

    # 윈도우 미리 계산
    from server import _windows_iter  # noqa: E402
    window_days = int(os.environ.get("SYNC_WINDOW_DAYS", "7"))
    windows = list(_windows_iter(0, window_days, start_date=args.start))
    print(f"[INFO] 7일 윈도우 {len(windows)}개로 분할 — 카테고리 2종 × {windows[0][0][:8]} ~ {windows[-1][1][:8]}")

    if args.dry_run:
        print("[INFO] --dry-run: 실제 호출 없이 윈도우 목록만 출력")
        for i, (s, e) in enumerate(windows[:5], 1):
            print(f"   {i:3d}. {s} ~ {e}")
        if len(windows) > 5:
            print(f"   ... (총 {len(windows)}개)")
        return 0

    print(f"[WARN] 약 {len(windows) * 2 * int(os.environ.get('SYNC_MAX_PAGES_ANN', '5'))} 회 API 호출이 예상됩니다. 시작합니다...")
    print()

    from server import _run_sync_for_source  # noqa: E402
    started = datetime.now()
    # trigger='backfill' → SYNC_INCREMENTAL=true 이어도 강제로 전체 구간 재수집
    _run_sync_for_source(args.source, trigger="backfill")
    elapsed = (datetime.now() - started).total_seconds()
    print()
    print(f"[OK]   백필 완료 — 소요 {elapsed:.1f}s ({elapsed/60:.1f}분)")
    print(f"[INFO] 결과는 관리자 콘솔 → 데이터 수집 → 수집 히스토리 또는 DataSyncLog 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
