"""동기화 헬퍼 — G2B/D2B 파싱, upsert, HTTP retry.

server.py L4285–4796 의 헬퍼들을 재노출.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

_parse_date = _server._parse_date
_extract_g2b_items = _server._extract_g2b_items
_detect_defense = _server._detect_defense
get_announcement_url = _server.get_announcement_url
build_g2b_url = _server.build_g2b_url
_normalize_item = _server._normalize_item
_upsert_announcements = _server._upsert_announcements
_windows_iter = _server._windows_iter
_record_sync_error = _server._record_sync_error
_build_sync_url = _server._build_sync_url
_build_result_url = _server._build_result_url
_normalize_result_item = _server._normalize_result_item
_aggregate_prelim_prices = _server._aggregate_prelim_prices
_upsert_results = _server._upsert_results
_http_fetch_with_retry = _server._http_fetch_with_retry
_run_sync_for_source = _server._run_sync_for_source

__all__ = [
    "_parse_date",
    "_extract_g2b_items",
    "_detect_defense",
    "get_announcement_url",
    "build_g2b_url",
    "_normalize_item",
    "_upsert_announcements",
    "_windows_iter",
    "_record_sync_error",
    "_build_sync_url",
    "_build_result_url",
    "_normalize_result_item",
    "_aggregate_prelim_prices",
    "_upsert_results",
    "_http_fetch_with_retry",
    "_run_sync_for_source",
]
