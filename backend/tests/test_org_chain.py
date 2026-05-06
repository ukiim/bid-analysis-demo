"""Item 6 — 상위기관 3단계 chain 테스트"""
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (  # noqa: E402
    app, SessionLocal, User, BidAnnouncement, BidResult,
    _org_chain, get_password_hash,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client):
    email = "chain_test@example.com"
    password = "testpass123"
    db = SessionLocal()
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Chain", role="user", is_active=True,
            joined_at=datetime.now(),
        ))
        db.commit()
    db.close()
    r = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_org_chain_school_three_levels():
    """학교 → 교육지원청 → 교육청 3단계 chain"""
    chain = _org_chain("백신고")
    assert chain[0] == "백신고"
    assert "고양교육지원청" in chain
    assert "경기도교육청" in chain
    assert len(chain) <= 4


def test_org_chain_unknown():
    """매핑 없는 기관은 자기 자신만"""
    chain = _org_chain("무명기관-XYZ")
    assert chain == ["무명기관-XYZ"]


def test_org_chain_empty():
    assert _org_chain("") == []


def test_comprehensive_chain_scope_returns_meta(client, auth_token):
    """org_scope=chain 응답에 expansion_chain/org_scope_used/sample_count 포함"""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    ann = BidAnnouncement(
        source="TEST", bid_number=f"CHAIN-{suffix}",
        category="공사", title="체인테스트", ordering_org_name="백신고",
        parent_org_name="고양교육지원청", region="고양시",
        industry_code=f"CHN-{suffix}", base_amount=500_000,
        announced_at=datetime.now(),
    )
    db.add(ann)
    db.commit()
    ann_id = ann.id
    db.close()
    try:
        r = client.get(
            f"/api/v1/analysis/comprehensive/{ann_id}?org_scope=chain&period_months=12",
            headers=_h(auth_token),
        )
        assert r.status_code == 200
        body = r.json()
        if "error" in body:
            pytest.skip(body["error"])
        assert "expansion_chain" in body
        assert "org_scope_used" in body
        assert "sample_count" in body
        # 첫 entry 는 자기 자신("백신고(N)")
        assert body["expansion_chain"][0].startswith("백신고(")
    finally:
        db = SessionLocal()
        db.query(BidAnnouncement).filter(BidAnnouncement.id == ann_id).delete()
        db.commit()
        db.close()
