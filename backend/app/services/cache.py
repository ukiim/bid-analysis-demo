"""분석 결과 인메모리 캐시 — TTL 기반.

server.py 의 invalidate_analysis_cache 등을 재노출.
scripts/recompute_match_rate.py 가 직접 import 하므로 시그니처 보존.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

invalidate_analysis_cache = _server.invalidate_analysis_cache
_cache_get = _server._cache_get
_cache_set = _server._cache_set
_cache_key = _server._cache_key

__all__ = [
    "invalidate_analysis_cache",
    "_cache_get",
    "_cache_set",
    "_cache_key",
]
