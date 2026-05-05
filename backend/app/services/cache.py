"""분석 결과 TTL 캐시 — server.py L511-557 에서 분리 (F3).

간단한 LRU + TTL 메모리 캐시. 운영 시 Redis 교체 가능.
scripts/recompute_match_rate.py 가 invalidate_analysis_cache 를 직접 import.
"""
from __future__ import annotations

import logging
import os
import threading
import time as _time


logger = logging.getLogger("bid-insight")

_CACHE_MAX = int(os.environ.get("ANALYSIS_CACHE_SIZE", "256"))
_CACHE_TTL = int(os.environ.get("ANALYSIS_CACHE_TTL", "300"))  # 초
_cache_store: dict = {}
_cache_lock = threading.Lock()


def _cache_get(key: str):
    with _cache_lock:
        entry = _cache_store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if _time.time() > expires_at:
            _cache_store.pop(key, None)
            return None
        return value


def _cache_set(key: str, value):
    with _cache_lock:
        # 크기 초과 시 만료된 항목부터 정리
        if len(_cache_store) >= _CACHE_MAX:
            now = _time.time()
            expired = [k for k, (t, _) in _cache_store.items() if now > t]
            for k in expired:
                _cache_store.pop(k, None)
            # 여전히 초과면 가장 오래된 항목 제거
            if len(_cache_store) >= _CACHE_MAX:
                oldest = min(_cache_store.items(), key=lambda kv: kv[1][0])[0]
                _cache_store.pop(oldest, None)
        _cache_store[key] = (_time.time() + _CACHE_TTL, value)


def _cache_key(*parts) -> str:
    return "|".join(str(p) for p in parts)


def invalidate_analysis_cache():
    """공고/수집 데이터 변경 시 호출"""
    with _cache_lock:
        _cache_store.clear()
    logger.info("analysis cache invalidated")


__all__ = [
    "_cache_get",
    "_cache_set",
    "_cache_key",
    "invalidate_analysis_cache",
]
