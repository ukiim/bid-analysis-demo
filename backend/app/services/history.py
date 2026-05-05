"""조회 이력 헬퍼 — server.save_query_history 의 이전.

분석 핸들러들이 호출하는 공용 헬퍼이므로 서비스 모듈로 분리한다 (F4 보조).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from app.core.database import db_session
from app.models import QueryHistory, User

logger = logging.getLogger("bid-insight")


def save_query_history(
    user_id: str,
    announcement_id: str,
    analysis_type: str,
    parameters: dict | None = None,
    result_summary: dict | None = None,
) -> None:
    """분석 조회 이력 저장. 예외는 운영에 영향 없도록 로그만."""
    try:
        with db_session() as db:
            db.add(QueryHistory(
                user_id=user_id,
                announcement_id=announcement_id,
                analysis_type=analysis_type,
                parameters=json.dumps(parameters, ensure_ascii=False) if parameters else None,
                result_summary=json.dumps(result_summary, ensure_ascii=False) if result_summary else None,
                queried_at=datetime.now(),
            ))
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.query_count = (user.query_count or 0) + 1
            db.commit()
    except Exception as exc:
        logger.debug("query history 저장 실패 (분석 결과에 영향 없음): %s", exc)
