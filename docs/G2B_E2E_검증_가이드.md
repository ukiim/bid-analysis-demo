# 공공데이터(G2B/D2B) 실 API 키 E2E 검증 가이드

> 클라이언트로부터 발급받은 공공데이터포털 인증키로 실 수집 파이프라인을
> 단계별로 검증하기 위한 운영 가이드. **DB 변경 없이 안전하게 실행 가능**.

---

## 0. 사전 준비

### API 키 발급 확인
- [공공데이터포털](https://www.data.go.kr) 회원가입 후
- "나라장터(G2B) 입찰공고정보" 활용 신청 → **승인 완료** 상태 확인
- 마이페이지 → 개발계정 → **일반 인증키(Encoding)** 복사

```bash
# 발급키 환경변수 등록
export G2B_API_KEY="발급받은_일반_인증키"
export D2B_API_KEY="국방조달_API_키"   # D2B 사용 시
```

> ⚠️ 키에 `+`, `/`, `=` 등이 포함되어 있어도 그대로 사용. CLI/엔드포인트가 자동 URL 인코딩.

---

## 1. CLI 단독 검증 — 가장 안전한 첫 단계

서버 실행 없이 단독으로 G2B 응답을 수신/파싱/검증한다.

### 1-1. Dry-run (DB 변경 없음, 권장 시작 단계)

```bash
cd backend
python3 scripts/sync_check.py --source G2B --dry-run --verbose --rows 5
```

**예상 출력 (성공 시)**
```
[  OK] G2B_API_KEY 감지 (a1b2c3…wxyz, len=88)
[INFO] GET https://apis.data.go.kr/1230000/BidPublicInfoService05/...
[  OK] 응답 수신 12345바이트 / 412ms
[  OK] items 5건 추출
[  OK] 정규화 완료 — 유효 5 / 무효 0
[ DIM] 샘플: bid=20240519XXXX  title=도로 포장 공사  org=서울특별시  amount=580000000
[INFO] [DRY-RUN] 삽입 예정 5 / 중복 0
[  OK] ──────────────────────────────────────────────────
[  OK] E2E 검증 완료 — 수신 5 / 유효 5 / 신규 0 / 중복 0 / 소요 0.5s
```

### 1-2. 실 적재 (DB에 신규 공고 저장)

Dry-run 결과가 정상이면 실제 적재 실행:

```bash
python3 scripts/sync_check.py --source G2B --rows 50
python3 scripts/sync_check.py --source D2B --rows 50      # D2B 사용 시
```

성공 시 `DataSyncLog` 테이블에 자동 기록되며 관리자 화면에서 즉시 확인 가능.

### 1-3. JSON 출력 (자동화 통합용)

```bash
python3 scripts/sync_check.py --source G2B --dry-run --json | jq '.'
```

### 1-4. 종료 코드 (CI 통합)

| 코드 | 의미 |
|------|------|
| 0 | 성공 (1건 이상 정상 파싱) |
| 1 | 일반 오류 (네트워크/파싱 실패) |
| 2 | API 키 누락 |
| 3 | DB 오류 |

---

## 2. 서버 통합 검증 — 운영 환경 시뮬레이션

서버를 실 환경으로 띄우고 관리자 권한으로 진단 엔드포인트 호출.

### 2-1. 서버 기동

```bash
cd backend
export G2B_API_KEY="..."
export SECRET_KEY="$(openssl rand -hex 32)"
python3 server.py
```

### 2-2. 관리자 토큰 획득

```bash
# 시드 관리자 계정 (admin@bid-insight.com / demo1234)
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login?username=admin@bid-insight.com&password=demo1234" \
  | jq -r '.access_token')
echo "토큰: ${TOKEN:0:20}..."
```

### 2-3. 진단 엔드포인트 (DB 변경 없음)

```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/sync/diagnose?source=G2B&rows=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**응답 예시**
```json
{
  "source": "G2B",
  "ok": true,
  "steps": [
    {"step": "api_key", "ok": true, "detail": "길이 88, 마스킹 a1b2…wxyz"},
    {"step": "build_url", "ok": true, "detail": "길이 234자"},
    {"step": "http_fetch", "ok": true, "detail": "12345바이트 / 412ms",
     "response_size": 12345, "elapsed_ms": 412},
    {"step": "extract_items", "ok": true, "detail": "5건 추출 (응답 헤드: ...)",
     "count": 5},
    {"step": "normalize", "ok": true, "detail": "유효 5 / 무효 0",
     "valid_count": 5, "invalid_count": 0}
  ],
  "sample_records": [
    {"bid_number": "20240519XXXX", "title": "도로 포장 공사",
     "org": "서울특별시", "amount": 580000000}
  ],
  "note": "이 엔드포인트는 DB를 변경하지 않습니다. 실제 적재는 POST /api/v1/admin/sync 사용."
}
```

### 2-4. 실 적재 트리거

```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/sync" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 2-5. 수집 이력 확인

```bash
curl -s "http://localhost:8000/api/v1/admin/sync/history?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.items[0:3]'
```

---

## 3. 자동 수집 스케줄러 검증

### 3-1. 스케줄 상태 조회 — 다음 실행 시각 표시

```bash
curl -s "http://localhost:8000/api/v1/admin/schedule" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

```json
{
  "interval": "daily",
  "time": "02:00",
  "enabled": true,
  "scheduler_running": true,
  "next_run": "2026-04-25 02:00:00"
}
```

### 3-2. 즉시 실행 검증을 위한 임시 변경 (예: 5분 뒤 한 번)

```bash
# 매시 정각으로 변경 → 다음 정각에 자동 호출됨
curl -s -X PUT "http://localhost:8000/api/v1/admin/schedule?interval=hourly&time=00:00&enabled=true" \
  -H "Authorization: Bearer $TOKEN"
```

서버 로그에서 다음과 같이 호출 확인:
```
INFO [bid-insight] scheduled sync job started
INFO [bid-insight] sync result source=G2B status=success records=50 inserted=12
INFO [bid-insight] sync result source=D2B status=success records=50 inserted=8
```

### 3-3. 검증 후 운영 설정 복원

```bash
curl -s -X PUT "http://localhost:8000/api/v1/admin/schedule?interval=daily&time=02:00&enabled=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. 수집 결과 확인 (UI)

브라우저에서 `http://localhost:8000` 접속 후:

1. **공고 화면** → 신규 등록 공고 (source: G2B/D2B) 노출 확인
2. **관리자 → 데이터 수집 관리** → 수집 히스토리 테이블에 성공/실패 라인 확인
3. **관리자 → 오류 모니터링** → 실패 시 `error_message` 정확 표시

---

## 5. 자주 발생하는 오류와 대응

| 증상 | 원인 | 해결 |
|------|------|------|
| `HTTP 500 Unexpected errors` | 키 미승인 / 잘못된 인증키 | 공공데이터포털에서 활용 신청 상태 재확인 |
| XML 응답 (JSON이 아님) | `type=json` 미지원 / 키 권한 미설정 | data.go.kr 마이페이지에서 활용 신청 후 1~2시간 대기 |
| `items 추출 결과 0건` | 응답 스키마 변경 또는 검색 결과 없음 | `--verbose`로 응답 헤드 확인, 일자 범위 조정 |
| `정규화 무효 N건` | bidNtceNo / bidNtceNm 누락 | 정상. 일부 응답이 비어있을 수 있음 |
| `30 errors / second` | Rate Limit 초과 | data.go.kr 일일 호출량 한도 (트래픽 한도 모니터링) |
| `Read timed out` | 네트워크 일시 장애 | CLI 자동 재시도 2회 / 운영 시 스케줄러 재시도 가능 |

---

## 6. CI / 모니터링 통합 예시

### GitHub Actions (일 1회 키 유효성 점검)
```yaml
- name: 공공데이터 키 유효성 점검
  env:
    G2B_API_KEY: ${{ secrets.G2B_API_KEY }}
  run: |
    cd backend
    python3 scripts/sync_check.py --source G2B --dry-run --rows 1 --json
```

### Crontab (시간당 1회 진단)
```cron
0 * * * * cd /app/backend && /usr/bin/python3 scripts/sync_check.py --source G2B --dry-run --json >> /app/data/sync_check.log 2>&1
```

---

## 부록: 단계별 체크리스트

- [ ] 공공데이터포털 활용 신청 **승인** 완료
- [ ] `G2B_API_KEY` 환경변수 등록
- [ ] `python3 scripts/sync_check.py --source G2B --dry-run --verbose` 성공
- [ ] `python3 scripts/sync_check.py --source G2B` (실 적재) 성공
- [ ] `POST /api/v1/admin/sync/diagnose` 응답에서 5단계 모두 ok=true
- [ ] `POST /api/v1/admin/sync` 호출 후 관리자 화면에서 신규 데이터 확인
- [ ] `GET /api/v1/admin/schedule` 에서 `scheduler_running=true`, `next_run` 표시
- [ ] 임시 스케줄 변경 → 자동 수집 1회 → 운영 스케줄 복원
- [ ] `/healthz` 200, `/metrics` `sync_success_total` 증가 확인
