"""나라장터(G2B) 공공데이터 API 클라이언트

조달청 나라장터 Open API를 통해 입찰공고, 낙찰결과, 계약정보를 수집합니다.
- 입찰공고정보서비스
- 낙찰정보서비스 (공사/용역)
- 계약정보서비스
"""

import logging
from datetime import datetime, timedelta

import httpx
import xmltodict

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "http://apis.data.go.kr/1230000"

# API 엔드포인트 매핑
ENDPOINTS = {
    # 입찰공고
    "bid_notice_construction": "/BidPublicInfoInfoService04/getBidPblancListInfoCnstwk",
    "bid_notice_service": "/BidPublicInfoInfoService04/getBidPblancListInfoServc",
    # 낙찰정보
    "award_construction": "/ScsbidInfoService/getOpengResultListInfoCnstwk",
    "award_service": "/ScsbidInfoService/getOpengResultListInfoServc",
    # 계약정보
    "contract_construction": "/CntrctInfoService/getCntrctInfoListCnstwk",
    "contract_service": "/CntrctInfoService/getCntrctInfoListServc",
}


class G2BClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.data_go_kr_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def _request(
        self,
        endpoint_key: str,
        params: dict | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """API 요청 공통 메서드"""
        url = BASE_URL + ENDPOINTS[endpoint_key]

        request_params = {
            "ServiceKey": self.api_key,
            "pageNo": str(page),
            "numOfRows": str(page_size),
            "type": "json",
        }
        if params:
            request_params.update(params)

        try:
            response = await self.client.get(url, params=request_params)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "xml" in content_type or response.text.startswith("<?xml"):
                # XML 응답 → dict 변환
                data = xmltodict.parse(response.text)
                return data.get("response", {}).get("body", {})
            else:
                data = response.json()
                return data.get("response", {}).get("body", {})

        except httpx.HTTPError as e:
            logger.error(f"G2B API 요청 실패 [{endpoint_key}]: {e}")
            raise
        except Exception as e:
            logger.error(f"G2B API 파싱 실패 [{endpoint_key}]: {e}")
            raise

    async def fetch_bid_notices(
        self,
        category: str = "construction",
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        """입찰공고 목록 조회

        Args:
            category: construction(공사) 또는 service(용역)
            date_from: 조회 시작일 (YYYYMMDD)
            date_to: 조회 종료일 (YYYYMMDD)
        """
        endpoint_key = f"bid_notice_{category}"

        params = {}
        if date_from:
            params["inqBgnDt"] = date_from
        if date_to:
            params["inqEndDt"] = date_to

        body = await self._request(endpoint_key, params, page, page_size)
        items = body.get("items", [])

        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]

        return items or []

    async def fetch_award_results(
        self,
        category: str = "construction",
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        """낙찰 결과 조회

        Args:
            category: construction(공사) 또는 service(용역)
            date_from: 조회 시작일 (YYYYMMDD)
            date_to: 조회 종료일 (YYYYMMDD)
        """
        endpoint_key = f"award_{category}"

        params = {}
        if date_from:
            params["inqBgnDt"] = date_from
        if date_to:
            params["inqEndDt"] = date_to

        body = await self._request(endpoint_key, params, page, page_size)
        items = body.get("items", [])

        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]

        return items or []

    async def fetch_contract_info(
        self,
        category: str = "construction",
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        """계약 정보 조회"""
        endpoint_key = f"contract_{category}"

        params = {}
        if date_from:
            params["inqBgnDt"] = date_from
        if date_to:
            params["inqEndDt"] = date_to

        body = await self._request(endpoint_key, params, page, page_size)
        items = body.get("items", [])

        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]

        return items or []

    async def fetch_all_pages(
        self,
        fetch_func,
        category: str = "construction",
        date_from: str | None = None,
        date_to: str | None = None,
        max_pages: int = 50,
    ) -> list[dict]:
        """전체 페이지 순회하여 모든 데이터 수집"""
        all_items = []
        page = 1

        while page <= max_pages:
            items = await fetch_func(
                category=category,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=100,
            )

            if not items:
                break

            all_items.extend(items)
            logger.info(
                f"[G2B] {category} page {page}: {len(items)}건 수집 (누적 {len(all_items)}건)"
            )

            if len(items) < 100:
                break

            page += 1

        return all_items


def parse_bid_notice(raw: dict, category: str) -> dict:
    """API 응답 → DB 입력용 dict 변환 (입찰공고)"""
    category_kr = "공사" if category == "construction" else "용역"

    return {
        "source": "G2B",
        "bid_number": raw.get("bidNtceNo", "") + "-" + raw.get("bidNtceOrd", "00"),
        "category": category_kr,
        "title": raw.get("bidNtceNm", ""),
        "ordering_org_name": raw.get("ntceInsttNm", raw.get("dminsttNm", "")),
        "ordering_org_type": _classify_org_type(raw.get("ntceInsttNm", "")),
        "region": raw.get("cmmnSpldmdCorpRgnNm", raw.get("prtcptLmtRgnNm", "")),
        "industry_code": raw.get("ntceInsttCd", ""),
        "industry_name": raw.get("bidClsfcNo", ""),
        "base_amount": _parse_amount(raw.get("presmptPrce", raw.get("asignBdgtAmt"))),
        "estimated_price": _parse_amount(raw.get("rsrvtnPrceRngBgnRate")),
        "bid_method": raw.get("sucsfbidMthdNm", raw.get("bidMethdNm", "")),
        "announced_at": _parse_datetime(raw.get("bidNtceDt", raw.get("rgstDt"))),
        "bid_open_at": _parse_datetime(raw.get("opengDt")),
        "deadline_at": _parse_datetime(raw.get("bidClseDt")),
        "status": "진행중",
        "raw_json": raw,
    }


def parse_award_result(raw: dict, category: str) -> dict:
    """API 응답 → DB 입력용 dict 변환 (낙찰결과)"""
    base_amount = _parse_amount(raw.get("presmptPrce", raw.get("bssamt")))
    estimated_price = _parse_amount(raw.get("predPrce", raw.get("estmtPrce")))
    winning_amount = _parse_amount(raw.get("sucsfbidAmt", raw.get("fnlSucsfbidAmt")))

    assessment_rate = None
    if base_amount and estimated_price and base_amount > 0:
        assessment_rate = round((estimated_price / base_amount) * 100, 4)

    winning_rate = None
    if estimated_price and winning_amount and estimated_price > 0:
        winning_rate = round((winning_amount / estimated_price) * 100, 4)

    # 복수예비가격 파싱
    preliminary_prices = []
    for i in range(1, 16):
        key = f"bssamt{i:02d}" if i < 10 else f"bssamt{i}"
        alt_key = f"rsrvtnPrce{i:02d}"
        price = _parse_amount(raw.get(key, raw.get(alt_key)))
        if price:
            preliminary_prices.append({"index": i, "amount": price})

    return {
        "bid_number": raw.get("bidNtceNo", "") + "-" + raw.get("bidNtceOrd", "00"),
        "winning_amount": winning_amount,
        "winning_rate": winning_rate,
        "assessment_rate": assessment_rate,
        "num_bidders": _parse_int(raw.get("prtcptCnum", raw.get("bidprcPrtcptCnum"))),
        "winning_company": raw.get("sucsfbidBzNm", raw.get("opengCorpInfo", "")),
        "preliminary_prices": preliminary_prices if preliminary_prices else None,
        "opened_at": _parse_datetime(raw.get("opengDt")),
        "raw_json": raw,
    }


def _classify_org_type(org_name: str) -> str:
    """발주기관 유형 분류"""
    if not org_name:
        return "기타"
    if any(k in org_name for k in ["부", "처", "청", "원", "위원회"]):
        return "중앙부처"
    if any(k in org_name for k in ["시", "도", "군", "구청"]):
        return "지자체"
    if any(k in org_name for k in ["공사", "공단", "진흥원", "재단"]):
        return "공기업"
    if any(k in org_name for k in ["대학", "학교"]):
        return "교육기관"
    return "기타"


def _parse_amount(value) -> int | None:
    """금액 파싱 (문자열 → 정수)"""
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_datetime(value) -> datetime | None:
    """날짜/시간 파싱"""
    if not value:
        return None

    value = str(value).strip()
    for fmt in [
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y%m%d",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None
