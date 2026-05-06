# 비드스타 Frontend E2E (Playwright)

스펙 §1/2/3 사정률 예측 로직 및 UI fix(U1~U7) 회귀를 자동화한 Playwright 테스트.

## 사전 요구

1. **백엔드 가동**
   ```bash
   cd backend
   python3 server.py
   # 또는 PORT=8001 python3 server.py 후 BASE_URL=http://localhost:8001
   ```

2. **Playwright 1회 설치** (최초 1회만)
   ```bash
   cd frontend
   npm run e2e:install
   ```
   → `@playwright/test` + chromium 브라우저 다운로드 (~140MB).

## 실행

```bash
cd frontend
npm run e2e                          # 헤드리스 전체
npm run e2e:headed                   # 브라우저 보면서
npm run e2e -- analysis.spec.ts      # 특정 파일만
npm run e2e -- --grep "Tab2"         # 특정 테스트만
npm run e2e:report                   # HTML 리포트 열기
BASE_URL=http://localhost:8001 npm run e2e   # 다른 포트
```

## 테스트 구성 (총 14건)

| 파일 | 테스트 | 검증 |
|---|---|---|
| `auth.spec.ts` | 3 | 로그인 / 데모 빠른 로그인 / 사이드바 5개 메뉴 + 종합분석 빈 안내 |
| `announcements.spec.ts` | 5 | U1 외부링크 / U2 navigate / U3 IME / U4 ?id= / U5 KPI 보존 |
| `analysis.spec.ts` | 8 | Tab1 모드 토글, Tab2 검색 5종, Tab3 상관관계 카드, 엑셀 다운로드, 학습 저장 |

## CI 권장 설정

`.github/workflows/e2e.yml` 예:
```yaml
- run: cd backend && pip install -r requirements.txt && python3 server.py &
- run: sleep 5
- run: cd frontend && npm install && npm run e2e:install && npm run e2e
```

## 트러블슈팅

| 증상 | 해결 |
|---|---|
| `Error: locator.click: Timeout` | 백엔드가 안 떴거나 포트 충돌 — `lsof -i :8000` 확인 |
| 다운로드 spec 실패 | `playwright.config.ts` 의 `use.acceptDownloads` 확인 (기본 true) |
| 한글 검색 spec 실패 | 브라우저 locale ko-KR 인지 확인 (config 에 설정됨) |
| flaky 분석 spec | 백엔드 DB 에 BidResult 가 충분한지 (`tests/test_prediction_e2e.py` 의 fixture 패턴 참고) |
