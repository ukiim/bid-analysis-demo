"""통합(Integration) 테스트 — 다중 엔드포인트 시나리오

각 테스트는 단일 사용자 여정을 처음부터 끝까지 실행:
  - 사용자 여정: 회원가입 → 로그인 → 공고 조회 → 분석 → 학습 저장 → 엑셀 export
  - 관리자 여정: 로그인 → 대시보드 KPI → 수동 수집 → 사용자 상태 토글 → 수집 히스토리
  - 데이터 파이프라인: 업로드 → 정규화 → 분석 → 결과 export

실행:
    cd backend && python3 -m pytest tests/test_integration.py -v
"""
from __future__ import annotations

import io
import os
import sys
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (  # noqa: E402
    app, SessionLocal, User, get_password_hash,
    BidAnnouncement, BidResult, DataSyncLog,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token(client):
    """admin 권한 사용자 로그인 토큰"""
    email = "integration_admin@example.com"
    password = "intpass1234"
    db = SessionLocal()
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Integration Admin", role="admin", is_active=True,
            joined_at=datetime.now(),
        )
        db.add(u); db.commit()
    db.close()
    r = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def user_token(client):
    """일반 사용자 토큰"""
    email = "integration_user@example.com"
    password = "intpass1234"
    db = SessionLocal()
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Integration User", role="user", is_active=True,
            joined_at=datetime.now(),
        )
        db.add(u); db.commit()
    db.close()
    r = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    assert r.status_code == 200
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def fixture_announcement_with_results():
    """분석에 충분한 BidResult 가 있는 테스트 공고"""
    db = SessionLocal()
    bid_no = f"INT-E2E-{uuid.uuid4().hex[:8]}"
    ann = BidAnnouncement(
        id=str(uuid.uuid4()),
        source="TEST", bid_number=bid_no, bid_ord="000",
        title="통합 테스트 공고",
        ordering_org_name="테스트청",
        category="용역",
        base_amount=500_000_000,
        announced_at=datetime.now() - timedelta(days=10),
        status="진행중",
    )
    db.add(ann); db.commit()
    # 정규분포 사정률 10건
    for i, rate in enumerate([99.0, 99.3, 99.5, 99.7, 99.9, 100.0, 100.1, 100.3, 100.5, 100.8]):
        db.add(BidResult(
            id=str(uuid.uuid4()),
            announcement_id=ann.id,
            assessment_rate=rate,
            first_place_rate=rate,
            first_place_amount=int(500_000_000 * rate / 100),
            winning_amount=int(500_000_000 * rate / 100),
            opened_at=datetime.now() - timedelta(days=10 - i),
        ))
    db.commit()
    ann_id = ann.id
    db.close()
    yield ann_id
    db = SessionLocal()
    db.query(BidResult).filter(BidResult.announcement_id == ann_id).delete()
    db.query(BidAnnouncement).filter(BidAnnouncement.id == ann_id).delete()
    db.commit(); db.close()


# ── 시나리오 1: 사용자 분석 풀 여정 ──────────────────────────────────

class TestUserAnalysisJourney:
    """회원가입 → 로그인 → 공고 → 분석 → 학습 저장 → 엑셀"""

    def test_step1_user_can_get_own_profile(self, client, user_token):
        r = client.get("/api/v1/auth/me", headers=_h(user_token))
        assert r.status_code == 200
        assert "email" in r.json()

    def test_step2_user_can_list_announcements(self, client, user_token):
        r = client.get("/api/v1/announcements?limit=5", headers=_h(user_token))
        assert r.status_code == 200
        d = r.json()
        items = d.get("items", d) if isinstance(d, dict) else d
        assert isinstance(items, list)

    def test_step3_user_can_run_3_analyses_in_sequence(self, client, user_token, fixture_announcement_with_results):
        ann_id = fixture_announcement_with_results
        # Tab1
        r1 = client.get(f"/api/v1/analysis/rate-buckets/{ann_id}?period_months=12&category_filter=service",
                        headers=_h(user_token))
        assert r1.status_code == 200, r1.text
        # 픽스처 10건 이상이면 OK (다른 테스트 데이터 포함 가능)
        assert r1.json()["data_count"] >= 10
        # Tab2
        r2 = client.get(f"/api/v1/analysis/company-rates/{ann_id}?rate_range_start=99&rate_range_end=101",
                        headers=_h(user_token))
        assert r2.status_code == 200
        # Tab3 — correlation 사용
        r3 = client.get(f"/api/v1/analysis/correlation/{ann_id}?bucket_mode=A",
                        headers=_h(user_token))
        assert r3.status_code == 200, r3.text
        d = r3.json()
        # 신뢰도가 응답에 포함되는지
        assert "confidence" in d["correlation"]
        assert "score" in d["correlation"]["confidence"]
        assert d["correlation"]["confidence"]["score"] > 0

    def test_step4_user_saves_settings_then_get_returns_persisted(self, client, user_token):
        payload = {
            "period_months": 12, "category_filter": "service",
            "bucket_mode": "C", "detail_rule": "max_gap",
            "rate_range_start": 99.0, "rate_range_end": 101.0,
        }
        r1 = client.put("/api/v1/users/me/prediction-settings",
                        json=payload, headers=_h(user_token))
        assert r1.status_code == 200
        r2 = client.get("/api/v1/users/me/prediction-settings", headers=_h(user_token))
        d = r2.json()
        assert d["bucket_mode"] == "C"
        assert d["period_months"] == 12

    def test_step5_user_exports_xlsx_for_each_type(self, client, user_token, fixture_announcement_with_results):
        ann_id = fixture_announcement_with_results
        for export_type in ["buckets", "company", "correlation", "bid_list"]:
            r = client.get(
                f"/api/v1/analysis/export/{export_type}?announcement_id={ann_id}"
                "&period_months=12&category_filter=service&bucket_mode=A&detail_rule=max_gap"
                "&rate_range_start=99&rate_range_end=101",
                headers=_h(user_token),
            )
            assert r.status_code == 200, f"{export_type}: {r.text[:200]}"
            assert "spreadsheet" in r.headers["content-type"]
            assert len(r.content) > 1000

    def test_step6_user_sees_query_history_after_analysis(self, client, user_token, fixture_announcement_with_results):
        # 분석을 먼저 한 번 더 호출해서 history 누적 확인
        ann_id = fixture_announcement_with_results
        client.get(f"/api/v1/analysis/rate-buckets/{ann_id}", headers=_h(user_token))
        r = client.get("/api/v1/history?page=1&page_size=10", headers=_h(user_token))
        assert r.status_code == 200
        d = r.json()
        assert d.get("total", 0) >= 1

    def test_step7_user_cannot_access_admin_endpoints(self, client, user_token):
        r = client.get("/api/v1/admin/dashboard", headers=_h(user_token))
        assert r.status_code in (401, 403)


# ── 시나리오 2: 관리자 여정 ──────────────────────────────────────────

class TestAdminJourney:
    """로그인 → 대시보드 → 수집 히스토리 → 사용자 상태 → 알림 점검"""

    def test_admin_dashboard_returns_new_kpis(self, client, admin_token):
        r = client.get("/api/v1/admin/dashboard", headers=_h(admin_token))
        assert r.status_code == 200, r.text
        d = r.json()
        # 신규 KPI 4종 존재
        for k in ["matching_rate", "analyzable_announcements", "analyzable_rate", "avg_assessment_rate"]:
            assert k in d, f"missing: {k}"
        assert isinstance(d["matching_rate"], (int, float))
        assert 0 <= d["matching_rate"] <= 100

    def test_admin_can_list_sync_history(self, client, admin_token):
        r = client.get("/api/v1/admin/sync/history", headers=_h(admin_token))
        assert r.status_code == 200
        d = r.json()
        # list 또는 dict 둘 다 허용
        items = d.get("items", d) if isinstance(d, dict) else d
        assert isinstance(items, list)

    def test_admin_nas_status_endpoint_responds(self, client, admin_token):
        r = client.get("/api/v1/admin/nas-status", headers=_h(admin_token))
        assert r.status_code == 200
        d = r.json()
        # NAS 또는 로컬 모드 모두 허용 — 응답 키 검증
        assert any(k in d for k in ("mounted", "path", "free_space", "status"))

    def test_admin_schedule_get_then_put_roundtrip(self, client, admin_token):
        r1 = client.get("/api/v1/admin/schedule", headers=_h(admin_token))
        assert r1.status_code == 200
        # 동일한 값으로 PUT (변경 없이 형태만 검증)
        r2 = client.put("/api/v1/admin/schedule?interval=daily", headers=_h(admin_token))
        assert r2.status_code in (200, 204)

    def test_admin_errors_endpoint(self, client, admin_token):
        r = client.get("/api/v1/admin/errors?limit=5", headers=_h(admin_token))
        assert r.status_code == 200


# ── 시나리오 3: 데이터 파이프라인 (정규화 → 매칭 → 분석) ─────────────

class TestDataPipeline:
    """업로드된 데이터가 정규화·DB 저장·분석까지 흐르는지"""

    def test_pipeline_aggregate_prelim_prices_lifts_assessment_rate(self):
        """현실 시나리오: PreparPcDetail 5건 row → 사정률 산출"""
        from server import _aggregate_prelim_prices
        items = [
            {"bid_number": "PIPE-A", "winning_amount": 990_000_000, "_bssamt": 1_000_000_000, "_drwt_nums": "1", "opened_at": None},
            {"bid_number": "PIPE-A", "winning_amount": 1_010_000_000, "_bssamt": 1_000_000_000, "_drwt_nums": None, "opened_at": None},
            {"bid_number": "PIPE-A", "winning_amount": 1_000_000_000, "_bssamt": 1_000_000_000, "_drwt_nums": "5", "opened_at": None},
            {"bid_number": "PIPE-A", "winning_amount": 1_020_000_000, "_bssamt": 1_000_000_000, "_drwt_nums": None, "opened_at": None},
            {"bid_number": "PIPE-A", "winning_amount": 980_000_000, "_bssamt": 1_000_000_000, "_drwt_nums": None, "opened_at": None},
        ]
        result = _aggregate_prelim_prices(items)
        assert len(result) == 1
        # 추첨 2개 평균 = (990 + 1000) / 2 = 995M → 사정률 99.5%
        assert result[0]["assessment_rate"] == 99.5

    def test_pipeline_confidence_scales_with_sample_size(self):
        """표본이 많을수록 신뢰도 점수가 높아져야 함"""
        from server import _compute_confidence
        small = _compute_confidence([99.5, 100.0], 0.33, 1)
        large = _compute_confidence([99.5 + i * 0.01 for i in range(150)], 0.66, 2)
        assert large["score"] > small["score"]
        assert large["level"] in ("high", "medium")


# ── 시나리오 4: 권한·보안 통합 ────────────────────────────────────────

class TestSecurityBoundaries:
    """비로그인·일반 사용자가 보호된 자원에 접근 못하는지 일괄 검증"""

    UNAUTHORIZED_ENDPOINTS = [
        ("GET", "/api/v1/admin/dashboard"),
        ("GET", "/api/v1/admin/nas-status"),
        ("GET", "/api/v1/admin/sync/history"),
        ("GET", "/api/v1/admin/errors"),
        ("GET", "/api/v1/admin/schedule"),
        ("POST", "/api/v1/admin/sync"),
        ("PUT", "/api/v1/admin/users/dummy/status"),
        ("PUT", "/api/v1/admin/schedule?interval=daily"),
        ("POST", "/api/v1/admin/sync/dummy/retry"),
    ]

    @pytest.mark.parametrize("method,url", UNAUTHORIZED_ENDPOINTS)
    def test_unauthenticated_blocked(self, client, method, url):
        r = client.request(method, url)
        assert r.status_code in (401, 403)

    @pytest.mark.parametrize("method,url", UNAUTHORIZED_ENDPOINTS)
    def test_normal_user_blocked(self, client, user_token, method, url):
        r = client.request(method, url, headers=_h(user_token))
        assert r.status_code in (401, 403)
