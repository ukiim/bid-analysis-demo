"""bid-insight 백엔드 애플리케이션 패키지.

server.py 모놀리스에서 점진적으로 분리되는 모듈식 구조.
- core/    : 설정, DB, 보안, 의존성
- models/  : SQLAlchemy ORM 모델
- services/: 비즈니스 로직 헬퍼 (집계, 통계 등)
- routes/  : FastAPI 라우터 (현재 server.py에 잔존)
- tasks/   : 백그라운드 작업
"""
