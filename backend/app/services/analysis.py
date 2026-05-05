"""분석 헬퍼 — 통계, 회귀, 클러스터링, 신뢰구간, 이상탐지.

server.py L1099–1736 의 순수 헬퍼 함수들을 재노출. 호출 시그니처 동일.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

# 기초 통계
_remove_outliers_iqr = _server._remove_outliers_iqr
_time_weighted_rates = _server._time_weighted_rates
_confidence_interval = _server._confidence_interval
_homogeneity_score = _server._homogeneity_score
_compute_confidence = _server._compute_confidence

# 앙상블 / 추세
_ensemble_predict = _server._ensemble_predict
_trend_momentum = _server._trend_momentum

# 검증 / 베이지안
_walk_forward_validate = _server._walk_forward_validate
_bayesian_shrinkage = _server._bayesian_shrinkage

# 카테고리 필터 / 이상 탐지
_apply_category_filter = _server._apply_category_filter
_detect_anomaly = _server._detect_anomaly

# 군집화 / KNN / OLS
_kmeans_simple = _server._kmeans_simple
_knn_similar_announcements = _server._knn_similar_announcements
_ols_regression = _server._ols_regression

# 사정률 히스토그램 / 버킷 / 추출
_build_rate_histogram = _server._build_rate_histogram
_compute_rate_buckets = _server._compute_rate_buckets
_extract_detail_rate = _server._extract_detail_rate

__all__ = [
    "_remove_outliers_iqr",
    "_time_weighted_rates",
    "_confidence_interval",
    "_homogeneity_score",
    "_compute_confidence",
    "_ensemble_predict",
    "_trend_momentum",
    "_walk_forward_validate",
    "_bayesian_shrinkage",
    "_apply_category_filter",
    "_detect_anomaly",
    "_kmeans_simple",
    "_knn_similar_announcements",
    "_ols_regression",
    "_build_rate_histogram",
    "_compute_rate_buckets",
    "_extract_detail_rate",
]
