#!/usr/bin/env python3
"""관리자 계정 초기 생성 스크립트

사용법:
    # 대화식 (안전)
    python3 scripts/init_admin.py

    # 명시 (CI/배포 자동화)
    python3 scripts/init_admin.py --email admin@example.com --name "운영 관리자"

    # 비밀번호 자동 생성 (출력 후 안전 보관)
    python3 scripts/init_admin.py --email admin@example.com --auto-password

    # 환경변수 (DSM 작업 스케줄러 1회 실행)
    INIT_ADMIN_EMAIL=admin@example.com INIT_ADMIN_PASSWORD=Pa$$w0rd \\
        python3 scripts/init_admin.py
"""
import argparse
import getpass
import os
import re
import secrets
import string
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# noqa: E402
from server import SessionLocal, User, get_password_hash  # type: ignore


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def gen_password(length: int = 16) -> str:
    """소문자+대문자+숫자+특수문자 포함 랜덤 비밀번호"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)):
            return pwd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="bid-insight 관리자 계정 생성")
    p.add_argument("--email", default=os.environ.get("INIT_ADMIN_EMAIL"),
                   help="관리자 이메일 (환경변수 INIT_ADMIN_EMAIL 도 사용 가능)")
    p.add_argument("--password", default=os.environ.get("INIT_ADMIN_PASSWORD"),
                   help="비밀번호 (환경변수 INIT_ADMIN_PASSWORD)")
    p.add_argument("--name", default=os.environ.get("INIT_ADMIN_NAME", "운영 관리자"),
                   help="표시 이름")
    p.add_argument("--auto-password", action="store_true",
                   help="강력한 비밀번호 자동 생성 후 출력")
    p.add_argument("--update-existing", action="store_true",
                   help="동일 이메일 사용자가 있으면 admin 권한 부여 + 비밀번호 갱신")
    return p.parse_args()


def ensure_email(args) -> str:
    email = args.email
    if not email:
        if not sys.stdin.isatty():
            print("[ERROR] 이메일이 필요합니다. --email 또는 INIT_ADMIN_EMAIL 사용", file=sys.stderr)
            sys.exit(2)
        email = input("관리자 이메일: ").strip()
    if not EMAIL_RE.match(email):
        print(f"[ERROR] 잘못된 이메일 형식: {email}", file=sys.stderr)
        sys.exit(2)
    return email


def ensure_password(args) -> tuple[str, bool]:
    """(password, was_generated)"""
    if args.auto_password:
        return gen_password(), True
    pwd = args.password
    if pwd:
        if len(pwd) < 8:
            print("[ERROR] 비밀번호는 최소 8자 이상이어야 합니다.", file=sys.stderr)
            sys.exit(2)
        return pwd, False
    if not sys.stdin.isatty():
        # 비대화식인데 인자 없음 → 자동 생성
        return gen_password(), True
    while True:
        a = getpass.getpass("비밀번호 (8자 이상): ")
        if len(a) < 8:
            print("  너무 짧습니다.")
            continue
        b = getpass.getpass("비밀번호 확인: ")
        if a != b:
            print("  일치하지 않습니다.")
            continue
        return a, False


def main() -> int:
    args = parse_args()
    email = ensure_email(args)
    password, generated = ensure_password(args)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.email == email) | (User.username == email)
        ).first()

        if existing and not args.update_existing:
            print(f"[ERROR] 이미 존재하는 이메일: {email}")
            print(f"        기존 사용자 권한: {existing.role}, is_active: {existing.is_active}")
            print(f"        기존 사용자에게 관리자 권한을 부여하려면 --update-existing 옵션 사용")
            return 3

        if existing and args.update_existing:
            existing.hashed_password = get_password_hash(password)
            existing.role = "admin"
            existing.is_active = True
            existing.last_login_at = None
            db.commit()
            print(f"[OK] 기존 사용자 갱신: {email}")
            user_id = existing.id
        else:
            user = User(
                username=email,
                email=email,
                hashed_password=get_password_hash(password),
                name=args.name,
                role="admin",
                plan="운영",
                is_active=True,
                joined_at=datetime.now(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_id = user.id
            print(f"[OK] 관리자 계정 생성 완료")

        print()
        print("=" * 60)
        print(f"  이메일:   {email}")
        print(f"  이름:     {args.name}")
        print(f"  역할:     admin")
        print(f"  ID:       {user_id}")
        if generated:
            print(f"  비밀번호: {password}")
            print()
            print("  ⚠️  위 비밀번호는 다시 표시되지 않습니다. 안전한 곳에 보관 후")
            print("      첫 로그인 시 마이페이지에서 변경하세요.")
        else:
            print(f"  비밀번호: (지정한 값 사용)")
        print("=" * 60)
        return 0
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 생성 실패: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
