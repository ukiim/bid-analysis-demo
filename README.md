# 입찰 인사이트 - 조달 입찰 사정률 예측 플랫폼

공공데이터포털 Open API를 활용한 입찰가 산정 및 사정률 분석 웹 플랫폼 데모입니다.

## 핵심 기능

1. **공고 통합 조회** - 나라장터(G2B) + 국방부(D2B) 입찰공고 통합 수집/조회
2. **사정률 예측** - 과거 낙찰 데이터 기반 ML 모델로 사정률/입찰가 예측
3. **통계 리포트** - 업종별·지역별 사정률 추이 분석
4. **관리자 모니터링** - 데이터 파이프라인, 모델 성능, 사용자 관리

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 16 |
| ML | scikit-learn, XGBoost, statsmodels, SHAP |
| Scheduler | APScheduler |
| Infra | Docker Compose |

## 빠른 시작

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에 DATA_GO_KR_API_KEY 입력

# 2. Docker Compose로 전체 실행
docker-compose up -d

# 3. DB 마이그레이션
cd backend
alembic upgrade head

# 4. 시드 데이터 삽입
python seed_data.py

# 5. 접속
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## 수동 실행 (개발 모드)

```bash
# PostgreSQL 실행
docker-compose up -d postgres

# 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed_data.py
uvicorn app.main:app --reload --port 8000

# 프론트엔드
cd frontend
npm install
npm run dev
```

## 프로젝트 구조

```
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── api/routes/    # REST API 엔드포인트
│   │   ├── db/            # SQLAlchemy 모델, DB 세션
│   │   ├── etl/           # 공공데이터 API 클라이언트, ETL 파이프라인
│   │   ├── ml/            # 피처 엔지니어링, 학습, 예측 모듈 ⭐
│   │   ├── schemas/       # Pydantic 요청/응답 스키마
│   │   └── main.py
│   ├── alembic/           # DB 마이그레이션
│   ├── models/            # 학습된 ML 모델 파일
│   └── seed_data.py       # 데모 시드 데이터
└── frontend/
    └── src/
        ├── app/           # Next.js App Router
        ├── components/    # UI 컴포넌트 (4개 페이지)
        └── lib/           # API 클라이언트, 유틸
```

## 사정률 예측 모델

### 예측 대상
- **사정률** = 예정가격 / 기초금액 × 100

### 모델 파이프라인
1. **Baseline**: 카테고리×지역×기관유형별 평균
2. **Ridge Regression**: 정규화 선형회귀
3. **XGBoost**: Gradient Boosting (Optuna 하이퍼파라미터 튜닝)

### 주요 피처
- 업종코드 (Target Encoding)
- 지역 (Target Encoding)
- 발주기관 유형 (One-hot)
- 예산 규모 (Log-transform)
- 시간 (Cyclical Encoding)
- 기관별 과거 사정률 (Rolling Average)

### 자동 재학습
- 신규 낙찰결과 100건 축적 시 자동 재학습
- 모델 성능 비교 후 최적 모델 자동 교체

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/announcements` | 공고 목록 (필터/페이지네이션) |
| GET | `/api/v1/announcements/{id}` | 공고 상세 |
| POST | `/api/v1/predictions` | 사정률 예측 실행 |
| GET | `/api/v1/predictions/{id}` | 예측 결과 조회 |
| GET | `/api/v1/stats/kpi` | 대시보드 KPI |
| GET | `/api/v1/stats/trends` | 사정률 월별 추이 |
| GET | `/api/v1/stats/by-region` | 지역별 통계 |
| GET | `/api/v1/stats/by-industry` | 업종별 통계 |
| GET | `/api/v1/admin/dashboard` | 관리자 대시보드 |
| POST | `/api/v1/admin/retrain` | 모델 재학습 트리거 |
| POST | `/api/v1/admin/sync` | 데이터 수집 트리거 |

## 공공데이터 API 연동

### 조달청 나라장터 (G2B)
- 입찰공고정보서비스
- 낙찰정보서비스
- 계약정보서비스

### 방위사업청 국방전자조달 (D2B)
- 군수품조달정보 입찰공고
- 군수품조달정보 입찰결과
- 군수품조달정보 계약정보

> 공공데이터포털(data.go.kr)에서 API 키를 발급받아 `.env`에 설정하세요.
