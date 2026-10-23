import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header

from torob.merchant.auth import (
    get_current_seller,
    generate_secure_otp,
    verify_otp_code,
    normalize_phone_number,
    is_valid_phone,
    is_iranian_landline
)
from torob.merchant.models import (
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    TokenResponse,
    SellerDto,
    ShopDto,
    ShopUpdateDto,
    ShopChangeRequestCreateDto,
    ShopChangeRequestDto,
    InquiryDto,
    InquiryResponseRequest,
    InquiryResponseDto,
    BatchSyncRequest,
    BatchSyncResponse,
    PushTokenRegisterRequest,
    PushPreferenceRequest,
    PushLogDto,
    MetricsDto
)
from torob.merchant.working_hours import is_shop_effectively_open
from torob.merchant.push_service import push_service
from torob.merchant.metrics import compute_store_metrics
from torob.storage.db import db_manager

router = APIRouter(tags=["Merchant Android API"])


def _format_inquiry_row(row) -> InquiryDto:
    now = datetime.utcnow()
    created_str = row["created_at"] or row["requested_at"] or now.strftime("%Y-%m-%d %H:%M:%S")
    expires_str = row["expires_at"] or row["deadline_at"] or now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        if expires_dt.tzinfo is not None:
            expires_dt = expires_dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        try:
            expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            expires_dt = now

    remaining_seconds = max(0, int((expires_dt - now).total_seconds()))
    status = row["status"]
    if status in ("ACTIVE", "created", "queued", "delivered") and remaining_seconds <= 0:
        status = "EXPIRED"

    keys = row.keys() if hasattr(row, "keys") else []
    tracking_code = row["tracking_code"] if ("tracking_code" in keys and row["tracking_code"]) else f"TRK-{row['inquiry_id'][:8].upper()}"

    rec_price = row["recorded_price_toman"] if "recorded_price_toman" in keys and row["recorded_price_toman"] else 0
    cust_name = row["customer_name"] if "customer_name" in keys and row["customer_name"] else "کاربر ترب"
    inq_type = row["inquiry_type"] if "inquiry_type" in keys and row["inquiry_type"] else "price_and_stock"

    return InquiryDto(
        inquiry_id=row["inquiry_id"],
        tracking_code=tracking_code,
        shop_id=row["shop_id"],
        product_id=row["product_id"] if "product_id" in keys else None,
        product_title=row["product_title"] if "product_title" in keys and row["product_title"] else "کالای درخواستی",
        product_image_url=row["product_image_url"] if "product_image_url" in keys else None,
        category_name=row["category_name"] if "category_name" in keys else None,
        recorded_price_toman=int(rec_price),
        customer_name=cust_name,
        customer_phone=row["customer_phone"] if "customer_phone" in keys else None,
        inquiry_type=inq_type,
        user_note=row["user_note"] if "user_note" in keys else None,
        status=status,
        created_at=str(created_str),
        expires_at=str(expires_str),
        remaining_seconds=remaining_seconds,
        decline_reason=row["decline_reason"] if "decline_reason" in keys else None,
        response_price=int(row["offered_price_toman"]) if ("offered_price_toman" in keys and row["offered_price_toman"] is not None) else None,
        response_in_stock=bool(row["is_in_stock"]) if ("is_in_stock" in keys and row["is_in_stock"] is not None) else None,
        response_notes=row["response_notes"] if "response_notes" in keys else None
    )


# =========================================================================
# 1. AUTHENTICATION ENDPOINTS
# =========================================================================

@router.post("/seller/auth/request-otp", response_model=RequestOtpResponse)
@router.post("/api/seller/auth/request-otp", response_model=RequestOtpResponse, include_in_schema=False)
async def request_otp(payload: RequestOtpRequest):
    phone = normalize_phone_number(payload.phone_number)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره تلفن وارد شده نامعتبر است.")

    is_limited, err_msg, code = generate_secure_otp(phone)
    if is_limited:
        raise HTTPException(status_code=429, detail=err_msg)

    delivery_method = "voice_call" if is_iranian_landline(phone) else "sms"
    return RequestOtpResponse(
        success=True,
        message="کد تایید با موفقیت ارسال شد.",
        demo_otp=code,
        delivery_method=delivery_method
    )


@router.post("/seller/auth/verify-otp", response_model=TokenResponse)
@router.post("/api/seller/auth/verify-otp", response_model=TokenResponse, include_in_schema=False)
def verify_otp(payload: VerifyOtpRequest):
    phone = normalize_phone_number(payload.phone_number)
    code = payload.otp_code.strip()

    if not verify_otp_code(phone, code):
        raise HTTPException(status_code=400, detail="کد تایید وارد شده نادرست یا منقضی شده است.")

    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT seller_id, phone_number, shop_id, full_name, is_active FROM sellers WHERE phone_number = ?",
        (phone,)
    )
    row = cursor.fetchone()

    if not row:
        # Auto-provision new seller linked to default shop
        seller_id = f"seller_{uuid.uuid4().hex[:8]}"
        shop_id = "shop_51d0c1a6edf81ba759726bab"
        full_name = "فروشنده جدید ترب"
        cursor.execute("""
        INSERT INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
        VALUES (?, ?, ?, ?, 1)
        """, (seller_id, phone, shop_id, full_name))
        conn.commit()

        seller_dto = SellerDto(
            seller_id=seller_id,
            phone_number=phone,
            shop_id=shop_id,
            full_name=full_name,
            is_active=True
        )
    else:
        seller_dto = SellerDto(
            seller_id=row["seller_id"],
            phone_number=row["phone_number"],
            shop_id=row["shop_id"],
            full_name=row["full_name"],
            is_active=bool(row["is_active"])
        )

    return TokenResponse(
        access_token=f"token_{seller_dto.seller_id}",
        token_type="bearer",
        seller=seller_dto
    )


@router.get("/seller/auth/me", response_model=SellerDto)
@router.get("/api/seller/auth/me", response_model=SellerDto, include_in_schema=False)
def get_me(seller: SellerDto = Depends(get_current_seller)):
    return seller


# =========================================================================
# 2. SHOP PROFILE & SETTINGS
# =========================================================================

@router.get("/seller/shop", response_model=ShopDto)
@router.get("/api/seller/shop", response_model=ShopDto, include_in_schema=False)
def get_shop_profile(seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, voice_reminders_enabled
    FROM shop_settings
    WHERE shop_id = ?
    """, (seller.shop_id,))
    row = cursor.fetchone()

    if not row:
        cursor.execute("""
        INSERT INTO shop_settings (shop_id, shop_name, address, phone, is_open, voice_reminders_enabled)
        VALUES (?, 'فروشگاه من', 'تهران، خیابان ولیعصر', ?, 1, 1)
        """, (seller.shop_id, seller.phone_number))
        conn.commit()
        cursor.execute("SELECT * FROM shop_settings WHERE shop_id = ?", (seller.shop_id,))
        row = cursor.fetchone()

    is_open_setting = bool(row["is_open"])
    holiday_mode = bool(row["holiday_mode"])
    open_time = row["open_time"] or "09:00"
    close_time = row["close_time"] or "21:00"
    voice_enabled = bool(row["voice_reminders_enabled"]) if "voice_reminders_enabled" in row.keys() else True

    effective_open, within_hours, status_msg = is_shop_effectively_open(
        is_open_setting=is_open_setting,
        holiday_mode=holiday_mode,
        open_time=open_time,
        close_time=close_time
    )

    return ShopDto(
        shop_id=row["shop_id"],
        shop_name=row["shop_name"] or "فروشگاه",
        address=row["address"] or "تهران",
        phone=row["phone"] or seller.phone_number,
        is_open=effective_open,
        open_time=open_time,
        close_time=close_time,
        accept_inquiries=bool(row["accept_inquiries"]),
        holiday_mode=holiday_mode,
        manual_is_open=is_open_setting,
        is_within_working_hours=within_hours,
        status_message=status_msg,
        voice_reminders_enabled=voice_enabled
    )


@router.put("/seller/shop", response_model=ShopDto)
@router.put("/api/seller/shop", response_model=ShopDto, include_in_schema=False)
def update_shop_profile(payload: ShopUpdateDto, seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shop_settings WHERE shop_id = ?", (seller.shop_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO shop_settings (shop_id, shop_name) VALUES (?, 'فروشگاه')", (seller.shop_id,))
        conn.commit()
        cursor.execute("SELECT * FROM shop_settings WHERE shop_id = ?", (seller.shop_id,))
        row = cursor.fetchone()

    # Security rule from merchant spec: General info (name, address, hours) requires change request
    has_general_info_change = False
    if payload.shop_name is not None and payload.shop_name != row["shop_name"]:
        has_general_info_change = True
    if payload.phone is not None and payload.phone != row["phone"]:
        has_general_info_change = True
    if payload.address is not None and payload.address != row["address"]:
        has_general_info_change = True
    if payload.open_time is not None and payload.open_time != row["open_time"]:
        has_general_info_change = True
    if payload.close_time is not None and payload.close_time != row["close_time"]:
        has_general_info_change = True

    if has_general_info_change:
        raise HTTPException(
            status_code=400,
            detail="تغییر مشخصات اصلی فروشگاه (نام، آدرس، تلفن و ساعات کاری) مستلزم ثبت درخواست تغییر در بخش پشتیبانی است."
        )

    # Operational settings can be updated directly
    updates = []
    params = []
    if payload.is_open is not None:
        updates.append("is_open = ?")
        params.append(1 if payload.is_open else 0)
    if payload.accept_inquiries is not None:
        updates.append("accept_inquiries = ?")
        params.append(1 if payload.accept_inquiries else 0)
    if payload.holiday_mode is not None:
        updates.append("holiday_mode = ?")
        params.append(1 if payload.holiday_mode else 0)
    if payload.voice_reminders_enabled is not None:
        updates.append("voice_reminders_enabled = ?")
        params.append(1 if payload.voice_reminders_enabled else 0)

    if updates:
        params.append(seller.shop_id)
        cursor.execute(f"UPDATE shop_settings SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE shop_id = ?", params)
        conn.commit()

    return get_shop_profile(seller)


@router.post("/seller/shop/toggle-status", response_model=ShopDto)
@router.post("/api/seller/shop/toggle-status", response_model=ShopDto, include_in_schema=False)
def toggle_shop_status(seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT is_open FROM shop_settings WHERE shop_id = ?", (seller.shop_id,))
    row = cursor.fetchone()
    current_status = bool(row["is_open"]) if row else True
    new_status = not current_status

    cursor.execute(
        "UPDATE shop_settings SET is_open = ?, updated_at = CURRENT_TIMESTAMP WHERE shop_id = ?",
        (1 if new_status else 0, seller.shop_id)
    )
    conn.commit()
    return get_shop_profile(seller)


@router.post("/seller/shop/change-requests", response_model=ShopChangeRequestDto)
@router.post("/api/seller/shop/change-requests", response_model=ShopChangeRequestDto, include_in_schema=False)
def submit_change_request(payload: ShopChangeRequestCreateDto, seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    req_id = f"req_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO shop_change_requests (
        request_id, shop_id, seller_id, requested_shop_name, requested_phone,
        requested_address, requested_open_time, requested_close_time, reason, status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
    """, (
        req_id, seller.shop_id, seller.seller_id,
        payload.requested_shop_name, payload.requested_phone, payload.requested_address,
        payload.requested_open_time, payload.requested_close_time, payload.reason, now_iso
    ))
    conn.commit()

    return ShopChangeRequestDto(
        request_id=req_id,
        shop_id=seller.shop_id,
        seller_id=seller.seller_id,
        requested_shop_name=payload.requested_shop_name,
        requested_phone=payload.requested_phone,
        requested_address=payload.requested_address,
        requested_open_time=payload.requested_open_time,
        requested_close_time=payload.requested_close_time,
        reason=payload.reason,
        status="PENDING",
        created_at=now_iso
    )


@router.get("/seller/shop/change-requests/latest", response_model=ShopChangeRequestDto)
@router.get("/api/seller/shop/change-requests/latest", response_model=ShopChangeRequestDto, include_in_schema=False)
def get_latest_change_request(seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM shop_change_requests
    WHERE shop_id = ?
    ORDER BY created_at DESC LIMIT 1
    """, (seller.shop_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="هیچ درخواست تغییری ثبت نشده است.")

    return ShopChangeRequestDto(
        request_id=row["request_id"],
        shop_id=row["shop_id"],
        seller_id=row["seller_id"],
        requested_shop_name=row["requested_shop_name"],
        requested_phone=row["requested_phone"],
        requested_address=row["requested_address"],
        requested_open_time=row["requested_open_time"],
        requested_close_time=row["requested_close_time"],
        reason=row["reason"],
        status=row["status"],
        created_at=str(row["created_at"]),
        reviewed_at=str(row["reviewed_at"]) if row["reviewed_at"] else None,
        review_notes=row["review_notes"]
    )


# =========================================================================
# 3. MERCHANT INQUIRIES & RESPONSES
# =========================================================================

@router.get("/seller/inquiries", response_model=List[InquiryDto])
@router.get("/api/seller/inquiries", response_model=List[InquiryDto], include_in_schema=False)
def list_inquiries(
    status: Optional[str] = Query(None, description="Filter: ACTIVE, ANSWERED, OUT_OF_STOCK, DECLINED, EXPIRED, or HISTORY"),
    seller: SellerDto = Depends(get_current_seller)
):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    # Auto-expire past-due items
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE inquiries
    SET status = 'EXPIRED'
    WHERE status IN ('ACTIVE', 'created', 'queued', 'delivered')
      AND (datetime(expires_at) <= datetime(?) OR datetime(deadline_at) <= datetime(?))
    """, (now_iso, now_iso))
    conn.commit()

    if status:
        st_upper = status.upper()
        if st_upper == "HISTORY":
            cursor.execute("""
            SELECT * FROM inquiries
            WHERE shop_id = ? AND status NOT IN ('ACTIVE', 'created', 'queued', 'delivered')
            ORDER BY created_at DESC
            """, (seller.shop_id,))
        elif st_upper == "ACTIVE":
            cursor.execute("""
            SELECT * FROM inquiries
            WHERE shop_id = ? AND status IN ('ACTIVE', 'created', 'queued', 'delivered')
            ORDER BY created_at DESC
            """, (seller.shop_id,))
        else:
            cursor.execute("""
            SELECT * FROM inquiries
            WHERE shop_id = ? AND status = ?
            ORDER BY created_at DESC
            """, (seller.shop_id, st_upper))
    else:
        cursor.execute("""
        SELECT * FROM inquiries
        WHERE shop_id = ?
        ORDER BY created_at DESC
        """, (seller.shop_id,))

    rows = cursor.fetchall()
    return [_format_inquiry_row(r) for r in rows]


@router.get("/seller/inquiries/{inquiry_id}", response_model=InquiryDto)
@router.get("/api/seller/inquiries/{inquiry_id}", response_model=InquiryDto, include_in_schema=False)
def get_inquiry_detail(inquiry_id: str, seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (inquiry_id, seller.shop_id))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="استعلام یافت نشد.")

    return _format_inquiry_row(row)


@router.post("/seller/inquiries/{inquiry_id}/respond", response_model=InquiryResponseDto)
@router.post("/api/seller/inquiries/{inquiry_id}/respond", response_model=InquiryResponseDto, include_in_schema=False)
def respond_to_inquiry(
    inquiry_id: str,
    payload: InquiryResponseRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    # 1. Idempotency Check: Has this client_response_id already been recorded?
    cursor.execute("SELECT * FROM inquiry_responses WHERE client_response_id = ?", (payload.client_response_id,))
    existing = cursor.fetchone()
    if existing:
        existing_keys = existing.keys() if hasattr(existing, "keys") else []
        stock_cnt = existing["stock_count"] if "stock_count" in existing_keys and existing["stock_count"] is not None else (1 if existing["is_in_stock"] else 0)
        return InquiryResponseDto(
            response_id=existing["response_id"],
            client_response_id=existing["client_response_id"],
            inquiry_id=existing["inquiry_id"],
            offered_price_toman=existing["offered_price_toman"],
            is_in_stock=bool(existing["is_in_stock"]),
            stock_count=stock_cnt,
            notes=existing["notes"],
            status=existing["status"] if "status" in existing_keys else None,
            decline_reason=existing["decline_reason"] if "decline_reason" in existing_keys else None,
            submitted_at=existing["submitted_at"],
            received_at=existing["received_at"],
            is_duplicate=True
        )

    # 2. Check inquiry validity
    cursor.execute("SELECT * FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (inquiry_id, seller.shop_id))
    inquiry = cursor.fetchone()
    if not inquiry:
        raise HTTPException(status_code=404, detail="استعلام معتبر یافت نشد.")

    if inquiry["status"] == "EXPIRED":
        raise HTTPException(status_code=400, detail="مهلت پاسخ‌گویی به این استعلام به پایان رسیده و منقضی شده است.")

    # 3. Determine target status & preserve exact stock_count
    target_status = payload.status
    decline_reason = payload.decline_reason

    # CRITICAL: Preserve exact count, never replacing 0 with 1
    if payload.stock_count is not None:
        stock_count = payload.stock_count
    else:
        stock_count = 1 if payload.is_in_stock else 0

    if not target_status:
        if payload.notes and ("رد استعلام" in payload.notes):
            target_status = "DECLINED"
        elif not payload.is_in_stock or stock_count == 0:
            target_status = "OUT_OF_STOCK"
        else:
            target_status = "ANSWERED"

    if target_status == "DECLINED" and not decline_reason:
        decline_reason = payload.notes

    # 4. Save response in operational table
    response_id = f"resp_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    scope_json = json.dumps({"inquiry_id": inquiry_id, "shop_id": seller.shop_id})
    answer_json = json.dumps({
        "price": payload.offered_price_toman,
        "is_in_stock": payload.is_in_stock,
        "stock_count": stock_count,
        "notes": payload.notes
    })

    cursor.execute("""
    INSERT INTO inquiry_responses (
        response_id, client_response_id, inquiry_id, seller_id, shop_id,
        offered_price_toman, is_in_stock, stock_count, notes, status, decline_reason, submitted_at, received_at,
        actor_id, ingested_at, scope_json, answer_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        response_id, payload.client_response_id, inquiry_id, seller.seller_id, seller.shop_id,
        payload.offered_price_toman, 1 if payload.is_in_stock else 0, stock_count,
        payload.notes, target_status, decline_reason, payload.submitted_at, now_iso,
        seller.seller_id, now_iso, scope_json, answer_json
    ))

    # 5. Update inquiry
    cursor.execute("""
    UPDATE inquiries
    SET status = ?, decline_reason = ?, offered_price_toman = ?, is_in_stock = ?, response_notes = ?
    WHERE inquiry_id = ?
    """, (
        target_status, decline_reason, payload.offered_price_toman,
        1 if payload.is_in_stock else 0, payload.notes, inquiry_id
    ))

    # 6. Update timeline
    cursor.execute("SELECT registered_at, initial_push_at FROM inquiry_timelines WHERE inquiry_id = ?", (inquiry_id,))
    t_row = cursor.fetchone()
    response_time_seconds = None
    if t_row:
        ref_str = t_row["registered_at"] or t_row["initial_push_at"]
        if ref_str:
            try:
                ref_dt = datetime.strptime(ref_str, "%Y-%m-%d %H:%M:%S")
                now_dt = datetime.strptime(now_iso, "%Y-%m-%d %H:%M:%S")
                response_time_seconds = max(1, int((now_dt - ref_dt).total_seconds()))
            except Exception:
                pass

    cursor.execute("""
    UPDATE inquiry_timelines
    SET seller_responded_at = ?, response_time_seconds = ?
    WHERE inquiry_id = ?
    """, (now_iso, response_time_seconds, inquiry_id))

    # 7. Append evidence event into central evidence ledger
    ev_stock_id = f"ev_resp_{uuid.uuid4().hex[:10]}"
    cursor.execute("""
    INSERT INTO evidence_events
    (event_id, event_type, scope_json, observed_at, ingested_at, source_code, actor_id, payload_json)
    VALUES (?, 'seller_response_stock', ?, ?, ?, 'merchant_app', ?, ?)
    """, (
        ev_stock_id,
        json.dumps({
            "shop_id": seller.shop_id,
            "inquiry_id": inquiry_id,
            "product_id": inquiry["product_id"] if "product_id" in inquiry.keys() else None
        }),
        now_iso,
        now_iso,
        seller.seller_id,
        json.dumps({
            "in_stock": payload.is_in_stock,
            "stock_count": stock_count,
            "status": target_status,
            "notes": payload.notes
        })
    ))

    if payload.offered_price_toman > 0:
        ev_price_id = f"ev_price_{uuid.uuid4().hex[:10]}"
        cursor.execute("""
        INSERT INTO evidence_events
        (event_id, event_type, scope_json, observed_at, ingested_at, source_code, actor_id, payload_json)
        VALUES (?, 'seller_response_price', ?, ?, ?, 'merchant_app', ?, ?)
        """, (
            ev_price_id,
            json.dumps({
                "shop_id": seller.shop_id,
                "inquiry_id": inquiry_id,
                "product_id": inquiry["product_id"] if "product_id" in inquiry.keys() else None
            }),
            now_iso,
            now_iso,
            seller.seller_id,
            json.dumps({
                "price_toman": payload.offered_price_toman,
                "status": target_status
            })
        ))

    conn.commit()

    return InquiryResponseDto(
        response_id=response_id,
        client_response_id=payload.client_response_id,
        inquiry_id=inquiry_id,
        offered_price_toman=payload.offered_price_toman,
        is_in_stock=payload.is_in_stock,
        stock_count=stock_count,
        notes=payload.notes,
        status=target_status,
        decline_reason=decline_reason,
        submitted_at=payload.submitted_at,
        received_at=now_iso,
        is_duplicate=False
    )


@router.post("/seller/inquiries/batch-sync", response_model=BatchSyncResponse)
@router.post("/api/seller/inquiries/batch-sync", response_model=BatchSyncResponse, include_in_schema=False)
@router.post("/seller/sync/batch-responses", response_model=BatchSyncResponse)
@router.post("/api/seller/sync/batch-responses", response_model=BatchSyncResponse, include_in_schema=False)
def batch_sync_responses(
    payload: BatchSyncRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    """
    Offline sync handler: Safely processes responses queued when mobile device was offline.
    Uses client_response_id for complete deduplication and idempotency.
    """
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    results: List[InquiryResponseDto] = []
    synced_count = 0
    duplicate_count = 0
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for item in payload.items:
        # Check idempotency
        cursor.execute("SELECT * FROM inquiry_responses WHERE client_response_id = ?", (item.client_response_id,))
        existing = cursor.fetchone()
        if existing:
            duplicate_count += 1
            existing_keys = existing.keys() if hasattr(existing, "keys") else []
            stock_cnt = existing["stock_count"] if "stock_count" in existing_keys and existing["stock_count"] is not None else (1 if existing["is_in_stock"] else 0)
            results.append(InquiryResponseDto(
                response_id=existing["response_id"],
                client_response_id=existing["client_response_id"],
                inquiry_id=existing["inquiry_id"],
                offered_price_toman=existing["offered_price_toman"],
                is_in_stock=bool(existing["is_in_stock"]),
                stock_count=stock_cnt,
                notes=existing["notes"],
                status=existing["status"] if "status" in existing_keys else None,
                decline_reason=existing["decline_reason"] if "decline_reason" in existing_keys else None,
                submitted_at=existing["submitted_at"],
                received_at=existing["received_at"],
                is_duplicate=True
            ))
            continue

        cursor.execute("SELECT * FROM inquiries WHERE inquiry_id = ? AND shop_id = ?", (item.inquiry_id, seller.shop_id))
        inq_row = cursor.fetchone()
        if not inq_row:
            continue

        target_status = item.status
        decline_reason = item.decline_reason

        # Preserve exact count
        if item.stock_count is not None:
            stock_count = item.stock_count
        else:
            stock_count = 1 if item.is_in_stock else 0

        if not target_status:
            if item.notes and ("رد استعلام" in item.notes):
                target_status = "DECLINED"
            elif not item.is_in_stock or stock_count == 0:
                target_status = "OUT_OF_STOCK"
            else:
                target_status = "ANSWERED"

        if target_status == "DECLINED" and not decline_reason:
            decline_reason = item.notes

        resp_id = f"resp_{uuid.uuid4().hex[:10]}"
        scope_json = json.dumps({"inquiry_id": item.inquiry_id, "shop_id": seller.shop_id})
        answer_json = json.dumps({
            "price": item.offered_price_toman,
            "is_in_stock": item.is_in_stock,
            "stock_count": stock_count,
            "notes": item.notes
        })

        cursor.execute("""
        INSERT INTO inquiry_responses (
            response_id, client_response_id, inquiry_id, seller_id, shop_id,
            offered_price_toman, is_in_stock, stock_count, notes, status, decline_reason, submitted_at, received_at,
            actor_id, ingested_at, scope_json, answer_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resp_id, item.client_response_id, item.inquiry_id, seller.seller_id, seller.shop_id,
            item.offered_price_toman, 1 if item.is_in_stock else 0, stock_count,
            item.notes, target_status, decline_reason, item.submitted_at, now_iso,
            seller.seller_id, now_iso, scope_json, answer_json
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
            stock_count=stock_count,
            notes=item.notes,
            status=target_status,
            decline_reason=decline_reason,
            submitted_at=item.submitted_at,
            received_at=now_iso,
            is_duplicate=False
        ))

    conn.commit()
    return BatchSyncResponse(
        total_processed=len(payload.items),
        synced_count=synced_count,
        duplicate_count=duplicate_count,
        results=results
    )


# =========================================================================
# 4. PUSH NOTIFICATION TOKEN REGISTRATION
# =========================================================================

@router.post("/seller/push/register-token")
@router.post("/api/seller/push/register-token", include_in_schema=False)
def register_push_token(
    payload: PushTokenRegisterRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    cursor.execute("SELECT device_id FROM seller_devices WHERE fcm_token = ?", (payload.fcm_token,))
    row = cursor.fetchone()

    if row:
        device_id = row["device_id"]
        cursor.execute("""
        UPDATE seller_devices
        SET seller_id = ?, device_model = ?, os_version = ?, app_version = ?,
            notifications_enabled = ?, updated_at = CURRENT_TIMESTAMP
        WHERE fcm_token = ?
        """, (
            seller.seller_id, payload.device_model, payload.os_version, payload.app_version,
            1 if payload.notifications_enabled else 0, payload.fcm_token
        ))
    else:
        device_id = f"dev_{uuid.uuid4().hex[:10]}"
        cursor.execute("""
        INSERT INTO seller_devices (
            device_id, seller_id, fcm_token, device_model, os_version, app_version, notifications_enabled
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            device_id, seller.seller_id, payload.fcm_token, payload.device_model,
            payload.os_version, payload.app_version, 1 if payload.notifications_enabled else 0
        ))

    conn.commit()
    return {"success": True, "device_id": device_id, "message": "توکن پوش‌نوتیفیکیشن با موفقیت ثبت شد."}


@router.put("/seller/push/preferences")
@router.put("/api/seller/push/preferences", include_in_schema=False)
def update_push_preferences(
    payload: PushPreferenceRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE seller_devices
    SET notifications_enabled = ?, updated_at = CURRENT_TIMESTAMP
    WHERE seller_id = ?
    """, (1 if payload.notifications_enabled else 0, seller.seller_id))
    conn.commit()
    return {"success": True, "notifications_enabled": payload.notifications_enabled}


@router.get("/seller/push/logs", response_model=List[PushLogDto])
@router.get("/api/seller/push/logs", response_model=List[PushLogDto], include_in_schema=False)
def get_push_logs(seller: SellerDto = Depends(get_current_seller)):
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM push_audit_logs
    WHERE shop_id = ?
    ORDER BY dispatched_at DESC
    LIMIT 50
    """, (seller.shop_id,))
    rows = cursor.fetchall()
    return [
        PushLogDto(
            log_id=r["log_id"],
            inquiry_id=r["inquiry_id"],
            shop_id=r["shop_id"],
            fcm_token=r["fcm_token"],
            notification_type=r["notification_type"],
            title=r["title"],
            body=r["body"],
            status=r["status"],
            error_detail=r["error_detail"],
            dispatched_at=str(r["dispatched_at"])
        )
        for r in rows
    ]


# =========================================================================
# 5. METRICS & PERFORMANCE
# =========================================================================

@router.get("/seller/metrics", response_model=MetricsDto)
@router.get("/api/seller/metrics", response_model=MetricsDto, include_in_schema=False)
def get_store_metrics(seller: SellerDto = Depends(get_current_seller)):
    return compute_store_metrics(seller.shop_id)
