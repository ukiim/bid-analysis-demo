"""데이터 업로드 라우터 — CSV/Excel 입찰 데이터 업로드 및 이력.

server.py 의 `/api/v1/data/upload` 및 `/api/v1/data/uploads` 핸들러를 이전.
MIGRATION.md F4.
"""
from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.database import SessionLocal
from app.core.security import require_auth
from app.models import BidAnnouncement, UploadLog, User
from app.services.cache import invalidate_analysis_cache

router = APIRouter(prefix="/api/v1/data", tags=["데이터"])


@router.post("/upload")
def upload_data(file: UploadFile = File(...), current_user: User = Depends(require_auth)):
    """CSV/Excel 입찰 데이터 업로드 — 중복 검사·행별 오류 추적 포함"""
    import io
    allowed_ext = {".csv", ".xlsx", ".xls"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다. ({', '.join(allowed_ext)})")

    content = file.file.read()
    file_size = len(content)
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    if file_size > MAX_SIZE:
        raise HTTPException(status_code=413, detail=f"파일 크기가 10MB를 초과합니다. (현재 {round(file_size/1024/1024, 1)}MB)")

    db = SessionLocal()
    upload = UploadLog(
        user_id=current_user.id, filename=file.filename,
        file_size=file_size, status="processing",
        uploaded_at=datetime.now(),
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    def _fail(msg: str, code: int = 400):
        upload.status = "failed"
        upload.error_message = msg
        db.commit()
        db.close()
        raise HTTPException(status_code=code, detail=msg)

    try:
        import pandas as pd
        try:
            if ext == ".csv":
                # 한국어 파일 인코딩 대응 (utf-8 → cp949 폴백)
                try:
                    df = pd.read_csv(io.BytesIO(content))
                except UnicodeDecodeError:
                    df = pd.read_csv(io.BytesIO(content), encoding="cp949")
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            _fail(f"파일 파싱 실패: {str(e)[:200]}")

        # 필수 컬럼 확인
        required_cols = {"공고번호", "공고명", "발주기관", "기초금액"}
        missing = required_cols - set(df.columns)
        if missing:
            _fail(f"필수 컬럼 누락: {', '.join(missing)}")

        total_rows = len(df)
        if total_rows == 0:
            _fail("데이터 행이 없습니다.")

        # 기존 bid_number 집합 (중복 검사)
        existing_numbers = {
            row[0] for row in db.query(BidAnnouncement.bid_number).all()
        }

        inserted = 0
        duplicates = 0
        error_rows: list[dict] = []
        seen_in_file: set[str] = set()
        batch: list[BidAnnouncement] = []

        for idx, row in df.iterrows():
            row_num = idx + 2  # 엑셀 기준: 헤더 1행 + 1-based
            try:
                bid_number = str(row.get("공고번호", "")).strip()
                title = str(row.get("공고명", "")).strip()
                org = str(row.get("발주기관", "")).strip()
                base_raw = row.get("기초금액")

                # 필드 값 검증
                if not bid_number or bid_number == "nan":
                    error_rows.append({"row": row_num, "error": "공고번호 비어 있음"})
                    continue
                if not title or title == "nan":
                    error_rows.append({"row": row_num, "error": "공고명 비어 있음"})
                    continue
                if not org or org == "nan":
                    error_rows.append({"row": row_num, "error": "발주기관 비어 있음"})
                    continue
                if pd.isna(base_raw):
                    error_rows.append({"row": row_num, "error": "기초금액 누락"})
                    continue
                try:
                    base_amount = int(float(base_raw))
                    if base_amount < 0:
                        error_rows.append({"row": row_num, "error": "기초금액 음수"})
                        continue
                except (ValueError, TypeError):
                    error_rows.append({"row": row_num, "error": f"기초금액 숫자 변환 실패: {base_raw}"})
                    continue

                # 중복 검사 (DB + 파일 내)
                if bid_number in existing_numbers or bid_number in seen_in_file:
                    duplicates += 1
                    continue
                seen_in_file.add(bid_number)

                category = str(row.get("카테고리", "용역")).strip() or "용역"
                region = str(row.get("지역", "")).strip() if "지역" in df.columns else None
                if region in ("", "nan"):
                    region = None

                batch.append(BidAnnouncement(
                    source="UPLOAD",
                    bid_number=bid_number,
                    category=category,
                    title=title,
                    ordering_org_name=org,
                    region=region,
                    base_amount=base_amount,
                    announced_at=datetime.now(),
                    status="업로드",
                ))
                inserted += 1
            except Exception as e:
                error_rows.append({"row": row_num, "error": f"예외: {str(e)[:120]}"})

        if batch:
            db.bulk_save_objects(batch)
            invalidate_analysis_cache()

        # 요약 기록
        upload.records_count = inserted
        final_status = "success" if inserted > 0 else ("failed" if error_rows and not duplicates else "partial")
        upload.status = final_status
        upload.error_message = None if not error_rows else f"오류 {len(error_rows)}건"
        db.commit()
        # 세션 close 전에 primitive 값 캡처
        upload_id = upload.id
        db.close()

        summary = {
            "total": total_rows,
            "inserted": inserted,
            "duplicates": duplicates,
            "errors": len(error_rows),
        }
        return {
            "message": f"{inserted}건 등록 / {duplicates}건 중복 / {len(error_rows)}건 오류",
            "upload_id": upload_id,
            "status": final_status,
            "summary": summary,
            "error_rows": error_rows[:50],  # 상위 50건만 반환
        }

    except HTTPException:
        raise
    except Exception as e:
        upload.status = "failed"
        upload.error_message = str(e)[:500]
        db.commit()
        db.close()
        raise HTTPException(status_code=500, detail=f"데이터 처리 중 오류: {str(e)}")


@router.get("/uploads")
def list_uploads(current_user: User = Depends(require_auth)):
    """업로드 이력 조회"""
    db = SessionLocal()
    try:
        uploads = db.query(UploadLog).filter(
            UploadLog.user_id == current_user.id
        ).order_by(UploadLog.uploaded_at.desc()).limit(50).all()
    finally:
        db.close()
    return [{
        "id": u.id, "filename": u.filename,
        "file_size": u.file_size, "records_count": u.records_count,
        "status": u.status, "error_message": u.error_message,
        "uploaded_at": u.uploaded_at.strftime("%Y-%m-%d %H:%M") if u.uploaded_at else None,
    } for u in uploads]
