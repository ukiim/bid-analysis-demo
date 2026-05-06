"""G2B/D2B 동기화 헬퍼 — server.py L3430-4119 에서 분리 (F3).

공공데이터포털(나라장터/방위사업청) API 응답 파싱, upsert, 재시도 fetch.
"""
from __future__ import annotations

import json
import logging
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models import BidAnnouncement, BidResult, DataSyncLog
from app.services.cache import invalidate_analysis_cache


logger = logging.getLogger("bid-insight")


def _parse_date(s) -> "datetime | None":
    """문자열 → datetime (공공데이터 여러 포맷 대응)"""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%Y%m%d%H%M", "%Y%m%d", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _validate_deadline(dt: "datetime | None") -> "datetime | None":
    """입찰 마감일 검증 — 비현실적인 날짜는 NULL 처리.

    G2B 데이터에 9999-12-31 sentinel 또는 다년 임대계약 종료일(예: 2030+)이
    bidClseDt 필드에 잘못 들어오는 경우가 있어 입찰 마감일로 부적합.
    cutoff: 현재로부터 2년 이후의 마감일은 NULL 처리.
    """
    if dt is None:
        return None
    cutoff = datetime.now().replace(year=datetime.now().year + 2)
    if dt > cutoff or dt.year >= 9000:
        return None
    return dt


def _extract_g2b_items(payload_bytes: bytes) -> list[dict]:
    """G2B BidPublicInfoService 응답에서 items 리스트 추출"""
    import json as _json
    try:
        data = _json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        logger.warning("G2B 응답 파싱 실패 (size=%d): %s", len(payload_bytes), exc)
        return []
    # 표준 응답 경로: response.body.items
    try:
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, list):
            return items
    except (AttributeError, KeyError, TypeError) as exc:
        logger.debug("G2B items 경로 추출 실패: %s", exc)
    return []


# 국방·군 발주 자동 인식 키워드
DEFENSE_KEYWORDS = (
    "국방", "육군", "해군", "공군", "방위", "방사청", "국군", "병무",
    "계룡대", "훈련소", "사령부", "군수", "방산", "국방과학",
)


def _detect_defense(org_name, title=None) -> bool:
    """발주기관/제목에 국방 관련 키워드가 있으면 True"""
    text = f"{org_name or ''} {title or ''}"
    return any(kw in text for kw in DEFENSE_KEYWORDS)


def get_announcement_url(ann) -> str:
    """공고의 외부 URL 반환 — external_url 우선, 없으면 표준 G2B URL fallback."""
    return (getattr(ann, "external_url", None)
            or build_g2b_url(getattr(ann, "bid_number", ""),
                             getattr(ann, "bid_ord", None) or "000"))


def build_g2b_url(bid_number: str, bid_ord: str = "000") -> str:
    """G2B 공고 상세 페이지 fallback URL 생성.

    실제 응답의 bidNtceDtlUrl이 우선이지만, 없을 경우 표준 패턴으로 생성.
    """
    if not bid_number:
        return ""
    ord_str = (bid_ord or "000").zfill(3)
    return (
        "https://www.g2b.go.kr/link/PNPE027_01/single/"
        f"?bidPbancNo={bid_number}&bidPbancOrd={ord_str}"
    )


def _normalize_item(source: str, item: dict) -> "dict | None":
    """공공데이터 item → BidAnnouncement 필드로 정규화.

    실제 필드명은 소스별로 다르지만 아래 후보 키들을 순회하며 매핑.
    """
    def pick(*keys):
        for k in keys:
            if k in item and item[k] not in (None, "", "null"):
                return item[k]
        return None

    bid_number = pick("bidNtceNo", "bidNo", "bid_number", "noticeNo")
    title = pick("bidNtceNm", "bidNm", "title", "noticeNm")
    org = pick("dminsttNm", "ordInsttNm", "ordering_org_name", "orgNm")
    if not bid_number or not title:
        return None
    # 취소·유찰·폐기·무효 공고 차단 (정밀 패턴)
    # 단순 "유찰"/"폐기"/"무효" contains 는 "폐기물처리"/"업무효율화" 등 오인 매칭 발생 →
    # 명확한 마커 패턴(괄호/대괄호 포함)만 차단
    _t = str(title)
    if "취소" in _t:  # 취소는 단순 contains 유지 (오인 매칭 거의 없음)
        return None
    _excludes = ("[유찰", "(유찰", "유찰공고", "[폐기", "(폐기공고",
                 "폐기공고", "무효공고", "[연기공고", "(연기공고", "입찰취소")
    if any(p in _t for p in _excludes):
        return None
    # 단가계약(다년 일괄) 차단 — "각 수요기관" 발주처는 분석 대상 아님
    if str(org).strip() == "각 수요기관":
        return None

    # 기초금액: presmptPrce / basicAmt / budgetAmt / asignBdgtAmt 순으로 폴백
    base_raw = pick("presmptPrce", "basicAmt", "bssamt", "asignBdgtAmt", "budgetAmt", "base_amount")
    try:
        base_amount = int(float(base_raw)) if base_raw else None
        if base_amount is not None and base_amount < 0:
            base_amount = None
    except (ValueError, TypeError):
        base_amount = None

    announced_at = _parse_date(pick("bidNtceDt", "ntceDt", "announced_at")) or datetime.now()
    deadline_at = _validate_deadline(_parse_date(pick("bidClseDt", "opengDt", "deadline_at")))
    category = pick("bsnsDivNm", "category") or "용역"
    if isinstance(category, str):
        if "공사" in category:
            category = "공사"
        elif "용역" in category:
            category = "용역"
        elif "물품" in category:
            category = "물품"

    org_str = str(org).strip() if org else "미상"
    title_str = str(title).strip()
    bid_no = str(bid_number).strip()
    bid_ord_raw = pick("bidNtceOrd", "bid_ord") or "000"
    bid_ord = str(bid_ord_raw).strip() or "000"
    # 응답의 bidNtceDtlUrl 우선, 없으면 표준 패턴으로 생성
    ext_url = pick("bidNtceDtlUrl", "bidNtceUrl", "external_url") or build_g2b_url(bid_no, bid_ord)
    return {
        "source": source,
        "bid_number": bid_no,
        "bid_ord": bid_ord,
        "title": title_str,
        "ordering_org_name": org_str,
        "region": pick("prtcptLmtRgnNm", "region"),
        "industry_code": pick("indstrytyCd", "industry_code"),
        "base_amount": base_amount,
        "bid_method": pick("cntrctCnclsMthdNm", "bid_method"),
        "announced_at": announced_at,
        "deadline_at": deadline_at,
        "category": category,
        "status": "진행중",
        "is_defense": _detect_defense(org_str, title_str),
        "external_url": ext_url[:1000] if ext_url else None,
    }


def _upsert_announcements(db, source: str, items: list[dict]) -> dict:
    """공고 upsert — 신규는 insert, 기존은 가변 필드(status/deadline/base_amount)만 update.

    - 신규(bid_number 미존재): 그대로 insert
    - 기존: status / deadline_at / base_amount / external_url 만 비교 후 변경 시 update
      (title / org / category 등 불변 메타는 최초 적재 값 보존)
    """
    if not items:
        return {"inserted": 0, "skipped": 0, "updated": 0, "invalid": 0}
    numbers = [i["bid_number"] for i in items if i.get("bid_number")]
    existing_rows = {
        row.bid_number: row for row in
        db.query(BidAnnouncement).filter(BidAnnouncement.bid_number.in_(numbers)).all()
    }
    inserted = 0
    skipped = 0
    updated = 0
    batch: list[BidAnnouncement] = []
    seen_in_payload: set = set()
    # 상태 변경 감지 대상 필드 (값이 바뀌면 update)
    # category 포함: 엔드포인트 기반 강제 분류 적용 후 재수집 시 기존 오분류 자동 정정
    MUTABLE_FIELDS = ("status", "deadline_at", "base_amount", "external_url", "category")
    for norm in items:
        bn = norm["bid_number"]
        if bn in seen_in_payload:
            skipped += 1
            continue
        seen_in_payload.add(bn)

        existing = existing_rows.get(bn)
        if existing is None:
            batch.append(BidAnnouncement(**norm))
            inserted += 1
            continue

        # 기존 레코드 — 변경된 가변 필드만 패치
        changed = False
        for field in MUTABLE_FIELDS:
            new_val = norm.get(field)
            if new_val is None:
                continue
            old_val = getattr(existing, field, None)
            # base_amount: 0/None 은 "비어있음"으로 간주 (보강만)
            if field == "base_amount" and (not old_val) and new_val:
                setattr(existing, field, new_val)
                changed = True
            elif old_val != new_val and field != "base_amount":
                setattr(existing, field, new_val)
                changed = True
        if changed:
            updated += 1
        else:
            skipped += 1
    if batch:
        db.bulk_save_objects(batch)
    if batch or updated:
        db.commit()
        invalidate_analysis_cache()  # 신규/변경 시 종합분석 캐시 무효화
    return {"inserted": inserted, "skipped": skipped, "updated": updated, "invalid": 0}


# G2B 카테고리별 신규 엔드포인트 (/ad/BidPublicInfoService — 2026 운영 버전)
# 비즈니스 요건상 용역/공사만 수집 (물품/외자 제외)
G2B_CATEGORIES = [
    ("용역", "getBidPblancListInfoServc"),
    ("공사", "getBidPblancListInfoCnstwk"),
]

# 낙찰결과 + 사정률 상세 (예정가격) 엔드포인트 (/as/ScsbidInfoService)
G2B_RESULT_CATEGORIES = [
    ("용역", "getOpengResultListInfoServcPreparPcDetail"),
    ("공사", "getOpengResultListInfoCnstwkPreparPcDetail"),
]


def _windows_iter(total_days: int, window_days: int, start_date=None):
    """오늘부터 거꾸로 window_days 단위로 (start_str, end_str) 튜플 yield.

    형식: 'YYYYMMDDHHMM' (G2B inqryDiv 표준).
    data.go.kr API는 7일 초과 inqry 시 빈 응답 → 윈도우 분할 필수.

    - start_date(YYYY-MM-DD) 가 주어지면 해당 일자까지 거꾸로 모두 순회 (전체 백필).
      total_days 는 무시됨. 예) "2019-01-01" → 2019-01-01 ~ 오늘 전 구간을 7일 단위 분할.
    - start_date 가 없으면 기존처럼 최근 total_days 만 순회.
    """
    now = datetime.now()
    if start_date:
        try:
            floor_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            floor_dt = None
        if floor_dt:
            win_end = now
            while win_end > floor_dt:
                win_start = max(floor_dt, win_end - timedelta(days=window_days))
                yield (
                    win_start.strftime("%Y%m%d") + "0000",
                    win_end.strftime("%Y%m%d") + "2359",
                )
                win_end = win_start
            return
    # 기본: 최근 total_days 만 순회
    produced = 0
    while produced < total_days:
        win = min(window_days, total_days - produced)
        win_end = now - timedelta(days=produced)
        win_start = win_end - timedelta(days=win)
        yield (
            win_start.strftime("%Y%m%d") + "0000",
            win_end.strftime("%Y%m%d") + "2359",
        )
        produced += win


def _record_sync_error(per_cat_errors: list, name: str, cat_label: str, page: int, exc: Exception):
    """수집 루프 예외를 분류해서 per_cat_errors 에 기록."""
    if isinstance(exc, urllib.error.HTTPError):
        per_cat_errors.append(f"{name} {cat_label} p{page} HTTP {exc.code}")
    elif isinstance(exc, (urllib.error.URLError, TimeoutError)):
        per_cat_errors.append(f"{name} {cat_label} p{page} 네트워크: {str(exc)[:60]}")
    else:
        per_cat_errors.append(f"{name} {cat_label} p{page} 파싱: {str(exc)[:60]}")


def _build_sync_url(source: str, api_key: str, rows: int = 100, page_no: int = 1,
                    start_date: str = None, end_date: str = None,
                    category_op: str = "getBidPblancListInfoServc",
                    days: int = 30) -> str:
    """data.go.kr 표준 API URL 빌더 — 페이지네이션 + 일자 범위 지원

    G2B는 `/1230000/ad/BidPublicInfoService/{operation}` 형태이며
    필수 파라미터로 inqryDiv=01 + inqryBgnDt + inqryEndDt 가 필요.
    start_date / end_date 형식: 'YYYYMMDDHHMM' (없으면 최근 days일 자동 설정)
    """
    qkey = urllib.parse.quote(api_key, safe="")
    if source == "G2B":
        if not start_date or not end_date:
            now = datetime.now()
            end_date = end_date or now.strftime("%Y%m%d") + "2359"
            start_date = start_date or (now - timedelta(days=days)).strftime("%Y%m%d") + "0000"
        return (
            f"https://apis.data.go.kr/1230000/ad/BidPublicInfoService/{category_op}"
            f"?serviceKey={qkey}&numOfRows={rows}&pageNo={page_no}&type=json"
            f"&inqryDiv=01&inqryBgnDt={start_date}&inqryEndDt={end_date}"
        )
    if source == "D2B":
        return f"https://d2b.go.kr/bidApi/list?apiKey={qkey}&size={rows}"
    raise ValueError(f"알 수 없는 source: {source}")


def _build_result_url(api_key: str, category_op: str, rows: int = 100, page_no: int = 1,
                      start_date: str = None, end_date: str = None,
                      days: int = 7) -> str:
    """낙찰결과(예정가격 상세) URL 빌더 — 페이지네이션 + 기간 옵션.

    PreparPcDetail 응답이 무거우므로 기본 7일치 + numOfRows=100으로 제한.
    """
    qkey = urllib.parse.quote(api_key, safe="")
    if not start_date or not end_date:
        now = datetime.now()
        end_date = end_date or now.strftime("%Y%m%d") + "2359"
        start_date = start_date or (now - timedelta(days=days)).strftime("%Y%m%d") + "0000"
    return (
        f"https://apis.data.go.kr/1230000/as/ScsbidInfoService/{category_op}"
        f"?serviceKey={qkey}&numOfRows={rows}&pageNo={page_no}&type=json"
        f"&inqryDiv=01&inqryBgnDt={start_date}&inqryEndDt={end_date}"
    )


def _normalize_result_item(item: dict) -> "dict | None":
    """낙찰결과 PreparPcDetail item → BidResult 필드로 정규화.

    핵심 매핑:
      plnprc → 사정률 계산 (plnprc / bssamt * 100)
      bssamt → 기초금액 (BidAnnouncement.base_amount 보강용)
      plnprc → winning_amount (낙찰가 근사치)
      compnoRsrvtnPrceMkngDt → opened_at
    """
    bid_number = item.get("bidNtceNo")
    if not bid_number:
        return None

    plnprc = item.get("plnprc")
    bssamt = item.get("bssamt")
    try:
        plnprc_f = float(plnprc) if plnprc not in (None, "", "null") else None
        bssamt_f = float(bssamt) if bssamt not in (None, "", "null") else None
    except (ValueError, TypeError):
        plnprc_f = bssamt_f = None

    # 사정률 = plnprc / bssamt * 100
    assessment_rate = None
    if plnprc_f and bssamt_f and bssamt_f > 0:
        assessment_rate = round(plnprc_f / bssamt_f * 100, 4)

    opened_at = _parse_date(item.get("rlOpengDt") or item.get("compnoRsrvtnPrceMkngDt") or item.get("inptDt"))

    return {
        "bid_number": str(bid_number).strip(),
        "winning_amount": int(plnprc_f) if plnprc_f else None,
        "winning_rate": assessment_rate,
        "assessment_rate": assessment_rate,
        # first_place_*는 별도 endpoint에서 보강 (현재 미수집)
        "first_place_rate": assessment_rate,
        "first_place_amount": int(plnprc_f) if plnprc_f else None,
        "num_bidders": None,
        "winning_company": None,
        "opened_at": opened_at or datetime.now(),
        # 메타 (참조용, 모델엔 없음)
        "_bssamt": int(bssamt_f) if bssamt_f else None,
        "_drwt_nums": item.get("drwtNum"),
    }


def _aggregate_prelim_prices(items: list[dict]) -> list[dict]:
    """PreparPcDetail 응답을 bid_number 단위로 집계 — 매칭률 향상 핵심.

    한 공고당 15개 예비가격 row 가 옴. 그중:
      1) 추첨된(drwtNum != null) 4개의 plnprc 평균 = 사정가(예정가격)
      2) 추첨된 게 없으면 15개 plnprc 평균을 fallback 으로 사용
      3) bssamt(기초금액)는 모든 row 에 동일

    사정률 = 사정가 / bssamt × 100
    """
    by_bid: dict = {}
    for it in items:
        bn = it.get("bid_number")
        if not bn:
            continue
        by_bid.setdefault(bn, []).append(it)

    aggregated = []
    for bn, rows in by_bid.items():
        # 추첨된 예비가격 우선 (drwtNum 값 존재)
        selected_prices = []
        all_prices = []
        bssamt = None
        opened_at = None
        for r in rows:
            plnprc = r.get("winning_amount")  # _normalize_result_item 에서 이미 plnprc → winning_amount
            bs = r.get("_bssamt")
            if plnprc:
                all_prices.append(plnprc)
                if r.get("_drwt_nums"):  # 추첨번호 존재 → 선택된 예비가
                    selected_prices.append(plnprc)
            if bs and not bssamt:
                bssamt = bs
            if r.get("opened_at") and not opened_at:
                opened_at = r["opened_at"]

        prelim_prices = selected_prices or all_prices
        if not prelim_prices:
            continue

        avg_prearng = sum(prelim_prices) / len(prelim_prices)
        rate = round(avg_prearng / bssamt * 100, 4) if bssamt and bssamt > 0 else None

        aggregated.append({
            "bid_number": bn,
            "winning_amount": int(avg_prearng),
            "winning_rate": rate,
            "assessment_rate": rate,
            "first_place_rate": rate,
            "first_place_amount": int(avg_prearng),
            "num_bidders": None,
            "winning_company": None,
            "opened_at": opened_at,
            "_bssamt": bssamt,
            "preliminary_prices": ",".join(str(int(p)) for p in all_prices),
            "selected_price_indices": ",".join(["1"] * len(selected_prices)) if selected_prices else "",
        })
    return aggregated


def _upsert_results(db, items: list[dict]) -> dict:
    """낙찰결과 upsert — 공고별 1건만 유지.

    PreparPcDetail 의 다중 예비가격을 _aggregate_prelim_prices() 로 집계 후
    공고별 사정률(평균 사정가 / 기초금액) 산출.
    부수 효과: BidAnnouncement.base_amount 가 비어 있으면 bssamt 로 보강.
    """
    if not items:
        return {"inserted": 0, "skipped": 0, "no_announcement": 0}

    # 매칭률 개선 — 첫 row dedup 대신 전체 집계
    items = _aggregate_prelim_prices(items)

    bid_numbers = [it["bid_number"] for it in items if it.get("bid_number")]
    # bid_number → BidAnnouncement.id 매핑
    ann_map = {
        a.bid_number: a for a in
        db.query(BidAnnouncement).filter(BidAnnouncement.bid_number.in_(bid_numbers)).all()
    }
    # 이미 결과가 있는 announcement_id
    if ann_map:
        existing_ann_ids = {
            row[0] for row in
            db.query(BidResult.announcement_id).filter(
                BidResult.announcement_id.in_([a.id for a in ann_map.values()])
            ).all()
        }
    else:
        existing_ann_ids = set()

    inserted = 0
    skipped = 0
    no_ann = 0
    batch_results: list[BidResult] = []
    for it in items:
        ann = ann_map.get(it["bid_number"])
        if not ann:
            no_ann += 1
            continue
        if ann.id in existing_ann_ids:
            skipped += 1
            continue
        existing_ann_ids.add(ann.id)

        # base_amount 보강
        if (ann.base_amount in (None, 0)) and it.get("_bssamt"):
            ann.base_amount = it["_bssamt"]

        batch_results.append(BidResult(
            announcement_id=ann.id,
            winning_amount=it.get("winning_amount"),
            winning_rate=it.get("winning_rate"),
            assessment_rate=it.get("assessment_rate"),
            first_place_rate=it.get("first_place_rate"),
            first_place_amount=it.get("first_place_amount"),
            num_bidders=it.get("num_bidders"),
            winning_company=it.get("winning_company"),
            preliminary_prices=it.get("preliminary_prices"),
            selected_price_indices=it.get("selected_price_indices"),
            opened_at=it.get("opened_at"),
        ))
        inserted += 1

    if batch_results:
        db.bulk_save_objects(batch_results)
        db.commit()
        invalidate_analysis_cache()

    return {"inserted": inserted, "skipped": skipped, "no_announcement": no_ann}


def _http_fetch_with_retry(url: str, timeout: int = 15, retries: int = 2) -> bytes:
    """일시적 네트워크 오류 시 지수 백오프로 재시도"""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "bid-insight/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last_exc = e
            if attempt < retries:
                import time as _t
                _t.sleep(0.5 * (2 ** attempt))  # 0.5s → 1s
                logger.warning("retrying sync fetch attempt=%d url=%s err=%s",
                              attempt + 1, url[:80], e)
                continue
            raise
    raise last_exc  # 도달 불가


def _lookup(name: str, default):
    """server 모듈에 monkeypatch 된 동명 심볼이 있으면 우선 반환 (테스트 호환).

    pytest 가 `monkeypatch.setattr(server_mod, "G2B_CATEGORIES", fake)` 처럼
    facade 모듈에 stub 을 꽂는 경우, 실 파이프라인이 그 stub 을 보도록 한다.
    """
    server_mod = sys.modules.get("server")
    if server_mod is not None and hasattr(server_mod, name):
        return getattr(server_mod, name)
    return default


def _run_sync_for_source(source: str, trigger: str = "manual",
                          resume_from_log_id: "str | None" = None) -> dict:
    """공공데이터 실 수집 파이프라인.

    API 키가 있으면 실제 호출 → JSON 파싱 → 정규화 → BidAnnouncement upsert.
    키가 없거나 호출/파싱이 실패하면 로그만 남기고 DB는 변경하지 않음.

    Item 1 — 진행률 + chunk-level resume 지원:
      - in_progress 레코드를 사전에 insert → 페이지마다 progress_pct/last_page/last_cursor_date 업데이트.
      - resume_from_log_id 가 있고 last_checkpoint/last_page>0 이면 그 위치부터 재개.
    """
    db = SessionLocal()
    started = datetime.now()
    status = "success"
    error_message = None
    summary = {"fetched": 0, "inserted": 0, "skipped": 0, "invalid": 0,
               "results_fetched": 0, "results_inserted": 0, "results_skipped": 0,
               "results_no_announcement": 0}

    # 진행 상태 기록용 in_progress 로그 사전 등록 (Item 1)
    progress_log = DataSyncLog(
        source=source,
        sync_type=f"공고+낙찰 수집 ({trigger})",
        status="in_progress",
        records_fetched=0,
        inserted_count=0,
        started_at=started,
        progress_pct=0.0,
        last_page=0,
    )
    db.add(progress_log)
    db.commit()
    db.refresh(progress_log)
    progress_log_id = progress_log.id

    # resume 정보 — last_checkpoint("cat_idx:win_idx:page") 우선, 없으면 last_page (deprecated) 폴백
    resume_cat_idx = 0
    resume_win_idx = 0
    resume_page = 1
    resume_active = False
    if resume_from_log_id:
        prev = db.query(DataSyncLog).filter(DataSyncLog.id == resume_from_log_id).first()
        if prev:
            ckpt = (getattr(prev, "last_checkpoint", None) or "").strip()
            parsed = False
            if ckpt:
                try:
                    parts = ckpt.split(":")
                    if len(parts) == 3:
                        resume_cat_idx = int(parts[0])
                        resume_win_idx = int(parts[1])
                        resume_page = int(parts[2]) + 1  # 다음 페이지부터
                        resume_active = True
                        parsed = True
                        logger.info("sync resume: log=%s checkpoint=%s -> cat=%d win=%d page=%d",
                                    resume_from_log_id, ckpt, resume_cat_idx, resume_win_idx, resume_page)
                except (ValueError, IndexError):
                    parsed = False
            if not parsed and (prev.last_page or 0) > 0:
                # 백워드 호환: 옛 last_page 만 있는 경우 첫 카테고리/첫 윈도우 시작 페이지로만 적용
                resume_page = (prev.last_page or 0) + 1
                resume_active = True
                logger.info("sync resume (legacy last_page): log=%s 시작 페이지=%d",
                            resume_from_log_id, resume_page)

    key_env = f"{source}_API_KEY"
    api_key = os.environ.get(key_env, "").strip()

    # 페이지네이션 / 기간 한계 (환경변수로 조정)
    # data.go.kr API는 7일 초과 inqry 시 빈 응답 → 7일 단위 슬라이딩 윈도우로 분할 호출
    rows_per_page = int(os.environ.get("SYNC_ROWS_PER_PAGE", "100"))
    max_pages_ann = int(os.environ.get("SYNC_MAX_PAGES_ANN", "5"))      # 공고: 윈도우당 최대 5페이지
    max_pages_res = int(os.environ.get("SYNC_MAX_PAGES_RES", "5"))      # 낙찰: 윈도우당 최대 5페이지
    window_days = int(os.environ.get("SYNC_WINDOW_DAYS", "7"))           # API 호환 윈도우 크기
    # 공고는 낙찰일자 - 2~3개월 전 등록되므로 충분히 길게 (낙찰결과와 매칭률↑)
    total_days_ann = int(os.environ.get("SYNC_TOTAL_DAYS_ANN", "60"))   # 공고: 누적 최대 60일 (start_date 미지정 시)
    total_days_res = int(os.environ.get("SYNC_TOTAL_DAYS_RES", "14"))   # 낙찰: 누적 최대 14일 (start_date 미지정 시)
    # 전체 백필 시작일 — 지정 시 해당 일자부터 오늘까지 7일 단위 전 구간 수집
    # 기본값 2019-01-01: 공공데이터 포털 G2B 데이터 가용 기간 시작점
    sync_start_ann = os.environ.get("SYNC_START_DATE_ANN", os.environ.get("SYNC_START_DATE", "2019-01-01")).strip() or None
    sync_start_res = os.environ.get("SYNC_START_DATE_RES", os.environ.get("SYNC_START_DATE", "2019-01-01")).strip() or None

    # 증분 모드 — 직전 성공 수집 시점 이후만 다시 호출 (cron 비용 절감)
    # SYNC_INCREMENTAL=true 이면 DataSyncLog 의 마지막 성공 시점 - 1일(buffer) 부터만 윈도우 생성.
    # SYNC_FORCE_FULL=true (또는 trigger=='backfill') 이면 강제로 전체 구간 재수집.
    incremental = os.environ.get("SYNC_INCREMENTAL", "false").lower() in ("true", "1", "yes")
    force_full = os.environ.get("SYNC_FORCE_FULL", "false").lower() in ("true", "1", "yes") or trigger == "backfill"
    if incremental and not force_full:
        last_ok = (
            db.query(DataSyncLog.finished_at)
            .filter(DataSyncLog.source == source, DataSyncLog.status == "success")
            .order_by(DataSyncLog.finished_at.desc())
            .first()
        )
        if last_ok and last_ok[0]:
            buf_days = int(os.environ.get("SYNC_INCREMENTAL_BUFFER_DAYS", "1"))
            inc_floor = (last_ok[0] - timedelta(days=buf_days)).strftime("%Y-%m-%d")
            # 전체 백필 시작일보다 더 최근 시점일 때만 좁힌다 (앞으로 당기지는 않음)
            if not sync_start_ann or inc_floor > sync_start_ann:
                sync_start_ann = inc_floor
                sync_start_res = inc_floor
            logger.info("incremental sync floor=%s (last_ok=%s)", inc_floor, last_ok[0])

    # 테스트에서 server 모듈에 monkeypatch 한 stub 우선 사용
    _windows_iter_fn = _lookup("_windows_iter", _windows_iter)
    _http_fetch_fn = _lookup("_http_fetch_with_retry", _http_fetch_with_retry)
    _extract_items_fn = _lookup("_extract_g2b_items", _extract_g2b_items)
    _normalize_item_fn = _lookup("_normalize_item", _normalize_item)
    _normalize_result_fn = _lookup("_normalize_result_item", _normalize_result_item)
    _upsert_ann_fn = _lookup("_upsert_announcements", _upsert_announcements)
    _upsert_res_fn = _lookup("_upsert_results", _upsert_results)
    _build_sync_url_fn = _lookup("_build_sync_url", _build_sync_url)
    _build_result_url_fn = _lookup("_build_result_url", _build_result_url)
    _record_sync_error_fn = _lookup("_record_sync_error", _record_sync_error)
    _G2B_CATEGORIES = _lookup("G2B_CATEGORIES", G2B_CATEGORIES)
    _G2B_RESULT_CATEGORIES = _lookup("G2B_RESULT_CATEGORIES", G2B_RESULT_CATEGORIES)

    # 총 페이지 추정치 (진행률 계산용) — 카테고리 × 윈도우 × 페이지
    def _count_windows(total_days: int, win_days: int, start_date: "str | None") -> int:
        try:
            return sum(1 for _ in _windows_iter_fn(total_days, win_days, start_date=start_date))
        except Exception:
            return 1

    try:
        if api_key:
            # G2B는 용역/공사 2개 카테고리 순회 수집
            categories = _G2B_CATEGORIES if source == "G2B" else [(None, None)]
            result_categories = _G2B_RESULT_CATEGORIES if source == "G2B" else []
            per_cat_errors = []

            # 총 페이지 추정 (진행률 % 계산 분모)
            ann_windows = _count_windows(total_days_ann, window_days, sync_start_ann)
            res_windows = _count_windows(total_days_res, window_days, sync_start_res)
            total_pages_est = max(1,
                len(categories) * ann_windows * max_pages_ann +
                len(result_categories) * res_windows * max_pages_res
            )
            pages_done = 0

            progress_broken = {"flag": False}

            def _commit_progress(page_idx: int, cursor_end: "str | None",
                                 cat_idx: int = 0, win_idx: int = 0, page: int = 0):
                """페이지마다 진행률을 DB 에 commit (Item 1).

                Bug B 수정: last_checkpoint 에 (cat_idx:win_idx:page) 3-int 좌표 저장.
                last_page 는 deprecated 글로벌 누적 (백워드 호환 표시용).
                """
                try:
                    pl = db.query(DataSyncLog).filter(DataSyncLog.id == progress_log_id).first()
                    if not pl:
                        return
                    pl.last_page = page_idx
                    pl.last_checkpoint = f"{cat_idx}:{win_idx}:{page}"
                    pl.progress_pct = round(min(100.0, page_idx / total_pages_est * 100.0), 2)
                    if cursor_end:
                        try:
                            pl.last_cursor_date = datetime.strptime(cursor_end[:10], "%Y-%m-%d")
                        except Exception:
                            pass
                    pl.records_fetched = summary["fetched"] + summary.get("results_fetched", 0)
                    pl.inserted_count = summary["inserted"] + summary.get("results_inserted", 0)
                    db.commit()
                except Exception as _e:
                    # Quality 3: 단순 swallow 가 아니라 외부 루프가 알 수 있도록 플래그 셋
                    logger.warning("progress commit failed: %s", _e)
                    progress_broken["flag"] = True
                    try:
                        db.rollback()
                    except Exception:
                        pass

            # ① 입찰공고 수집 (카테고리 × 슬라이딩 윈도우 × 페이지)
            for cat_idx, (cat_label, cat_op) in enumerate(categories):
                cat_fetched = cat_inserted = 0
                # resume: 체크포인트보다 앞선 카테고리 전체 스킵
                if resume_active and cat_idx < resume_cat_idx:
                    continue
                for win_idx, (win_start, win_end) in enumerate(_windows_iter_fn(total_days_ann, window_days, start_date=sync_start_ann)):
                    # resume: 같은 카테고리에서 체크포인트보다 앞선 윈도우 스킵
                    if resume_active and cat_idx == resume_cat_idx and win_idx < resume_win_idx:
                        continue
                    # resume: 정확히 체크포인트 (cat,win) 인 경우만 페이지를 늦춤, 그 외는 1
                    if resume_active and cat_idx == resume_cat_idx and win_idx == resume_win_idx:
                        page_start = resume_page
                    else:
                        page_start = 1
                    for page in range(page_start, max_pages_ann + 1):
                        try:
                            url = _build_sync_url_fn(
                                source, api_key, rows=rows_per_page, page_no=page,
                                start_date=win_start, end_date=win_end,
                                category_op=cat_op or "getBidPblancListInfoServc",
                            )
                            payload = _http_fetch_fn(url, timeout=20, retries=2)
                            raw_items = _extract_items_fn(payload)
                            if not raw_items:
                                break
                            summary["fetched"] += len(raw_items)
                            cat_fetched += len(raw_items)
                            normalized = []
                            for it in raw_items:
                                norm = _normalize_item_fn(source, it)
                                if norm:
                                    # 엔드포인트가 카테고리를 명시한 경우 강제 적용
                                    # (Cnstwk/Servc 엔드포인트의 응답에는 bsnsDivNm 이 누락되거나 다른 값일 수 있어
                                    #  _normalize_item 의 기본값 "용역"이 잘못 적용되는 문제를 방지)
                                    if cat_label:
                                        norm["category"] = cat_label
                                    normalized.append(norm)
                                else:
                                    summary["invalid"] += 1
                            up = _upsert_ann_fn(db, source, normalized)
                            summary["inserted"] += up["inserted"]
                            summary["skipped"] += up["skipped"]
                            cat_inserted += up["inserted"]
                            pages_done += 1
                            _commit_progress(pages_done, win_end,
                                             cat_idx=cat_idx, win_idx=win_idx, page=page)
                            if progress_broken["flag"]:
                                raise RuntimeError("progress commit failed (DB session 손상)")
                            if len(raw_items) < rows_per_page:
                                break
                        except Exception as exc:
                            _record_sync_error_fn(per_cat_errors, "공고", cat_label, page, exc)
                            break
                if cat_label:
                    logger.info(
                        "g2b ann sync category=%s fetched=%d inserted=%d total_days=%d",
                        cat_label, cat_fetched, cat_inserted, total_days_ann,
                    )

            # ② 낙찰결과(예정가격 상세) 수집 - 슬라이딩 윈도우 적용
            # 체크포인트 cat_idx 는 [공고 카테고리 수 + 낙찰 카테고리 인덱스] 로 표현
            res_cat_offset = len(categories)
            for r_idx, (cat_label, cat_op) in enumerate(result_categories):
                res_cat_idx = res_cat_offset + r_idx
                cat_fetched = cat_inserted = 0
                if resume_active and res_cat_idx < resume_cat_idx:
                    continue
                for win_idx, (win_start, win_end) in enumerate(_windows_iter_fn(total_days_res, window_days, start_date=sync_start_res)):
                    if resume_active and res_cat_idx == resume_cat_idx and win_idx < resume_win_idx:
                        continue
                    if resume_active and res_cat_idx == resume_cat_idx and win_idx == resume_win_idx:
                        page_start_r = resume_page
                    else:
                        page_start_r = 1
                    for page in range(page_start_r, max_pages_res + 1):
                        try:
                            url = _build_result_url_fn(
                                api_key, cat_op, rows=rows_per_page,
                                page_no=page, start_date=win_start, end_date=win_end,
                            )
                            payload = _http_fetch_fn(url, timeout=30, retries=2)
                            raw_items = _extract_items_fn(payload)
                            if not raw_items:
                                break
                            summary["results_fetched"] += len(raw_items)
                            cat_fetched += len(raw_items)
                            normalized = [n for n in (_normalize_result_fn(it) for it in raw_items) if n]
                            up = _upsert_res_fn(db, normalized)
                            summary["results_inserted"] += up["inserted"]
                            summary["results_skipped"] += up["skipped"]
                            summary["results_no_announcement"] += up["no_announcement"]
                            cat_inserted += up["inserted"]
                            pages_done += 1
                            _commit_progress(pages_done, win_end,
                                             cat_idx=res_cat_idx, win_idx=win_idx, page=page)
                            if progress_broken["flag"]:
                                raise RuntimeError("progress commit failed (DB session 손상)")
                            if len(raw_items) < rows_per_page:
                                break
                        except Exception as exc:
                            _record_sync_error_fn(per_cat_errors, "낙찰", cat_label, page, exc)
                            break
                logger.info(
                    "g2b result sync category=%s fetched=%d inserted=%d total_days=%d",
                    cat_label, cat_fetched, cat_inserted, total_days_res,
                )

            if per_cat_errors:
                # 일부만 실패해도 부분 성공으로 처리, 전체 실패 시 failed
                total_fetched = summary["fetched"] + summary["results_fetched"]
                if total_fetched == 0:
                    status = "failed"
                error_message = "; ".join(per_cat_errors)[:500]
            elif summary["fetched"] == 0:
                status = "failed"
                error_message = f"{source} 응답에서 item을 찾지 못했습니다."
        else:
            # 시드 폴백: DB 변경 없이 기록만
            summary["fetched"] = random.randint(15, 80)
            summary["skipped"] = summary["fetched"]  # 시드 모드는 삽입 없음
            error_message = None
    except Exception as e:
        status = "failed"
        error_message = f"수집 중 예외: {str(e)[:150]}"

    finished = datetime.now()
    total_fetched = summary["fetched"] + summary.get("results_fetched", 0)
    total_inserted = summary["inserted"] + summary.get("results_inserted", 0)
    # 진행 로그를 최종 상태로 업데이트 (Item 1)
    log = db.query(DataSyncLog).filter(DataSyncLog.id == progress_log_id).first()
    if log is None:
        log = DataSyncLog(
            id=progress_log_id, source=source,
            sync_type=f"공고+낙찰 수집 ({trigger})",
            status=status, started_at=started,
        )
        db.add(log)
    log.status = status
    log.records_fetched = total_fetched
    log.inserted_count = total_inserted
    log.error_message = (error_message[:500] if error_message else None)
    log.finished_at = finished
    log.progress_pct = 100.0 if status == "success" else (log.progress_pct or 0.0)
    db.commit()
    db.refresh(log)
    sync_id = log.id
    db.close()
    return {
        "sync_id": sync_id,
        "source": source,
        "status": status,
        "records": summary["fetched"],
        "inserted": summary["inserted"],
        "skipped": summary["skipped"],
        "invalid": summary["invalid"],
        "results_fetched": summary.get("results_fetched", 0),
        "results_inserted": summary.get("results_inserted", 0),
        "results_skipped": summary.get("results_skipped", 0),
        "results_no_announcement": summary.get("results_no_announcement", 0),
        "duration_sec": int((finished - started).total_seconds()),
        "error_message": error_message,
    }

