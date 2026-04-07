"""통합 데모 서버 — KBID 스타일 1순위 예상 낙찰가 분석 시스템

SQLite + FastAPI로 백엔드 API 서빙 + 프론트엔드 정적 파일 서빙
단일 프로세스로 전체 데모 구동

실행: python3 server.py
"""

import os
import sys
import uuid
import json
import random
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text, DateTime, Boolean,
    func, case, select, text, ForeignKey,
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from jose import JWTError, jwt
from passlib.context import CryptContext

# ─── DB 설정 (SQLite) ──────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")
NAS_PATH = os.environ.get("NAS_MOUNT_PATH", os.path.join(os.path.dirname(__file__), "data"))
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ─── 모델 ──────────────────────────────────────────────────────────────────

class BidAnnouncement(Base):
    __tablename__ = "bid_announcements"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    bid_number = Column(String, nullable=False)
    category = Column(String, nullable=False)          # 공사 / 용역
    title = Column(String, nullable=False)
    ordering_org_name = Column(String, nullable=False)
    ordering_org_type = Column(String)
    parent_org_name = Column(String)                    # 상위 발주기관 (경기도 등)
    region = Column(String)
    industry_code = Column(String)
    base_amount = Column(Integer)
    bid_method = Column(String)
    announced_at = Column(DateTime)
    deadline_at = Column(DateTime)
    status = Column(String, default="진행중")


class BidResult(Base):
    __tablename__ = "bid_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    announcement_id = Column(String, nullable=False)
    winning_amount = Column(Integer)
    winning_rate = Column(Float)
    assessment_rate = Column(Float)
    first_place_rate = Column(Float)                    # 1순위 사정률
    first_place_amount = Column(Integer)                # 1순위 낙찰가
    num_bidders = Column(Integer)
    winning_company = Column(String)
    preliminary_prices = Column(Text)                   # JSON: 복수예비가격 15개
    selected_price_indices = Column(Text)               # JSON: 추첨된 4개 인덱스
    opened_at = Column(DateTime)


class CompanyBidRecord(Base):
    """업체별 투찰 기록"""
    __tablename__ = "company_bid_records"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    announcement_id = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    bid_amount = Column(Integer)
    bid_rate = Column(Float)                            # 업체 투찰률
    ranking = Column(Integer)
    is_first_place = Column(Boolean, default=False)


class DataSyncLog(Base):
    __tablename__ = "data_sync_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    records_fetched = Column(Integer, default=0)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    role = Column(String, default="user")              # user / admin
    plan = Column(String, default="무료")
    is_active = Column(Boolean, default=True)
    query_count = Column(Integer, default=0)
    joined_at = Column(DateTime)
    last_login_at = Column(DateTime)


class QueryHistory(Base):
    """사용자 조회 이력"""
    __tablename__ = "query_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    announcement_id = Column(String)
    analysis_type = Column(String)                     # frequency / company / comprehensive
    parameters = Column(Text)                          # JSON
    result_summary = Column(Text)                      # JSON
    queried_at = Column(DateTime, default=datetime.now)


class UploadLog(Base):
    """데이터 업로드 이력"""
    __tablename__ = "upload_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_size = Column(Integer)
    records_count = Column(Integer, default=0)
    status = Column(String, default="processing")      # processing / success / failed
    error_message = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.now)


# ─── 발주기관 계층 매핑 ───────────────────────────────────────────────────

ORG_HIERARCHY = {
    "고양시": "경기도", "수원시": "경기도", "성남시": "경기도", "용인시": "경기도",
    "안양시": "경기도", "부천시": "경기도", "화성시": "경기도", "안산시": "경기도",
    "서울특별시 강남구": "서울특별시", "서울특별시 서초구": "서울특별시",
    "서울특별시 송파구": "서울특별시", "서울특별시 강동구": "서울특별시",
    "부산광역시 해운대구": "부산광역시", "부산광역시 사하구": "부산광역시",
    "대전광역시 유성구": "대전광역시", "인천광역시 남동구": "인천광역시",
    "고양시교육청": "경기도교육청", "수원시교육청": "경기도교육청",
    "국토교통부": "중앙부처", "환경부": "중앙부처", "교육부": "중앙부처",
    "행정안전부": "중앙부처", "국방부": "중앙부처",
    "한국도로공사": "공기업", "한국수자원공사": "공기업", "한국토지주택공사": "공기업",
    "부산항만공사": "공기업", "인천국제공항공사": "공기업",
    "서울대학교": "교육기관", "부산대학교": "교육기관", "충남대학교": "교육기관",
    "경기도": "경기도", "서울특별시": "서울특별시", "부산광역시": "부산광역시",
    "대전광역시": "대전광역시", "인천광역시": "인천광역시", "세종특별자치시": "세종특별자치시",
}

# ─── 시드 데이터 ───────────────────────────────────────────────────────────

REGIONS = ["서울", "경기", "부산", "대전", "인천", "광주", "대구", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

CONSTRUCTION_TITLES = [
    "도로 포장 보수공사", "하수관로 정비공사", "청사 리모델링 공사",
    "교량 보강 공사", "공원 조성공사", "학교 시설 보수공사",
    "하천 정비공사", "문화체육센터 신축공사", "소방서 신축공사",
    "항만시설 확장공사", "상수도관 교체공사", "터널 보수공사",
]

SERVICE_TITLES = [
    "시설 유지보수 용역", "정보시스템 운영 용역", "설계 감리 용역",
    "환경영향평가 용역", "도시계획 수립 용역", "보안관제 운영 용역",
    "전산장비 유지보수 용역", "스마트시티 플랫폼 구축 용역",
    "데이터센터 운영 용역", "통합관제 구축 용역", "교통영향분석 용역",
]

ORGS = {
    "중앙부처": ["국토교통부", "환경부", "교육부", "행정안전부", "국방부"],
    "지자체": ["서울특별시", "부산광역시", "대전광역시", "인천광역시", "경기도", "세종특별자치시",
               "고양시", "수원시", "성남시", "용인시", "안양시", "부천시"],
    "공기업": ["한국도로공사", "한국수자원공사", "한국토지주택공사", "부산항만공사", "인천국제공항공사"],
    "교육기관": ["서울대학교", "부산대학교", "충남대학교"],
}

COMPANY_NAMES = [
    "(주)대한건설", "(주)한양종합건설", "(주)태영건설", "(주)일신건설산업",
    "(주)동아건설", "(주)세진종합건설", "(주)삼호건설", "(주)현대건설",
    "(주)우림건설", "(주)한솔건설", "(주)대우건설", "(주)신세계건설",
    "(주)미래건설", "(주)동원건설", "(주)풍림건설", "(주)코오롱건설",
    "(주)금호건설", "(주)포스코건설", "(주)롯데건설", "(주)GS건설",
    "(주)서영시스템즈", "(주)아이티플러스", "(주)하나정보기술", "(주)위드텍",
    "(주)넥스트웨이브", "(주)에스앤아이", "(주)유비쿼터스", "(주)스마트솔루션",
]

REGION_RATE_ADJ = {
    "서울": 0.15, "경기": 0.05, "부산": -0.10, "대전": 0.20,
    "인천": 0.05, "강원": -0.15, "세종": 0.10, "대구": -0.20,
    "광주": -0.05, "울산": 0.0, "충북": -0.05, "충남": 0.0,
    "전북": -0.10, "전남": -0.15, "경북": -0.10, "경남": -0.05, "제주": -0.20,
}


def seed_database():
    """600건의 현실적 데모 데이터 생성 (용역/공사만)"""
    db = SessionLocal()

    if db.query(BidAnnouncement).first():
        print("데이터 이미 존재. 시드 건너뜀.")
        db.close()
        return

    print("시드 데이터 생성 시작...")
    random.seed(42)

    announcements = []
    for i in range(600):
        is_construction = random.random() < 0.55
        category = "공사" if is_construction else "용역"
        source = "D2B" if random.random() < 0.12 else "G2B"
        org_type = random.choice(list(ORGS.keys()))
        org_name = random.choice(ORGS[org_type])
        region = random.choice(REGIONS)
        parent_org = ORG_HIERARCHY.get(org_name, org_type)

        if is_construction:
            title = f"{region} {random.choice(CONSTRUCTION_TITLES)}"
            base_amount = random.randint(5000, 500000) * 10000
        else:
            title = f"{org_name} {random.choice(SERVICE_TITLES)}"
            base_amount = random.randint(1000, 100000) * 10000

        days_ago = random.randint(1, 730)
        announced_at = datetime.now() - timedelta(days=days_ago)
        deadline_at = announced_at + timedelta(days=random.randint(10, 30))
        status = "개찰완료" if days_ago > 30 else "진행중"

        ann = BidAnnouncement(
            source=source,
            bid_number=f"{'D' if source == 'D2B' else 'G'}{announced_at.strftime('%Y%m')}-{i:05d}",
            category=category,
            title=title,
            ordering_org_name=org_name,
            ordering_org_type=org_type,
            parent_org_name=parent_org,
            region=region,
            industry_code=f"{'C' if is_construction else 'S'}{random.randint(100, 999)}",
            base_amount=base_amount,
            bid_method=random.choice(["적격심사", "최저가", "2단계경쟁", "협상에의한계약"]),
            announced_at=announced_at,
            deadline_at=deadline_at,
            status=status,
        )
        db.add(ann)
        db.flush()
        announcements.append((ann, status, category, region, base_amount, org_type))

    # ── 낙찰결과 + 업체 투찰기록 생성 ──
    result_count = 0
    company_count = 0
    for ann, status, category, region, base_amount, org_type in announcements:
        if status != "개찰완료":
            continue

        # Beta 분포 기반 사정률 (99.3~99.5% 구간 집중)
        base_rate = 99.3 if category == "공사" else 99.5
        adj = REGION_RATE_ADJ.get(region, 0)
        # Beta 분포로 현실적 클러스터링
        alpha, beta_param = 8, 2
        raw = random.betavariate(alpha, beta_param)
        assessment_rate = base_rate + adj + (raw - 0.8) * 2.0
        assessment_rate = max(97.0, min(102.0, assessment_rate))
        assessment_rate = round(assessment_rate, 4)

        # 복수예비가격 15개 생성
        estimated_price = int(base_amount * assessment_rate / 100)
        prelim_prices = []
        for _ in range(15):
            deviation = random.uniform(-0.03, 0.03)
            prelim_prices.append(int(estimated_price * (1 + deviation)))
        selected_indices = sorted(random.sample(range(15), 4))
        avg_selected = sum(prelim_prices[j] for j in selected_indices) / 4

        # 업체 투찰 기록 생성
        num_bidders = random.randint(5, 25)
        companies = random.sample(COMPANY_NAMES, min(num_bidders, len(COMPANY_NAMES)))
        company_records = []
        for comp in companies:
            # 업체 사정률: 사정률 근처 ± 0.5% 내 분포, 일부 클러스터링
            cluster_center = assessment_rate + random.gauss(0, 0.2)
            bid_rate = cluster_center + random.gauss(0, 0.15)
            bid_rate = round(max(97.0, min(102.0, bid_rate)), 4)
            bid_amount = int(base_amount * bid_rate / 100)
            company_records.append({
                "company": comp, "rate": bid_rate, "amount": bid_amount,
            })

        # 사정률에 가장 가까운 업체 = 1순위
        company_records.sort(key=lambda x: abs(x["rate"] - assessment_rate))
        first_place = company_records[0]
        first_place_rate = first_place["rate"]
        first_place_amount = first_place["amount"]

        # 랭킹 부여
        company_records.sort(key=lambda x: abs(x["rate"] - assessment_rate))
        for rank_idx, cr in enumerate(company_records):
            cr["ranking"] = rank_idx + 1
            cr["is_first"] = (rank_idx == 0)

        # BidResult 저장
        winning_rate = round(first_place_amount / estimated_price * 100, 4) if estimated_price else 0
        result = BidResult(
            announcement_id=ann.id,
            winning_amount=first_place_amount,
            winning_rate=winning_rate,
            assessment_rate=assessment_rate,
            first_place_rate=first_place_rate,
            first_place_amount=first_place_amount,
            num_bidders=num_bidders,
            winning_company=first_place["company"],
            preliminary_prices=json.dumps(prelim_prices),
            selected_price_indices=json.dumps(selected_indices),
            opened_at=ann.announced_at + timedelta(days=random.randint(14, 45)),
        )
        db.add(result)
        result_count += 1

        # CompanyBidRecord 저장
        for cr in company_records:
            db.add(CompanyBidRecord(
                announcement_id=ann.id,
                company_name=cr["company"],
                bid_amount=cr["amount"],
                bid_rate=cr["rate"],
                ranking=cr["ranking"],
                is_first_place=cr["is_first"],
            ))
            company_count += 1

    # ── 수집 로그 ──
    for src in ["G2B", "D2B"]:
        for stype in ["공고 수집", "낙찰 데이터 수집"]:
            db.add(DataSyncLog(
                source=src, sync_type=stype, status="success",
                records_fetched=random.randint(80, 400),
                started_at=datetime.now() - timedelta(hours=random.randint(1, 12)),
                finished_at=datetime.now() - timedelta(minutes=random.randint(1, 60)),
            ))

    # ── 사용자 ── (username, name, email, role, plan, query_count)
    _pwd = CryptContext(schemes=["bcrypt"]).hash("demo1234")
    users_data = [
        ("admin", "관리자", "admin@bidinsight.kr", "admin", "프리미엄", 0),
        ("ykim", "김영호", "ykim@guncorp.co.kr", "user", "프리미엄", 342),
        ("sypark", "박수연", "sypark@daewoo.co.kr", "user", "스탠다드", 128),
        ("jwlee", "이재원", "jwlee@hanshin.com", "user", "프리미엄", 489),
        ("mjchoi", "최민준", "mjchoi@hyundai-eng.com", "user", "무료", 24),
        ("dhjeong", "정다혜", "dhjeong@posco.co.kr", "user", "스탠다드", 216),
    ]
    for username, name, email, role, plan, qc in users_data:
        db.add(User(
            username=username, email=email, hashed_password=_pwd,
            name=name, role=role, plan=plan, query_count=qc,
            joined_at=datetime.now() - timedelta(days=random.randint(30, 180)),
            last_login_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
        ))

    db.commit()
    db.close()
    print(f"  공고 {len(announcements)}건, 낙찰결과 {result_count}건, 업체투찰 {company_count}건 생성 완료!")


# ─── FastAPI 앱 ────────────────────────────────────────────────────────────

app = FastAPI(title="입찰 인사이트 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── 인증 설정 ──────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "bid-insight-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    """JWT 토큰에서 현재 사용자 조회. 토큰 없으면 None 반환."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return user


def require_auth(current_user: User = Depends(get_current_user)):
    """인증 필수 의존성"""
    if not current_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return current_user


def require_admin(current_user: User = Depends(require_auth)):
    """관리자 권한 필수 의존성"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


# ─── API: 인증 ──────────────────────────────────────────────────────────

@app.post("/api/v1/auth/register")
def register(username: str = Query(...), email: str = Query(...),
             password: str = Query(...), name: str = Query(None)):
    db = SessionLocal()
    # 중복 확인
    if db.query(User).filter(User.username == username).first():
        db.close()
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
    if db.query(User).filter(User.email == email).first():
        db.close()
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    user = User(
        username=username, email=email,
        hashed_password=get_password_hash(password),
        name=name or username, role="user",
        joined_at=datetime.now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id})
    db.close()
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "name": user.name,
                 "email": user.email, "role": user.role, "plan": user.plan},
    }


@app.post("/api/v1/auth/login")
def login(username: str = Query(...), password: str = Query(...)):
    db = SessionLocal()
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        db.close()
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    user.last_login_at = datetime.now()
    db.commit()
    token = create_access_token({"sub": user.id})
    db.close()
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "name": user.name,
                 "email": user.email, "role": user.role, "plan": user.plan},
    }


@app.get("/api/v1/auth/me")
def get_me(current_user: User = Depends(require_auth)):
    return {
        "id": current_user.id, "username": current_user.username,
        "name": current_user.name, "email": current_user.email,
        "role": current_user.role, "plan": current_user.plan,
        "query_count": current_user.query_count,
        "joined_at": current_user.joined_at.strftime("%Y-%m-%d") if current_user.joined_at else None,
    }


@app.post("/api/v1/auth/refresh")
def refresh_token(current_user: User = Depends(require_auth)):
    token = create_access_token({"sub": current_user.id})
    return {"access_token": token, "token_type": "bearer"}


# ─── API: 공고 목록 ──────────────────────────────────────────────────────

@app.get("/api/v1/announcements")
def list_announcements(
    category: str = None, source: str = None, region: str = None,
    keyword: str = None, status: str = None,
    page: int = 1, page_size: int = 20,
):
    db = SessionLocal()
    q = db.query(BidAnnouncement)

    # 용역/공사만
    q = q.filter(BidAnnouncement.category.in_(["공사", "용역"]))

    if category and category != "all":
        cats = [c.strip() for c in category.split(",")]
        if len(cats) == 1:
            q = q.filter(BidAnnouncement.category == cats[0])
        else:
            q = q.filter(BidAnnouncement.category.in_(cats))
    if source and source != "all":
        q = q.filter(BidAnnouncement.source == source)
    if region and region != "all":
        q = q.filter(BidAnnouncement.region == region)
    if status and status != "all":
        q = q.filter(BidAnnouncement.status == status)
    if keyword:
        q = q.filter(
            BidAnnouncement.title.contains(keyword) |
            BidAnnouncement.ordering_org_name.contains(keyword)
        )

    total = q.count()
    items = q.order_by(BidAnnouncement.announced_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for ann in items:
        res = db.query(BidResult).filter(BidResult.announcement_id == ann.id).first()
        result_items.append({
            "id": ann.id,
            "bid_number": ann.bid_number,
            "title": ann.title,
            "org": ann.ordering_org_name,
            "type": ann.category,
            "area": ann.region,
            "budget": ann.base_amount,
            "deadline": ann.deadline_at.strftime("%Y-%m-%d") if ann.deadline_at else "",
            "rate": round(res.assessment_rate, 2) if res and res.assessment_rate else None,
            "first_place_rate": round(res.first_place_rate, 4) if res and res.first_place_rate else None,
            "first_place_amount": res.first_place_amount if res else None,
            "status": ann.status,
            "source": ann.source,
            "bid_method": ann.bid_method,
            "num_bidders": res.num_bidders if res else None,
        })

    db.close()
    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@app.get("/api/v1/announcements/{announcement_id}")
def get_announcement(announcement_id: str):
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}
    res = db.query(BidResult).filter(BidResult.announcement_id == ann.id).first()
    db.close()
    return {
        "id": ann.id, "bid_number": ann.bid_number, "title": ann.title,
        "org": ann.ordering_org_name, "org_type": ann.ordering_org_type,
        "parent_org": ann.parent_org_name,
        "type": ann.category, "area": ann.region, "source": ann.source,
        "budget": ann.base_amount, "bid_method": ann.bid_method,
        "industry_code": ann.industry_code, "status": ann.status,
        "deadline": ann.deadline_at.strftime("%Y-%m-%d") if ann.deadline_at else "",
        "announced_at": ann.announced_at.strftime("%Y-%m-%d") if ann.announced_at else "",
        "rate": round(res.assessment_rate, 4) if res and res.assessment_rate else None,
        "first_place_rate": round(res.first_place_rate, 4) if res and res.first_place_rate else None,
        "first_place_amount": res.first_place_amount if res else None,
        "num_bidders": res.num_bidders if res else None,
    }


# ─── API: 사정률 발생빈도 분석 ────────────────────────────────────────────

@app.get("/api/v1/analysis/frequency/{announcement_id}")
def analysis_frequency(
    announcement_id: str,
    period_months: int = Query(12, ge=3, le=24),
    org_scope: str = Query("specific"),  # specific | parent
):
    """사정률 발생빈도 히스토그램 + 피크 구간 분석"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}

    cutoff = datetime.now() - timedelta(days=period_months * 30)

    # 동일 카테고리 + 발주처 범위의 과거 사정률
    q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidResult.assessment_rate.isnot(None),
        BidResult.opened_at >= cutoff,
    )
    if org_scope == "parent" and ann.parent_org_name:
        # 상위 기관 범위
        q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
    else:
        # 동일 발주기관
        q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

    rows = q.all()
    if not rows:
        # 폴백: 같은 카테고리+지역 전체
        q = db.query(BidResult.assessment_rate, BidResult.first_place_rate).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.region == ann.region,
            BidResult.assessment_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        rows = q.all()

    rates = [r.assessment_rate for r in rows if r.assessment_rate]
    first_place_rates = [r.first_place_rate for r in rows if r.first_place_rate]

    if not rates:
        db.close()
        return {"bins": [], "peaks": [], "stats": {}, "data_count": 0}

    # 0.1% 단위 히스토그램
    min_r = math.floor(min(rates) * 10) / 10
    max_r = math.ceil(max(rates) * 10) / 10
    bin_size = 0.1
    bins = []
    current = min_r
    while current <= max_r + 0.001:
        count = sum(1 for r in rates if current - bin_size / 2 <= r < current + bin_size / 2)
        fp_count = sum(1 for r in first_place_rates if current - bin_size / 2 <= r < current + bin_size / 2)
        bins.append({
            "rate": round(current, 2),
            "count": count,
            "first_place_count": fp_count,
        })
        current = round(current + bin_size, 2)

    # 피크 구간 (상위 5개)
    sorted_bins = sorted(bins, key=lambda b: b["count"], reverse=True)
    peaks = []
    for b in sorted_bins[:5]:
        if b["count"] > 0:
            peaks.append({
                "rate": b["rate"],
                "range_start": round(b["rate"] - bin_size / 2, 2),
                "range_end": round(b["rate"] + bin_size / 2, 2),
                "count": b["count"],
            })

    stat = {
        "mean": round(statistics.mean(rates), 4),
        "median": round(statistics.median(rates), 4),
        "std": round(statistics.stdev(rates), 4) if len(rates) > 1 else 0,
        "min": round(min(rates), 4),
        "max": round(max(rates), 4),
    }

    db.close()
    return {
        "bins": bins,
        "peaks": peaks,
        "stats": stat,
        "data_count": len(rates),
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "org": ann.ordering_org_name, "area": ann.region,
            "budget": ann.base_amount,
        },
    }


# ─── API: 업체사정률 분석 (갭 분석) ───────────────────────────────────────

@app.get("/api/v1/analysis/company-rates/{announcement_id}")
def analysis_company_rates(
    announcement_id: str,
    rate_range_start: float = Query(99.0),
    rate_range_end: float = Query(100.0),
    period_months: int = Query(12, ge=3, le=24),
):
    """선택 구간 내 업체 투찰률 분포 + 최대 갭 분석"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}

    cutoff = datetime.now() - timedelta(days=period_months * 30)

    # 선택 구간 내 업체 투찰률
    records = db.query(CompanyBidRecord).join(
        BidAnnouncement, CompanyBidRecord.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidAnnouncement.announced_at >= cutoff,
        CompanyBidRecord.bid_rate >= rate_range_start,
        CompanyBidRecord.bid_rate <= rate_range_end,
    ).order_by(CompanyBidRecord.bid_rate).all()

    company_rates = [
        {
            "company": r.company_name,
            "rate": round(r.bid_rate, 4),
            "amount": r.bid_amount,
            "ranking": r.ranking,
            "is_first_place": r.is_first_place,
        }
        for r in records
    ]

    # 갭 분석: 연속 투찰률 간 최대 빈 공간
    unique_rates = sorted(set(r.bid_rate for r in records))
    gaps = []
    if len(unique_rates) >= 2:
        for i in range(len(unique_rates) - 1):
            gap_size = round(unique_rates[i + 1] - unique_rates[i], 4)
            if gap_size > 0.01:  # 유의미한 갭만
                gaps.append({
                    "start": round(unique_rates[i], 4),
                    "end": round(unique_rates[i + 1], 4),
                    "size": gap_size,
                    "midpoint": round((unique_rates[i] + unique_rates[i + 1]) / 2, 4),
                })

    gaps.sort(key=lambda g: g["size"], reverse=True)
    largest_gap_midpoint = gaps[0]["midpoint"] if gaps else round((rate_range_start + rate_range_end) / 2, 4)
    refined_rate = largest_gap_midpoint

    # 1순위 예측 리스트 (해당 구간 내 과거 1순위 결과)
    first_place_in_range = db.query(BidResult, BidAnnouncement).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidResult.first_place_rate >= rate_range_start,
        BidResult.first_place_rate <= rate_range_end,
        BidResult.opened_at >= cutoff,
    ).order_by(BidResult.opened_at.desc()).limit(20).all()

    first_place_list = [
        {
            "title": a.title,
            "org": a.ordering_org_name,
            "area": a.region,
            "assessment_rate": round(r.assessment_rate, 4),
            "first_place_rate": round(r.first_place_rate, 4),
            "first_place_amount": r.first_place_amount,
            "date": r.opened_at.strftime("%Y-%m-%d") if r.opened_at else "",
        }
        for r, a in first_place_in_range
    ]

    db.close()
    return {
        "company_rates": company_rates[:100],  # 최대 100건
        "gaps": gaps[:10],
        "largest_gap_midpoint": largest_gap_midpoint,
        "refined_rate": refined_rate,
        "total_companies": len(company_rates),
        "unique_rate_count": len(unique_rates),
        "first_place_predictions": first_place_list,
    }


# ─── API: 종합분석 ────────────────────────────────────────────────────────

@app.get("/api/v1/analysis/comprehensive/{announcement_id}")
def analysis_comprehensive(
    announcement_id: str,
    confirmed_rate: float = Query(99.5),
    period_months: int = Query(12, ge=3, le=24),
    org_scope: str = Query("specific"),
):
    """확정사정률 기반 과거 1순위 비교 + 종합 분석"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}

    # 기간별 분석 (밀어내기식)
    periods = [3, 6, 9, 12, 24]
    period_results = {}

    for pm in periods:
        if pm > period_months:
            continue
        cutoff = datetime.now() - timedelta(days=pm * 30)

        q = db.query(BidResult, BidAnnouncement).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidResult.assessment_rate.isnot(None),
            BidResult.first_place_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )

        if org_scope == "parent" and ann.parent_org_name:
            q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
        elif org_scope == "specific":
            q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

        past_data = q.order_by(BidResult.opened_at.desc()).all()

        match_count = 0
        comparisons = []
        for res, past_ann in past_data:
            # 예측사정률(confirmed_rate)로 1순위 되었을지 확인
            diff = abs(confirmed_rate - res.assessment_rate)
            actual_diff = abs(res.first_place_rate - res.assessment_rate)
            is_match = diff <= actual_diff + 0.02  # 오차범위 0.02%

            if is_match:
                match_count += 1

            comparisons.append({
                "id": past_ann.id,
                "title": past_ann.title,
                "org": past_ann.ordering_org_name,
                "area": past_ann.region,
                "date": res.opened_at.strftime("%Y-%m-%d") if res.opened_at else "",
                "assessment_rate": round(res.assessment_rate, 4),
                "first_place_rate": round(res.first_place_rate, 4),
                "predicted_rate": round(confirmed_rate, 4),
                "predicted_diff": round(diff, 4),
                "actual_first_diff": round(actual_diff, 4),
                "is_match": is_match,
                "first_place_amount": res.first_place_amount,
            })

        total = len(comparisons)
        period_results[f"{pm}m"] = {
            "period_months": pm,
            "match_count": match_count,
            "total": total,
            "match_rate": round(match_count / total * 100, 1) if total > 0 else 0,
            "comparisons": comparisons[:30],  # 최대 30건
        }

    # 1순위 예상 낙찰가
    predicted_first_place_amount = int(ann.base_amount * confirmed_rate / 100) if ann.base_amount else 0

    # 상위기관 동시 분석
    parent_analysis = None
    if ann.parent_org_name and org_scope == "specific":
        cutoff = datetime.now() - timedelta(days=period_months * 30)
        parent_q = db.query(BidResult, BidAnnouncement).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.parent_org_name == ann.parent_org_name,
            BidResult.assessment_rate.isnot(None),
            BidResult.first_place_rate.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        parent_data = parent_q.all()
        parent_match = sum(
            1 for res, _ in parent_data
            if abs(confirmed_rate - res.assessment_rate) <= abs(res.first_place_rate - res.assessment_rate) + 0.02
        )
        parent_analysis = {
            "parent_org": ann.parent_org_name,
            "match_count": parent_match,
            "total": len(parent_data),
            "match_rate": round(parent_match / len(parent_data) * 100, 1) if parent_data else 0,
        }

    db.close()
    return {
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "org": ann.ordering_org_name, "parent_org": ann.parent_org_name,
            "area": ann.region, "budget": ann.base_amount,
        },
        "confirmed_rate": round(confirmed_rate, 4),
        "predicted_first_place": {
            "rate": round(confirmed_rate, 4),
            "amount": predicted_first_place_amount,
        },
        "period_results": period_results,
        "parent_analysis": parent_analysis,
    }


# ─── API: 기관 계층 조회 ──────────────────────────────────────────────────

@app.get("/api/v1/orgs/hierarchy")
def get_org_hierarchy():
    return {"hierarchy": ORG_HIERARCHY}


# ─── API: 추첨예가 빈도수 분석 ────────────────────────────────────────────

@app.get("/api/v1/analysis/preliminary-frequency/{announcement_id}")
def analysis_preliminary_frequency(
    announcement_id: str,
    period_months: int = Query(12, ge=3, le=24),
    org_scope: str = Query("specific"),
):
    """복수예비가격 15개 번호 중 추첨 빈도 분석"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}

    cutoff = datetime.now() - timedelta(days=period_months * 30)
    q = db.query(BidResult).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidResult.selected_price_indices.isnot(None),
        BidResult.opened_at >= cutoff,
    )
    if org_scope == "parent" and ann.parent_org_name:
        q = q.filter(BidAnnouncement.parent_org_name == ann.parent_org_name)
    else:
        q = q.filter(BidAnnouncement.ordering_org_name == ann.ordering_org_name)

    results = q.all()
    if not results:
        # 폴백: 같은 카테고리+지역
        q = db.query(BidResult).join(
            BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
        ).filter(
            BidAnnouncement.category == ann.category,
            BidAnnouncement.region == ann.region,
            BidResult.selected_price_indices.isnot(None),
            BidResult.opened_at >= cutoff,
        )
        results = q.all()

    # 15개 번호별 추첨 횟수 집계
    freq = {i: 0 for i in range(1, 16)}
    total_cases = 0
    for res in results:
        try:
            indices = json.loads(res.selected_price_indices) if isinstance(res.selected_price_indices, str) else res.selected_price_indices
            if indices:
                total_cases += 1
                for idx in indices:
                    if 1 <= idx <= 15:
                        freq[idx] += 1
        except (json.JSONDecodeError, TypeError):
            continue

    bins = [{"number": i, "count": freq[i], "percentage": round(freq[i] / total_cases * 100, 1) if total_cases > 0 else 0} for i in range(1, 16)]
    max_count = max(b["count"] for b in bins) if bins else 0
    peak_numbers = [b["number"] for b in bins if b["count"] == max_count and max_count > 0]

    db.close()
    return {
        "bins": bins,
        "total_cases": total_cases,
        "peak_numbers": peak_numbers,
        "selected_per_case": 4,
    }


# ─── API: 통계 ────────────────────────────────────────────────────────────

@app.get("/api/v1/stats/kpi")
def get_kpi():
    db = SessionLocal()
    total = db.query(BidAnnouncement).filter(BidAnnouncement.category.in_(["공사", "용역"])).count()
    today = db.query(BidAnnouncement).filter(
        func.date(BidAnnouncement.announced_at) == func.date(datetime.now())
    ).count()
    construction = db.query(BidAnnouncement).filter(BidAnnouncement.category == "공사").count()
    service = db.query(BidAnnouncement).filter(BidAnnouncement.category == "용역").count()
    avg_rate = db.query(func.avg(BidResult.assessment_rate)).scalar()
    avg_fp_rate = db.query(func.avg(BidResult.first_place_rate)).scalar()
    db.close()
    return {
        "total_announcements": total,
        "today_announcements": today,
        "construction_count": construction,
        "service_count": service,
        "avg_assessment_rate": round(float(avg_rate), 2) if avg_rate else 0,
        "avg_first_place_rate": round(float(avg_fp_rate), 4) if avg_fp_rate else 0,
    }


@app.get("/api/v1/stats/trends")
def get_trends(months: int = 6, category: str = None):
    db = SessionLocal()
    q = db.query(
        func.strftime("%Y-%m", BidResult.opened_at).label("period"),
        BidAnnouncement.category,
        func.avg(BidResult.assessment_rate).label("avg_rate"),
        func.count(BidResult.id).label("cnt"),
    ).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidResult.assessment_rate.isnot(None),
        BidResult.opened_at.isnot(None),
        BidAnnouncement.category.in_(["공사", "용역"]),
    )
    if category and category != "all":
        q = q.filter(BidAnnouncement.category == category)
    rows = q.group_by(
        func.strftime("%Y-%m", BidResult.opened_at),
        BidAnnouncement.category,
    ).order_by("period").all()

    period_data = {}
    for row in rows:
        p = row.period
        if p not in period_data:
            period_data[p] = {"period": p, "construction": None, "service": None, "total": None, "count": 0}
        if row.category == "공사":
            period_data[p]["construction"] = round(row.avg_rate, 2)
        elif row.category == "용역":
            period_data[p]["service"] = round(row.avg_rate, 2)
        period_data[p]["count"] += row.cnt

    for p in period_data:
        vals = [v for v in [period_data[p]["construction"], period_data[p]["service"]] if v]
        period_data[p]["total"] = round(sum(vals) / len(vals), 2) if vals else None

    data = sorted(period_data.values(), key=lambda x: x["period"])[-months:]
    db.close()
    return {"data": data}


@app.get("/api/v1/stats/by-region")
def get_region_stats():
    db = SessionLocal()
    rows = db.query(
        BidAnnouncement.region,
        func.avg(BidResult.assessment_rate).label("avg_rate"),
        func.count(BidResult.id).label("count"),
        func.min(BidResult.assessment_rate).label("min_rate"),
        func.max(BidResult.assessment_rate).label("max_rate"),
    ).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidResult.assessment_rate.isnot(None),
        BidAnnouncement.region.isnot(None),
        BidAnnouncement.category.in_(["공사", "용역"]),
    ).group_by(BidAnnouncement.region).order_by(func.count(BidResult.id).desc()).all()

    data = [
        {
            "region": r.region,
            "rate": round(r.avg_rate, 2),
            "count": r.count,
            "min_rate": round(r.min_rate, 2) if r.min_rate else None,
            "max_rate": round(r.max_rate, 2) if r.max_rate else None,
        }
        for r in rows
    ]
    db.close()
    return {"data": data}


# ─── API: 예측 (기존 호환) ────────────────────────────────────────────────

@app.get("/api/v1/predictions/{announcement_id}")
def predict(announcement_id: str):
    """실시간 사정률 예측 (통계 기반 간이 모델)"""
    db = SessionLocal()
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == announcement_id).first()
    if not ann:
        db.close()
        return {"error": "공고를 찾을 수 없습니다."}

    stats = db.query(
        func.avg(BidResult.assessment_rate).label("avg"),
        func.min(BidResult.assessment_rate).label("min"),
        func.max(BidResult.assessment_rate).label("max"),
        func.count(BidResult.id).label("cnt"),
    ).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidAnnouncement.region == ann.region,
        BidResult.assessment_rate.isnot(None),
    ).first()

    org_stats = db.query(
        func.avg(BidResult.assessment_rate)
    ).join(
        BidAnnouncement, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.ordering_org_type == ann.ordering_org_type,
        BidResult.assessment_rate.isnot(None),
    ).scalar()

    if stats and stats.avg and stats.cnt >= 5:
        pred_rate = round(stats.avg * 0.7 + (org_stats or stats.avg) * 0.3, 2)
        ci_width = max(1.0, (stats.max - stats.min) * 0.3)
        confidence = min(95, 50 + stats.cnt * 0.5)
    else:
        pred_rate = 99.3 if ann.category == "공사" else 99.5
        ci_width = 3.0
        confidence = 30

    pred_min = round(pred_rate - ci_width, 2)
    pred_max = round(pred_rate + ci_width, 2)
    bid_pred = int(ann.base_amount * pred_rate / 100) if ann.base_amount else 0
    bid_min = int(ann.base_amount * pred_min / 100) if ann.base_amount else 0
    bid_max = int(ann.base_amount * pred_max / 100) if ann.base_amount else 0

    similar = db.query(BidAnnouncement, BidResult).join(
        BidResult, BidResult.announcement_id == BidAnnouncement.id
    ).filter(
        BidAnnouncement.category == ann.category,
        BidResult.assessment_rate.isnot(None),
    ).order_by(BidResult.opened_at.desc()).limit(10).all()

    similar_list = [
        {
            "title": s[0].title, "area": s[0].region,
            "rate": round(s[1].assessment_rate, 2),
            "first_place_rate": round(s[1].first_place_rate, 4) if s[1].first_place_rate else None,
            "amount": s[1].winning_amount,
            "date": s[1].opened_at.strftime("%Y-%m") if s[1].opened_at else "",
        }
        for s in similar
    ]

    db.close()
    return {
        "announcement": {
            "id": ann.id, "title": ann.title, "type": ann.category,
            "area": ann.region, "budget": ann.base_amount,
            "org": ann.ordering_org_name, "org_type": ann.ordering_org_type,
            "bid_method": ann.bid_method,
        },
        "prediction": {
            "predRate": round(pred_rate, 2),
            "predMin": pred_min, "predMax": pred_max,
            "bidAmountPred": bid_pred, "bidMin": bid_min, "bidMax": bid_max,
            "confidence": round(confidence),
            "dataPoints": stats.cnt if stats else 0,
        },
        "similar": similar_list,
    }


# ─── API: 관리자 ──────────────────────────────────────────────────────────

@app.get("/api/v1/admin/dashboard")
def admin_dashboard():
    db = SessionLocal()
    total_users = db.query(User).count()
    premium = db.query(User).filter(User.plan == "프리미엄").count()
    total_ann = db.query(BidAnnouncement).count()
    total_res = db.query(BidResult).count()

    logs = db.query(DataSyncLog).order_by(DataSyncLog.started_at.desc()).limit(10).all()
    pipelines = []
    seen = set()
    for log in logs:
        key = f"{log.source}_{log.sync_type}"
        if key in seen:
            continue
        seen.add(key)
        pipelines.append({
            "name": f"{log.source} {log.sync_type}",
            "status": log.status,
            "last": log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else "",
            "count": f"{log.records_fetched}건",
        })

    users = db.query(User).order_by(User.query_count.desc()).all()
    user_list = [
        {
            "name": u.name, "email": u.email, "plan": u.plan,
            "joined": u.joined_at.strftime("%Y.%m.%d") if u.joined_at else "",
            "last": u.last_login_at.strftime("%Y-%m-%d") if u.last_login_at else "",
            "queries": u.query_count,
        }
        for u in users
    ]

    db.close()
    return {
        "total_users": total_users, "premium_users": premium,
        "total_announcements": total_ann, "total_results": total_res,
        "pipelines": pipelines,
        "users": user_list,
    }


@app.post("/api/v1/admin/sync")
def trigger_sync():
    db = SessionLocal()
    records = random.randint(15, 80)
    now = datetime.now()
    for src in ["G2B", "D2B"]:
        db.add(DataSyncLog(
            source=src, sync_type="공고 수집", status="success",
            records_fetched=records + random.randint(-10, 10),
            started_at=now - timedelta(seconds=random.randint(30, 120)),
            finished_at=now,
        ))
    db.commit()
    db.close()
    return {"message": "데이터 수집 완료", "records": records, "status": "success"}


@app.get("/api/v1/admin/nas-status")
def nas_status():
    """NAS 마운트/용량 확인"""
    nas_exists = os.path.exists(NAS_PATH)
    if nas_exists:
        try:
            stat = os.statvfs(NAS_PATH)
            total_gb = round(stat.f_frsize * stat.f_blocks / (1024 ** 3), 1)
            free_gb = round(stat.f_frsize * stat.f_bavail / (1024 ** 3), 1)
        except Exception:
            total_gb = 0
            free_gb = 0
    else:
        total_gb = 0
        free_gb = 0
    return {
        "mounted": nas_exists,
        "path": NAS_PATH,
        "total_gb": total_gb,
        "free_gb": free_gb,
        "db_path": DB_PATH,
        "db_size_mb": round(os.path.getsize(DB_PATH) / (1024 * 1024), 1) if os.path.exists(DB_PATH) else 0,
    }


# ─── API: 조회 이력 ──────────────────────────────────────────────────────

@app.get("/api/v1/history")
def list_history(
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(require_auth),
):
    """현재 사용자의 분석 조회 이력"""
    db = SessionLocal()
    q = db.query(QueryHistory).filter(QueryHistory.user_id == current_user.id)
    total = q.count()
    items = q.order_by(QueryHistory.queried_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for h in items:
        ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == h.announcement_id).first()
        result.append({
            "id": h.id,
            "announcement_id": h.announcement_id,
            "announcement_title": ann.title if ann else None,
            "analysis_type": h.analysis_type,
            "parameters": json.loads(h.parameters) if h.parameters else None,
            "result_summary": json.loads(h.result_summary) if h.result_summary else None,
            "queried_at": h.queried_at.strftime("%Y-%m-%d %H:%M") if h.queried_at else None,
        })

    db.close()
    return {"items": result, "total": total, "page": page, "page_size": page_size}


@app.get("/api/v1/history/{history_id}")
def get_history(history_id: str, current_user: User = Depends(require_auth)):
    db = SessionLocal()
    h = db.query(QueryHistory).filter(
        QueryHistory.id == history_id, QueryHistory.user_id == current_user.id
    ).first()
    if not h:
        db.close()
        raise HTTPException(status_code=404, detail="조회 이력을 찾을 수 없습니다.")
    ann = db.query(BidAnnouncement).filter(BidAnnouncement.id == h.announcement_id).first()
    db.close()
    return {
        "id": h.id,
        "announcement_id": h.announcement_id,
        "announcement_title": ann.title if ann else None,
        "analysis_type": h.analysis_type,
        "parameters": json.loads(h.parameters) if h.parameters else None,
        "result_summary": json.loads(h.result_summary) if h.result_summary else None,
        "queried_at": h.queried_at.strftime("%Y-%m-%d %H:%M") if h.queried_at else None,
    }


def save_query_history(user_id: str, announcement_id: str, analysis_type: str,
                       parameters: dict = None, result_summary: dict = None):
    """분석 조회 이력 저장 (헬퍼 함수)"""
    try:
        db = SessionLocal()
        h = QueryHistory(
            user_id=user_id,
            announcement_id=announcement_id,
            analysis_type=analysis_type,
            parameters=json.dumps(parameters, ensure_ascii=False) if parameters else None,
            result_summary=json.dumps(result_summary, ensure_ascii=False) if result_summary else None,
            queried_at=datetime.now(),
        )
        db.add(h)
        # 사용자 조회 횟수 증가
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.query_count = (user.query_count or 0) + 1
        db.commit()
        db.close()
    except Exception:
        pass  # 이력 저장 실패는 분석 결과에 영향 없음


# ─── API: 데이터 업로드 ──────────────────────────────────────────────────

@app.post("/api/v1/data/upload")
def upload_data(file: UploadFile = File(...), current_user: User = Depends(require_auth)):
    """CSV/Excel 입찰 데이터 업로드"""
    import io
    allowed_ext = {".csv", ".xlsx", ".xls"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다. ({', '.join(allowed_ext)})")

    content = file.file.read()
    file_size = len(content)

    db = SessionLocal()
    upload = UploadLog(
        user_id=current_user.id, filename=file.filename,
        file_size=file_size, status="processing",
        uploaded_at=datetime.now(),
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # 필수 컬럼 확인
        required_cols = {"공고번호", "공고명", "발주기관", "기초금액"}
        missing = required_cols - set(df.columns)
        if missing:
            upload.status = "failed"
            upload.error_message = f"필수 컬럼 누락: {', '.join(missing)}"
            db.commit()
            db.close()
            raise HTTPException(status_code=400, detail=upload.error_message)

        records_count = 0
        for _, row in df.iterrows():
            ann = BidAnnouncement(
                source="UPLOAD",
                bid_number=str(row.get("공고번호", "")),
                category=str(row.get("카테고리", "용역")),
                title=str(row.get("공고명", "")),
                ordering_org_name=str(row.get("발주기관", "")),
                region=str(row.get("지역", "")) if "지역" in df.columns else None,
                base_amount=int(row["기초금액"]) if pd.notna(row.get("기초금액")) else None,
                announced_at=datetime.now(),
                status="업로드",
            )
            db.add(ann)
            records_count += 1

        upload.records_count = records_count
        upload.status = "success"
        db.commit()
        db.close()
        return {"message": f"{records_count}건 업로드 완료", "upload_id": upload.id, "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)
        db.commit()
        db.close()
        raise HTTPException(status_code=500, detail=f"데이터 처리 중 오류: {str(e)}")


@app.get("/api/v1/data/uploads")
def list_uploads(current_user: User = Depends(require_auth)):
    """업로드 이력 조회"""
    db = SessionLocal()
    uploads = db.query(UploadLog).filter(
        UploadLog.user_id == current_user.id
    ).order_by(UploadLog.uploaded_at.desc()).limit(50).all()
    db.close()
    return [{
        "id": u.id, "filename": u.filename,
        "file_size": u.file_size, "records_count": u.records_count,
        "status": u.status, "error_message": u.error_message,
        "uploaded_at": u.uploaded_at.strftime("%Y-%m-%d %H:%M") if u.uploaded_at else None,
    } for u in uploads]


# ─── 프론트엔드 서빙 ──────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/proposal")
def serve_proposal():
    return FileResponse(os.path.join(DOCS_DIR, "기술제안서.html"))


# ─── 시작 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(engine)
    seed_database()
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🚀 서버 시작: http://localhost:{port}")
    print(f"   API 문서: http://localhost:{port}/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
