"""데모 시드 데이터 생성 스크립트

DB에 데모용 공고/낙찰결과/모델이력/사용자 데이터를 삽입합니다.
실행: python seed_data.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from _legacy_app.db.models import (
    Base,
    BidAnnouncement,
    BidResult,
    DataSyncLog,
    User,
)
from _legacy_app.db.session import engine, async_session


# ── 시드 데이터 정의 ──

REGIONS = ["서울", "경기", "부산", "대전", "인천", "광주", "대구", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

ORG_TYPES = ["중앙부처", "지자체", "공기업", "교육기관", "기타"]

CONSTRUCTION_TITLES = [
    "도로 포장 보수공사", "하수관로 정비공사", "청사 리모델링 공사",
    "교량 보강 공사", "공원 조성공사", "학교 시설 보수공사",
    "아파트 재건축 기반시설공사", "하천 정비공사", "문화체육센터 신축공사",
    "소방서 신축공사", "도시가스 배관 공사", "항만시설 확장공사",
    "지하주차장 건설공사", "상수도관 교체공사", "터널 보수공사",
    "막사 신축공사", "격납고 보수공사", "부대시설 정비공사",
]

SERVICE_TITLES = [
    "시설 유지보수 용역", "정보시스템 운영 용역", "건물 청소 위탁 용역",
    "설계 감리 용역", "환경영향평가 용역", "교통영향분석 용역",
    "도시계획 수립 용역", "폐기물 처리 위탁 용역", "보안관제 운영 용역",
    "전산장비 유지보수 용역", "급식 위탁 운영 용역", "조경 유지관리 용역",
    "스마트시티 플랫폼 구축 용역", "데이터센터 운영 용역", "통합관제 구축 용역",
]

ORGS = {
    "중앙부처": ["국토교통부", "환경부", "교육부", "행정안전부", "문화체육관광부", "국방부", "방위사업청"],
    "지자체": ["서울특별시", "부산광역시", "대전광역시", "인천광역시", "경기도", "강원도", "세종특별자치시"],
    "공기업": ["한국도로공사", "한국수자원공사", "한국토지주택공사", "부산항만공사", "인천국제공항공사"],
    "교육기관": ["서울대학교", "부산대학교", "충남대학교", "전북대학교"],
    "기타": ["한국과학기술원", "국방과학연구소", "한국전자통신연구원"],
}


def random_date(start_days_ago: int, end_days_ago: int = 0) -> datetime:
    days = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=days)


def generate_announcements(count: int = 500) -> list[dict]:
    """데모용 공고 데이터 생성"""
    data = []
    for i in range(count):
        is_construction = random.random() < 0.55
        is_defense = random.random() < 0.15
        category = "공사" if is_construction else "용역"
        source = "D2B" if is_defense else "G2B"

        org_type = random.choice(ORG_TYPES) if not is_defense else "국방부"
        org_name = random.choice(ORGS.get(org_type, ORGS["기타"]))
        region = random.choice(REGIONS)

        if is_construction:
            title = f"{region} {random.choice(CONSTRUCTION_TITLES)}"
            base_amount = random.randint(5000, 500000) * 10000  # 5천만 ~ 50억
        else:
            title = f"{org_name} {random.choice(SERVICE_TITLES)}"
            base_amount = random.randint(1000, 100000) * 10000  # 1천만 ~ 10억

        announced_at = random_date(730, 1)  # 최근 2년

        data.append({
            "source": source,
            "bid_number": f"{'D' if is_defense else 'G'}{announced_at.strftime('%Y%m')}-{i:05d}-00",
            "category": category,
            "title": title,
            "ordering_org_name": org_name,
            "ordering_org_type": org_type,
            "region": region,
            "industry_code": f"{'C' if is_construction else 'S'}{random.randint(100, 999)}",
            "industry_name": category,
            "base_amount": base_amount,
            "bid_method": random.choice(["적격심사", "최저가", "2단계경쟁", "협상에의한계약"]),
            "announced_at": announced_at,
            "bid_open_at": announced_at + timedelta(days=random.randint(14, 45)),
            "deadline_at": announced_at + timedelta(days=random.randint(10, 30)),
            "status": "개찰완료" if announced_at < datetime.now() - timedelta(days=30) else "진행중",
        })

    return data


def generate_result(ann: dict) -> dict | None:
    """공고에 대한 낙찰결과 생성 (개찰완료 건만)"""
    if ann["status"] != "개찰완료":
        return None

    base = ann["base_amount"]

    # 사정률: 기본 99~100% 범위에서 카테고리/지역에 따라 변동
    if ann["category"] == "공사":
        mean_rate = 99.3 + random.gauss(0, 0.8)
    else:
        mean_rate = 99.5 + random.gauss(0, 0.6)

    # 지역 보정
    region_adj = {"서울": 0.2, "경기": 0.1, "부산": -0.1, "대전": 0.3, "강원": -0.2}
    mean_rate += region_adj.get(ann["region"], 0)

    assessment_rate = max(95.0, min(104.0, mean_rate))
    estimated_price = int(base * assessment_rate / 100)

    # 낙찰률: 예정가격 대비 87~98%
    winning_rate = random.uniform(87.0, 98.0)
    winning_amount = int(estimated_price * winning_rate / 100)

    num_bidders = random.randint(2, 30)

    # 복수예비가격 (15개) 생성
    preliminary_prices = []
    for j in range(1, 16):
        variance = random.uniform(-0.03, 0.03)  # ±3%
        price = int(base * (1 + variance))
        preliminary_prices.append({"index": j, "amount": price})

    return {
        "winning_amount": winning_amount,
        "winning_rate": round(winning_rate, 4),
        "assessment_rate": round(assessment_rate, 4),
        "num_bidders": num_bidders,
        "winning_company": f"(주)건설{random.randint(1, 100)}",
        "preliminary_prices": preliminary_prices,
        "selected_price_indices": random.sample(range(1, 16), 4),
        "opened_at": ann["bid_open_at"],
    }


async def seed_database():
    """시드 데이터 삽입"""
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # 기존 데이터 확인
        count = (await db.execute(select(BidAnnouncement.id).limit(1))).scalar()
        if count:
            print("이미 데이터가 존재합니다. 시드를 건너뜁니다.")
            return

        print("시드 데이터 생성 시작...")

        # 1. 공고 + 결과 생성
        announcements_data = generate_announcements(500)
        announcement_objs = []

        for ann_data in announcements_data:
            ann = BidAnnouncement(**ann_data)
            db.add(ann)
            announcement_objs.append((ann, ann_data))

        await db.flush()  # ID 생성

        result_count = 0
        for ann, ann_data in announcement_objs:
            result_data = generate_result(ann_data)
            if result_data:
                result_data["announcement_id"] = ann.id
                db.add(BidResult(**result_data))
                result_count += 1

        print(f"  공고 {len(announcements_data)}건, 낙찰결과 {result_count}건 생성")

        # 2. 사용자
        users_data = [
            ("김영호", "ykim@guncorp.co.kr", "프리미엄", 342),
            ("박수연", "sypark@daewoo.co.kr", "스탠다드", 128),
            ("이재원", "jwlee@hanshin.com", "프리미엄", 489),
            ("최민준", "mjchoi@hyundai-eng.com", "무료", 24),
            ("정다혜", "dhjeong@posco.co.kr", "스탠다드", 216),
            ("관리자", "admin@bidinsight.kr", "프리미엄", 0),
        ]

        for name, email, plan, queries in users_data:
            user = User(
                email=email,
                hashed_password="$2b$12$demo_hash_not_real",
                name=name,
                plan=plan,
                is_admin=(name == "관리자"),
                query_count=queries,
                last_login_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
            )
            db.add(user)

        print(f"  사용자 {len(users_data)}명 생성")

        # 3. 수집 로그
        for source in ["G2B", "D2B"]:
            for sync_type in ["announcement", "result"]:
                log = DataSyncLog(
                    source=source,
                    sync_type=sync_type,
                    status="success",
                    records_fetched=random.randint(50, 400),
                    records_inserted=random.randint(10, 100),
                    records_updated=random.randint(5, 50),
                    started_at=datetime.now() - timedelta(hours=random.randint(1, 24)),
                    finished_at=datetime.now() - timedelta(hours=random.randint(0, 23)),
                )
                db.add(log)

        await db.commit()
        print("시드 데이터 생성 완료!")


if __name__ == "__main__":
    asyncio.run(seed_database())
