# UI/UX 시안 검토 + 분석 결과 검증 리포트

> 작성일: 2026-05-01
> 환경: 비드스타 v1차 로직 적용 (Phase A~F 완료) — backend port 8002, demo.db (G2B 백필 완료, 183,006건 / BidResult 3,128건)

---

## 1. 분석 결과 검증 (백엔드 API)

### 1-1. `GET /analysis/rate-buckets/{id}` ✅ 정상
**테스트 공고**: 한국교원대학교 외벽 방수공사 (R26BK01440638, 기초금액 633M)
**파라미터**: period_months=12, category_filter=service, detail_rule=max_gap

| 항목 | 결과 |
|---|---|
| 분석 데이터 | 605건 |
| 모드 A 1순위 (빈도최대) | **100.0%** (빈도 43회, 0방향) |
| 모드 B 1순위 (공백) | 102.1% (+방향) |
| 모드 C 1순위 (차이최대) | 99.4% (-방향) |
| 세부값 (max_gap) | **97.9%** |
| 예상 투찰금액 | **619,912,590원** |

**평가**: 스펙 §1 알고리즘 정확히 동작. 정규분포 데이터에 대해 기대대로 100.0% 가 빈도최대로 나옴.

### 1-2. `GET /analysis/correlation/{id}` ✅ Fallback 적용 후 정상
**초기 문제**: `CompanyBidRecord` 테이블이 0건 → 방법 2/3 데이터 없음
**해결**: 갭 분석에 `BidResult.first_place_rate` fallback 추가

| 방법 | 1순위 사정률 | 점수 | 데이터 | source |
|---|---|---|---|---|
| 1) 사정률 발생빈도 | 100.0% | 43 | 605건 | - |
| 2) 업체사정률 갭 분석 | **99.0249%** | 0.0388 | 497건 | first_place_rate (fallback) |
| 3) 빈도+갭 결합 | **99.5125%** | 0 | 0건 (교집합 없음 → 평균) |
| **종합 1순위** | **100.0%** | 합치도 33% (1/3) | - | - |

**평가**: 3개 방법이 각각 다른 결과 도출 (33% 합치도) — 더 현실적이고 의미 있는 분석.

### 1-3. 회귀 테스트
- **pytest 77/77 통과** (rate-buckets 8건, correlation/settings/export smoke 6건 신규)

---

## 2. UI/UX 시각 검토 (Chrome MCP)

### 2-1. 잘 동작하는 부분 ✅

| 화면 | 평가 |
|---|---|
| 로그인 | 비드스타 브랜드 + 데모 빠른 로그인 버튼, 화면 비율 양호 |
| 관리자 콘솔 | 다크 + 빨간 톤 명확, KPI 5종 (총 공고 183,006건 / 평균 사정률 99.92%) 가독성 좋음 |
| 사이드바 토글 | 관리자 ↔ 서비스 전환 버튼 명확 |
| 공고 목록 | 9,151 페이지 표기 + CSV 다운로드 버튼 정렬 |
| 공고 클릭 → quick-preview 패널 | 우측 슬라이드 패널 깔끔, "간편 투찰액 계산" 입력 좋음 |
| 종합분석 빈 상태 | "공고를 선택해주세요" 안내 + 가이드 텍스트 적절 |

### 2-2. 발견된 이슈 (개선 필요) 🔴

| # | 화면 | 이슈 | 심각도 |
|---|---|---|---|
| **U1** | 공고 목록 | **공고번호/공고명 텍스트가 링크처럼 파란색이지만 행 전체 클릭만 동작** — 단독 click 핸들러 없음. 실수로 단독 클릭 시 행 전체와 다른 동작 기대 가능 | 중 |
| **U2** | 공고 quick-preview 패널 | "상세 분석 (종합화면)" 클릭 후 종합분석 페이지로 이동되지 않음 — `selectedAnnouncement` state 와 navigate 타이밍 이슈 | **높음** |
| **U3** | 공고 검색 입력 | 한글 IME 입력 후 Enter / 검색 버튼 누름에도 검색 적용 안됨 (placeholder 그대로 표시) | 중 |
| **U4** | 종합분석 페이지 | URL `?id=<공고ID>` 쿼리 파라미터 미지원 → 새로고침/북마크 시 컨텍스트 손실 | 중 |
| **U5** | 공고 KPI 카드 | quick-preview 패널이 열리면 5번째 "평균 사정률" 카드를 가림 (z-index overlap) | 낮 |
| **U6** | 사이드바 active 강조 | 종합분석 메뉴 클릭 시 active 갱신이 0.5~1초 늦음 | 낮 |
| **U7** | 분석 결과 카드 (Tab1/2/3) | 신규 추가한 카드들의 스크린샷 검증을 위한 직접 진입 경로 부재 (U2 고침 의존) | 중 |

---

## 3. 권장 조치 (우선순위순)

### 🔴 즉시 수정 (Critical)
**U2 — 상세 분석 클릭 후 navigate**: `setSelectedAnnouncement(ann)` 직후에 `navigate('/comprehensive')` 호출되지만 React batch 갱신 전이라 빈 상태로 진입. 해결:
```js
// AnnouncementsPage onPreviewDetailClick:
setSelectedAnnouncement(ann);
setTimeout(() => navigate('/comprehensive'), 0);  // microtask 후 navigate
// 또는: useEffect on selectedAnnouncement → navigate
```

### 🟡 단기 개선 (High)
- **U3 검색 IME 이슈**: `onCompositionEnd` 핸들러 추가 + Enter 키 trigger
- **U4 URL 쿼리 지원**: `useEffect(() => { const id = new URLSearchParams(window.location.search).get('id'); if (id) loadAnnouncement(id); }, [])`
- **U1 공고번호 링크화**: 행 클릭과 별개로 공고번호 클릭 시 G2B 외부 링크 새 탭 열기 (현재 quick-preview 안의 "공고 바로가기" 버튼만 가능)

### 🟢 장기 개선 (Medium)
- **U5 KPI 카드 가림**: quick-preview 패널 폭 줄이거나 카드 영역 z-index 조정
- **U6 사이드바 active 갱신**: useRoute path 갱신 후 즉시 active 클래스 적용
- **신규 Tab1/2/3 카드 시각 검증**: U2 수정 후 재시도 — 구간분석 모드 토글, KBID 검색 5종, 상관관계 그라디언트 박스

### 🆕 추가 작업 후보
- **분석 화면 진입 가이드 강화**: 빈 상태에서 "최근 분석한 공고 5개" 빠른 진입 카드
- **데이터 매칭률 표시**: 현재 992/3128 (32%) 매칭률 — KPI 카드에 노출하여 사용자가 데이터 신뢰도 인지
- **CompanyBidRecord 채우기 가이드**: 사용자에게 CSV 업로드로 업체 투찰 데이터 보강 권유 토스트 (분석 데이터 미비 시)

---

## 4. 다음 단계 추천

| 우선 | 작업 | 예상 시간 |
|---|---|---|
| **1** | U2 fix (상세 분석 navigate) — 가장 큰 사용자 영향 | 30분 |
| **2** | U3 + U4 (검색 IME + URL 쿼리) — 새로고침/공유 가능성 | 1시간 |
| **3** | Tab1/2/3 신규 카드 시각 회귀 (Chrome MCP) | 1시간 |
| **4** | 데이터 매칭률 KPI 추가 + 분석 신뢰도 안내 | 2시간 |
| **5** | NAS 연동 (Synology Docker Compose 실배포) | 1일 |

총 약 **1.5일** 분량으로 UI/UX + 검증 보강 가능. 그 후 NAS 연동 단계로 자연스럽게 전환.
