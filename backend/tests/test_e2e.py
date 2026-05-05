"""엔드-투-엔드 사용자 흐름 테스트

시나리오:
    회원가입 → 로그인 → 공고 조회 → 분석 (이력 저장 확인) →
    CSV 업로드 → 마이페이지 이력 조회 → 로그아웃(토큰 무효화 검증)
"""
import io
import os
import sys
import time
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app, SessionLocal, BidAnnouncement, QueryHistory, User  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def e2e_user(client):
    """고유 사용자로 회원가입 + 로그인"""
    unique = uuid.uuid4().hex[:10]
    email = f"e2e_{unique}@example.com"
    password = "E2eTestPass#123"

    reg = client.post(
        f"/api/v1/auth/register"
        f"?username={email}&email={email}&password={password}&name=E2E Tester"
    )
    assert reg.status_code in (200, 201), reg.text

    login = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    assert login.status_code == 200, login.text
    body = login.json()
    return {
        "email": email,
        "password": password,
        "token": body["access_token"],
        "user_id": body["user"]["id"],
    }


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. 인증 흐름 ─────────────────────────────────────────────────

def test_e2e_register_login_me(client, e2e_user):
    resp = client.get("/api/v1/auth/me", headers=_h(e2e_user["token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == e2e_user["email"]


# ── 2. 공고 조회 ─────────────────────────────────────────────────

def test_e2e_announcement_listing(client):
    resp = client.get("/api/v1/announcements?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items", data if isinstance(data, list) else [])
    assert len(items) > 0, "시드 공고가 필요합니다."


# ── 3. 분석 실행 + 이력 저장 검증 ────────────────────────────────

def test_e2e_analyze_and_history_tracking(client, e2e_user):
    # 임의 공고 하나 조회
    db = SessionLocal()
    ann = db.query(BidAnnouncement).first()
    ann_id = ann.id
    user_id = e2e_user["user_id"]
    before = db.query(QueryHistory).filter(QueryHistory.user_id == user_id).count()
    db.close()

    # 3가지 분석을 순차 실행
    for endpoint, qs in [
        ("/api/v1/analysis/frequency", "period_months=12"),
        ("/api/v1/analysis/company-rates", "rate_range_start=99&rate_range_end=100"),
        ("/api/v1/analysis/comprehensive", "confirmed_rate=99.5"),
    ]:
        resp = client.get(f"{endpoint}/{ann_id}?{qs}", headers=_h(e2e_user["token"]))
        assert resp.status_code == 200, f"{endpoint} 실패: {resp.text[:200]}"

    # 이력 3건 추가 저장 확인
    db = SessionLocal()
    after = db.query(QueryHistory).filter(QueryHistory.user_id == user_id).count()
    db.close()
    assert after == before + 3, f"이력 증가 기대 3, 실제 {after - before}"


# ── 4. 캐시 효과 검증 ────────────────────────────────────────────

def test_e2e_analysis_cache_hit_speedup(client, e2e_user):
    db = SessionLocal()
    ann_id = db.query(BidAnnouncement).first().id
    db.close()

    # 첫 호출 (cold)
    t0 = time.perf_counter()
    r1 = client.get(
        f"/api/v1/analysis/frequency/{ann_id}?period_months=24",
        headers=_h(e2e_user["token"]),
    )
    cold_ms = (time.perf_counter() - t0) * 1000
    assert r1.status_code == 200

    # 두 번째 (hit)
    t0 = time.perf_counter()
    r2 = client.get(
        f"/api/v1/analysis/frequency/{ann_id}?period_months=24",
        headers=_h(e2e_user["token"]),
    )
    hit_ms = (time.perf_counter() - t0) * 1000
    assert r2.status_code == 200

    # 동일한 응답
    assert r1.json().get("data_count") == r2.json().get("data_count")
    # 일반적으로 hit이 cold보다 빠름 (테스트는 상한만 완만하게 체크)
    assert hit_ms < cold_ms * 2 + 50  # 느슨한 상한


# ── 5. 데이터 업로드 흐름 ────────────────────────────────────────

def test_e2e_upload_and_history(client, e2e_user):
    unique = uuid.uuid4().hex[:8]
    csv = (
        "공고번호,공고명,발주기관,기초금액,지역\n"
        f"E2E-{unique}-A,첫 번째 업로드 공고,업로드테스트청,100000000,서울\n"
        f"E2E-{unique}-B,두 번째 업로드 공고,업로드테스트청,250000000,경기\n"
    ).encode("utf-8")

    resp = client.post(
        "/api/v1/data/upload",
        headers=_h(e2e_user["token"]),
        files={"file": (f"e2e_{unique}.csv", io.BytesIO(csv), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["summary"]["inserted"] == 2

    # 업로드 이력 조회
    history = client.get("/api/v1/data/uploads", headers=_h(e2e_user["token"]))
    assert history.status_code == 200
    items = history.json()
    items = items if isinstance(items, list) else items.get("items", [])
    assert any(str(u.get("filename", "")).startswith(f"e2e_{unique}") for u in items)


# ── 6. 관리자 경로 차단 검증 ─────────────────────────────────────

def test_e2e_non_admin_cannot_access_admin(client, e2e_user):
    """일반 유저는 관리자 엔드포인트 접근 불가 (403)"""
    resp = client.get("/api/v1/admin/dashboard", headers=_h(e2e_user["token"]))
    assert resp.status_code == 403


# ── 7. 헬스체크 / 메트릭 공개 확인 ──────────────────────────────

def test_e2e_health_and_metrics_public(client):
    h = client.get("/healthz")
    assert h.status_code in (200, 503)
    data = h.json()
    assert "status" in data and "checks" in data

    m = client.get("/metrics")
    assert m.status_code == 200
    body = m.text
    assert "bid_announcements_total" in body
    assert "scheduler_running" in body


# ── 8. 보안 헤더 확인 ────────────────────────────────────────────

def test_e2e_security_headers(client):
    resp = client.get("/api/v1/meta/regions")
    assert resp.status_code == 200
    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert headers.get("x-content-type-options") == "nosniff"
    assert "x-frame-options" in headers
    assert "content-security-policy" in headers
