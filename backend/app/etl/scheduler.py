"""데이터 수집 스케줄러 및 ETL 오케스트레이션"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import BidAnnouncement, BidResult, DataSyncLog
from app.db.session import async_session
from app.etl.g2b_client import G2BClient, parse_bid_notice, parse_award_result
from app.etl.d2b_client import D2BClient, parse_d2b_notice, parse_d2b_result

logger = logging.getLogger(__name__)


async def run_sync(source: str = "G2B"):
    """데이터 수집 실행"""
    async with async_session() as db:
        if source == "G2B":
            await sync_g2b(db)
        elif source == "D2B":
            await sync_d2b(db)


async def sync_g2b(db: AsyncSession):
    """나라장터 데이터 수집"""
    client = G2BClient()

    # 최근 7일 데이터 수집
    date_to = datetime.now().strftime("%Y%m%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

    for category in ["construction", "service"]:
        sync_log = DataSyncLog(
            source="G2B",
            sync_type=f"announcement_{category}",
            status="running",
        )
        db.add(sync_log)
        await db.commit()

        try:
            # 공고 수집
            notices = await client.fetch_all_pages(
                client.fetch_bid_notices,
                category=category,
                date_from=date_from,
                date_to=date_to,
            )

            inserted = 0
            updated = 0
            for raw in notices:
                parsed = parse_bid_notice(raw, category)
                bid_number = parsed["bid_number"]

                # upsert
                existing = (
                    await db.execute(
                        select(BidAnnouncement).where(
                            BidAnnouncement.source == "G2B",
                            BidAnnouncement.bid_number == bid_number,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    for key, value in parsed.items():
                        if key != "raw_json" and value is not None:
                            setattr(existing, key, value)
                    existing.raw_json = raw
                    updated += 1
                else:
                    db.add(BidAnnouncement(**parsed))
                    inserted += 1

            await db.commit()

            sync_log.status = "success"
            sync_log.records_fetched = len(notices)
            sync_log.records_inserted = inserted
            sync_log.records_updated = updated
            sync_log.finished_at = datetime.now()

            logger.info(
                f"[G2B] {category} 공고 수집 완료: {len(notices)}건 "
                f"(신규 {inserted}, 갱신 {updated})"
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.finished_at = datetime.now()
            logger.error(f"[G2B] {category} 공고 수집 실패: {e}")

        await db.commit()

        # 낙찰결과 수집
        result_log = DataSyncLog(
            source="G2B",
            sync_type=f"result_{category}",
            status="running",
        )
        db.add(result_log)
        await db.commit()

        try:
            awards = await client.fetch_all_pages(
                client.fetch_award_results,
                category=category,
                date_from=date_from,
                date_to=date_to,
            )

            inserted = 0
            for raw in awards:
                parsed = parse_award_result(raw, category)
                bid_number = parsed.pop("bid_number")

                # 매칭되는 공고 찾기
                ann = (
                    await db.execute(
                        select(BidAnnouncement).where(
                            BidAnnouncement.source == "G2B",
                            BidAnnouncement.bid_number == bid_number,
                        )
                    )
                ).scalar_one_or_none()

                if ann:
                    # 기존 결과 확인
                    existing_result = (
                        await db.execute(
                            select(BidResult).where(
                                BidResult.announcement_id == ann.id
                            )
                        )
                    ).scalar_one_or_none()

                    if not existing_result:
                        parsed["announcement_id"] = ann.id
                        db.add(BidResult(**parsed))
                        inserted += 1
                        ann.status = "개찰완료"

            await db.commit()

            result_log.status = "success"
            result_log.records_fetched = len(awards)
            result_log.records_inserted = inserted
            result_log.finished_at = datetime.now()

            logger.info(
                f"[G2B] {category} 낙찰결과 수집 완료: {len(awards)}건 (신규 {inserted})"
            )

        except Exception as e:
            result_log.status = "failed"
            result_log.error_message = str(e)
            result_log.finished_at = datetime.now()
            logger.error(f"[G2B] {category} 낙찰결과 수집 실패: {e}")

        await db.commit()

    await client.close()


async def sync_d2b(db: AsyncSession):
    """국방전자조달 데이터 수집"""
    client = D2BClient()

    date_to = datetime.now().strftime("%Y%m%d")
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

    sync_log = DataSyncLog(source="D2B", sync_type="announcement", status="running")
    db.add(sync_log)
    await db.commit()

    try:
        notices = await client.fetch_all_pages(
            client.fetch_bid_notices, date_from=date_from, date_to=date_to
        )

        inserted = 0
        for raw in notices:
            parsed = parse_d2b_notice(raw)
            bid_number = parsed["bid_number"]

            existing = (
                await db.execute(
                    select(BidAnnouncement).where(
                        BidAnnouncement.source == "D2B",
                        BidAnnouncement.bid_number == bid_number,
                    )
                )
            ).scalar_one_or_none()

            if not existing:
                db.add(BidAnnouncement(**parsed))
                inserted += 1

        await db.commit()

        sync_log.status = "success"
        sync_log.records_fetched = len(notices)
        sync_log.records_inserted = inserted
        sync_log.finished_at = datetime.now()

    except Exception as e:
        sync_log.status = "failed"
        sync_log.error_message = str(e)
        sync_log.finished_at = datetime.now()
        logger.error(f"[D2B] 공고 수집 실패: {e}")

    await db.commit()

    # 결과 수집
    result_log = DataSyncLog(source="D2B", sync_type="result", status="running")
    db.add(result_log)
    await db.commit()

    try:
        results = await client.fetch_all_pages(
            client.fetch_bid_results, date_from=date_from, date_to=date_to
        )

        inserted = 0
        for raw in results:
            parsed = parse_d2b_result(raw)
            bid_number = parsed.pop("bid_number")

            ann = (
                await db.execute(
                    select(BidAnnouncement).where(
                        BidAnnouncement.source == "D2B",
                        BidAnnouncement.bid_number == bid_number,
                    )
                )
            ).scalar_one_or_none()

            if ann:
                existing_result = (
                    await db.execute(
                        select(BidResult).where(BidResult.announcement_id == ann.id)
                    )
                ).scalar_one_or_none()

                if not existing_result:
                    parsed["announcement_id"] = ann.id
                    db.add(BidResult(**parsed))
                    inserted += 1

        await db.commit()

        result_log.status = "success"
        result_log.records_fetched = len(results)
        result_log.records_inserted = inserted
        result_log.finished_at = datetime.now()

    except Exception as e:
        result_log.status = "failed"
        result_log.error_message = str(e)
        result_log.finished_at = datetime.now()
        logger.error(f"[D2B] 결과 수집 실패: {e}")

    await db.commit()
    await client.close()
