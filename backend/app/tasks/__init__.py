"""백그라운드 작업 — 스케줄러, 캐시 무효화, 모델 재학습.

server.py 의 _scheduled_* / _check_* / _send_alert_* 함수를 재노출.
"""
from __future__ import annotations

import sys as _sys
import os as _os

_BACKEND_DIR = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)

import server as _server  # noqa: E402

_send_alert_webhook = _server._send_alert_webhook
_check_sync_failure_threshold = _server._check_sync_failure_threshold
_scheduled_model_retrain = _server._scheduled_model_retrain
_scheduled_sync_job = _server._scheduled_sync_job
_apply_schedule_config = _server._apply_schedule_config

__all__ = [
    "_send_alert_webhook",
    "_check_sync_failure_threshold",
    "_scheduled_model_retrain",
    "_scheduled_sync_job",
    "_apply_schedule_config",
]
