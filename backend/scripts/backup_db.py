#!/usr/bin/env python3
"""SQLite DB 안전 백업 스크립트

사용법:
    python3 scripts/backup_db.py                     # ./backups/ 에 타임스탬프 백업
    python3 scripts/backup_db.py --output /nas/bid/  # 지정 경로
    python3 scripts/backup_db.py --retain 14         # 14개 초과분 자동 정리
    python3 scripts/backup_db.py --verify            # 백업 후 sqlite3 integrity_check
    python3 scripts/backup_db.py --restore FILE.db   # 대화식 복원 확인

크론 예시:
    0 3 * * *  /usr/bin/python3 /app/scripts/backup_db.py --retain 30 >> /app/data/backup.log 2>&1
"""
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime


DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo.db")
DEFAULT_OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")


def safe_backup(src: str, dest: str) -> int:
    """sqlite3 백업 API로 잠금 없이 안전하게 복사. 바이트 수 반환."""
    if not os.path.exists(src):
        raise FileNotFoundError(f"소스 DB를 찾을 수 없습니다: {src}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dest)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()
    return os.path.getsize(dest)


def verify(path: str) -> bool:
    """integrity_check 실행"""
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        return bool(row and row[0] == "ok")
    finally:
        conn.close()


def prune(outdir: str, retain: int) -> int:
    """오래된 백업 정리. retain 개수만 남기고 삭제. 삭제 건수 반환."""
    files = sorted(
        (f for f in os.listdir(outdir) if f.startswith("demo-") and f.endswith(".db")),
        reverse=True,
    )
    to_delete = files[retain:]
    for f in to_delete:
        os.remove(os.path.join(outdir, f))
    return len(to_delete)


def restore(dest: str, backup: str) -> None:
    """백업 파일로 DB 복원. 운영자 확인 후 수행."""
    if not os.path.exists(backup):
        raise FileNotFoundError(f"백업 파일이 없습니다: {backup}")
    if os.path.exists(dest):
        ans = input(f"기존 DB({dest})를 덮어쓰시겠습니까? [y/N] ").strip().lower()
        if ans != "y":
            print("취소됨.")
            sys.exit(1)
        shutil.copy2(dest, dest + ".before-restore")
        print(f"기존 DB를 {dest}.before-restore 로 보관했습니다.")
    shutil.copy2(backup, dest)
    print(f"복원 완료: {backup} → {dest}")


def main() -> int:
    p = argparse.ArgumentParser(description="bid-insight SQLite 백업/복원")
    p.add_argument("--db", default=DEFAULT_DB, help=f"소스 DB 경로 (기본: {DEFAULT_DB})")
    p.add_argument("--output", default=DEFAULT_OUTDIR, help="백업 디렉토리")
    p.add_argument("--retain", type=int, default=30, help="유지할 백업 개수 (기본 30)")
    p.add_argument("--verify", action="store_true", help="백업 후 integrity_check")
    p.add_argument("--restore", metavar="FILE", help="지정 파일로 DB 복원")
    args = p.parse_args()

    if args.restore:
        restore(args.db, args.restore)
        return 0

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(args.output, f"demo-{ts}.db")
    try:
        size = safe_backup(args.db, out)
    except Exception as e:
        print(f"[ERROR] 백업 실패: {e}", file=sys.stderr)
        return 1

    ok = True
    if args.verify:
        ok = verify(out)
        if not ok:
            print(f"[WARN] integrity_check 실패: {out}", file=sys.stderr)

    deleted = prune(args.output, args.retain)
    print(
        f"[OK] backup={out} size={size/1024/1024:.2f}MB "
        f"verified={'yes' if args.verify and ok else ('fail' if args.verify else 'skipped')} "
        f"pruned={deleted}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
