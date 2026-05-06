"""Item 1 — DataSyncLog 진행률 + chunk-level resume 테스트"""
import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch  # noqa: E402

import server as server_mod  # noqa: E402
from server import app, SessionLocal, User, DataSyncLog, get_password_hash  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token(client):
    email = "sync_progress_admin@example.com"
    password = "testpass123"
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            username=email, email=email,
            hashed_password=get_password_hash(password),
            name="Sync Admin", role="admin", is_active=True,
            joined_at=datetime.now(),
        )
        db.add(user)
        db.commit()
    db.close()
    resp = client.post(f"/api/v1/auth/login?username={email}&password={password}")
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_progress_endpoint_no_active(client, admin_token):
    """진행 중이 없으면 in_progress=False"""
    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    db.commit()
    db.close()
    r = client.get("/api/v1/admin/sync/progress", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["in_progress"] is False


def test_progress_endpoint_with_active(client, admin_token):
    """in_progress 레코드가 있으면 진행률 필드를 반환"""
    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    log = DataSyncLog(
        source="G2B", sync_type="공고+낙찰 수집 (manual)",
        status="in_progress", started_at=datetime.now(),
        progress_pct=42.5, last_page=3,
        last_cursor_date=datetime(2026, 4, 1),
    )
    db.add(log)
    db.commit()
    db.close()
    r = client.get("/api/v1/admin/sync/progress", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["in_progress"] is True
    assert body["progress_pct"] == 42.5
    assert body["last_page"] == 3
    assert body["last_cursor_date"] == "2026-04-01"
    # 정리
    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    db.commit()
    db.close()


# ── Bug B — chunk-resume checkpoint 정확도 ─────────────────────────────────

def _stub_pipeline_record_visited(monkeypatch_env=None):
    """`_run_sync_for_source` 내부에서 호출되는 카테고리/윈도우 루프를
    가짜 데이터로 돌려 visited (cat_idx, win_idx, page) 좌표를 수집한다."""
    visited: list[tuple[int, int, int]] = []

    # categories 2개, 윈도우 2개, 페이지 2개씩
    fake_categories = [("용역", "getBidPblancListInfoServc"), ("공사", "getBidPblancListInfoCnstwk")]
    fake_result_categories = []  # 본 테스트 범위 외 — 단순화

    def fake_windows_iter(total_days, win_days, start_date=None):
        return iter([("2026-04-01", "2026-04-07"), ("2026-04-08", "2026-04-14")])

    def fake_http(url, timeout=15, retries=2):
        # url 에서 pageNo 추출 → 1페이지마다 1개 row, 2페이지부터는 0개로 break
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(url).query)
        page_no = int(qs.get("pageNo", ["1"])[0])
        if page_no > 1:
            return b'{"response":{"body":{"items":[]}}}'
        return b'{"response":{"body":{"items":[{"bidNtceNo":"X","bidNtceNm":"t","ntceInsttNm":"o","dminsttNm":"o","presmptPrce":"1000","bidNtceDate":"20260401"}]}}}'

    def fake_extract(payload):
        import json
        return json.loads(payload).get("response", {}).get("body", {}).get("items", [])

    def fake_normalize(source, it):
        return None  # invalid → DB write skip

    def fake_normalize_result(it):
        return None

    def fake_upsert_ann(db, source, items):
        return {"inserted": 0, "skipped": 0}

    def fake_upsert_res(db, items):
        return {"inserted": 0, "skipped": 0, "no_announcement": 0}

    def fake_build_url(source, api_key, rows, page_no, start_date, end_date, category_op):
        return f"http://x?pageNo={page_no}&op={category_op}"

    return visited, {
        "G2B_CATEGORIES": fake_categories,
        "G2B_RESULT_CATEGORIES": fake_result_categories,
        "_windows_iter": fake_windows_iter,
        "_http_fetch_with_retry": fake_http,
        "_extract_g2b_items": fake_extract,
        "_normalize_item": fake_normalize,
        "_normalize_result_item": fake_normalize_result,
        "_upsert_announcements": fake_upsert_ann,
        "_upsert_results": fake_upsert_res,
        "_build_sync_url": fake_build_url,
    }


def test_sync_resume_checkpoint(monkeypatch):
    """체크포인트 (cat=1:win=0:page=0) 가 있으면 cat 1 부터, win 0 부터, page 1 부터 재개"""
    # 환경: API 키 (실제 호출은 mock 대체)
    monkeypatch.setenv("G2B_API_KEY", "TEST")
    monkeypatch.setenv("SYNC_MAX_PAGES_ANN", "2")
    monkeypatch.setenv("SYNC_MAX_PAGES_RES", "1")

    _, stubs = _stub_pipeline_record_visited()
    for k, v in stubs.items():
        monkeypatch.setattr(server_mod, k, v, raising=False)

    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    db.commit()
    # 사전 체크포인트: 카테고리1 / 윈도우0 / 페이지0 까지 처리됨 → 다음 카테고리1 / 윈도우0 / 페이지1 재개
    prev = DataSyncLog(
        source="G2B", sync_type="공고+낙찰 수집 (manual)",
        status="failed", started_at=datetime.now(),
        progress_pct=50.0, last_page=2,
        last_checkpoint="1:0:0",
    )
    db.add(prev)
    db.commit()
    prev_id = prev.id
    db.close()

    # 실행 — 시작 좌표가 cat=1 인지 확인
    res = server_mod._run_sync_for_source("G2B", trigger="retry",
                                          resume_from_log_id=prev_id)
    # 새 in_progress 로그의 last_checkpoint 가 cat_idx=1 로 시작했는지 확인
    db = SessionLocal()
    new_log = db.query(DataSyncLog).filter(DataSyncLog.id == res["sync_id"]).first()
    # 마지막으로 commit 된 checkpoint 의 cat_idx 가 1 이상이어야 함
    assert new_log.last_checkpoint is not None
    cat_idx, win_idx, page = [int(x) for x in new_log.last_checkpoint.split(":")]
    assert cat_idx >= 1, f"resume 이 cat_idx<1 좌표를 방문해선 안 됨: {new_log.last_checkpoint}"
    db.query(DataSyncLog).filter(DataSyncLog.id.in_([prev_id, res["sync_id"]])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_retry_endpoint_with_last_page_only(client, admin_token, monkeypatch):
    """백워드 호환: 옛 last_page>0 만 있는 실패 로그 → retry 가 resume 활성화"""
    monkeypatch.setenv("G2B_API_KEY", "TEST")
    monkeypatch.setenv("SYNC_MAX_PAGES_ANN", "1")
    monkeypatch.setenv("SYNC_MAX_PAGES_RES", "1")
    _, stubs = _stub_pipeline_record_visited()
    for k, v in stubs.items():
        monkeypatch.setattr(server_mod, k, v, raising=False)

    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    db.commit()
    failed_log = DataSyncLog(
        source="G2B", sync_type="공고+낙찰 수집 (manual)",
        status="failed", started_at=datetime.now(),
        progress_pct=10.0, last_page=1, last_checkpoint=None,
    )
    db.add(failed_log)
    db.commit()
    fid = failed_log.id
    db.close()

    r = client.post(f"/api/v1/admin/sync/{fid}/retry", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert "new_sync_id" in body
    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.id.in_([fid, body["new_sync_id"]])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_retry_endpoint_with_last_page_zero(client, admin_token, monkeypatch):
    """last_page=0 이고 checkpoint 없음 → resume 비활성, 처음부터 실행"""
    monkeypatch.setenv("G2B_API_KEY", "TEST")
    monkeypatch.setenv("SYNC_MAX_PAGES_ANN", "1")
    monkeypatch.setenv("SYNC_MAX_PAGES_RES", "1")
    _, stubs = _stub_pipeline_record_visited()
    for k, v in stubs.items():
        monkeypatch.setattr(server_mod, k, v, raising=False)

    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.status == "in_progress").delete()
    db.commit()
    failed_log = DataSyncLog(
        source="G2B", sync_type="공고+낙찰 수집 (manual)",
        status="failed", started_at=datetime.now(),
        progress_pct=0.0, last_page=0, last_checkpoint=None,
    )
    db.add(failed_log)
    db.commit()
    fid = failed_log.id
    db.close()

    r = client.post(f"/api/v1/admin/sync/{fid}/retry", headers=_h(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert "new_sync_id" in body
    db = SessionLocal()
    db.query(DataSyncLog).filter(DataSyncLog.id.in_([fid, body["new_sync_id"]])).delete(synchronize_session=False)
    db.commit()
    db.close()
