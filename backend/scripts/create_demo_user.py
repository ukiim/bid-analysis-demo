#!/usr/bin/env python3
"""클라이언트 데모용 read-only 사용자 1회 생성 스크립트.

사용법:
    cd backend && python3 scripts/create_demo_user.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS))


def main() -> int:
    from server import SessionLocal, User, get_password_hash

    EMAIL = os.environ.get("DEMO_EMAIL", "client@demo.com")
    PASSWORD = os.environ.get("DEMO_PASSWORD", "demo2026!")
    NAME = "클라이언트 데모"

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == EMAIL).first()
        if existing:
            print(f"[SKIP] 데모 계정 이미 존재: {EMAIL} (role={existing.role})")
            return 0
        user = User(
            username="client_demo",
            email=EMAIL,
            hashed_password=get_password_hash(PASSWORD),
            name=NAME,
            role="user",  # read-only — admin 메뉴 자동 차단
            is_active=True,
            joined_at=datetime.now(),
        )
        db.add(user)
        db.commit()
        print(f"[OK] 데모 계정 생성: {EMAIL} (role=user, read-only)")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"[FAIL] {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
