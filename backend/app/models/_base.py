"""SQLAlchemy declarative_base 단일 인스턴스.

모든 ORM 모델이 이 Base 를 상속한다. server.py 는 이 Base 를 재노출.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()

__all__ = ["Base"]
