"""사정률 예측 분석 헬퍼 — server.py L858-1495 에서 분리 (F3).

스펙 §1: 3가지 구간 알고리즘 (히스토그램, 시간가중, KNN/OLS, 베이지안 등)
모든 함수는 순수 함수에 가까우며, 유일한 ORM 의존성은 _apply_category_filter
가 BidAnnouncement 를 사용하는 것뿐이다.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta

from app.models import BidAnnouncement, BidResult


# ─── 사정률 예측 로직 (스펙 §1) — 3가지 구간 알고리즘 ─────────────────────

def _resolve_recent_results(db, target: BidAnnouncement,
                              lookback_days: list = None) -> dict:
    """동일 공종 + 동일 지역 우선 fallback (Item 5).

    target_industry + target_region + announced_at 가 N일 내인 BidResult 표본을
    단계적으로 확장하여 최소 10건 이상이 될 때까지 lookback 일수를 늘린다.
    Returns: {results: list[(BidResult, BidAnnouncement)], lookback_used_days, sample_source}
    """
    lookbacks = lookback_days or [30, 90, 180]
    ref_date = target.announced_at or datetime.now()
    last_results: list = []
    last_lookback = lookbacks[-1]
    for ld in lookbacks:
        cutoff = ref_date - timedelta(days=ld)
        q = db.query(BidResult, BidAnnouncement).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == target.category,
            BidResult.opened_at.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        if target.industry_code:
            q = q.filter(BidAnnouncement.industry_code == target.industry_code)
        if target.region:
            q = q.filter(BidAnnouncement.region == target.region)
        rows = q.all()
        last_results = rows
        last_lookback = ld
        if len(rows) >= 10:
            break
    sample_source = (
        f"기간:{last_lookback}일/공종:{target.industry_code or '전체'}/"
        f"지역:{target.region or '전국'}"
    )
    return {
        "results": last_results,
        "lookback_used_days": last_lookback,
        "sample_source": sample_source,
    }


def _remove_outliers_iqr(values: list, multiplier: float = 1.5) -> list:
    """IQR 기반 이상치 제거 — 사정률 분포 안정화.

    Q1-1.5×IQR ~ Q3+1.5×IQR 구간 밖 제거.
    표본이 5건 미만이면 그대로 반환 (제거 시 무의미).
    """
    if len(values) < 5:
        return list(values)
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return [v for v in values if lower <= v <= upper]


def _time_weighted_rates(rates_with_dates: list, half_life_days: int = 180,
                          ref_date: datetime = None) -> list:
    """시계열 가중치 — 최근 데이터를 더 높게 (지수 감쇠).

    Args:
        rates_with_dates: [(rate, date), ...]
        half_life_days: 가중치가 절반이 되는 일수 (기본 6개월)
        ref_date: 기준일 (기본 오늘)
    Returns:
        weight 적용한 rates 리스트 (가중 표본 — 가중치만큼 복제)
        예) 가중치 0.5 → 1번 등장, 가중치 1.0 → 2번 등장
    """
    if not rates_with_dates:
        return []
    ref = ref_date or datetime.now()
    import math as _math
    weighted = []
    for rate, dt in rates_with_dates:
        if not dt:
            weighted.append(rate)  # 날짜 없으면 가중치 1
            continue
        days_old = (ref - dt).days if isinstance(dt, datetime) else 0
        # exp(-ln(2) * t / half_life) → t=0 일 때 1, t=half_life 일 때 0.5
        weight = _math.exp(-_math.log(2) * max(0, days_old) / half_life_days)
        # 0~2 범위로 환산 — 가중치 1 = 표본 2번 카운트, 0.5 = 1번
        replicate = max(1, int(round(weight * 2)))
        weighted.extend([rate] * replicate)
    return weighted


def _confidence_interval(values: list, confidence: float = 0.95) -> tuple:
    """평균 ± 신뢰구간 (정규분포 가정, n≥10 권장).

    Returns: (mean, lower, upper, margin)
    margin = z * std / sqrt(n)
    """
    if not values:
        return (None, None, None, None)
    if len(values) < 2:
        return (values[0], values[0], values[0], 0)
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    n = len(values)
    # z-score: 95% → 1.96, 99% → 2.576
    z = 2.576 if confidence >= 0.99 else 1.96 if confidence >= 0.95 else 1.645
    margin = z * std / (n ** 0.5)
    return (round(mean, 4), round(mean - margin, 4), round(mean + margin, 4), round(margin, 4))


def _homogeneity_score(target_org: str, target_industry: str,
                        sample_orgs: list, sample_industries: list) -> float:
    """동종성 점수 — 표본이 대상 공고와 얼마나 유사한가 (0~1).

    동일 발주처 비율(0.6) + 동일 업종 비율(0.4) 가중 평균.
    """
    if not sample_orgs:
        return 0.0
    n = len(sample_orgs)
    same_org = sum(1 for o in sample_orgs if o == target_org) / n
    same_ind = (sum(1 for i in sample_industries if i and i == target_industry) / n
                if target_industry else 0)
    return round(same_org * 0.6 + same_ind * 0.4, 4)


# ─── 앙상블 + 모멘텀 + Walk-forward ──────────────────────────────────

def _ensemble_predict(predictions: list) -> dict:
    """가중 앙상블 예측.

    Args:
        predictions: [{rate, weight, name}, ...]
                     weight 가 클수록 영향 큼. None rate 는 자동 제외.
    Returns:
        {final_rate, total_weight, contributions: [{name, rate, weight, share}]}
    """
    valid = [p for p in predictions if p.get("rate") is not None and p.get("weight", 0) > 0]
    if not valid:
        return {"final_rate": None, "total_weight": 0, "contributions": []}
    total_w = sum(p["weight"] for p in valid)
    final_rate = sum(p["rate"] * p["weight"] for p in valid) / total_w
    contributions = [
        {
            "name": p.get("name", "?"),
            "rate": round(p["rate"], 4),
            "weight": round(p["weight"], 4),
            "share": round(p["weight"] / total_w * 100, 1),
        }
        for p in valid
    ]
    return {
        "final_rate": round(final_rate, 4),
        "total_weight": round(total_w, 4),
        "contributions": contributions,
    }


def _trend_momentum(series: list) -> dict:
    """시계열 시리즈에 선형 회귀 → 월간 변화율(slope) 산출.

    Args:
        series: [{period, avg_rate, count}, ...] (시간순 정렬 가정)
    Returns:
        {slope, intercept, r_squared, direction, next_predicted, n}
    """
    import numpy as np
    valid = [s for s in series if s.get("avg_rate") is not None]
    if len(valid) < 3:
        return {"slope": None, "direction": "insufficient_data", "n": len(valid)}

    x = np.arange(len(valid), dtype=float)
    y = np.array([s["avg_rate"] for s in valid], dtype=float)

    # OLS: y = a*x + b
    A = np.vstack([x, np.ones_like(x)]).T
    try:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    except (np.linalg.LinAlgError, ValueError) as exc:
        logger.warning("trend momentum lstsq 실패 (n=%d): %s", len(valid), exc)
        return {"slope": None, "direction": "error", "n": len(valid)}
    slope, intercept = float(coef[0]), float(coef[1])

    # R²
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # 다음 시점 예측
    next_x = float(len(valid))
    next_pred = slope * next_x + intercept

    # 방향 (절대값 0.05% 미만은 보합)
    if abs(slope) < 0.05:
        direction = "flat"
    elif slope > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "slope": round(slope, 4),                       # % per period (월별이면 %/월)
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "direction": direction,
        "next_predicted": round(next_pred, 4),
        "n": len(valid),
    }


def _walk_forward_validate(samples_with_dates: list, window_days: int = 90,
                            stride_days: int = 30) -> dict:
    """시계열 walk-forward 검증.

    각 시점마다: [t-window, t] 데이터로 학습 → t 시점 예측 → 실제값과 비교.
    stride_days 만큼 t를 앞으로 이동 (rolling window).

    Args:
        samples_with_dates: [(rate, date), ...]
    Returns:
        {windows: [{period, predicted, actual_avg, mae, n}, ...], overall_mae}
    """
    if len(samples_with_dates) < 30:
        return {"windows": [], "overall_mae": None, "reason": "표본 부족"}

    from datetime import datetime as _dt, timedelta as _td
    sorted_samples = sorted(samples_with_dates, key=lambda x: x[1] or _dt.min)
    valid = [(r, d) for r, d in sorted_samples if d]
    if len(valid) < 30:
        return {"windows": [], "overall_mae": None, "reason": "유효 날짜 표본 부족"}

    start_date = valid[0][1]
    end_date = valid[-1][1]

    windows = []
    cursor = start_date + _td(days=window_days)
    while cursor < end_date:
        train_start = cursor - _td(days=window_days)
        train_end = cursor
        test_end = min(end_date, cursor + _td(days=stride_days))

        train = [r for r, d in valid if train_start <= d < train_end]
        test = [r for r, d in valid if train_end <= d < test_end]

        if len(train) >= 5 and len(test) >= 1:
            # 학습: 단순 평균을 다음 기간 예측치로 (가장 robust한 baseline)
            predicted = sum(train) / len(train)
            actual_avg = sum(test) / len(test)
            mae = abs(predicted - actual_avg)
            windows.append({
                "period": cursor.strftime("%Y-%m-%d"),
                "predicted": round(predicted, 4),
                "actual_avg": round(actual_avg, 4),
                "mae": round(mae, 4),
                "n_train": len(train),
                "n_test": len(test),
            })
        cursor += _td(days=stride_days)

    if not windows:
        return {"windows": [], "overall_mae": None, "reason": "윈도우 생성 실패"}

    overall_mae = round(sum(w["mae"] for w in windows) / len(windows), 4)
    return {
        "windows": windows,
        "overall_mae": overall_mae,
        "n_windows": len(windows),
    }


# ─── Bayesian Shrinkage / 이상 탐지 / K-NN 유사 공고 ──────────────────

def _bayesian_shrinkage(local_rates: list, global_rates: list,
                         prior_strength: int = 10) -> dict:
    """경험적 베이지안 shrinkage — 소표본 발주처 평균을 전체 평균으로 끌어당김.

    weighted = (n_local × local_mean + k × global_mean) / (n_local + k)
    n_local 이 작을수록 global_mean 영향력 ↑

    Args:
        local_rates: 대상 발주처(또는 좁은 범위) 사정률 리스트
        global_rates: 카테고리 전체 사정률 리스트
        prior_strength: shrinkage 강도 — 사실상 "가상 표본 k건"
    Returns:
        {shrunk_rate, local_mean, global_mean, shrinkage_factor (0~1, 1=완전 global)}
    """
    if not global_rates:
        return {"shrunk_rate": None, "local_mean": None, "global_mean": None,
                "shrinkage_factor": None, "n_local": len(local_rates)}
    g_mean = sum(global_rates) / len(global_rates)
    n_local = len(local_rates)
    if n_local == 0:
        return {"shrunk_rate": round(g_mean, 4), "local_mean": None,
                "global_mean": round(g_mean, 4), "shrinkage_factor": 1.0, "n_local": 0}
    l_mean = sum(local_rates) / n_local
    shrunk = (n_local * l_mean + prior_strength * g_mean) / (n_local + prior_strength)
    factor = prior_strength / (n_local + prior_strength)
    return {
        "shrunk_rate": round(shrunk, 4),
        "local_mean": round(l_mean, 4),
        "global_mean": round(g_mean, 4),
        "shrinkage_factor": round(factor, 4),
        "n_local": n_local,
        "n_global": len(global_rates),
    }


def _apply_category_filter(q, category_filter: str, ann=None):
    """카테고리 필터 공통 적용 — 6개 분석 엔드포인트 중복 제거.

    Args:
        q: SQLAlchemy 쿼리 (BidAnnouncement 가 join 되어 있어야 함)
        category_filter: 'same' / 'all' / 'construction' / 'service' / 'industry'
        ann: 'same'/'industry' 모드 시 기준 공고
    """
    if category_filter == "construction":
        return q.filter(BidAnnouncement.category == "공사")
    if category_filter == "service":
        return q.filter(BidAnnouncement.category == "용역")
    if category_filter == "industry" and ann and ann.industry_code:
        return q.filter(BidAnnouncement.industry_code == ann.industry_code)
    if category_filter == "same" and ann:
        return q.filter(BidAnnouncement.category == ann.category)
    return q  # all (또는 fallback)


def _detect_anomaly(target_value: float, peer_values: list,
                     z_threshold: float = 2.0) -> dict:
    """z-score 기반 이상 탐지 — 대상값이 표본 분포에서 비정상인지 판정.

    Args:
        target_value: 대상 공고 기초금액 (또는 사정률)
        peer_values: 유사 표본의 동일 지표 리스트
        z_threshold: |z| 이 임계값보다 크면 이상 플래그
    Returns:
        {is_anomaly, z_score, peer_mean, peer_std, severity}
    """
    if len(peer_values) < 5:
        return {"is_anomaly": False, "z_score": None, "reason": "표본 부족"}
    mean = sum(peer_values) / len(peer_values)
    if len(peer_values) > 1:
        std = statistics.stdev(peer_values)
    else:
        std = 0
    if std == 0:
        return {"is_anomaly": False, "z_score": 0, "peer_mean": round(mean, 4)}
    z = (target_value - mean) / std
    abs_z = abs(z)
    if abs_z > z_threshold * 1.5:
        severity = "high"
    elif abs_z > z_threshold:
        severity = "medium"
    else:
        severity = "normal"
    return {
        "is_anomaly": abs_z > z_threshold,
        "z_score": round(z, 3),
        "abs_z": round(abs_z, 3),
        "peer_mean": round(mean, 4),
        "peer_std": round(std, 4),
        "severity": severity,
    }


def _kmeans_simple(features: list, k: int = 5, max_iter: int = 30, seed: int = 42) -> tuple:
    """초간단 K-means (numpy) — 외부 의존성 없음.

    Args:
        features: list of feature vectors (list of lists)
        k: 군집 수
    Returns:
        (labels, centroids) — labels[i] = i번째 표본 군집 인덱스
    """
    import numpy as np
    if len(features) < k:
        return ([0] * len(features), [features[0]] if features else [])
    X = np.array(features, dtype=float)
    rng = np.random.default_rng(seed)
    # 초기 centroid: 무작위 k개 표본
    init_idx = rng.choice(len(X), size=k, replace=False)
    centroids = X[init_idx].copy()

    for _ in range(max_iter):
        # 각 점의 가장 가까운 centroid (Euclidean)
        dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
        labels = dists.argmin(axis=1)
        # centroid 갱신
        new_centroids = np.array([
            X[labels == c].mean(axis=0) if (labels == c).any() else centroids[c]
            for c in range(k)
        ])
        if np.allclose(new_centroids, centroids, atol=1e-4):
            break
        centroids = new_centroids
    return (labels.tolist(), centroids.tolist())


def _knn_similar_announcements(target: dict, candidates: list, k: int = 5) -> list:
    """K-NN 유사 공고 추천 — 가중 거리 기반.

    Distance = |log(amount_diff)| × 0.4 + region_mismatch × 0.3 +
               industry_mismatch × 0.2 + (days_old / 365) × 0.1

    Args:
        target: {base_amount, region, industry, category}
        candidates: [{id, base_amount, region, industry, title, ..., assessment_rate, days_old}, ...]
        k: 상위 N건 반환
    Returns:
        sorted by similarity desc, top k
    """
    target_log_amount = math.log(max(1, target.get("base_amount") or 1))
    target_region = target.get("region")
    target_industry = target.get("industry")

    scored = []
    for c in candidates:
        c_amount = c.get("base_amount") or 0
        if c_amount <= 0:
            continue
        log_amount_diff = abs(math.log(max(1, c_amount)) - target_log_amount)
        region_mm = 0 if c.get("region") == target_region else 1
        ind_mm = 0 if (target_industry and c.get("industry") == target_industry) else 1
        days_old = c.get("days_old", 0) or 0

        distance = (log_amount_diff * 0.4
                    + region_mm * 0.3
                    + ind_mm * 0.2
                    + (days_old / 365) * 0.1)
        # similarity = 1 / (1 + distance), 0~1 정규화
        similarity = round(1 / (1 + distance), 4)
        scored.append({**c, "distance": round(distance, 4), "similarity": similarity})

    scored.sort(key=lambda x: -x["similarity"])
    return scored[:k]


# ─── 회귀 분석 (numpy OLS) ────────────────────────────────────────────

def _ols_regression(samples: list, target_features: dict) -> dict:
    """다중 선형 회귀 — 사정률 예측 (numpy lstsq).

    Args:
        samples: [{rate, base_amount, category, region, industry, org_type, days_old}, ...]
        target_features: 대상 공고의 동일 feature dict
    Returns:
        {predicted_rate, r_squared, coefficients, residual_std, n}
    """
    import numpy as np
    if len(samples) < 10:
        return {"predicted_rate": None, "r_squared": None, "n": len(samples),
                "reason": "표본 부족 (10건 미만)"}

    # ── feature 추출: log(base_amount), category=공사, region one-hot top5, days_old ──
    # 지역 상위 빈출 5개
    from collections import Counter
    region_counts = Counter(s.get("region") for s in samples if s.get("region"))
    top_regions = [r for r, _ in region_counts.most_common(5)]

    def featurize(s: dict) -> list:
        ba = s.get("base_amount") or 1
        log_ba = math.log(max(1, ba))
        is_construction = 1 if s.get("category") == "공사" else 0
        region_oh = [1 if s.get("region") == r else 0 for r in top_regions]
        days_old = s.get("days_old", 0) or 0
        # bias term + features
        return [1.0, log_ba, is_construction] + region_oh + [days_old]

    X = np.array([featurize(s) for s in samples], dtype=float)
    y = np.array([s["rate"] for s in samples], dtype=float)

    # OLS: β = (X'X)^-1 X'y, lstsq 로 안정 풀이
    try:
        coef, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    except Exception as e:
        return {"predicted_rate": None, "r_squared": None, "error": str(e)}

    # 예측값 + R² 계산
    y_pred = X @ coef
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    residual_std = float(np.sqrt(ss_res / max(1, len(y) - len(coef))))

    # 대상 공고 예측
    target_x = np.array(featurize(target_features), dtype=float)
    target_pred = float(target_x @ coef)
    # 사정률 안전 범위 클램프 (90~110)
    target_pred = max(90.0, min(110.0, target_pred))

    # 특성 영향도 (절대값 큰 순)
    feature_names = ["intercept", "log(기초금액)", "공사여부"] + [f"지역={r}" for r in top_regions] + ["경과일수"]
    importance = sorted(
        [(n, round(float(c), 4)) for n, c in zip(feature_names, coef) if n != "intercept"],
        key=lambda x: -abs(x[1])
    )[:5]

    return {
        "predicted_rate": round(target_pred, 4),
        "r_squared": round(r_squared, 4),
        "residual_std": round(residual_std, 4),
        "n": len(samples),
        "top_features": importance,  # [(name, coef), ...]
    }


def _build_rate_histogram(rates: list, bin_size: float = 0.1) -> list:
    """사정률 리스트 → 0.1% bin 히스토그램. 빈 bin 도 0 으로 채워서 반환."""
    if not rates:
        return []
    min_r = math.floor(min(rates) * 10) / 10
    max_r = math.ceil(max(rates) * 10) / 10
    bins = []
    cur = min_r
    while cur <= max_r + 0.001:
        cnt = sum(1 for r in rates if cur - bin_size / 2 <= r < cur + bin_size / 2)
        bins.append({"rate": round(cur, 2), "count": cnt})
        cur = round(cur + bin_size, 2)
    return bins


def _compute_rate_buckets(bins: list, mode: str = "A", top_n: int = 5) -> list:
    """스펙 §1 — 3가지 구간 산출 알고리즘.

    100 을 기준으로 +방향 / -방향 각각 정렬하여 범위(range) 반환.

    Args:
        bins: _build_rate_histogram() 결과
        mode: 'A' 빈도최대 / 'B' 공백 / 'C' 차이최대
        top_n: 반환할 상위 구간 수

    Returns:
        [{rate, side: '+'|'-'|'0', score, range_start, range_end, rank}, ...]
    """
    if not bins:
        return []

    candidates = []
    if mode == "A":
        # 막대가 가장 큰 값 (빈도 최대) → 막대 높이순 정렬
        for b in bins:
            if b["count"] > 0:
                side = "+" if b["rate"] > 100 else ("-" if b["rate"] < 100 else "0")
                candidates.append({
                    "rate": b["rate"],
                    "score": b["count"],  # 빈도 자체가 점수
                    "side": side,
                    "distance": abs(b["rate"] - 100),
                })
        candidates.sort(key=lambda c: (-c["score"], c["distance"]))

    elif mode == "B":
        # 막대가 없는 값 (공백) → 100 기준 가까운 순
        for b in bins:
            if b["count"] == 0:
                side = "+" if b["rate"] > 100 else ("-" if b["rate"] < 100 else "0")
                candidates.append({
                    "rate": b["rate"],
                    "score": 0,
                    "side": side,
                    "distance": abs(b["rate"] - 100),
                })
        candidates.sort(key=lambda c: c["distance"])

    elif mode == "C":
        # 막대 차이가 가장 큰 값 → 인접 차이 절대값 순
        for i, b in enumerate(bins):
            prev_cnt = bins[i - 1]["count"] if i > 0 else 0
            next_cnt = bins[i + 1]["count"] if i < len(bins) - 1 else 0
            diff = max(abs(b["count"] - prev_cnt), abs(b["count"] - next_cnt))
            if diff > 0:
                side = "+" if b["rate"] > 100 else ("-" if b["rate"] < 100 else "0")
                candidates.append({
                    "rate": b["rate"],
                    "score": diff,
                    "side": side,
                    "distance": abs(b["rate"] - 100),
                })
        candidates.sort(key=lambda c: (-c["score"], c["distance"]))
    else:
        return []

    # range_start/end + 순위 부여, top_n 제한
    result = []
    bin_size = 0.1
    for i, c in enumerate(candidates[:top_n]):
        c["range_start"] = round(c["rate"] - bin_size / 2, 2)
        c["range_end"] = round(c["rate"] + bin_size / 2, 2)
        c["rank"] = i + 1
        c["mode"] = mode
        result.append(c)
    return result


def _extract_detail_rate(table_rates: list, rule: str = "first_after") -> float:
    """스펙 §1 — 세부 사정률 값 추출.

    Args:
        table_rates: 막대그래프 아래 표의 사정률 리스트 (정렬 가정)
        rule: 'first_after'  첫값 바로 뒤
              'last_after'   마지막값 바로 뒤
              'max_gap'      간격이 가장 큰 값
    """
    if not table_rates:
        return None
    sorted_rates = sorted(table_rates)
    if rule == "first_after":
        return sorted_rates[1] if len(sorted_rates) > 1 else sorted_rates[0]
    if rule == "last_after":
        return sorted_rates[-1]  # "바로 뒤" 해석: 끝값을 그대로 사용
    if rule == "max_gap":
        if len(sorted_rates) < 2:
            return sorted_rates[0]
        max_gap = 0
        max_gap_rate = sorted_rates[0]
        for i in range(1, len(sorted_rates)):
            gap = sorted_rates[i] - sorted_rates[i - 1]
            if gap > max_gap:
                max_gap = gap
                # "간격이 가장 큰 값" — 간격 직후 값 (큰 쪽)
                max_gap_rate = sorted_rates[i]
        return max_gap_rate
    return None


def _compute_confidence(rates: list, agreement: float, methods_aligned_count: int) -> dict:
    """예측 신뢰도 계산 — 표본 크기·합치도·분포 안정성 종합.

    Returns: {score: 0~100, level: 'high|medium|low', reasons: [..]}
    """
    score = 0
    reasons = []

    # 1) 표본 크기 (최대 40점)
    n = len(rates)
    if n >= 100:
        score += 40
        reasons.append(f"표본 풍부 ({n}건)")
    elif n >= 30:
        score += 25
        reasons.append(f"표본 적정 ({n}건)")
    elif n >= 10:
        score += 10
        reasons.append(f"표본 부족 ({n}건)")
    else:
        reasons.append(f"표본 매우 부족 ({n}건)")

    # 2) 합치도 (최대 35점)
    score += int(agreement * 35)
    if agreement >= 0.66:
        reasons.append(f"방법 간 합치 높음 ({methods_aligned_count}/3)")
    elif agreement >= 0.34:
        reasons.append(f"방법 간 합치 보통 ({methods_aligned_count}/3)")
    else:
        reasons.append(f"방법 간 합치 낮음 ({methods_aligned_count}/3)")

    # 3) 분포 안정성 — 표준편차 (최대 25점)
    if n > 1:
        std = statistics.stdev(rates)
        if std < 0.5:
            score += 25
            reasons.append("분포 매우 집중")
        elif std < 1.0:
            score += 15
            reasons.append("분포 집중")
        elif std < 2.0:
            score += 5
            reasons.append("분포 다소 분산")
        else:
            reasons.append("분포 분산")

    score = min(100, max(0, score))
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"
    return {"score": score, "level": level, "reasons": reasons}

