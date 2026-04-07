"""국방전자조달(D2B) 공공데이터 API 클라이언트

방위사업청 군수품조달정보 API를 통해 입찰공고, 입찰결과, 계약정보를 수집합니다.
"""

import logging
from datetime import datetime

import httpx
import xmltodict

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "http://apis.data.go.kr/9230000"

ENDPOINTS = {
    "bid_notice": "/MltsrtPrcrmtBidPblancInfoService/getBidPblancListInfoServc01",
    "bid_result": "/MltsrtPrcrmtBidRsltInfoService/getBidResultInfoService01",
    "contract": "/MltsrtPrcrmtCntrctInfoService/getCntrctInfoListServc01",
}


class D2BClient:
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
                data = xmltodict.parse(response.text)
                return data.get("response", {}).get("body", {})
            else:
                data = response.json()
                return data.get("response", {}).get("body", {})

        except httpx.HTTPError as e:
            logger.error(f"D2B API 요청 실패 [{endpoint_key}]: {e}")
            raise

    async def fetch_bid_notices(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        """국방 입찰공고 조회"""
        params = {}
        if date_from:
            params["inqBgnDt"] = date_from
        if date_to:
            params["inqEndDt"] = date_to

        body = await self._request("bid_notice", params, page, page_size)
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items or []

    async def fetch_bid_results(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        """국방 입찰결과 조회"""
        params = {}
        if date_from:
            params["inqBgnDt"] = date_from
        if date_to:
            params["inqEndDt"] = date_to

        body = await self._request("bid_result", params, page, page_size)
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items or []

    async def fetch_all_pages(
        self,
        fetch_func,
        date_from: str | None = None,
        date_to: str | None = None,
        max_pages: int = 50,
    ) -> list[dict]:
        """전체 페이지 순회"""
        all_items = []
        page = 1

        while page <= max_pages:
            items = await fetch_func(
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=100,
            )
            if not items:
                break

            all_items.extend(items)
            logger.info(f"[D2B] page {page}: {len(items)}건 수집 (누적 {len(all_items)}건)")

            if len(items) < 100:
                break
            page += 1

        return all_items


def parse_d2b_notice(raw: dict) -> dict:
    """D2B 공고 → DB 입력용 dict"""
    return {
        "source": "D2B",
        "bid_number": raw.get("bidNtceNo", "") + "-" + raw.get("bidNtceOrd", "00"),
        "category": raw.get("prdctClsfcNm", "용역"),
        "title": raw.get("bidNtceNm", ""),
        "ordering_org_name": raw.get("dminsttNm", ""),
        "ordering_org_type": "국방부",
        "region": raw.get("dlvrTmNm", ""),
        "industry_code": raw.get("bidClsfcNo", ""),
        "industry_name": raw.get("prdctClsfcNm", ""),
        "base_amount": _parse_amount(raw.get("asignBdgtAmt")),
        "estimated_price": _parse_amount(raw.get("presmptPrce")),
        "bid_method": raw.get("cntrctMthdNm", ""),
        "announced_at": _parse_datetime(raw.get("bidNtceDt")),
        "bid_open_at": _parse_datetime(raw.get("opengDt")),
        "deadline_at": _parse_datetime(raw.get("bidClseDt")),
        "status": "진행중",
        "raw_json": raw,
    }


def parse_d2b_result(raw: dict) -> dict:
    """D2B 결과 → DB 입력용 dict"""
    base_amount = _parse_amount(raw.get("asignBdgtAmt", raw.get("bssamt")))
    estimated_price = _parse_amount(raw.get("presmptPrce", raw.get("estmtPrce")))
    winning_amount = _parse_amount(raw.get("sucsfbidAmt"))

    assessment_rate = None
    if base_amount and estimated_price and base_amount > 0:
        assessment_rate = round((estimated_price / base_amount) * 100, 4)

    winning_rate = None
    if estimated_price and winning_amount and estimated_price > 0:
        winning_rate = round((winning_amount / estimated_price) * 100, 4)

    return {
        "bid_number": raw.get("bidNtceNo", "") + "-" + raw.get("bidNtceOrd", "00"),
        "winning_amount": winning_amount,
        "winning_rate": winning_rate,
        "assessment_rate": assessment_rate,
        "num_bidders": _parse_int(raw.get("prtcptCnum")),
        "winning_company": raw.get("sucsfbidBzNm", ""),
        "opened_at": _parse_datetime(raw.get("opengDt")),
        "raw_json": raw,
    }


def _parse_amount(value) -> int | None:
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
    if not value:
        return None
    value = str(value).strip()
    for fmt in ["%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
