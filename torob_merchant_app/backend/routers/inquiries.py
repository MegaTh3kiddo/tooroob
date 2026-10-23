import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from database import get_db
from models import (
    InquiryDto,
    InquiryResponseRequest,
    InquiryResponseDto,
    BatchSyncRequest,
    BatchSyncResponse,
    SellerDto,
)
from routers.auth import get_current_seller

router = APIRouter(prefix="/seller/inquiries", tags=["Seller Inquiries"])

def _format_inquiry_row(row) -> InquiryDto:
    now = datetime.utcnow()
    created_str = row["created_at"]
    expires_str = row["expires_at"]

    try:
        expires_dt = datetime.fromisoformat(expires_str.replace("Z", ""))
    except Exception:
        expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")

    remaining_seconds = max(0, int((expires_dt - now).total_seconds()))

    status = row["status"]
    if status == "ACTIVE" and remaining_seconds <= 0:
        status = "EXPIRED"

    keys = row.keys() if hasattr(row, "keys") else []

    return InquiryDto(
        inquiry_id=row["inquiry_id"],
        tracking_code=row["tracking_code"],
        shop_id=row["shop_id"],
        product_id=row["product_id"],
        product_title=row["product_title"],
        product_image_url=row["product_image_url"],
        category_name=row["category_name"],
        recorded_price_toman=row["recorded_price_toman"],
        customer_name=row["customer_name"],
        customer_phone=row["customer_phone"],
        inquiry_type=row["inquiry_type"],
        user_note=row["user_note"],
        status=status,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        remaining_seconds=remaining_seconds,
        decline_reason=row["decline_reason"] if "decline_reason" in keys else None,
        response_price=row["offered_price_toman"] if "offered_price_toman" in keys else None,
        response_in_stock=bool(row["is_in_stock"]) if ("is_in_stock" in keys and row["is_in_stock"] is not None) else None,
        response_notes=row["response_notes"] if "response_notes" in keys else None
    )

@router.get("", response_model=List[InquiryDto])
def list_inquiries(
    status: Optional[str] = Query(None, description="Filter: ACTIVE, ANSWERED, OUT_OF_STOCK, DECLINED, EXPIRED, or HISTORY"),
    seller: SellerDto = Depends(get_current_seller)
):
    conn = get_db()
    cursor = conn.cursor()

    # Auto-expire any past-due active inquiries on-the-fly
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE inquiries
    SET status = 'EXPIRED'
    WHERE status = 'ACTIVE' AND datetime(expires_at) <= datetime(?)
    """, (now_iso,))
    conn.commit()

    if status:
        if status.upper() == "HISTORY":
            cursor.execute("""
            SELECT * FROM inquiries
            WHERE shop_id = ? AND status != 'ACTIVE'
            ORDER BY created_at DESC
            """, (seller.shop_id,))
        else:
            cursor.execute("""
            SELECT * FROM inquiries
            WHERE shop_id = ? AND status = ?
            ORDER BY created_at DESC
            """, (seller.shop_id, status.upper()))
    else:
        cursor.execute("""
        SELECT * FROM inquiries
        WHERE shop_id = ?
        ORDER BY created_at DESC
        """, (seller.shop_id,))

    rows = cursor.fetchall()
    conn.close()

    return [_format_inquiry_row(r) for r in rows]

@router.get("/{inquiry_id}", response_model=InquiryDto)
def get_inquiry_detail(inquiry_id: str, seller: SellerDto = Depends(get_current_seller)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (inquiry_id, seller.shop_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="استعلام یافت نشد")

    return _format_inquiry_row(row)

@router.post("/{inquiry_id}/respond", response_model=InquiryResponseDto)
def respond_to_inquiry(
    inquiry_id: str,
    payload: InquiryResponseRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    conn = get_db()
    cursor = conn.cursor()

    # 1. Check idempotency: Has this client_response_id already been recorded?
    cursor.execute("""
    SELECT * FROM inquiry_responses WHERE client_response_id = ?
    """, (payload.client_response_id,))
    existing_resp = cursor.fetchone()
    if existing_resp:
        conn.close()
        existing_keys = existing_resp.keys() if hasattr(existing_resp, "keys") else []
        return InquiryResponseDto(
            response_id=existing_resp["response_id"],
            client_response_id=existing_resp["client_response_id"],
            inquiry_id=existing_resp["inquiry_id"],
            offered_price_toman=existing_resp["offered_price_toman"],
            is_in_stock=bool(existing_resp["is_in_stock"]),
            stock_count=existing_resp["stock_count"] if "stock_count" in existing_keys else 1,
            notes=existing_resp["notes"],
            status=existing_resp["status"] if "status" in existing_keys else None,
            decline_reason=existing_resp["decline_reason"] if "decline_reason" in existing_keys else None,
            submitted_at=existing_resp["submitted_at"],
            received_at=existing_resp["received_at"],
            is_duplicate=True
        )

    # 2. Check inquiry validity
    cursor.execute("SELECT * FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (inquiry_id, seller.shop_id))
    inquiry = cursor.fetchone()
    if not inquiry:
        conn.close()
        raise HTTPException(status_code=404, detail="استعلام معتبر یافت نشد")

    if inquiry["status"] == "EXPIRED":
        conn.close()
        raise HTTPException(status_code=400, detail="مهلت پاسخ‌گویی به این استعلام به پایان رسیده و منقضی شده است")

    # Determine status & decline reason
    target_status = payload.status
    decline_reason = payload.decline_reason

    if not target_status:
        if payload.notes and (payload.notes.startswith("رد استعلام") or "رد استعلام" in payload.notes):
            target_status = "DECLINED"
        elif not payload.is_in_stock:
            target_status = "OUT_OF_STOCK"
        else:
            target_status = "ANSWERED"

    if target_status == "DECLINED" and not decline_reason:
        decline_reason = payload.notes

    # 3. Save response
    response_id = f"resp_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO inquiry_responses (
        response_id, client_response_id, inquiry_id, seller_id, shop_id,
        offered_price_toman, is_in_stock, stock_count, notes, status, decline_reason, submitted_at, received_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        response_id, payload.client_response_id, inquiry_id, seller.seller_id, seller.shop_id,
        payload.offered_price_toman, 1 if payload.is_in_stock else 0, payload.stock_count or 1, payload.notes,
        target_status, decline_reason, payload.submitted_at, now_iso
    ))

    # 4. Mark inquiry with status and response details
    cursor.execute("""
    UPDATE inquiries
    SET status = ?, decline_reason = ?, offered_price_toman = ?, is_in_stock = ?, response_notes = ?
    WHERE inquiry_id = ?
    """, (
        target_status, decline_reason, payload.offered_price_toman,
        1 if payload.is_in_stock else 0, payload.notes, inquiry_id
    ))

    # 5. Update timeline and calculate response time
    cursor.execute("SELECT registered_at FROM inquiry_timelines WHERE inquiry_id = ?", (inquiry_id,))
    timeline_row = cursor.fetchone()
    response_time_seconds = None
    if timeline_row and timeline_row["registered_at"]:
        try:
            reg_dt = datetime.strptime(timeline_row["registered_at"], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.strptime(now_iso, "%Y-%m-%d %H:%M:%S")
            response_time_seconds = max(1, int((now_dt - reg_dt).total_seconds()))
        except Exception:
            pass

    cursor.execute("""
    UPDATE inquiry_timelines
    SET seller_responded_at = ?, response_time_seconds = ?
    WHERE inquiry_id = ?
    """, (now_iso, response_time_seconds, inquiry_id))

    conn.commit()
    conn.close()

    return InquiryResponseDto(
        response_id=response_id,
        client_response_id=payload.client_response_id,
        inquiry_id=inquiry_id,
        offered_price_toman=payload.offered_price_toman,
        is_in_stock=payload.is_in_stock,
        stock_count=payload.stock_count or 1,
        notes=payload.notes,
        status=target_status,
        decline_reason=decline_reason,
        submitted_at=payload.submitted_at,
        received_at=now_iso,
        is_duplicate=False
    )

@router.post("/batch-sync", response_model=BatchSyncResponse)
@router.post("/batch-responses", response_model=BatchSyncResponse)
def batch_sync_responses(
    payload: BatchSyncRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    """
    Offline sync endpoint: Processes queued responses submitted when device was disconnected.
    Safely skips duplicate client_response_ids and records all new responses.
    """
    conn = get_db()
    cursor = conn.cursor()
    results: List[InquiryResponseDto] = []
    synced_count = 0
    duplicate_count = 0

    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for item in payload.items:
        # Check if already processed
        cursor.execute("SELECT * FROM inquiry_responses WHERE client_response_id = ?", (item.client_response_id,))
        existing = cursor.fetchone()
        if existing:
            duplicate_count += 1
            existing_keys = existing.keys() if hasattr(existing, "keys") else []
            results.append(InquiryResponseDto(
                response_id=existing["response_id"],
                client_response_id=existing["client_response_id"],
                inquiry_id=existing["inquiry_id"],
                offered_price_toman=existing["offered_price_toman"],
                is_in_stock=bool(existing["is_in_stock"]),
                stock_count=existing["stock_count"] if "stock_count" in existing_keys else 1,
                notes=existing["notes"],
                status=existing["status"] if "status" in existing_keys else None,
                decline_reason=existing["decline_reason"] if "decline_reason" in existing_keys else None,
                submitted_at=existing["submitted_at"],
                received_at=existing["received_at"],
                is_duplicate=True
            ))
            continue

        # Check inquiry
        cursor.execute("SELECT status FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (item.inquiry_id, seller.shop_id))
        inq_row = cursor.fetchone()
        if not inq_row:
            continue

        # Determine status & decline reason
        target_status = item.status
        decline_reason = item.decline_reason

        if not target_status:
            if item.notes and (item.notes.startswith("رد استعلام") or "رد استعلام" in item.notes):
                target_status = "DECLINED"
            elif not item.is_in_stock:
                target_status = "OUT_OF_STOCK"
            else:
                target_status = "ANSWERED"

        if target_status == "DECLINED" and not decline_reason:
            decline_reason = item.notes

        resp_id = f"resp_{uuid.uuid4().hex[:10]}"
        cursor.execute("""
        INSERT INTO inquiry_responses (
            response_id, client_response_id, inquiry_id, seller_id, shop_id,
            offered_price_toman, is_in_stock, stock_count, notes, status, decline_reason, submitted_at, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resp_id, item.client_response_id, item.inquiry_id, seller.seller_id, seller.shop_id,
            item.offered_price_toman, 1 if item.is_in_stock else 0, item.stock_count or 1, item.notes,
            target_status, decline_reason, item.submitted_at, now_iso
        ))

        cursor.execute("""
        UPDATE inquiries
        SET status = ?, decline_reason = ?, offered_price_toman = ?, is_in_stock = ?, response_notes = ?
        WHERE inquiry_id = ?
        """, (
            target_status, decline_reason, item.offered_price_toman,
            1 if item.is_in_stock else 0, item.notes, item.inquiry_id
        ))
        cursor.execute("UPDATE inquiry_timelines SET seller_responded_at = ? WHERE inquiry_id = ?", (now_iso, item.inquiry_id))

        synced_count += 1
        results.append(InquiryResponseDto(
            response_id=resp_id,
            client_response_id=item.client_response_id,
            inquiry_id=item.inquiry_id,
            offered_price_toman=item.offered_price_toman,
            is_in_stock=item.is_in_stock,
            stock_count=item.stock_count or 1,
            notes=item.notes,
            status=target_status,
            decline_reason=decline_reason,
            submitted_at=item.submitted_at,
            received_at=now_iso,
            is_duplicate=False
        ))

    conn.commit()
    conn.close()

    return BatchSyncResponse(
        total_processed=len(payload.items),
        synced_count=synced_count,
        duplicate_count=duplicate_count,
        results=results
    )
