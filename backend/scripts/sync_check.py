#!/usr/bin/env python3
"""공공데이터 수집 E2E 진단 CLI

API 키를 받은 직후 실 호출 → 파싱 → DB 반영까지 단계별로 결과를 출력한다.
서버 실행 없이 단독으로 동작한다.

사용법:
    # 환경변수로 키 주입
    export G2B_API_KEY="발급받은_인증키"
    python3 scripts/sync_check.py --source G2B

    # 옵션
    python3 scripts/sync_check.py --source G2B --dry-run        # DB 변경 없음
    python3 scripts/sync_check.py --source G2B --rows 10         # 10건만 시도
    python3 scripts/sync_check.py --source D2B --verbose         # 응답 본문 일부 출력
    python3 scripts/sync_check.py --source G2B --json            # 결과를 JSON으로

종료 코드:
    0: 성공 (1건 이상 정상 파싱)
    1: 일반 오류 (네트워크/파싱 실패)
    2: API 키 누락
    3: DB 오류
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

# server.py 모듈 로드를 위한 경로 추가
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_THIS_DIR))

from server import (  # noqa: E402
    SessionLocal, BidAnnouncement, DataSyncLog,
    _extract_g2b_items, _normalize_item, _upsert_announcements,
)


# ── ANSI 색상 ─────────────────────────────────────────────────────
class C:
    G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[94m"; D = "\033[2m"; X = "\033[0m"


def log(level: str, msg: str):
    color = {"OK": C.G, "WARN": C.Y, "FAIL": C.R, "INFO": C.B, "DIM": C.D}.get(level, "")
    print(f"{color}[{level:>4}]{C.X} {msg}")


# ── G2B/D2B URL 빌드 ─────────────────────────────────────────────

def build_url(source: str, api_key: str, rows: int,
              category_op: str = "getBidPblancListInfoServc") -> str:
    """data.go.kr 표준 호출 URL 구성 (신규 /ad/ 엔드포인트 + 필수 파라미터)"""
    from datetime import datetime, timedelta as _td
    qkey = urllib.parse.quote(api_key, safe="")
    if source == "G2B":
        now = datetime.now()
        end_s = now.strftime("%Y%m%d") + "2359"
        start_s = (now - _td(days=7)).strftime("%Y%m%d") + "0000"
        return (
            f"https://apis.data.go.kr/1230000/ad/BidPublicInfoService/{category_op}"
            f"?serviceKey={qkey}&numOfRows={rows}&pageNo=1&type=json"
            f"&inqryDiv=01&inqryBgnDt={start_s}&inqryEndDt={end_s}"
        )
    if source == "D2B":
        return (
            "https://d2b.go.kr/bidApi/list"
            f"?apiKey={qkey}&size={rows}"
        )
    raise ValueError(f"알 수 없는 source: {source}")


def http_fetch(url: str, timeout: int) -> bytes:
    """GET + User-Agent + 타임아웃"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "bid-insight-syncchk/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ── 단계별 진단 ──────────────────────────────────────────────────

def step_check_key(source: str) -> str:
    key = os.environ.get(f"{source}_API_KEY", "").strip()
    if not key:
        log("FAIL", f"{source}_API_KEY 환경변수가 비어 있습니다.")
        log("INFO", f"export {source}_API_KEY='발급받은_인증키' 후 다시 실행하세요.")
        sys.exit(2)
    masked = key[:6] + "…" + key[-4:] if len(key) > 12 else "***"
    log("OK", f"{source}_API_KEY 감지 ({masked}, len={len(key)})")
    return key


def step_fetch(url: str, timeout: int, verbose: bool) -> bytes:
    log("INFO", f"GET {url[:120]}{'…' if len(url) > 120 else ''}")
    t0 = time.perf_counter()
    try:
        payload = http_fetch(url, timeout)
    except urllib.error.HTTPError as e:
        log("FAIL", f"HTTP {e.code} {e.reason}")
        body = e.read()[:500] if e.fp else b""
        if body:
            log("DIM", f"본문(500자): {body.decode('utf-8', errors='replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        log("FAIL", f"네트워크 오류: {e.reason}")
        sys.exit(1)
    except TimeoutError:
        log("FAIL", f"{timeout}초 타임아웃")
        sys.exit(1)
    elapsed = (time.perf_counter() - t0) * 1000
    log("OK", f"응답 수신 {len(payload)}바이트 / {elapsed:.0f}ms")

    if verbose:
        head = payload[:500].decode("utf-8", errors="replace")
        log("DIM", f"응답 헤드: {head}")

    # XML 응답이면 키 등록 미완 등 경고
    if payload.lstrip().startswith(b"<"):
        log("WARN", "JSON이 아닌 XML 응답입니다 — 키 미승인 또는 잘못된 type 파라미터일 수 있습니다.")
        snippet = payload[:300].decode("utf-8", errors="replace")
        log("DIM", snippet)
    return payload


def step_extract(payload: bytes) -> list:
    items = _extract_g2b_items(payload)
    if not items:
        log("WARN", "items 추출 결과 0건 — 응답 스키마 확인 필요")
    else:
        log("OK", f"items {len(items)}건 추출")
    return items


def step_normalize(source: str, items: list, verbose: bool) -> tuple:
    """정규화 결과 + 무효 건수 반환"""
    valid = []
    invalid = 0
    for idx, it in enumerate(items, 1):
        norm = _normalize_item(source, it)
        if norm is None:
            invalid += 1
            if verbose:
                keys = list(it.keys())[:5]
                log("DIM", f"#{idx} 정규화 실패 (필수 필드 누락) keys={keys}")
        else:
            valid.append(norm)
    log("OK" if invalid == 0 else "WARN",
        f"정규화 완료 — 유효 {len(valid)} / 무효 {invalid}")
    if valid and verbose:
        sample = valid[0]
        log("DIM", f"샘플: bid={sample['bid_number']}  title={sample['title'][:40]}  "
                   f"org={sample['ordering_org_name']}  amount={sample['base_amount']}")
    return valid, invalid


def step_upsert(source: str, normalized: list, dry_run: bool) -> dict:
    if dry_run:
        # 중복 검사만 수행
        db = SessionLocal()
        nums = [n["bid_number"] for n in normalized]
        existing = {
            row[0] for row in
            db.query(BidAnnouncement.bid_number).filter(
                BidAnnouncement.bid_number.in_(nums)
            ).all()
        } if nums else set()
        db.close()
        would_insert = sum(1 for n in normalized if n["bid_number"] not in existing)
        would_skip = len(normalized) - would_insert
        log("INFO", f"[DRY-RUN] 삽입 예정 {would_insert} / 중복 {would_skip}")
        return {"inserted": 0, "skipped": would_skip,
                "would_insert": would_insert, "dry_run": True}

    db = SessionLocal()
    try:
        res = _upsert_announcements(db, source, normalized)
    except Exception as e:
        db.close()
        log("FAIL", f"DB upsert 오류: {e}")
        sys.exit(3)
    db.close()
    log("OK", f"DB 반영 — 신규 {res['inserted']} / 중복 {res['skipped']}")
    return res


def step_record_sync_log(source: str, summary: dict, error: str = None):
    db = SessionLocal()
    db.add(DataSyncLog(
        source=source, sync_type="공고 수집 (sync_check)",
        status="success" if not error else "failed",
        records_fetched=summary.get("fetched", 0),
        inserted_count=summary.get("inserted", 0),
        error_message=error,
        started_at=summary["started"],
        finished_at=datetime.now(),
    ))
    db.commit()
    db.close()
    log("OK", "DataSyncLog 기록 완료")


# ── 메인 ──────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="공공데이터 수집 E2E 진단")
    p.add_argument("--source", required=True, choices=["G2B", "D2B"])
    p.add_argument("--rows", type=int, default=20, help="numOfRows (기본 20)")
    p.add_argument("--timeout", type=int, default=15, help="HTTP 타임아웃 초 (기본 15)")
    p.add_argument("--dry-run", action="store_true", help="DB 변경 없이 검증만")
    p.add_argument("--verbose", action="store_true", help="응답/샘플 일부 출력")
    p.add_argument("--json", action="store_true", help="결과를 JSON으로만 출력")
    args = p.parse_args()

    started = datetime.now()
    summary = {"source": args.source, "started": started, "fetched": 0,
               "valid": 0, "invalid": 0, "inserted": 0, "skipped": 0}

    try:
        key = step_check_key(args.source)
        url = build_url(args.source, key, args.rows)
        payload = step_fetch(url, args.timeout, args.verbose and not args.json)
        items = step_extract(payload)
        summary["fetched"] = len(items)

        if items:
            valid, invalid = step_normalize(args.source, items,
                                            args.verbose and not args.json)
            summary["valid"] = len(valid)
            summary["invalid"] = invalid
            if valid:
                up = step_upsert(args.source, valid, args.dry_run)
                summary["inserted"] = up.get("inserted", 0)
                summary["skipped"] = up.get("skipped", 0)
                if args.dry_run:
                    summary["would_insert"] = up.get("would_insert", 0)

        if not args.dry_run:
            step_record_sync_log(args.source, summary)

    except SystemExit:
        raise
    except Exception as e:
        log("FAIL", f"예상치 못한 오류: {e}")
        return 1

    summary["finished"] = datetime.now()
    summary["duration_sec"] = (summary["finished"] - summary["started"]).total_seconds()

    if args.json:
        # ISO 포맷으로 직렬화
        summary["started"] = summary["started"].isoformat()
        summary["finished"] = summary["finished"].isoformat()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print()
        log("OK" if summary["valid"] > 0 else "WARN", "─" * 50)
        log("OK" if summary["valid"] > 0 else "WARN",
            f"E2E 검증 완료 — 수신 {summary['fetched']} / 유효 {summary['valid']} / "
            f"신규 {summary['inserted']} / 중복 {summary['skipped']} / "
            f"소요 {summary['duration_sec']:.1f}s")

    return 0 if summary["valid"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
