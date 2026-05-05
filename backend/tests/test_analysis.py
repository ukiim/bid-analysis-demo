"""분석 엔드포인트 통합 테스트 — Tab1 빈도 / Tab2 갭 / Tab3 종합

실 DB에 시드 데이터가 있다는 전제로 실제 쿼리 경로를 검증한다.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app, SessionLocal, BidAnnouncement, User, get_password_hash  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_announcement_id():
    """시드 데이터에서 임의의 BidAnnouncement id 하나"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).first()
    db.close()
    if not ann:
        pytest.skip("시드 공고 데이터가 없습니다.")
    return ann.id


@pytest.fixture(scope="module")
def auth_token(client):
    """분석 이력 저장 검증용 사용자 토큰"""
    email = "analysis_test@example.com"
    password = "testpass123"
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Analysis Tester", role="user", is_active=True,
            joined_at=__import__("datetime").datetime.now(),
        )
        db.add(user)
        db.commit()
    db.close()
    resp = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tab1: 빈도 분석 ───────────────────────────────────────────────

def test_frequency_basic_structure(client, sample_announcement_id, auth_token):
    resp = client.get(f"/api/v1/analysis/frequency/{sample_announcement_id}", headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "bins" in data
    assert "peaks" in data
    assert "stats" in data
    assert "prediction_candidates" in data
    assert "announcement" in data


def test_frequency_with_period_query(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/frequency/{sample_announcement_id}?period_months=6&org_scope=parent"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    # 유효한 응답 스키마
    assert isinstance(data.get("bins"), list)
    assert isinstance(data.get("peaks"), list)


def test_frequency_invalid_id(client, auth_token):
    resp = client.get("/api/v1/analysis/frequency/nonexistent-id-xyz", headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    # 에러 케이스도 200으로 응답하지만 error 필드 포함
    assert "error" in data or data.get("data_count", 0) == 0


def test_frequency_history_logged_when_authed(client, sample_announcement_id, auth_token):
    """인증된 사용자의 호출은 QueryHistory에 기록되어야 함"""
    from server import SessionLocal as SL, QueryHistory, User as U
    db = SL()
    user = db.query(U).filter(U.email == "analysis_test@example.com").first()
    before = db.query(QueryHistory).filter(QueryHistory.user_id == user.id).count()
    db.close()

    resp = client.get(
        f"/api/v1/analysis/frequency/{sample_announcement_id}",
        headers=_headers(auth_token),
    )
    assert resp.status_code == 200

    db = SL()
    after = db.query(QueryHistory).filter(QueryHistory.user_id == user.id).count()
    db.close()
    assert after == before + 1, "인증 사용자 호출 시 이력이 저장되어야 합니다."


# ── Tab2: 갭 분석 ─────────────────────────────────────────────────

def test_company_rates_basic(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/company-rates/{sample_announcement_id}?rate_range_start=99&rate_range_end=100"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "company_rates" in data
    assert "gaps" in data
    assert "largest_gap_midpoint" in data
    assert "refined_rate" in data
    assert "next_year_validation" in data


def test_company_rates_gaps_sorted_by_size(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/company-rates/{sample_announcement_id}?rate_range_start=98&rate_range_end=101"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    gaps = resp.json().get("gaps", [])
    if len(gaps) >= 2:
        for i in range(len(gaps) - 1):
            assert gaps[i]["size"] >= gaps[i + 1]["size"], "갭은 크기 내림차순이어야 합니다."


# ── Tab3: 종합 분석 ───────────────────────────────────────────────

def test_comprehensive_basic(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/comprehensive/{sample_announcement_id}?confirmed_rate=99.5"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "announcement" in data
    assert "confirmed_rate" in data
    assert "predicted_first_place" in data
    assert data["predicted_first_place"]["rate"] == 99.5


def test_comprehensive_amount_calculation(client, sample_announcement_id, auth_token):
    """predicted_first_place.amount = base_amount * confirmed_rate / 100"""
    rate = 99.7
    resp = client.get(
        f"/api/v1/analysis/comprehensive/{sample_announcement_id}?confirmed_rate={rate}"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    budget = data["announcement"]["budget"]
    amount = data["predicted_first_place"]["amount"]
    if budget:
        expected = int(budget * rate / 100)
        assert abs(amount - expected) <= 1


# ── 밀어내기식 검토 ────────────────────────────────────────────────

def test_sliding_review_basic(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/sliding-review/{sample_announcement_id}?window_size=3m&confirmed_rate=99.5"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    assert "summary" in data
    assert "hit_rate" in data["summary"]


# ── 연도별 낙찰확률 검증 ──────────────────────────────────────────

def test_yearly_validation_basic(client, sample_announcement_id, auth_token):
    resp = client.get(
        f"/api/v1/analysis/yearly-validation/{sample_announcement_id}?confirmed_rate=99.5"
    , headers=_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "years" in data
    assert isinstance(data["years"], list)
    # 2020~2026 = 7개 연도
    if data["years"]:
        years = {y["year"] for y in data["years"]}
        assert 2020 in years or 2026 in years
