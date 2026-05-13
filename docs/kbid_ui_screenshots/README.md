# KBID 스타일 UI 캡쳐 (참고용)

> 캡쳐일: 2026-05-14
> 환경: Next.js 14 + 백엔드 8000 (실 G2B 데이터, demo admin 인증)
> 뷰포트: 1440 폭, fullPage 캡쳐
> 캡쳐 도구: `frontend/capture-kbid-ui.mjs` (Playwright chromium headless)

## 파일 목록

| 파일 | 화면 | 주요 요소 |
|------|------|-----------|
| `01_announcements_list.png` | 공고 통합 조회 (`/`) | 사이드바, KPI 4종, 검색 필터, ★ 1순위만 토글, 공고 테이블 (공고번호/공고명/발주기관/유형/예산/마감일/사정률/1순위 낙찰률/분석) — 총 1,388,494건 |
| `02_analysis_tab3_default.png` | 분석 페이지 Tab3 기본 (`/analysis/{id}`) | 파란 그라디언트 헤더, 6행 form-table 검색 패널, 요약 바, **CorrelationPanel** (3가지 방법 카드 + 종합 1순위), 데이터 테이블, 4개 탭 (Tab3 active), 히스토그램, 매트릭스, A/B/C 버킷, **업체사정률 갭 분석**, 예측값 선택, 통계, 하단 투찰금액 계산기 |
| `03_analysis_tab1_rate_chart.png` | 분석 페이지 Tab1 (`?tab=tab1`) | 사정률 그래프 분석 — Recharts 꺾은선 차트, 100% 기준선, 평균/최저/최고 사정률 시계열 |
| `04_analysis_tab2_preliminary_freq.png` | 분석 페이지 Tab2 (`?tab=tab2`) | 추첨된 예가빈도수 분석 — 예가번호별 빈도 막대 차트 (피크값 주황 강조) |
| `05_analysis_tab4_rate_table.png` | 분석 페이지 Tab4 (`?tab=tab4`) | 사정률 표 — first_place_predictions 30건/페이지 (입찰일/공고명/발주처/사정률/낙찰률/낙찰금액), 페이지네이션 |
| `06_analysis_tab3_with_selected_rate.png` | Tab3 + selectedRate 활성 (`?tab=tab3&rate=99.9469`) | 매트릭스 셀 99.9469% 파란 강조, Tab1·Tab4·Calculator로 자동 전이 확인 |
| `07_prediction_page.png` | 사정률 예측 (사이드바) | 예측 대상 공고 선택, 예측 입력 피처, 예측 결과 (예상 사정률/권장 입찰가/예측 신뢰도), 유사 업종 낙찰 이력 차트 |
| `08_statistics_page.png` | 통계 리포트 (사이드바) | 분석 기간 토글(1/3/6개월/1년), 사정률 월별 추이 + 지역별 평균 사정률, 지역별 상세 통계 표, PDF/CSV 다운로드 |
| `09_admin_page.png` | 관리자 모니터링 (사이드바) | KPI 4종(전체 사용자/프리미엄 구독/오늘 API 호출/수집 공고 총계), 데이터 파이프라인 현황(나라장터/국방부/낙찰/모델 재학습/리포트 집계), MAE/RMSE 예측 모델 성능 추이, 최근 가입 사용자 |
| `10_analysis_filters_applied.png` | 분석 페이지 필터 적용 (`?period_months=6&category=service`) | 분석 기간 6개월 + 업종 용역 필터로 데이터 재조회된 상태 |

### 향후 기능 확장 참고용 (확장 캡쳐)

#### 11-14. 풍부한 데이터 분석 페이지 (1,904건 사정률 데이터)
공고 ID `2da0a2d8-b8db-4ce6-938d-dab3818be871` (충북보건과학대학교 산학협력단 — 1,904건 사정률 분석)

| 파일 | 화면 | 비고 |
|------|------|------|
| `11_analysis_rich_tab3.png` | Tab3 + 풍부한 매트릭스 | 정규분포 히스토그램, 매트릭스 셀 다수 채워짐, A/B/C 버킷 활성, 예측 후보 다수 |
| `12_analysis_rich_tab1_chart.png` | Tab1 + 시계열 차트 | 충분한 트렌드 데이터로 라인 차트 완성도 검증 가능 |
| `13_analysis_rich_tab2_preliminary.png` | Tab2 + 예가 빈도 | 예가 추첨 분포 완전 표시 |
| `14_analysis_rich_tab4_table.png` | Tab4 + 사정률 표 | first_place_predictions 페이지네이션 검증 |

#### 15-19. 모바일 (375x812) — 5개 화면
현재 SPA는 데스크톱 전용 (사이드바 260px 고정) — 모바일에서 가로 스크롤 발생. 향후 반응형 작업 시 베이스라인.

| 파일 | 화면 |
|------|------|
| `15_mobile_announcements.png` | 공고 통합 조회 (사이드바가 화면 절반 차지) |
| `16_mobile_analysis.png` | 분석 페이지 (가로 스크롤 필요) |
| `17_mobile_prediction.png` | 사정률 예측 |
| `18_mobile_statistics.png` | 통계 리포트 |
| `19_mobile_admin.png` | 관리자 모니터링 |

#### 20-21. 태블릿 (768x1024) — 2개 화면

| 파일 | 화면 |
|------|------|
| `20_tablet_announcements.png` | 공고 리스트 (KPI/필터 줄바꿈) |
| `21_tablet_analysis.png` | 분석 페이지 (form-table 압축) |

#### 22-24. 에러/빈 상태

| 파일 | 화면 | 비고 |
|------|------|------|
| `22_no_auth_announcements.png` | 인증 없음 (공고 리스트) | API 401 → 빈 상태 처리 검증 |
| `23_no_auth_analysis.png` | 인증 없음 (분석 페이지) | 모든 fetch 실패 — 로딩→에러 처리 검증 |
| `24_invalid_analysis_id.png` | 잘못된 공고 ID | UUID 형식이지만 DB에 없는 경우의 처리 |

### 향후 기능 확장 시 활용 포인트

1. **반응형 디자인 작업** → 15-21번 베이스라인과 비교
2. **에러 핸들링 개선** → 22-24번에서 사용자에게 보이는 메시지 검토
3. **풍부한 데이터 UX 검증** → 11-14번에서 매트릭스/차트 가독성, 페이지네이션 성능 확인
4. **신규 페이지 추가** → 본 디렉토리에 동일 명명규칙으로 누적

### 1차 데모 검토(26.5.8) 대응 캡쳐 (2차 작업)
PDF 검토사항 4개 항목 대응 후 추가 캡쳐:

| 파일 | 화면 | 비고 |
|------|------|------|
| `25_analysis_tab5_company_rates.png` | Tab5 업체사정률 분석 (신규) | KBID PDF 3페이지 동등 — 좌측 업체 목록 + 우측 큰 매트릭스 (사정률 세로 × 업체 가로) + 갭분석 |
| `26_analysis_tab6_comprehensive.png` | Tab6 종합분석 (신규) | KBID PDF 4페이지 동등 — 구간정보/A/B/C/종합정보 5-카드 + 3가지 분석 방법 결과 |
| `01_announcements_list.png` (갱신) | 공고화면 KBID 동등 | 컬럼 9종(공고명+공고번호/업종면허+지역/공고기관+수요기관/기초금액+추정가격/투찰마감/개찰일시/현설일/유형/사정률+1순위), 필터 8종(검색/카테고리/업종면허/1순위만/시·도/시·군·구/공고기간/초기화) |
| `02_analysis_tab3_default.png` (갱신) | Tab3 매트릭스 | KBID 정밀도 **0.01% 단위 100컬럼** 매트릭스 + 낙찰순위 컬럼 |

### 캡쳐 스크립트
- `frontend/capture-kbid-ui.mjs` — 기본 12장 (1-10, 25-26)
- `frontend/capture-kbid-ui-extra.mjs` — 확장 14장 (11-24)

### 1차 데모 검토 대응 변경 사항 요약
- **백엔드 모델**: `BidAnnouncement` 에 `estimated_price`, `license_category`, `opening_at`, `site_visit_at` 4개 컬럼 추가 (SQLite ALTER TABLE 직접 실행 — `backend/scripts/add_kbid_announcement_fields.py`)
- **백엔드 API** `/api/v1/announcements`: parent_org / estimated_price / license_category / opening_at / site_visit_at 응답 노출, region_sido / region_sigungu / license_category 쿼리 파라미터 추가
- **백엔드 신규 엔드포인트** `/api/v1/announcements/meta/regions`: 시·도/시·군·구 옵션 + license_category 옵션 동적 추출
- **백엔드 API** `/api/v1/analysis/frequency`: `bin_size` 파라미터화 (기본 0.01), `category_filter` 추가 (same/all/construction/service/industry)
- **백엔드 API** `/api/v1/analysis/comprehensive` comparisons[]에 `rank` 필드 추가
- **프론트**: AnnouncementsPage 컬럼/필터 KBID 형식으로 재구성, Tab3 매트릭스 100컬럼 0.01%, AnalysisDataTable 낙찰순위 컬럼, Tab5/Tab6 신규

두 스크립트 모두 `node` 실행. 백엔드(8000)/Next.js(3100) 가동 후 사용. 토큰 만료 시 스크립트 상단 `TOKEN` 갱신 필요 (1년짜리 admin demo 토큰).

## KBID 컬러 (Tailwind)
- 진파랑 `#2C4F8A`, 중파랑 `#3358A4`, 연파랑 `#4A7ABF` / `#7C9CD1`
- 주황 (강조/1순위) `#E8913A`
- 초록 (일치 ●) `#4CAF50`
- 라벨 배경 `#E8EDF3`
- 페이지 배경 `#F0F4F8`

## 재캡쳐 방법

```bash
# 1) 백엔드 (8000) 가동
.venv/bin/python backend/server.py

# 2) Next.js (3100) 가동
cd frontend && npm run dev -- -p 3100

# 3) Playwright 캡쳐 실행 (frontend/ 디렉토리에서)
node capture-kbid-ui.mjs
```

캡쳐 스크립트는 `frontend/capture-kbid-ui.mjs` 에 있으며, 6개 화면 URL과 출력 경로가 명시되어 있다.
다른 공고 ID로 재캡쳐하려면 스크립트 내 `ID` 상수만 변경.

## 구조 정리 (참고용)

분석 페이지 컴포넌트 트리:
```
AnalysisPage (page.tsx)
├── AnalysisHeader            ← 파란 그라디언트 + 공고 타이틀
├── AnalysisFilterPanel       ← 6행 form-table (공고명/번호/발주처/구분/예가변동폭/투찰하한율/기초금액/추정가격/업종조건/분석건수/분석기간)
├── AnalysisSummaryBar        ← 평균/최하/최고/중간 사정률 + 선택엑셀출력
├── CorrelationPanel          ← 3가지 방법 카드 + 종합 1순위 + 신뢰도 + 95% 신뢰구간
├── AnalysisDataTable         ← comprehensive.comparisons 페이지네이션 테이블
├── AnalysisTabs
│   ├── Tab1RateChart         ← Recharts 꺾은선 (selectedRate 참조선)
│   ├── Tab2PreliminaryFreq   ← Recharts 막대 (예가 빈도)
│   ├── Tab3FrequencyMatrix   ← 히스토그램 + 0.1% 매트릭스 + A/B/C 버킷 + 갭 분석 + 예측 후보
│   └── Tab4RateTable         ← first_place_predictions 페이지네이션
└── AnalysisCalculator        ← 기초금액 × 선택사정률 = 투찰금액
```

상태 리프트: `selectedRate`가 Tab3 매트릭스/버킷/갭/예측후보/Correlation 카드에서 발생 → Tab1 참조선, Tab4 하이라이트, Calculator 자동 반영.
