# NAS 배포 가이드 — 비드스타

대상: **Synology DSM 7.x** / **QNAP QTS 5.x** Docker 지원 모델
배포 방식: Docker Compose 단일 컨테이너 + 볼륨 마운트
예상 소요 시간: **30~45분**

---

## 0. 사전 준비

### 0-1. NAS 측 요구사항
| 항목 | 권장 사양 |
|------|----------|
| OS | DSM 7.0 이상 / QTS 5.0 이상 |
| CPU | x86_64, 2코어 이상 |
| RAM | 4GB 이상 (Docker 컨테이너에 최소 1GB 할당) |
| 저장공간 | 10GB 이상 (DB + 로그 + 백업) |
| 패키지 | **Container Manager** (구 Docker) 설치됨 |

### 0-2. 사전에 받아야 할 정보
- [ ] NAS SSH 접근 (포트, 계정)
- [ ] 사용할 도메인 (예: `bid.example.com`)
- [ ] 관리자 이메일 주소
- [ ] G2B API 키 (이미 발급 완료)
- [ ] Cloudflare 계정 (Tunnel 설정 시)

---

## 1. NAS 디렉토리 구조 생성

SSH 접속 후:

```bash
ssh admin@<NAS_IP> -p <PORT>
```

```bash
# 프로젝트 루트 (Synology 기본)
sudo mkdir -p /volume1/docker/bid-insight
cd /volume1/docker/bid-insight

# 데이터 / 로그 / 백업 디렉토리
sudo mkdir -p data backups logs

# 권한 (Docker 컨테이너는 uid=1000으로 실행)
sudo chown -R 1000:1000 data backups logs
```

QNAP의 경우 경로가 `/share/Container/bid-insight` 입니다.

---

## 2. 코드·설정 파일 업로드

로컬에서 NAS로 코드 전송:

```bash
# 로컬 머신에서 실행
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='backend/demo.db' --exclude='backend/backups' \
  /Users/.../공공데이터*/ admin@<NAS_IP>:/volume1/docker/bid-insight/
```

또는 **DSM 파일 스테이션** 으로 ZIP 업로드 후 압축 해제.

---

## 3. 운영 환경변수 설정

```bash
cd /volume1/docker/bid-insight

# .env 생성 (운영 시크릿)
cp .env.example .env
sudo nano .env
```

필수 수정 항목:
```env
APP_ENV=production
SECRET_KEY=<openssl rand -hex 32 결과값>
CORS_ORIGINS=https://bid.example.com
G2B_API_KEY=<발급받은_88자_키>
SYNC_ENABLED=true
SYNC_TIME=02:00
LOG_LEVEL=INFO
LOG_FILE=/app/data/server.log
WORKERS=2
```

시크릿 생성:
```bash
openssl rand -hex 32
# 예: 8f3a2c1d9e7b4a6...의 64자 문자열
```

---

## 4. docker-compose 운영 파일 사용

```bash
# 운영용 compose 파일 사용 (개발용은 docker-compose.yml)
docker compose -f docker-compose.prod.yml up -d --build
```

또는 DSM **Container Manager → 프로젝트** 메뉴에서:
1. "프로젝트 생성"
2. 경로: `/volume1/docker/bid-insight`
3. `docker-compose.prod.yml` 자동 인식
4. "구축" 클릭

---

## 5. DB 초기화 및 관리자 계정 생성

```bash
# 컨테이너 안으로 진입
docker exec -it bid-backend /bin/bash

# Alembic 마이그레이션 (스키마 최신화)
python3 -m alembic upgrade head

# 관리자 계정 생성
python3 scripts/init_admin.py \
  --email admin@example.com \
  --password '$(openssl rand -base64 18)' \
  --name "운영 관리자"
exit
```

생성된 비밀번호는 **즉시 안전한 곳에 보관** 후 첫 로그인 시 변경.

---

## 5-1. 서비스 vs 관리자 영역 구조

비드스타는 **서비스 영역**과 **관리자 영역**이 시각·URL·권한 모두 분리되어 있습니다.

| 구분 | 서비스 영역 | 관리자 영역 |
|------|-----------|-----------|
| URL | `/`, `/announcements`, `/comprehensive`, `/mypage`, `/upload` | `/admin`, `/admin/sync`, `/admin/storage`, `/admin/errors` |
| 테마 | 파란색 (`#0066CC`) | **다크 + 빨강 (`#DC2626`)** ★시각적 구분 명확 |
| 사이드바 | 5개 메뉴 (서비스/관리 섹션) | 4개 메뉴 + "← 서비스로" 진입 버튼 |
| 톱바 | 일반 페이지 타이틀 | 빨간 "관리자 모드" 배지 |
| 권한 | 모든 로그인 사용자 | 관리자(role=admin)만 — 비관리자 진입 시 자동 리다이렉트 |
| API | `/api/v1/{auth,announcements,analysis,...}` | `/api/v1/admin/*` (require_admin 의존성) |

### 관리자 진입 방법
1. **사이드바 → '관리자' 메뉴 클릭** (서비스 영역에서)
2. **URL 직접 입력**: `https://<도메인>/admin`
3. 진입 시 페이지 전체가 어두운 다크 테마 + 빨간 강조색으로 즉시 전환되어 영역이 바뀜이 명확히 인지됨

### 관리자 4개 서브 페이지
| URL | 페이지 | 기능 |
|-----|--------|------|
| `/admin` 또는 `/admin/users` | 사용자 관리 | 사용자 목록, 활성/비활성 토글 |
| `/admin/sync` | 데이터 수집 | 수동 수집 실행, 수집 히스토리, 재시도 |
| `/admin/storage` | 스토리지·스케줄 | 자동 수집 스케줄(매시/매일/매주), NAS 디스크 사용량 |
| `/admin/errors` | 오류 모니터링 | 수집 실패 로그 및 상세 메시지 |

각 페이지 상단에는 공통 KPI Bar (총 공고/사용자/분석/평균 사정률/데이터 출처)가 표시됩니다.

---

## 6. 첫 데이터 수집 검증

```bash
# 컨테이너 안에서 또는 호스트에서 (curl)
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Authorization: Bearer <JWT_TOKEN>"

# 또는 sync_check.py
docker exec bid-backend python3 scripts/sync_check.py --source G2B --rows 5
```

기대 결과:
```
✅ E2E 검증 완료 — 수신 5 / 유효 5 / 신규 5 / 중복 0 / 소요 1.6s
```

---

## 7. 헬스체크 / 메트릭 확인

```bash
# 헬스
curl http://localhost:8000/healthz
# {"status":"ok","checks":{"db":"ok","scheduler":"running","env":"production"}}

# 메트릭
curl http://localhost:8000/metrics | head -10
# bid_announcements_total ...
# users_total ...
# sync_success_total ...
```

브라우저: `http://<NAS_IP>:8000/docs` (Swagger UI)

---

## 8. 백업 자동화

### 8-1. 호스트 cron (DSM 작업 스케줄러)

DSM **제어판 → 작업 스케줄러 → 생성 → 예약된 작업 → 사용자 정의 스크립트**:
- 사용자: `root`
- 스케줄: 매일 03:00
- 명령:
  ```bash
  docker exec bid-backend python3 /app/scripts/backup_db.py \
    --output /app/data/backups --retain 30 --verify
  ```

### 8-2. NAS 측 백업 디렉토리 동기화 (Hyper Backup 사용)

DSM **Hyper Backup**으로 `/volume1/docker/bid-insight/backups`을 외부 USB/클라우드에 주기 백업.

---

## 9. 로그 확인

### 실시간 로그
```bash
docker logs -f bid-backend
```

### 파일 로그
```bash
tail -f /volume1/docker/bid-insight/data/server.log
```

DSM **로그 센터**에서도 `Container > bid-backend` 로그 확인 가능.

---

## 10. 문제 해결

| 증상 | 진단 / 해결 |
|------|-----------|
| 컨테이너가 시작 안 됨 | `docker logs bid-backend` 에서 `SECRET_KEY` 또는 `CORS_ORIGINS` 검증 메시지 확인 |
| `/healthz`가 503 | DB 연결 실패 — `data/demo.db` 존재 여부, 권한 (uid 1000) 확인 |
| `/metrics`에 `sync_failed_total` 증가 | API 키 만료 또는 data.go.kr 일시 장애 — `/api/v1/admin/errors` 확인 |
| 디스크 공간 부족 | `backups/` 정리 (`--retain 7`로 변경), `data/server.log` 로테이션 |
| Docker 이미지 업데이트 | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |

---

## 11. 외부 접속 (도메인 / SSL)

다음 두 옵션 중 선택:
- **A. Cloudflare Tunnel** (권장) → `docs/Cloudflare_Tunnel_가이드.md` 참조
- **B. NAS 자체 리버스 프록시 + Let's Encrypt** → DSM의 **응용프로그램 포털** 사용

---

## 12. 일상 운영 체크리스트

매주 1회:
- [ ] `/healthz` 응답 확인
- [ ] `sync_failed_total` 증가 추세 확인
- [ ] 디스크 사용량 확인 (`df -h /volume1`)
- [ ] 백업 파일 정상 생성 여부

매월 1회:
- [ ] Docker 이미지 업데이트 (보안 패치)
- [ ] DB 백업 복원 테스트
- [ ] G2B API 키 만료 확인 (data.go.kr 마이페이지)

---

## 부록 A. 주요 환경변수 요약

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APP_ENV` | development | 운영 시 반드시 `production` |
| `SECRET_KEY` | (안전 기본값) | JWT 서명 키, 32자 이상 |
| `CORS_ORIGINS` | `*` | 운영 시 도메인 명시 (와일드카드 거부) |
| `G2B_API_KEY` | 빈 문자열 | data.go.kr 인증키 |
| `SYNC_INTERVAL` | daily | hourly/daily/weekly |
| `SYNC_TIME` | 02:00 | 실행 시각 (KST) |
| `SYNC_TOTAL_DAYS_ANN` | 60 | 공고 누적 조회일수 |
| `SYNC_TOTAL_DAYS_RES` | 14 | 낙찰 누적 조회일수 |
| `LOG_LEVEL` | INFO | DEBUG/INFO/WARNING/ERROR |
| `LOG_FILE` | (미설정) | 파일 로그 경로 |
| `WORKERS` | 2 | uvicorn 워커 수 |

---

작성일: 2026-04-27
지원 문의: support@bid-insight.example.com
