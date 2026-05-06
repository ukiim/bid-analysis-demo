FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 (pandas/openpyxl 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 비특권 사용자로 실행
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# NAS 마운트용 데이터 디렉토리
ENV NAS_MOUNT_PATH=/app/data \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    WORKERS=2

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:8000/api/v1/meta/regions || exit 1

# 프로덕션: --reload 제거, 멀티 워커
CMD uvicorn server:app --host 0.0.0.0 --port 8000 --workers ${WORKERS} --log-level ${LOG_LEVEL,,}
