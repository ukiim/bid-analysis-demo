#!/usr/bin/env python3
"""더미/시드 데이터 정리 스크립트

기준:
  - 실 데이터: bid_number LIKE 'R%BK%' (G2B 실 API 응답 형식)
  - 그 외 (G20XX-XXXXX, D20XX-XXXXX, UPLOAD, TEST 등) = 더미

삭제 대상:
  - BidAnnouncement (실 패턴 외)
  - BidResult (announcement_id 매칭으로 cascade)
  - CompanyBidRecord (announcement_id 매칭으로 cascade)
  - QueryHistory (사라진 announcement 참조)
  - DataSyncLog: 보존 (운영 기록 보존)
  - User: 보존
  - UploadLog: 보존 (이력 보존)

사용법:
    python3 scripts/purge_dummy_data.py --dry-run     # 시뮬레이션
    python3 scripts/purge_dummy_data.py --confirm     # 실제 삭제
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_, not_  # noqa: E402

from server import (  # noqa: E402
    SessionLocal, BidAnnouncement, BidResult, CompanyBidRecord, QueryHistory,
    User, UploadLog,
)


def is_real_pattern(col):
    """실 G2B bid_number 패턴 (R*BK*)"""
    return col.like("R%BK%")


# 운영에서 보존할 사용자 — 그 외는 데모/테스트로 간주하고 정리
KEEP_USER_EMAILS = {"admin@bidinsight.kr"}


def main() -> int:
    p = argparse.ArgumentParser(description="더미/시드 데이터 정리")
    p.add_argument("--dry-run", action="store_true", help="삭제하지 않고 카운트만 표시")
    p.add_argument("--confirm", action="store_true", help="실제 삭제 실행 (필수)")
    p.add_argument("--include-demo-users", action="store_true",
                   help="데모/테스트 사용자도 함께 삭제 (admin@bidinsight.kr 제외)")
    p.add_argument("--include-uploads", action="store_true",
                   help="UploadLog 기록을 모두 삭제")
    args = p.parse_args()

    if not args.confirm and not args.dry_run:
        print("[ERROR] --dry-run 또는 --confirm 중 하나는 반드시 필요합니다.")
        return 2

    db = SessionLocal()
    try:
        # 1. 더미 BidAnnouncement 식별
        dummy_anns = db.query(BidAnnouncement.id).filter(
            not_(is_real_pattern(BidAnnouncement.bid_number))
        ).all()
        dummy_ann_ids = [a.id for a in dummy_anns]

        # 2. 관련 BidResult / CompanyBidRecord / QueryHistory 카운트
        if dummy_ann_ids:
            dummy_results = db.query(BidResult).filter(
                BidResult.announcement_id.in_(dummy_ann_ids)
            ).count()
            dummy_records = db.query(CompanyBidRecord).filter(
                CompanyBidRecord.announcement_id.in_(dummy_ann_ids)
            ).count()
            dummy_qh = db.query(QueryHistory).filter(
                QueryHistory.announcement_id.in_(dummy_ann_ids)
            ).count()
        else:
            dummy_results = dummy_records = dummy_qh = 0

        real_anns = db.query(BidAnnouncement).filter(
            is_real_pattern(BidAnnouncement.bid_number)
        ).count()

        print("=" * 60)
        print(f"📊 정리 대상 (더미)")
        print(f"   BidAnnouncement:   {len(dummy_ann_ids):>7,} 건")
        print(f"   BidResult:         {dummy_results:>7,} 건")
        print(f"   CompanyBidRecord:  {dummy_records:>7,} 건")
        print(f"   QueryHistory:      {dummy_qh:>7,} 건")
        print()
        print(f"✅ 보존 (실 데이터)")
        print(f"   BidAnnouncement:   {real_anns:>7,} 건 (R*BK* 패턴)")
        print("=" * 60)

        if args.dry_run:
            print("\n[DRY-RUN] 실제 삭제는 수행하지 않았습니다.")
            print("실행하려면: --confirm 옵션 추가")
            return 0

        # 3. 실 삭제 (참조 무결성 위해 자식 → 부모 순)
        print("\n삭제 진행 중...")
        if dummy_ann_ids:
            n = db.query(QueryHistory).filter(
                QueryHistory.announcement_id.in_(dummy_ann_ids)
            ).delete(synchronize_session=False)
            print(f"  ✓ QueryHistory(공고FK) {n}건 삭제")
            n = db.query(CompanyBidRecord).filter(
                CompanyBidRecord.announcement_id.in_(dummy_ann_ids)
            ).delete(synchronize_session=False)
            print(f"  ✓ CompanyBidRecord {n}건 삭제")
            n = db.query(BidResult).filter(
                BidResult.announcement_id.in_(dummy_ann_ids)
            ).delete(synchronize_session=False)
            print(f"  ✓ BidResult {n}건 삭제")
            n = db.query(BidAnnouncement).filter(
                BidAnnouncement.id.in_(dummy_ann_ids)
            ).delete(synchronize_session=False)
            print(f"  ✓ BidAnnouncement {n}건 삭제")

        # 데모/테스트 사용자 (옵션)
        if args.include_demo_users:
            demo_users = db.query(User).filter(~User.email.in_(KEEP_USER_EMAILS)).all()
            demo_ids = [u.id for u in demo_users]
            if demo_ids:
                db.query(QueryHistory).filter(QueryHistory.user_id.in_(demo_ids)).delete(synchronize_session=False)
                db.query(UploadLog).filter(UploadLog.user_id.in_(demo_ids)).delete(synchronize_session=False)
                n = db.query(User).filter(User.id.in_(demo_ids)).delete(synchronize_session=False)
                print(f"  ✓ User(데모) {n}명 삭제: {[u.email for u in demo_users]}")

        # UploadLog 일괄 (옵션)
        if args.include_uploads:
            n = db.query(UploadLog).delete(synchronize_session=False)
            print(f"  ✓ UploadLog 전체 {n}건 삭제")

        db.commit()
        print("\n✅ 정리 완료")
        return 0
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 정리 실패: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
