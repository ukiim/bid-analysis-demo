"""데모 시드 데이터 생성 모듈.

운영 환경에서는 SKIP_SEED=true 로 비활성화. 개발/시연 시에만 사용.

사용:
    from seed import seed_database
    seed_database()
"""
import json
import random
from datetime import datetime, timedelta

import bcrypt

# server.py에서 import (lazy하게 사용 — 순환 import 회피)
from server import (  # noqa: E402
    SessionLocal,
    BidAnnouncement,
    BidResult,
    CompanyBidRecord,
    DataSyncLog,
    User,
    REGIONS,
    ORG_HIERARCHY,
)


# ── 시드 전용 상수 ─────────────────────────────────────────────────

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
    "지자체": [
        "서울특별시", "부산광역시", "대전광역시", "인천광역시", "경기도",
        "세종특별자치시", "고양시", "수원시", "성남시", "용인시", "안양시", "부천시",
    ],
    "공기업": [
        "한국도로공사", "한국수자원공사", "한국토지주택공사",
        "부산항만공사", "인천국제공항공사",
    ],
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


# ── 헬퍼 ──────────────────────────────────────────────────────────

def _create_announcements(db, n: int = 3000):
    """공고 n건 생성 → (ann, status, category, region, base_amount, org_type) 튜플 리스트 반환"""
    out = []
    for i in range(n):
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

        days_ago = random.randint(1, 2650)
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
        out.append((ann, status, category, region, base_amount, org_type))
    return out


def _create_results_and_bids(db, announcements):
    """각 공고에 대해 BidResult + CompanyBidRecord 생성"""
    result_count = 0
    company_count = 0
    for ann, status, category, region, base_amount, org_type in announcements:
        if status != "개찰완료":
            continue

        # Beta 분포 기반 사정률 (99.3~99.5% 구간 집중)
        base_rate = 99.3 if category == "공사" else 99.5
        adj = REGION_RATE_ADJ.get(region, 0)
        raw = random.betavariate(8, 2)
        assessment_rate = base_rate + adj + (raw - 0.8) * 2.0
        assessment_rate = round(max(97.0, min(102.0, assessment_rate)), 4)

        # 복수예비가격 15개
        estimated_price = int(base_amount * assessment_rate / 100)
        prelim_prices = [int(estimated_price * (1 + random.uniform(-0.03, 0.03))) for _ in range(15)]
        selected_indices = sorted(random.sample(range(15), 4))

        # 업체 투찰
        num_bidders = random.randint(5, 25)
        companies = random.sample(COMPANY_NAMES, min(num_bidders, len(COMPANY_NAMES)))
        records = []
        for comp in companies:
            cluster_center = assessment_rate + random.gauss(0, 0.2)
            bid_rate = round(max(97.0, min(102.0, cluster_center + random.gauss(0, 0.15))), 4)
            records.append({"company": comp, "rate": bid_rate, "amount": int(base_amount * bid_rate / 100)})

        records.sort(key=lambda x: abs(x["rate"] - assessment_rate))
        first = records[0]
        for rank_idx, cr in enumerate(records):
            cr["ranking"] = rank_idx + 1
            cr["is_first"] = rank_idx == 0

        winning_rate = round(first["amount"] / estimated_price * 100, 4) if estimated_price else 0
        db.add(BidResult(
            announcement_id=ann.id,
            winning_amount=first["amount"],
            winning_rate=winning_rate,
            assessment_rate=assessment_rate,
            first_place_rate=first["rate"],
            first_place_amount=first["amount"],
            num_bidders=num_bidders,
            winning_company=first["company"],
            preliminary_prices=json.dumps(prelim_prices),
            selected_price_indices=json.dumps(selected_indices),
            opened_at=ann.announced_at + timedelta(days=random.randint(14, 45)),
        ))
        result_count += 1

        for cr in records:
            db.add(CompanyBidRecord(
                announcement_id=ann.id,
                company_name=cr["company"],
                bid_amount=cr["amount"],
                bid_rate=cr["rate"],
                ranking=cr["ranking"],
                is_first_place=cr["is_first"],
            ))
            company_count += 1

    return result_count, company_count


def _create_sync_logs(db):
    for src in ("G2B", "D2B"):
        for stype in ("공고 수집", "낙찰 데이터 수집"):
            db.add(DataSyncLog(
                source=src, sync_type=stype, status="success",
                records_fetched=random.randint(80, 400),
                started_at=datetime.now() - timedelta(hours=random.randint(1, 12)),
                finished_at=datetime.now() - timedelta(minutes=random.randint(1, 60)),
            ))


def _create_demo_users(db):
    pwd = bcrypt.hashpw(b"demo1234", bcrypt.gensalt()).decode("utf-8")
    users = [
        ("admin", "관리자", "admin@bidinsight.kr", "admin", "프리미엄", 0),
        ("ykim", "김영호", "ykim@guncorp.co.kr", "user", "프리미엄", 342),
        ("sypark", "박수연", "sypark@daewoo.co.kr", "user", "스탠다드", 128),
        ("jwlee", "이재원", "jwlee@hanshin.com", "user", "프리미엄", 489),
        ("mjchoi", "최민준", "mjchoi@hyundai-eng.com", "user", "무료", 24),
        ("dhjeong", "정다혜", "dhjeong@posco.co.kr", "user", "스탠다드", 216),
    ]
    for username, name, email, role, plan, qc in users:
        db.add(User(
            username=username, email=email, hashed_password=pwd,
            name=name, role=role, plan=plan, query_count=qc,
            joined_at=datetime.now() - timedelta(days=random.randint(30, 180)),
            last_login_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
        ))


# ── 진입점 ────────────────────────────────────────────────────────

def seed_database(n_announcements: int = 3000):
    """3000건의 현실적 데모 데이터 생성 (용역/공사만, 2019~현재)"""
    db = SessionLocal()
    if db.query(BidAnnouncement).first():
        print("데이터 이미 존재. 시드 건너뜀.")
        db.close()
        return

    print("시드 데이터 생성 시작...")
    random.seed(42)

    announcements = _create_announcements(db, n_announcements)
    result_count, company_count = _create_results_and_bids(db, announcements)
    _create_sync_logs(db)
    _create_demo_users(db)

    db.commit()
    db.close()
    print(
        f"  공고 {len(announcements)}건, 낙찰결과 {result_count}건, "
        f"업체투찰 {company_count}건 생성 완료!"
    )


if __name__ == "__main__":
    seed_database()
