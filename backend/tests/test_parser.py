"""공공데이터 응답 파서 단위 테스트 — API 키 없이 실행 가능.

_parse_date, _extract_g2b_items, _normalize_item, _upsert_announcements
의 입력-출력을 모의 페이로드로 검증한다.
"""
import json
import os
import sys
import uuid
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (  # noqa: E402
    _parse_date,
    _extract_g2b_items,
    _normalize_item,
    _upsert_announcements,
    SessionLocal,
    BidAnnouncement,
)


# ── _parse_date ───────────────────────────────────────────────────

@pytest.mark.parametrize("s,expected_year", [
    ("2026-04-20 09:30:00", 2026),
    ("2026-04-20 09:30", 2026),
    ("2026-04-20", 2026),
    ("20260420", 2026),
    ("202604200930", 2026),
    ("2026/04/20 09:30", 2026),
])
def test_parse_date_accepts_multiple_formats(s, expected_year):
    dt = _parse_date(s)
    assert dt is not None
    assert dt.year == expected_year


def test_parse_date_returns_none_for_invalid():
    assert _parse_date("invalid") is None
    assert _parse_date("") is None
    assert _parse_date(None) is None
    assert _parse_date(20260420) is None  # 숫자는 거부


# ── _extract_g2b_items ────────────────────────────────────────────

def test_extract_g2b_items_standard_structure():
    payload = json.dumps({
        "response": {
            "body": {
                "items": [
                    {"bidNtceNo": "G2B-001", "bidNtceNm": "테스트 공사"},
                    {"bidNtceNo": "G2B-002", "bidNtceNm": "테스트 용역"},
                ]
            }
        }
    }).encode("utf-8")
    items = _extract_g2b_items(payload)
    assert len(items) == 2
    assert items[0]["bidNtceNo"] == "G2B-001"


def test_extract_g2b_items_dict_wrapped():
    """items가 {item: [...]} 형태로 래핑된 경우"""
    payload = json.dumps({
        "response": {
            "body": {
                "items": {"item": [{"bidNtceNo": "G2B-999"}]}
            }
        }
    }).encode("utf-8")
    items = _extract_g2b_items(payload)
    assert len(items) == 1
    assert items[0]["bidNtceNo"] == "G2B-999"


def test_extract_g2b_items_empty_or_invalid():
    assert _extract_g2b_items(b"not json") == []
    assert _extract_g2b_items(b"{}") == []
    assert _extract_g2b_items(json.dumps({"response": {}}).encode()) == []


# ── _normalize_item ───────────────────────────────────────────────

def test_normalize_item_minimal_required():
    item = {
        "bidNtceNo": "G2B-101",
        "bidNtceNm": "도로 포장 공사",
        "dminsttNm": "서울특별시청",
        "presmptPrce": "500000000",
        "bidNtceDt": "2026-04-20 09:00",
        "bsnsDivNm": "공사",
    }
    norm = _normalize_item("G2B", item)
    assert norm is not None
    assert norm["bid_number"] == "G2B-101"
    assert norm["title"] == "도로 포장 공사"
    assert norm["ordering_org_name"] == "서울특별시청"
    assert norm["base_amount"] == 500000000
    assert norm["category"] == "공사"
    assert norm["source"] == "G2B"
    assert isinstance(norm["announced_at"], datetime)


def test_normalize_item_rejects_missing_required():
    # bidNtceNo 없음
    assert _normalize_item("G2B", {"bidNtceNm": "제목만"}) is None
    # bidNtceNm 없음
    assert _normalize_item("G2B", {"bidNtceNo": "번호만"}) is None


def test_normalize_item_category_mapping():
    for kw, expected in [("공사입찰", "공사"), ("기술용역", "용역"), ("물품구매", "물품")]:
        norm = _normalize_item("G2B", {
            "bidNtceNo": f"T-{kw}", "bidNtceNm": "제목",
            "dminsttNm": "기관", "bsnsDivNm": kw,
        })
        assert norm["category"] == expected


def test_normalize_item_handles_bad_amount():
    norm = _normalize_item("G2B", {
        "bidNtceNo": "T-001", "bidNtceNm": "제목", "dminsttNm": "기관",
        "presmptPrce": "not-a-number",
    })
    assert norm is not None
    assert norm["base_amount"] is None


def test_normalize_item_fallback_fields():
    """대체 필드명도 인식"""
    norm = _normalize_item("G2B", {
        "bidNo": "B-999", "bidNm": "대체필드 공고", "ordInsttNm": "대체기관",
        "basicAmt": 100000,
    })
    assert norm is not None
    assert norm["bid_number"] == "B-999"
    assert norm["base_amount"] == 100000


# ── _upsert_announcements ─────────────────────────────────────────

def test_upsert_announcements_skips_duplicates():
    db = SessionLocal()
    unique = uuid.uuid4().hex[:8]
    norm = {
        "source": "TEST",
        "bid_number": f"UPSERT-{unique}-001",
        "title": "업서트 테스트 공고",
        "ordering_org_name": "테스트 기관",
        "region": "서울",
        "industry_code": None,
        "base_amount": 10000,
        "bid_method": None,
        "announced_at": datetime.now(),
        "deadline_at": None,
        "category": "용역",
        "status": "진행중",
    }

    # 첫 업서트: 2건 (둘 다 신규)
    dup = {**norm, "bid_number": f"UPSERT-{unique}-002"}
    res1 = _upsert_announcements(db, "TEST", [norm, dup])
    assert res1["inserted"] == 2
    assert res1["skipped"] == 0

    # 두 번째 업서트: 동일한 bid_number 포함 → 스킵
    new_one = {**norm, "bid_number": f"UPSERT-{unique}-003"}
    res2 = _upsert_announcements(db, "TEST", [norm, new_one])
    assert res2["inserted"] == 1
    assert res2["skipped"] == 1

    # 확인: DB에 3건이 존재
    count = db.query(BidAnnouncement).filter(
        BidAnnouncement.bid_number.like(f"UPSERT-{unique}-%")
    ).count()
    db.close()
    assert count == 3


def test_upsert_announcements_empty_list():
    db = SessionLocal()
    res = _upsert_announcements(db, "TEST", [])
    db.close()
    assert res == {"inserted": 0, "skipped": 0, "updated": 0, "invalid": 0}


# ── 통합: 실 G2B 응답 시나리오 ───────────────────────────────────

def test_end_to_end_g2b_payload_parsing():
    """실제 G2B API 응답 구조를 모사한 JSON이 정확히 DB로 유입되는지"""
    unique = uuid.uuid4().hex[:8]
    payload = json.dumps({
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "numOfRows": 2,
                "items": {"item": [
                    {
                        "bidNtceNo": f"G2B-E2E-{unique}-1",
                        "bidNtceNm": "강남구청 도로공사",
                        "dminsttNm": "강남구청",
                        "presmptPrce": "123456789",
                        "bidNtceDt": "2026-04-20 14:00",
                        "bsnsDivNm": "공사입찰",
                        "prtcptLmtRgnNm": "서울",
                    },
                    {
                        "bidNtceNo": f"G2B-E2E-{unique}-2",
                        "bidNtceNm": "IT 유지보수 용역",
                        "dminsttNm": "정보통신부",
                        "presmptPrce": "50000000",
                        "bidNtceDt": "20260421",
                        "bsnsDivNm": "기술용역",
                    },
                ]},
            }
        }
    }).encode("utf-8")

    items = _extract_g2b_items(payload)
    assert len(items) == 2

    normalized = [_normalize_item("G2B", it) for it in items]
    assert all(n is not None for n in normalized)

    db = SessionLocal()
    res = _upsert_announcements(db, "G2B", normalized)
    db.close()
    assert res["inserted"] == 2
    assert res["skipped"] == 0


# ── 신규: 상태 변경 update / 증분 모드 / purge 회귀 ────────────────

def test_upsert_announcements_updates_status_when_changed():
    """기존 공고의 status/deadline_at/external_url 가 바뀌면 update 반영"""
    db = SessionLocal()
    bid_no = f"UPDATE-TEST-{uuid.uuid4().hex[:8]}"
    base = {
        "id": str(uuid.uuid4()),
        "source": "G2B", "bid_number": bid_no, "category": "용역",
        "title": "테스트 공고", "ordering_org_name": "테스트 기관",
        "base_amount": 1000000, "status": "공고중",
        "deadline_at": datetime(2026, 5, 30),
        "external_url": "http://example.com/v1",
        "announced_at": datetime(2026, 4, 20),
    }
    res1 = _upsert_announcements(db, "G2B", [base])
    assert res1 == {"inserted": 1, "skipped": 0, "updated": 0, "invalid": 0}

    # 같은 bid_number 로 다른 status + deadline + url 재호출
    base2 = dict(base)
    base2["status"] = "마감"
    base2["deadline_at"] = datetime(2026, 6, 15)
    base2["external_url"] = "http://example.com/v2"
    res2 = _upsert_announcements(db, "G2B", [base2])
    assert res2["inserted"] == 0
    assert res2["updated"] == 1

    # DB 에서 실제 반영 확인
    row = db.query(BidAnnouncement).filter(BidAnnouncement.bid_number == bid_no).first()
    assert row.status == "마감"
    assert row.deadline_at == datetime(2026, 6, 15)
    assert row.external_url == "http://example.com/v2"

    # 변경 없는 재호출은 skipped
    res3 = _upsert_announcements(db, "G2B", [base2])
    assert res3["updated"] == 0
    assert res3["skipped"] == 1

    # cleanup
    db.query(BidAnnouncement).filter(BidAnnouncement.bid_number == bid_no).delete()
    db.commit()
    db.close()


def test_windows_iter_with_start_date():
    """start_date 지정 시 해당 일자까지 모두 순회"""
    from server import _windows_iter
    ws = list(_windows_iter(0, 7, start_date="2024-01-01"))
    assert len(ws) > 50  # 2024-01-01 ~ 오늘은 50주 이상
    # 마지막 윈도우는 floor(2024-01-01) 도달
    assert ws[-1][0].startswith("20240101")


def test_windows_iter_fallback_total_days():
    """start_date 없으면 기존 total_days 동작 유지"""
    from server import _windows_iter
    ws = list(_windows_iter(60, 7))
    # 60일 / 7일 ≈ 9개 윈도우
    assert 8 <= len(ws) <= 10


# ── 사정률 예측 로직 (스펙 §1) — 3가지 구간 알고리즘 ─────────────────

def test_build_rate_histogram_basic():
    from server import _build_rate_histogram
    rates = [99.5, 99.5, 100.0, 100.1, 100.1, 100.1, 100.5]
    bins = _build_rate_histogram(rates, bin_size=0.1)
    # 모든 bin 이 (rate, count) 튜플이고 합계가 입력 길이와 일치
    assert sum(b["count"] for b in bins) == len(rates)
    # 100.1 bin 이 가장 많음 (3건)
    top = max(bins, key=lambda b: b["count"])
    assert round(top["rate"], 1) == 100.1
    assert top["count"] == 3


def test_compute_rate_buckets_mode_A_max_frequency():
    from server import _build_rate_histogram, _compute_rate_buckets
    rates = [99.5, 99.5, 100.0, 100.1, 100.1, 100.1, 100.5]
    bins = _build_rate_histogram(rates)
    buckets = _compute_rate_buckets(bins, mode="A", top_n=3)
    # 1순위는 빈도 최대값 (100.1)
    assert round(buckets[0]["rate"], 1) == 100.1
    assert buckets[0]["score"] == 3
    assert buckets[0]["mode"] == "A"
    # range_start/end 0.05 폭
    assert buckets[0]["range_end"] - buckets[0]["range_start"] == pytest.approx(0.1, abs=0.01)


def test_compute_rate_buckets_mode_B_gaps():
    from server import _build_rate_histogram, _compute_rate_buckets
    # 99.5 와 100.5 만 있고 사이는 비어있음
    rates = [99.5, 100.5]
    bins = _build_rate_histogram(rates)
    buckets = _compute_rate_buckets(bins, mode="B", top_n=3)
    # 모든 결과는 score=0 (공백 구간)
    assert all(b["score"] == 0 for b in buckets)
    # 100 에 가까운 순서
    if len(buckets) >= 2:
        assert buckets[0]["distance"] <= buckets[1]["distance"]


def test_compute_rate_buckets_mode_C_max_difference():
    from server import _build_rate_histogram, _compute_rate_buckets
    # 갑작스러운 차이를 만드는 분포: 99.5 에 5건, 99.6 에 0건
    rates = [99.5] * 5 + [100.0]
    bins = _build_rate_histogram(rates)
    buckets = _compute_rate_buckets(bins, mode="C", top_n=3)
    assert len(buckets) > 0
    # 모드 C 결과
    assert buckets[0]["mode"] == "C"


def test_extract_detail_rate_first_after():
    from server import _extract_detail_rate
    table = [99.5, 99.7, 100.0, 100.3]
    # first_after = 첫값(99.5) 바로 뒤 = 99.7
    assert _extract_detail_rate(table, rule="first_after") == 99.7


def test_extract_detail_rate_last_after():
    from server import _extract_detail_rate
    table = [99.5, 99.7, 100.0, 100.3]
    assert _extract_detail_rate(table, rule="last_after") == 100.3


def test_extract_detail_rate_max_gap():
    from server import _extract_detail_rate
    # 99.5→99.7 (gap 0.2) , 99.7→100.5 (gap 0.8 ←최대) , 100.5→100.6 (gap 0.1)
    table = [99.5, 99.7, 100.5, 100.6]
    # max_gap 직후 큰 쪽 = 100.5
    assert _extract_detail_rate(table, rule="max_gap") == 100.5


def test_extract_detail_rate_empty_returns_none():
    from server import _extract_detail_rate
    assert _extract_detail_rate([], rule="first_after") is None


# ── 매칭률 개선 — _aggregate_prelim_prices ────────────────────────────

def test_aggregate_prelim_prices_uses_selected_when_available():
    from server import _aggregate_prelim_prices
    # 공고 BID-A: 5개 예비가, 그중 2개 추첨됨 (drwt_nums)
    items = [
        {"bid_number": "BID-A", "winning_amount": 990_000, "_bssamt": 1_000_000, "_drwt_nums": "1", "opened_at": None},
        {"bid_number": "BID-A", "winning_amount": 1_010_000, "_bssamt": 1_000_000, "_drwt_nums": None, "opened_at": None},
        {"bid_number": "BID-A", "winning_amount": 1_000_000, "_bssamt": 1_000_000, "_drwt_nums": "3", "opened_at": None},
        {"bid_number": "BID-A", "winning_amount": 1_020_000, "_bssamt": 1_000_000, "_drwt_nums": None, "opened_at": None},
        {"bid_number": "BID-A", "winning_amount": 980_000, "_bssamt": 1_000_000, "_drwt_nums": None, "opened_at": None},
    ]
    result = _aggregate_prelim_prices(items)
    assert len(result) == 1
    r = result[0]
    # 추첨된 2개 평균 = (990,000 + 1,000,000) / 2 = 995,000
    assert r["winning_amount"] == 995_000
    # 사정률 = 995,000 / 1,000,000 * 100 = 99.5
    assert r["assessment_rate"] == 99.5
    # 전체 5개 가격 모두 보존
    assert len(r["preliminary_prices"].split(",")) == 5


def test_aggregate_prelim_prices_falls_back_to_all_when_no_selected():
    from server import _aggregate_prelim_prices
    # 추첨 없음 → 모든 가격 평균 fallback
    items = [
        {"bid_number": "BID-B", "winning_amount": 1_000_000, "_bssamt": 1_000_000, "_drwt_nums": None, "opened_at": None},
        {"bid_number": "BID-B", "winning_amount": 1_020_000, "_bssamt": 1_000_000, "_drwt_nums": None, "opened_at": None},
    ]
    result = _aggregate_prelim_prices(items)
    assert len(result) == 1
    # 평균 = 1,010,000 → 사정률 101%
    assert result[0]["winning_amount"] == 1_010_000
    assert result[0]["assessment_rate"] == 101.0


def test_aggregate_prelim_prices_skips_when_no_prices():
    from server import _aggregate_prelim_prices
    items = [{"bid_number": "BID-EMPTY", "winning_amount": None, "_bssamt": None, "_drwt_nums": None, "opened_at": None}]
    result = _aggregate_prelim_prices(items)
    assert result == []


# ── 정확도 헬퍼 ────────────────────────────────────────────────────

def test_remove_outliers_iqr_filters_extreme_values():
    from server import _remove_outliers_iqr
    # 정상 분포 + 극단값 2개
    rates = [99.5, 99.6, 99.7, 99.8, 99.9, 100.0, 100.1, 100.2, 50.0, 200.0]
    cleaned = _remove_outliers_iqr(rates)
    assert 50.0 not in cleaned
    assert 200.0 not in cleaned
    assert 99.5 in cleaned and 100.0 in cleaned


def test_remove_outliers_iqr_skips_when_too_few():
    from server import _remove_outliers_iqr
    # 5건 미만은 그대로
    rates = [99.5, 100.0, 50.0]
    assert _remove_outliers_iqr(rates) == rates


def test_time_weighted_rates_recent_replicated_more():
    from server import _time_weighted_rates
    from datetime import datetime, timedelta
    now = datetime.now()
    samples = [
        (99.5, now),                     # 0일 → 가중치 1.0 → 2번
        (100.0, now - timedelta(days=180)),  # 6개월 = half_life → 가중치 0.5 → 1번
        (101.0, now - timedelta(days=720)),  # 2년 → 가중치 약 0.0625 → 1번 (min)
    ]
    weighted = _time_weighted_rates(samples, half_life_days=180, ref_date=now)
    # 최근(99.5) 이 가장 많이 등장
    assert weighted.count(99.5) >= weighted.count(101.0)


def test_confidence_interval_returns_4_tuple():
    from server import _confidence_interval
    rates = [99.5, 99.6, 99.7, 99.8, 99.9, 100.0, 100.1, 100.2, 100.3, 100.4]
    mean, lower, upper, margin = _confidence_interval(rates, confidence=0.95)
    assert lower < mean < upper
    assert abs(mean - 99.95) < 0.01  # 평균 99.95 (부동소수 오차 허용)
    assert margin > 0


def test_confidence_interval_handles_single_value():
    from server import _confidence_interval
    mean, lower, upper, margin = _confidence_interval([99.5])
    assert mean == lower == upper == 99.5
    assert margin == 0


def test_homogeneity_score_high_when_same_org():
    from server import _homogeneity_score
    score = _homogeneity_score(
        "서울특별시", "421",
        ["서울특별시"] * 8 + ["타기관"] * 2,
        ["421"] * 5 + ["999"] * 5,
    )
    # 동일 발주처 80% × 0.6 + 동일 업종 50% × 0.4 = 0.48 + 0.20 = 0.68
    assert 0.6 < score < 0.7


def test_homogeneity_score_zero_when_no_match():
    from server import _homogeneity_score
    score = _homogeneity_score("A기관", "111", ["B기관"] * 5, ["222"] * 5)
    assert score == 0.0


# ── 회귀 분석 ─────────────────────────────────────────────────────

def test_ols_regression_returns_prediction():
    from server import _ols_regression
    samples = [
        {"rate": 99.5 + 0.1 * (i % 3), "base_amount": 100_000_000 + i * 1_000_000,
         "category": "용역" if i % 2 else "공사", "region": "서울" if i % 3 else "경기",
         "industry": "421", "org_type": None, "days_old": i * 5}
        for i in range(20)
    ]
    target = {"base_amount": 150_000_000, "category": "용역",
              "region": "서울", "industry": "421", "org_type": None, "days_old": 0}
    result = _ols_regression(samples, target)
    assert result["predicted_rate"] is not None
    assert 90 <= result["predicted_rate"] <= 110
    assert result["r_squared"] is not None
    assert result["n"] == 20
    assert "top_features" in result
    assert len(result["top_features"]) <= 5


def test_ols_regression_too_few_samples():
    from server import _ols_regression
    result = _ols_regression([{"rate": 99.5, "base_amount": 1, "category": "용역",
                                "region": "서울", "industry": None, "org_type": None,
                                "days_old": 0}], {})
    assert result["predicted_rate"] is None
    assert "표본 부족" in result["reason"]


# ── 앙상블 + 모멘텀 + Walk-forward ────────────────────────────────

def test_ensemble_predict_weighted_average():
    from server import _ensemble_predict
    result = _ensemble_predict([
        {"name": "A", "rate": 100.0, "weight": 100},
        {"name": "B", "rate": 99.0, "weight": 50},
    ])
    # weighted = (100*100 + 99*50) / 150 = 99.667
    assert abs(result["final_rate"] - 99.6667) < 0.001
    assert len(result["contributions"]) == 2
    # share 합 = 100%
    assert sum(c["share"] for c in result["contributions"]) > 99.9


def test_ensemble_predict_skips_none_rates():
    from server import _ensemble_predict
    result = _ensemble_predict([
        {"name": "A", "rate": 100.0, "weight": 10},
        {"name": "B", "rate": None, "weight": 5},
    ])
    assert result["final_rate"] == 100.0
    assert len(result["contributions"]) == 1


def test_trend_momentum_detects_upward():
    from server import _trend_momentum
    series = [{"period": f"2025-{m:02d}", "avg_rate": 99.0 + m * 0.1, "count": 10}
              for m in range(1, 7)]
    result = _trend_momentum(series)
    assert result["direction"] == "up"
    assert result["slope"] > 0
    assert result["next_predicted"] > 99.6


def test_trend_momentum_detects_flat():
    from server import _trend_momentum
    series = [{"period": f"2025-{m:02d}", "avg_rate": 99.5 + (m % 2) * 0.01, "count": 10}
              for m in range(1, 7)]
    result = _trend_momentum(series)
    assert result["direction"] == "flat"


def test_walk_forward_validate_returns_windows():
    from server import _walk_forward_validate
    from datetime import datetime, timedelta
    base = datetime(2024, 1, 1)
    samples = [(99.5 + (i % 5) * 0.1, base + timedelta(days=i * 3)) for i in range(120)]
    result = _walk_forward_validate(samples, window_days=60, stride_days=30)
    assert len(result["windows"]) > 0
    assert result["overall_mae"] is not None
    assert result["overall_mae"] >= 0


# ── Bayesian Shrinkage / 이상 탐지 / K-NN ────────────────────────

def test_bayesian_shrinkage_pulls_small_sample_to_global():
    from server import _bayesian_shrinkage
    # 발주처 단 1건 → global 영향력 ↑
    result = _bayesian_shrinkage([99.0], [100.0] * 100, prior_strength=10)
    # 가중 = (1×99 + 10×100) / 11 = 99.909
    assert abs(result["shrunk_rate"] - 99.909) < 0.01
    assert result["shrinkage_factor"] > 0.9  # 거의 global 쪽으로

def test_bayesian_shrinkage_large_sample_keeps_local():
    from server import _bayesian_shrinkage
    # 발주처 100건 → local 영향력 ↑
    result = _bayesian_shrinkage([99.0] * 100, [100.0] * 100, prior_strength=10)
    # 가중 = (100×99 + 10×100) / 110 = 99.0909
    assert abs(result["shrunk_rate"] - 99.091) < 0.01
    assert result["shrinkage_factor"] < 0.1


def test_detect_anomaly_flags_extreme_value():
    from server import _detect_anomaly
    peers = [100.0] * 50 + [101.0] * 50  # 평균 100.5, std≈0.5
    result = _detect_anomaly(110.0, peers, z_threshold=2.0)
    assert result["is_anomaly"] is True
    assert result["abs_z"] > 2.0
    assert result["severity"] in ("medium", "high")


def test_detect_anomaly_normal_value():
    from server import _detect_anomaly
    peers = [99.5, 99.8, 100.0, 100.1, 100.3, 100.5]
    result = _detect_anomaly(100.0, peers, z_threshold=2.0)
    assert result["is_anomaly"] is False
    assert result["severity"] == "normal"


def test_knn_similar_returns_top_k_sorted():
    from server import _knn_similar_announcements
    target = {"base_amount": 100_000_000, "region": "서울", "industry": "421",
              "category": "용역"}
    candidates = [
        {"id": "A", "base_amount": 110_000_000, "region": "서울", "industry": "421",
         "days_old": 10},
        {"id": "B", "base_amount": 500_000_000, "region": "부산", "industry": "999",
         "days_old": 200},
        {"id": "C", "base_amount": 100_000_000, "region": "서울", "industry": "421",
         "days_old": 5},
    ]
    result = _knn_similar_announcements(target, candidates, k=2)
    assert len(result) == 2
    # C 가 가장 비슷 (동일 기초/지역/업종, 최근)
    assert result[0]["id"] == "C"
    # similarity 내림차순 정렬
    assert result[0]["similarity"] >= result[1]["similarity"]


# ── K-means + 모델 재학습 ─────────────────────────────────────────

def test_kmeans_simple_groups_features():
    from server import _kmeans_simple
    # 3개 명확한 클러스터
    feats = (
        [[1.0, 1.0]] * 10 +   # 군집 A
        [[10.0, 10.0]] * 10 + # 군집 B
        [[5.0, 5.0]] * 10     # 군집 C
    )
    labels, centroids = _kmeans_simple(feats, k=3, seed=1)
    assert len(labels) == 30
    # 동일 입력 벡터는 같은 군집
    assert labels[0] == labels[1] == labels[9]
    assert labels[10] == labels[11]
    assert labels[20] == labels[21]
    # 최소 2개 이상 군집 형성 (random init 영향)
    assert len(set(labels)) >= 2


def test_kmeans_simple_handles_few_features():
    from server import _kmeans_simple
    labels, _ = _kmeans_simple([[1.0]], k=3)
    # 표본 < k 면 모두 군집 0
    assert labels == [0]
