"""Item 5 — 직전 동일공종 우선 fallback 테스트"""
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (  # noqa: E402
    app, SessionLocal, User, BidAnnouncement, BidResult,
    _resolve_recent_results, get_password_hash,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client):
    email = "fallback_test@example.com"
    password = "testpass123"
    db = SessionLocal()
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="FB", role="user", is_active=True,
            joined_at=datetime.now(),
        ))
        db.commit()
    db.close()
    r = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_resolve_recent_results_30d_match():
    """30일 내에 10건 이상이면 30일 표본을 그대로 사용"""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    target = BidAnnouncement(
        source="TEST", bid_number=f"FB-T-{suffix}",
        category="공사", title="대상", ordering_org_name="여주시",
        region="여주시", industry_code=f"FBI-{suffix}",
        base_amount=1_000_000, announced_at=datetime.now(),
    )
    db.add(target)
    # 같은 공종/지역, 15일 전 결과 12건
    anns = []
    for i in range(12):
        a = BidAnnouncement(
            source="TEST", bid_number=f"FB-S-{suffix}-{i}",
            category="공사", title=f"표본{i}",
            ordering_org_name="여주시", region="여주시",
            industry_code=f"FBI-{suffix}", base_amount=900_000,
            announced_at=datetime.now() - timedelta(days=20),
        )
        db.add(a)
        anns.append(a)
    db.commit()
    for a in anns:
        db.add(BidResult(
            announcement_id=a.id, winning_amount=850_000,
            assessment_rate=99.0, first_place_rate=99.5,
            opened_at=datetime.now() - timedelta(days=15),
        ))
    db.commit()
    target_id = target.id
    ann_ids = [a.id for a in anns]
    try:
        rv = _resolve_recent_results(db, target)
        assert rv["lookback_used_days"] == 30
        assert len(rv["results"]) >= 10
        assert f"FBI-{suffix}" in rv["sample_source"]
    finally:
        db.query(BidResult).filter(BidResult.announcement_id.in_(ann_ids)).delete(synchronize_session=False)
        db.query(BidAnnouncement).filter(BidAnnouncement.id.in_(ann_ids + [target_id])).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_company_rates_with_use_recent_fallback(client, auth_token):
    """엔드포인트가 use_recent_fallback=true 일 때 lookback_used_days 를 응답에 포함"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).first()
    if not ann:
        pytest.skip("시드 공고 없음")
    ann_id = ann.id
    db.close()
    r = client.get(
        f"/api/v1/analysis/company-rates/{ann_id}?use_recent_fallback=true",
        headers=_h(auth_token),
    )
    assert r.status_code == 200
    body = r.json()
    if "error" in body:
        pytest.skip(body["error"])
    assert "lookback_used_days" in body
    assert body["lookback_used_days"] in (30, 90, 180)
    assert "sample_source" in body
    assert "기간:" in body["sample_source"]
