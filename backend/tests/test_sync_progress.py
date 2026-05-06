"""Item 1 — DataSyncLog 진행률 + chunk-level resume 테스트"""
import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
