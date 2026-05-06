# G2B API 키 설정 가이드

## 현황 (2026-05-06)

- 실데이터: 용역 182,836건 / **공사 0건**
- 원인: `G2B_API_KEY` 미설정 → 공공데이터 API 호출 불가
- 코드는 양 카테고리 모두 수집하도록 정상 구현되어 있음 (`G2B_CATEGORIES = [용역, 공사]`)

## 설정 절차

### 1. 인증키 발급
1. https://www.data.go.kr 접속 → 회원가입/로그인
2. "**나라장터(G2B) 입찰공고정보**" 검색 → API 신청
3. "**나라장터(G2B) 개찰결과정보**" 별도 신청
4. **마이페이지 → 데이터 활용 → API 인증키** 에서 일반 인증키(Encoding) 복사

### 2. .env 등록
```bash
cd backend
# G2B_API_KEY 라인의 주석 해제 + 키 입력
sed -i '' 's|^# G2B_API_KEY=.*|G2B_API_KEY=발급받은_인증키|' .env

# (선택) 국방조달도 사용 시
# D2B_API_KEY=...
# DEFENSE_ENABLED=true
```

### 3. 서버 재시작
```bash
pkill -f "python3 server.py"
cd backend && PORT=8005 nohup python3 server.py > /tmp/bidstar-server.log 2>&1 &
```

### 4. 수동 수집 트리거
- 관리자로 로그인 → `/admin/sync` → "수동 수집" 버튼
- 또는 `curl -X POST http://localhost:8005/api/v1/admin/sync -H "Authorization: Bearer $TOKEN"`
- 자동 수집 스케줄: 매일 02:00 (`SYNC_INTERVAL=daily`, `SYNC_TIME=02:00`)

## 예상 결과

기본 설정 (`SYNC_TOTAL_DAYS_ANN=60`, `SYNC_WINDOW_DAYS=7`, `SYNC_MAX_PAGES_ANN=5`):
- 60일 × 카테고리 2개 (용역+공사) × 윈도우 9개 × 페이지 5 = 최대 90페이지 호출
- 페이지당 100건 → 최대 9,000건 신규 적재 가능

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `inserted_count = 0` | 모두 중복 (upsert) | 정상. `records_fetched` 확인 |
| `status = failed` | API 키 무효/할당량 초과 | data.go.kr → API 활용현황 확인 |
| 공사만 0건 | `getBidPblancListInfoCnstwk` endpoint 미신청 | 공공데이터포털에서 별도 신청 |
| 503/타임아웃 | API 응답 지연 | `SYNC_MAX_PAGES_ANN` 줄이거나 윈도우 좁히기 |

## 참고

- 코드 위치: `backend/app/services/sync.py` `_run_sync_for_source` (line 555+)
- 카테고리 매핑: `G2B_CATEGORIES` (line 238)
- 진행률 모니터: `GET /api/v1/admin/sync/progress`
