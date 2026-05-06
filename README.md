# 비드스타 — 공공데이터 기반 사정률 분석 플랫폼

공공데이터포털(data.go.kr)의 나라장터(G2B) · 국방조달(D2B) API를 활용해 **과거 사정률 빈도 분석 · 업체 갭 분석 · 종합 예측**을 제공하는 NAS 기반 웹 서비스입니다.

---

## 핵심 기능

| 화면 | 설명 |
|---|---|
| **공고화면** | 공종/지역/일자/상태 필터로 실시간 공고 조회 |
| **Tab1 빈도 분석** | 사정률 히스토그램 + 1순위 예측 후보 |
| **Tab2 갭 분석** | 업체 투찰률 분포 + 최대 갭 구간 + 차기연도 검증 |
| **Tab3 종합 분석** | 확정사정률 기반 과거 1순위 비교 + 밀어내기식 검증 |
| **마이페이지** | 프로필, 비밀번호 변경, 분석 이력 조회 |
| **데이터 업로드** | Excel/CSV 드래그앤드롭 업로드 (중복 검사·행별 오류) |
| **관리자** | 사용자 관리, 자동 수집 스케줄, NAS 상태, 오류 모니터링 |

---

## 기술 스택

| 레이어 | 구성 |
|---|---|
| 프론트엔드 | 단일 파일 React SPA (`frontend/public/index.html`), in-browser Babel |
| 백엔드 | FastAPI, SQLAlchemy 2.0, JWT + bcrypt |
| DB | SQLite(개발) / PostgreSQL(선택) — Alembic 마이그레이션 |
| 스케줄러 | APScheduler (FastAPI lifespan 통합) |
| 인프라 | Docker, docker-compose, 헬스체크 |
| 보안 | Rate Limiting(slowapi), CSP/HSTS 헤더, CORS 제한 |
| 관찰성 | 구조화 로깅, `/healthz`, `/metrics` (Prometheus 호환) |
| 테스트 | pytest 23건 (smoke + 분석) |

---

## 빠른 시작 (개발)

```bash
# 1. Python 의존성
cd backend
pip install -r requirements.txt

# 2. DB 마이그레이션
python -m alembic upgrade head

# 3. 서버 기동 (시드 데이터 자동 생성)
python server.py
# → http://localhost:8000
```

## 프로덕션 배포 (NAS + Docker)

```bash
# 1. 환경 설정
cp .env.example .env
# .env 에 SECRET_KEY(openssl rand -hex 32), CORS_ORIGINS, G2B_API_KEY 입력
export APP_ENV=production

# 2. docker-compose
docker compose up -d --build
# → 헬스체크: curl http://localhost:8000/healthz
```

**NAS 볼륨 마운트**: 호스트 `./data` → 컨테이너 `/app/data` (SQLite DB + 로그 파일)

---

## 환경변수 (.env)

| 키 | 기본값 | 설명 |
|---|---|---|
| `APP_ENV` | development | `production`일 때 시작 시 SECRET_KEY/CORS 강제 검증 |
| `SECRET_KEY` | (개발용 기본값) | JWT 서명 키. **프로덕션 필수 변경** (32자 이상) |
| `CORS_ORIGINS` | `*` | 콤마 구분 허용 도메인. 프로덕션은 `*` 거부 |
| `G2B_API_KEY` / `D2B_API_KEY` | 빈값 | 공공데이터 API 인증키. 없으면 시드 폴백 |
| `SYNC_INTERVAL` / `SYNC_TIME` / `SYNC_ENABLED` | daily / 02:00 / true | 자동 수집 스케줄 |
| `LOG_LEVEL` / `LOG_FILE` | INFO / (stdout) | 로그 레벨 · 파일 경로 |
| `WORKERS` | 2 | uvicorn 워커 수 |
| `ANALYSIS_CACHE_TTL` / `ANALYSIS_CACHE_SIZE` | 300 / 256 | 분석 응답 캐시 TTL(초) · 최대 엔트리 |
| `ALERT_WEBHOOK_URL` | 빈값 | 수집 실패 시 Slack/Discord webhook |
| `NAS_MOUNT_PATH` | /app/data | NAS 마운트 경로 (DB + 로그) |

---

## 주요 엔드포인트

### 공개
- `GET /healthz` — DB/스케줄러 상태 (200 OK / 503 Degraded)
- `GET /metrics` — Prometheus 호환 메트릭
- `GET /api/v1/meta/regions`, `/meta/industry-codes`
- `GET /api/v1/announcements?keyword=&region=&industry_code=&date_from=&date_to=`

### 인증 (Rate Limit: 로그인 10/min)
- `POST /api/v1/auth/register` / `login` / `refresh`
- `GET /api/v1/auth/me` / `PUT /api/v1/auth/password`

### 분석 (Rate Limit: 30~60/min, TTL 캐시 적용)
- `GET /api/v1/analysis/frequency/{id}` — Tab1
- `GET /api/v1/analysis/company-rates/{id}` — Tab2
- `GET /api/v1/analysis/comprehensive/{id}` — Tab3
- `GET /api/v1/analysis/sliding-review/{id}`, `/yearly-validation/{id}`

### 데이터 업로드
- `POST /api/v1/data/upload` (multipart/form-data) — CSV/Excel
- `GET /api/v1/data/uploads`

### 관리자 (role=admin 필수)
- `GET /api/v1/admin/dashboard`, `/sync/history`, `/nas-status`, `/errors`
- `POST /api/v1/admin/sync` / `sync/{id}/retry`
- `GET/PUT /api/v1/admin/schedule` — 자동 수집 스케줄 조회/변경
- `PUT /api/v1/admin/users/{id}/status` — 활성/비활성 토글

---

## 테스트

```bash
cd backend
python -m pytest tests/ -v
# 23 passed (smoke 13 + 분석 10)
```

## 마이그레이션

```bash
# 모델 변경 후 자동 생성
python -m alembic revision --autogenerate -m "변경 설명"

# 적용
python -m alembic upgrade head

# 롤백
python -m alembic downgrade -1
```

---

## 운영 체크리스트

- [ ] `APP_ENV=production`, 강력한 `SECRET_KEY` 지정
- [ ] `CORS_ORIGINS`에 실제 도메인만 명시
- [ ] `G2B_API_KEY` / `D2B_API_KEY` 발급·설정
- [ ] NAS 볼륨 마운트 경로 권한 확인 (`/app/data` 읽기/쓰기)
- [ ] `ALERT_WEBHOOK_URL` 설정 (수집 실패 알림)
- [ ] Cloudflare Tunnel / reverse proxy HTTPS 구성
- [ ] `/metrics` 외부 노출 차단 (reverse proxy ACL)
- [ ] DB 정기 백업 (`sqlite` 또는 `pg_dump`)
- [ ] `alembic upgrade head` 배포 스크립트에 포함
