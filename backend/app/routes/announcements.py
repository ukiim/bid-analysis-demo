"""announcements 라우터 — 현재 server.py 의 @app.* 핸들러로 정의됨.

이 모듈은 향후 코드 이전을 위한 자리표시자.
신규 라우터 추가 시 server.py 가 아닌 본 파일에 APIRouter 로 작성 권장.
현재는 server.app 을 재노출.
"""
from app.main import app  # noqa: F401

__all__ = ["app"]
