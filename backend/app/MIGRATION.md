# `server.py` → `app/` 패키지 분리 작업 노트

## 현황 (2026-05-02 시점)

`backend/server.py` 는 5,583 라인의 모놀리스로,
- ORM 모델 (8개 클래스)
- FastAPI 앱 + 미들웨어
- 인증/보안 헬퍼 (JWT, bcrypt, OAuth2)
- 라우터 핸들러 (54개 `@app.*` 엔드포인트)
- 분석 헬퍼 (집계, 통계, 회귀, 클러스터링, 이상탐지)
- 동기화 / 스케줄러 / NAS 적재 로직
가 한 파일에 들어있다.

## 본 PR 의 분리 전략 (Inverted Façade)

원안 (서버 파일을 얇은 façade 로 만들고 구현을 `app/` 으로 이전) 대신,
**역방향 façade** 를 채택했다:

- `server.py` 는 단일 진실 공급원(SoT)으로 그대로 유지
- 새 `app/` 패키지가 `server.py` 의 공개 심볼을 재노출
- 신규 코드는 `from app.models import BidResult` 같은 모듈식 import 사용 가능
- 기존 `from server import ...` (스크립트, 테스트 148건) 는 변경 없이 동작

### 채택 이유
1. **무위험성** — 5,583 라인 중 단 한 줄의 비즈니스 로직도 이동시키지 않음.
   148개 pytest 케이스 100% 보존이 강제 조건.
2. **상호 의존성** — `server.py` 내부의 헬퍼/모델/라우터가 모두 동일 모듈
   네임스페이스를 가정하고 짜여 있어, 일부만 떼어내면 순환 import 위험이 큼.
3. **점진적 마이그레이션** — 향후 PR에서 한 모듈씩 진정한 이전(`server.py`
   → `app/...py` 코드 이동) 을 진행할 수 있는 기반 확립.

### 향후 계획 (별도 PR)
| Phase | 작업 |
|-------|------|
| F1    | `app/models/*.py` 에 ORM 클래스 정의를 옮기고, `server.py` 가 import |
| F2    | `app/core/{config,database,security,deps}.py` 동일 |
| F3    | `app/services/` 에 순수 헬퍼 (분석/집계/통계) 이동 |
| F4    | 라우터를 도메인별 `app/routes/*.py` 로 분리 + `APIRouter` 사용 |
| F5    | `server.py` 를 진정한 façade (8~10 라인) 로 축소 |

## 라인 매핑 (server.py 현재 구조)

| 라인 범위 | 영역 | 향후 이동 대상 |
|-----------|------|---------------|
| 26–67     | 로깅 설정 | `app/core/config.py` |
| 82–88     | DB 엔진/세션 | `app/core/database.py` |
| 93–231    | ORM 모델 (8개) | `app/models/*.py` |
| 236–255   | 발주기관 계층, REGIONS | `app/core/constants.py` |
| 263–533   | 알림/스케줄러/cron 헬퍼 | `app/tasks/scheduler.py` |
| 535–565   | DB 세션 의존성 | `app/core/deps.py` |
| 566–656   | FastAPI 앱 생성 + CORS + 미들웨어 | `app/main.py` |
| 658–717   | rate_limit, 캐시 | `app/core/cache.py` |
| 723–771   | 보안 미들웨어, 액세스 로그 | `app/core/middleware.py` |
| 782–858   | JWT, bcrypt, OAuth2, require_auth | `app/core/security.py` |
| 860–952   | 인증 라우터 | `app/routes/auth.py` |
| 954–971   | 메타 라우터 | `app/routes/meta.py` |
| 973–1097  | 공고 조회 라우터 | `app/routes/announcements.py` |
| 1099–1736 | 분석 헬퍼 (통계/회귀/클러스터/이상) | `app/services/analysis/*.py` |
| 1738–4022 | 분석 라우터 | `app/routes/analysis.py` |
| 4023–4283 | 통계/관리자 대시보드 라우터 | `app/routes/stats.py`, `app/routes/admin.py` |
| 4285–4796 | 동기화 헬퍼 (G2B/D2B 파싱, upsert) | `app/services/sync/*.py` |
| 4976–5210 | 관리자 동기화 라우터 | `app/routes/admin_sync.py` |
| 5212–5288 | 이력 라우터 | `app/routes/history.py` |
| 5289–5468 | 데이터 업로드 라우터 | `app/routes/upload.py` |
| 5470–5583 | 정적 파일 / SPA / 헬스체크 | `app/main.py` |

## 외부 의존성 (변경 금지)

다음 import 는 깨지면 안 됨:
- `from server import SessionLocal, BidResult, BidAnnouncement, invalidate_analysis_cache` (`scripts/recompute_match_rate.py`)
- `from server import app` (uvicorn, alembic env)
- `from server import Base` (alembic env)
- 148개 pytest 의 `from server import ...`
