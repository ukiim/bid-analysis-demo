"""Item 2 — 직전 공고 비교 엔드포인트 테스트"""
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (  # noqa: E402
    app, SessionLocal, User, BidAnnouncement, BidResult, get_password_hash,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client):
    email = "prev_test@example.com"
    password = "testpass123"
    db = SessionLocal()
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Prev Tester", role="user", is_active=True,
            joined_at=datetime.now(),
        ))
        db.commit()
    db.close()
    r = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def two_anns():
    """완전 일치 공고 2건 생성 (older + newer) + 결과"""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    older = BidAnnouncement(
        source="TEST", bid_number=f"PREV-{suffix}-1",
        category="공사", title=f"이전공고-{suffix}",
        ordering_org_name="테스트시", region="여주시",
        industry_code="IND-X", base_amount=1_000_000_000,
        announced_at=datetime.now() - timedelta(days=30),
        status="완료",
    )
    newer = BidAnnouncement(
        source="TEST", bid_number=f"PREV-{suffix}-2",
        category="공사", title=f"신규공고-{suffix}",
        ordering_org_name="테스트시", region="여주시",
        industry_code="IND-X", base_amount=1_200_000_000,
        announced_at=datetime.now() - timedelta(days=1),
        status="진행중",
    )
    db.add_all([older, newer])
    db.commit()
    res = BidResult(
        announcement_id=older.id, winning_amount=950_000_000,
        assessment_rate=98.5, first_place_rate=99.1,
        first_place_amount=940_000_000,
        opened_at=datetime.now() - timedelta(days=20),
    )
    db.add(res)
    db.commit()
    older_id, newer_id = older.id, newer.id
    db.close()
    yield older_id, newer_id
    db = SessionLocal()
    db.query(BidResult).filter(BidResult.announcement_id == older_id).delete()
    db.query(BidAnnouncement).filter(BidAnnouncement.id.in_([older_id, newer_id])).delete()
    db.commit()
    db.close()


def test_previous_exact_match(client, auth_token, two_anns):
    older_id, newer_id = two_anns
    r = client.get(f"/api/v1/announcements/{newer_id}/previous", headers=_h(auth_token))
    assert r.status_code == 200
    body = r.json()
    assert body["fallback_used"] == "exact"
    assert body["prev"]["id"] == older_id
    assert body["prev"]["result"]["assessment_rate"] == 98.5


def test_previous_not_found_for_unique(client, auth_token):
    """완전 신규 카테고리 — 어떤 공고로도 fallback 가능 (no_industry) 또는 none"""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    only = BidAnnouncement(
        source="TEST", bid_number=f"ONLY-{suffix}",
        category=f"UNIQUECAT-{suffix}",  # 다른 공고 없음
        title="유일공고",
        ordering_org_name="테스트시", region="여주시",
        industry_code="UNIQ", base_amount=100,
        announced_at=datetime.now(),
        status="진행중",
    )
    db.add(only)
    db.commit()
    only_id = only.id
    db.close()
    try:
        r = client.get(f"/api/v1/announcements/{only_id}/previous", headers=_h(auth_token))
        assert r.status_code == 200
        body = r.json()
        assert body["fallback_used"] == "none"
        assert body["prev"] is None
    finally:
        db = SessionLocal()
        db.query(BidAnnouncement).filter(BidAnnouncement.id == only_id).delete()
        db.commit()
        db.close()
