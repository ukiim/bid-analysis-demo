"""Phase A 마이그레이션 — BidAnnouncement에 KBID 동등성 5개 필드 추가.

기존 alembic 미설치 환경 우회용. SQLite ALTER TABLE 직접 사용.
- estimated_price: INTEGER
- license_category: VARCHAR (인덱스)
- opening_at: DATETIME
- site_visit_at: DATETIME
(parent_org_name 은 이미 존재)

idempotent — 이미 존재하는 컬럼은 skip.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "demo.db"


def column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def add_column(cur: sqlite3.Cursor, table: str, column: str, ddl: str) -> bool:
    if column_exists(cur, table, column):
        print(f"  [skip] {table}.{column} already exists")
        return False
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    print(f"  [add ] {table}.{column} {ddl}")
    return True


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print(f"DB: {DB_PATH}")
    print("Adding KBID announcement fields...")
    add_column(cur, "bid_announcements", "estimated_price", "INTEGER")
    add_column(cur, "bid_announcements", "license_category", "VARCHAR")
    add_column(cur, "bid_announcements", "opening_at", "DATETIME")
    add_column(cur, "bid_announcements", "site_visit_at", "DATETIME")

    # license_category 인덱스 (없으면 추가)
    idx_rows = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='bid_announcements'"
    ).fetchall()
    idx_names = {r[0] for r in idx_rows}
    if "ix_bid_announcements_license_category" not in idx_names:
        cur.execute(
            "CREATE INDEX ix_bid_announcements_license_category "
            "ON bid_announcements(license_category)"
        )
        print("  [add ] ix_bid_announcements_license_category")
    else:
        print("  [skip] ix_bid_announcements_license_category exists")

    conn.commit()
    conn.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
