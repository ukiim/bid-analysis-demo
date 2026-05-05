#!/usr/bin/env python3
"""기존 BidResult 데이터 매칭률 재집계

initial 적재된 BidResult 들은 첫 row dedup 이라 사정률 산출률 낮음 (~32%).
새 알고리즘(_aggregate_prelim_prices)을 적용하려면 G2B PreparPcDetail 을
다시 호출해야 하지만, 이미 사정률이 NULL 인 결과는 기초금액(BidAnnouncement.base_amount)
와 winning_amount 만으로도 사정률 보정 가능:

  rate = winning_amount / base_amount * 100   (둘 다 존재 시)

사용법:
    python3 scripts/recompute_match_rate.py            # 실제 적용
    python3 scripts/recompute_match_rate.py --dry-run  # 영향 행수만 출력
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS_DIR))


def main() -> int:
    p = argparse.ArgumentParser(description="기존 BidResult 사정률 재집계")
    p.add_argument("--dry-run", action="store_true", help="실제 update 없이 카운트만")
    args = p.parse_args()

    from server import SessionLocal, BidResult, BidAnnouncement, invalidate_analysis_cache

    db = SessionLocal()
    try:
        # 사정률이 NULL 인 결과 + 매칭 공고의 base_amount 가 있는 것
        candidates = (
            db.query(BidResult, BidAnnouncement)
            .join(BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id)
            .filter(
                BidResult.assessment_rate.is_(None),
                BidResult.winning_amount.isnot(None),
                BidAnnouncement.base_amount.isnot(None),
                BidAnnouncement.base_amount > 0,
            )
            .all()
        )
        print(f"[INFO] 보정 가능 후보: {len(candidates):,}건")

        before_total = db.query(BidResult).count()
        before_with_rate = db.query(BidResult).filter(BidResult.assessment_rate.isnot(None)).count()
        print(f"[INFO] 보정 전 매칭률: {before_with_rate}/{before_total} = "
              f"{round(before_with_rate / before_total * 100, 2) if before_total else 0}%")

        if args.dry_run:
            print("[INFO] --dry-run 종료")
            return 0

        if not candidates:
            print("[INFO] 보정할 항목 없음")
            return 0

        updated = 0
        for r, a in candidates:
            rate = round(r.winning_amount / a.base_amount * 100, 4)
            # 정상 사정률 범위 (95~105) 내에서만 적용 — 노이즈 제거
            if 95 <= rate <= 105:
                r.assessment_rate = rate
                if r.first_place_rate is None:
                    r.first_place_rate = rate
                if r.first_place_amount is None:
                    r.first_place_amount = r.winning_amount
                updated += 1
        db.commit()
        invalidate_analysis_cache()

        after_with_rate = db.query(BidResult).filter(BidResult.assessment_rate.isnot(None)).count()
        print(f"[OK]   보정 완료: {updated:,}건")
        print(f"[OK]   보정 후 매칭률: {after_with_rate}/{before_total} = "
              f"{round(after_with_rate / before_total * 100, 2)}%")
        return 0
    except Exception as e:
        db.rollback()
        print(f"[FAIL] {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
