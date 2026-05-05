"""Pydantic 요청/응답 스키마 — 향후 server.py 에서 분리 예정.

현재 server.py 는 Query 파라미터와 dict 응답을 직접 사용하므로
별도 스키마 클래스가 거의 없다. 신규 엔드포인트 추가 시 본 패키지에
Pydantic v2 모델을 정의하여 사용 권장.
"""
