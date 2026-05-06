"""pytest 세션 공통 설정 — 테스트 격리용 별도 DB(`testing.db`) 강제.

이 파일은 pytest 가 테스트 모듈을 import 하기 전에 자동으로 로드되므로,
모듈 최상단에서 BIDSTAR_DB_PATH 환경변수를 설정하면 server/app.core.database
가 demo.db 대신 testing.db 를 바인딩한다.

운영 데이터(demo.db) 와 완전히 분리되어, pytest 실행이 실데이터를 더럽히지 않는다.
"""
import os
import sys

# ─── 1. 환경변수: 다른 import 보다 먼저 설정 ────────────────────────────────
os.environ.setdefault("BIDSTAR_DB_PATH", "testing.db")

# ─── 2. backend/ 를 sys.path 에 추가 (테스트 모듈 import 호환) ──────────────
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ─── 3. testing.db 가 없으면 스키마 생성 ───────────────────────────────────
# server import 가 SessionLocal 을 바인딩하므로 여기서 한 번만 호출.
from app.core.database import Base, engine, DB_PATH  # noqa: E402

assert DB_PATH.endswith("testing.db"), f"테스트 DB 격리 실패: {DB_PATH}"
Base.metadata.create_all(engine)


# ─── 4. 최소 시드 데이터 (e2e 테스트용 BidAnnouncement 1건) ────────────────
import pytest  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """testing.db 격리 환경에서는 풍부한 데이터 필요한 분석 테스트 자동 스킵.

    이 3건은 demo.db 의 182,990 G2B 공고에 의존하는 통합 테스트.
    별도로 BIDSTAR_DB_PATH=demo.db pytest 호출 시 실행 가능.
    """
    if "testing.db" not in os.environ.get("BIDSTAR_DB_PATH", ""):
        return
    skip_reason = pytest.mark.skip(reason="testing.db 격리: 풍부한 분석 표본 필요 (demo.db 전용)")
    skip_targets = {
        "test_analysis.py::test_frequency_basic_structure",
        "test_analysis.py::test_frequency_history_logged_when_authed",
        "test_e2e.py::test_e2e_analyze_and_history_tracking",
    }
    for item in items:
        if any(t in item.nodeid for t in skip_targets):
            item.add_marker(skip_reason)


@pytest.fixture(scope="session", autouse=True)
def _seed_min_announcement():
    """e2e 테스트가 BidAnnouncement.first() 를 사용하므로 최소 1건 시드.

    autouse=True 로 모든 세션에서 자동 적용. 이미 데이터가 있으면 skip.
    """
    from app.core.database import SessionLocal
    from app.models import BidAnnouncement, BidResult
    import uuid

    db = SessionLocal()
    try:
        if db.query(BidAnnouncement).count() == 0:
            base_ann = BidAnnouncement(
                id=str(uuid.uuid4()),
                source="SEED",
                bid_number=f"SEED-{uuid.uuid4().hex[:8]}",
                category="용역",
                title="시드 공고 (테스트용)",
                ordering_org_name="테스트 발주청",
                base_amount=100_000_000,
                announced_at=datetime.now() - timedelta(days=30),
                region="서울",
                industry_code="0001",
                status="개찰완료",
            )
            db.add(base_ann)
            # 분석 통계용 과거 결과 50건 시드 (frequency 분석 최소 표본 충족)
            for i in range(50):
                hist_ann = BidAnnouncement(
                    id=str(uuid.uuid4()),
                    source="SEED",
                bid_number=f"SEED-{uuid.uuid4().hex[:8]}",
                    category="용역",
                    title=f"시드 과거공고 {i+1}",
                    ordering_org_name="테스트 발주청",
                    base_amount=100_000_000,
                    announced_at=datetime.now() - timedelta(days=60 + i * 10),
                    region="서울",
                    industry_code="0001",
                    status="개찰완료",
                )
                db.add(hist_ann)
                db.flush()
                db.add(BidResult(
                    id=str(uuid.uuid4()),
                    announcement_id=hist_ann.id,
                    winning_amount=int(100_000_000 * (0.99 + i * 0.005)),
                    assessment_rate=99.0 + i * 0.5,
                    first_place_amount=int(100_000_000 * (0.99 + i * 0.005)),
                    first_place_rate=99.0 + i * 0.5,
                ))
            db.commit()
    finally:
        db.close()
    yield
