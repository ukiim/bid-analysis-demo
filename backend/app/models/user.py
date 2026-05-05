"""사용자/권한 관련 모델 — server.py L160-197 에서 분리."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.models._base import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    role = Column(String, default="user")              # user / admin
    plan = Column(String, default="무료")
    is_active = Column(Boolean, default=True)
    query_count = Column(Integer, default=0)
    joined_at = Column(DateTime)
    last_login_at = Column(DateTime)


class QueryHistory(Base):
    """사용자 조회 이력"""
    __tablename__ = "query_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    announcement_id = Column(String)
    analysis_type = Column(String)                     # frequency / company / comprehensive
    parameters = Column(Text)                          # JSON
    result_summary = Column(Text)                      # JSON
    queried_at = Column(DateTime, default=datetime.now)


class UploadLog(Base):
    """데이터 업로드 이력"""
    __tablename__ = "upload_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_size = Column(Integer)
    records_count = Column(Integer, default=0)
    status = Column(String, default="processing")      # processing / success / failed
    error_message = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.now)


__all__ = ["User", "QueryHistory", "UploadLog"]
