"""스모크 테스트 — 주요 엔드포인트가 기본 응답을 반환하는지 확인

실행:
    cd backend && python3 -m pytest tests/ -v
"""
import io
import os
import sys

import pytest
from fastapi.testclient import TestClient

# server.py를 import 할 수 있도록 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app, SessionLocal, User, get_password_hash  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client):
    """테스트용 사용자로 로그인 후 토큰 획득"""
    email = "smoke_test@example.com"
    password = "testpass123"

    # 사용자 없으면 직접 생성 (register endpoint 의존 회피)
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            username=email,
            email=email,
            hashed_password=get_password_hash(password),
            name="Smoke Tester",
            role="admin",
            is_active=True,
            joined_at=__import__("datetime").datetime.now(),
        )
        db.add(user)
        db.commit()
    db.close()

    resp = client.post(
        f"/api/v1/auth/login?username={email}&password={password}",
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 인증 ───────────────────────────────────────────────────────────

def test_auth_me(client, auth_token):
    resp = client.get("/api/v1/auth/me", headers=_auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data


def test_auth_unauthorized(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


# ── 메타 ───────────────────────────────────────────────────────────

def test_meta_regions(client):
    resp = client.get("/api/v1/meta/regions")
    assert resp.status_code == 200
    data = resp.json()
    # 응답은 list 또는 {"regions": [...]} 허용
    regions = data if isinstance(data, list) else data.get("regions", [])
    assert len(regions) >= 15  # 최소 15개 지역


# ── 공고 ───────────────────────────────────────────────────────────

def test_announcements_list(client):
    resp = client.get("/api/v1/announcements")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or isinstance(data, list)


# ── 관리자 ─────────────────────────────────────────────────────────

def test_admin_dashboard_requires_auth(client):
    resp = client.get("/api/v1/admin/dashboard")
    assert resp.status_code in (401, 403)


# 모든 admin 엔드포인트가 비인증 접근 시 401/403을 반환하는지 일괄 검증.
# Phase 1: require_admin 누락 보강의 회귀 방지 테스트.
ADMIN_ENDPOINTS = [
    ("GET",    "/api/v1/admin/dashboard"),
    ("POST",   "/api/v1/admin/sync"),
    ("POST",   "/api/v1/admin/sync/diagnose"),
    ("GET",    "/api/v1/admin/nas-status"),
    ("PUT",    "/api/v1/admin/users/dummy-id/status"),
    ("GET",    "/api/v1/admin/sync/history"),
    ("POST",   "/api/v1/admin/sync/dummy-sync-id/retry"),
    ("GET",    "/api/v1/admin/schedule"),
    ("PUT",    "/api/v1/admin/schedule?interval=daily"),
    ("GET",    "/api/v1/admin/errors"),
]


@pytest.mark.parametrize("method,url", ADMIN_ENDPOINTS)
def test_admin_endpoints_require_admin(client, method, url):
    """비인증/일반 사용자로 admin 엔드포인트 호출 시 401/403."""
    resp = client.request(method, url)
    assert resp.status_code in (401, 403), (
        f"{method} {url} → {resp.status_code} (expected 401/403)"
    )


def test_admin_schedule(client, auth_token):
    resp = client.get("/api/v1/admin/schedule", headers=_auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "interval" in data
    assert "enabled" in data
    assert "scheduler_running" in data  # APScheduler 통합 확인


def test_admin_schedule_update(client, auth_token):
    resp = client.put(
        "/api/v1/admin/schedule?interval=daily&time=03:30&enabled=true",
        headers=_auth_headers(auth_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval"] == "daily"
    assert data["time"] == "03:30"


def test_admin_schedule_invalid_interval(client, auth_token):
    resp = client.put(
        "/api/v1/admin/schedule?interval=invalid&time=00:00&enabled=true",
        headers=_auth_headers(auth_token),
    )
    assert resp.status_code == 400


def test_admin_manual_sync(client, auth_token):
    resp = client.post("/api/v1/admin/sync", headers=_auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    # 기본은 G2B만 호출 (국방부 데이터 포함). D2B는 ENABLE_D2B_SYNC=true 시에만 추가됨
    assert len(data["results"]) >= 1
    assert any(r["source"] == "G2B" for r in data["results"])
    assert all("status" in r for r in data["results"])


def test_admin_sync_diagnose_without_key(client, auth_token):
    """API 키 미설정 시 진단 엔드포인트는 ok=False + steps 반환"""
    import os as _os
    saved = _os.environ.pop("G2B_API_KEY", None)
    try:
        resp = client.post("/api/v1/admin/sync/diagnose?source=G2B&rows=2",
                          headers=_auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "G2B"
        assert data["ok"] is False
        assert any(s["step"] == "api_key" and not s["ok"] for s in data["steps"])
    finally:
        if saved is not None:
            _os.environ["G2B_API_KEY"] = saved


def test_admin_sync_history(client, auth_token):
    resp = client.get("/api/v1/admin/sync/history", headers=_auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# ── 데이터 업로드 ─────────────────────────────────────────────────

def test_upload_rejects_bad_extension(client, auth_token):
    resp = client.post(
        "/api/v1/data/upload",
        headers=_auth_headers(auth_token),
        files={"file": ("test.txt", io.BytesIO(b"dummy"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "허용되지 않는" in resp.json()["detail"]


def test_upload_csv_with_errors(client, auth_token):
    """필수 컬럼 + 오류 행 + 중복 포함한 CSV (매회 고유한 공고번호)"""
    import time
    prefix = f"SMK-{int(time.time())}"
    csv = (
        "공고번호,공고명,발주기관,기초금액,지역\n"
        f"{prefix}-001,테스트공고1,테스트청,100000000,서울특별시\n"
        f"{prefix}-002,테스트공고2,테스트청,,경기도\n"  # 기초금액 누락 → 오류
        f"{prefix}-003,테스트공고3,테스트청,abc,부산광역시\n"  # 숫자 변환 실패 → 오류
        f"{prefix}-001,중복공고,테스트청,200000000,서울특별시\n"  # 파일 내 중복
        f"{prefix}-004,,테스트청,300000000,대구광역시\n"  # 공고명 누락 → 오류
    ).encode("utf-8")
    resp = client.post(
        "/api/v1/data/upload",
        headers=_auth_headers(auth_token),
        files={"file": ("smoke.csv", io.BytesIO(csv), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    summary = data["summary"]
    assert summary["total"] == 5
    assert summary["inserted"] >= 1
    assert summary["errors"] == 3
    assert summary["duplicates"] == 1
    assert len(data["error_rows"]) == 3


def test_upload_missing_required_column(client, auth_token):
    csv = "공고번호,공고명\nSMK-100,일부컬럼만\n".encode("utf-8")
    resp = client.post(
        "/api/v1/data/upload",
        headers=_auth_headers(auth_token),
        files={"file": ("missing.csv", io.BytesIO(csv), "text/csv")},
    )
    assert resp.status_code == 400
    assert "필수 컬럼" in resp.json()["detail"]


# ── 사정률 예측 로직 (Phase B/C/D/E) 회귀 ────────────────────────────────

def test_rate_buckets_endpoint_smoke(client):
    """rate-buckets 엔드포인트 — 비인증 호출 시 401, 또는 정상 응답"""
    resp = client.get("/api/v1/analysis/rate-buckets/dummy-id?period_months=6")
    # 인증 필요하므로 401 또는 공고 없음 메시지
    assert resp.status_code in (200, 401, 422)


def test_correlation_endpoint_smoke(client):
    resp = client.get("/api/v1/analysis/correlation/dummy-id?period_months=6&bucket_mode=A")
    assert resp.status_code in (200, 401, 422)


def test_prediction_settings_get_requires_auth(client):
    resp = client.get("/api/v1/users/me/prediction-settings")
    assert resp.status_code in (401, 403)


def test_prediction_settings_put_requires_auth(client):
    resp = client.put("/api/v1/users/me/prediction-settings", json={"period_months": 12})
    assert resp.status_code in (401, 403)


def test_export_xlsx_requires_auth(client):
    resp = client.get("/api/v1/analysis/export/buckets?announcement_id=dummy")
    assert resp.status_code in (401, 403)


def test_export_xlsx_invalid_type(client):
    """잘못된 export_type — 인증 거부 또는 400 반환"""
    resp = client.get("/api/v1/analysis/export/INVALID?announcement_id=dummy")
    assert resp.status_code in (400, 401, 403, 404)
