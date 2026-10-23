import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Header

from torob.merchant.push_service import push_service
from torob.merchant.working_hours import is_shop_effectively_open
from torob.merchant.scheduler import inquiry_scheduler
from torob.routing.distance import haversine_km
from torob.storage.db import db_manager

router = APIRouter(tags=["Customer Demo & App Parity"])


# --- Schemas ---

class CustomerCreateInquiryRequest(BaseModel):
    shop_id: str
    product_id: Optional[str] = None
    product_title: str
    recorded_price_toman: Optional[int] = 0
    customer_name: Optional[str] = "کاربر ترب"
    customer_phone: Optional[str] = None
    inquiry_type: Optional[str] = "price_and_stock"
    user_note: Optional[str] = None


class CustomerInquiryDto(BaseModel):
    inquiry_id: str
    tracking_code: str
    shop_id: str
    shop_name: str
    product_id: Optional[str] = None
    product_title: str
    recorded_price_toman: int
    offered_price_toman: Optional[int] = None
    is_in_stock: Optional[bool] = None
    status: str
    created_at: str
    expires_at: str
    remaining_seconds: int
    response_notes: Optional[str] = None
    user_note: Optional[str] = None
    customer_name: str
    seen: bool = True


class CustomerProfileDto(BaseModel):
    customer_id: str
    display_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_city: str = "Tehran"
    default_travel_mode: str = "DRIVING"
    plan_tier: str = "free"
    photo_url: Optional[str] = "img/avatar.svg"
    preferences: Dict[str, Any] = {}


class CustomerProfileUpdateDto(BaseModel):
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_city: Optional[str] = None
    default_travel_mode: Optional[str] = None
    photo_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class PlanStopDto(BaseModel):
    stop_id: str
    shop_id: str
    shop_name: str
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    categories: List[str] = []
    done: bool = False


class SavedPlanCreateDto(BaseModel):
    customer_id: Optional[str] = "cust_demo_01"
    plan_id: Optional[str] = None
    title: str
    mode: str = "smart"
    depart_time: Optional[str] = None
    stops: List[PlanStopDto] = []
    plan_data: Optional[Dict[str, Any]] = {}


class SavedPlanDto(BaseModel):
    saved_plan_id: str
    customer_id: str
    plan_id: Optional[str] = None
    title: str
    mode: str
    depart_time: Optional[str] = None
    stops: List[PlanStopDto]
    plan_data: Dict[str, Any] = {}
    created_at: str
    updated_at: str


class StopStatusUpdateDto(BaseModel):
    done: bool


class MapStoreDto(BaseModel):
    shop_id: str
    shop_name: str
    address: str
    phone: Optional[str] = None
    lat: float
    lon: float
    is_open: bool
    open_time: str
    close_time: str
    rating: float = 4.5
    distance_km: Optional[float] = None
    categories: List[str] = []
    active_offers_count: int = 1


class CompareStoresRequest(BaseModel):
    shop_ids: List[str]
    product_id: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None


class CompareStoreItemDto(BaseModel):
    shop_id: str
    shop_name: str
    address: str
    phone: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    price_toman: Optional[int] = None
    stock_confidence: float = 0.85
    travel_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    reliability_score: float = 0.88
    is_open: bool = True
    badges: List[str] = []


class SupportSubmissionRequest(BaseModel):
    customer_id: Optional[str] = "cust_demo_01"
    ticket_type: str = "general_feedback"
    subject: str
    description: str
    contact_info: Optional[str] = None


# =========================================================================
# 1. CUSTOMER INQUIRY INBOX & CREATION
# =========================================================================

@router.get("/customer/inquiries", response_model=List[CustomerInquiryDto])
def list_customer_inquiries(
    customer_id: Optional[str] = Query("cust_demo_01"),
    status: Optional[str] = Query(None)
):
    """
    Retrieve customer's active and answered inquiry inbox with live countdown and merchant responses.
    """
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    now = datetime.utcnow()

    # Query inquiries joined with shop_settings
    query = """
    SELECT i.*, s.shop_name
    FROM inquiries i
    LEFT JOIN shop_settings s ON i.shop_id = s.shop_id
    """
    params = []

    if status:
        st_upper = status.upper()
        if st_upper == "ACTIVE":
            query += " WHERE i.status IN ('ACTIVE', 'created', 'queued', 'delivered')"
        elif st_upper == "ANSWERED":
            query += " WHERE i.status IN ('ANSWERED', 'answered')"
        elif st_upper == "EXPIRED":
            query += " WHERE i.status IN ('EXPIRED', 'expired')"
        else:
            query += " WHERE i.status = ?"
            params.append(st_upper)

    query += " ORDER BY coalesce(i.created_at, i.requested_at) DESC LIMIT 100"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    items = []
    for r in rows:
        created_str = r["created_at"] or r["requested_at"] or now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = r["expires_at"] or r["deadline_at"] or now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if expires_dt.tzinfo is not None:
                expires_dt = expires_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            try:
                expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                expires_dt = now

        rem_secs = max(0, int((expires_dt - now).total_seconds()))
        st = r["status"]
        if st in ("ACTIVE", "created", "queued", "delivered") and rem_secs <= 0:
            st = "EXPIRED"

        tracking = r["tracking_code"] or f"TRK-{r['inquiry_id'][:8].upper()}"
        shop_name = r["shop_name"] or "فروشگاه ترب"

        items.append(CustomerInquiryDto(
            inquiry_id=r["inquiry_id"],
            tracking_code=tracking,
            shop_id=r["shop_id"],
            shop_name=shop_name,
            product_id=r["product_id"],
            product_title=r["product_title"] or "کالای درخواستی",
            recorded_price_toman=int(r["recorded_price_toman"] or 0),
            offered_price_toman=int(r["offered_price_toman"]) if r["offered_price_toman"] is not None else None,
            is_in_stock=bool(r["is_in_stock"]) if r["is_in_stock"] is not None else None,
            status=st,
            created_at=str(created_str),
            expires_at=str(expires_str),
            remaining_seconds=rem_secs,
            response_notes=r["response_notes"],
            user_note=r["user_note"],
            customer_name=r["customer_name"] or "کاربر ترب",
            seen=True
        ))

    return items


@router.post("/customer/inquiries", response_model=CustomerInquiryDto)
async def create_customer_inquiry(payload: CustomerCreateInquiryRequest):
    """
    Customer dispatches a live inquiry to a store.
    Registers SLA timeline in central ledger and pushes high-priority notification to merchant Android app.
    """
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    inquiry_id = f"inq_{uuid.uuid4().hex[:10]}"
    tracking_code = f"TRK-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    expires_iso = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

    scope_json = json.dumps({"type": payload.inquiry_type or "price_and_stock"})
    dedupe_key = f"{payload.shop_id}:{payload.product_id or 'none'}:{inquiry_id}"

    cursor.execute("""
    INSERT INTO inquiries (
        inquiry_id, tracking_code, shop_id, product_id, product_title,
        recorded_price_toman, customer_name, customer_phone, inquiry_type,
        user_note, status, created_at, expires_at, requested_at, deadline_at,
        question_scope_json, dedupe_key, policy_version
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, 'v1')
    """, (
        inquiry_id, tracking_code, payload.shop_id, payload.product_id, payload.product_title,
        payload.recorded_price_toman or 0, payload.customer_name or "کاربر ترب", payload.customer_phone,
        payload.inquiry_type or "price_and_stock", payload.user_note,
        now_iso, expires_iso, now_iso, expires_iso,
        scope_json, dedupe_key
    ))

    # Register SLA timeline
    cursor.execute("""
    INSERT OR REPLACE INTO inquiry_timelines (inquiry_id, registered_at, initial_push_at)
    VALUES (?, ?, ?)
    """, (inquiry_id, now_iso, now_iso))
    conn.commit()

    # Dispatch FCM push to merchant Android devices
    title = "استعلام جدید قیمت و موجودی در ترب"
    body = f"مشتری برای کالای «{payload.product_title}» منتظر پاسخ شماست."
    data = {
        "inquiry_id": inquiry_id,
        "action": "open_inquiry_detail",
        "type": "INITIAL_INQUIRY",
        "product_title": payload.product_title
    }
    await push_service.send_to_shop(
        shop_id=payload.shop_id,
        inquiry_id=inquiry_id,
        notification_type="INITIAL_INQUIRY",
        title=title,
        body=body,
        data_payload=data
    )

    # Get shop name
    cursor.execute("SELECT shop_name FROM shop_settings WHERE shop_id = ?", (payload.shop_id,))
    s_row = cursor.fetchone()
    shop_name = s_row["shop_name"] if s_row else "فروشگاه ترب"

    return CustomerInquiryDto(
        inquiry_id=inquiry_id,
        tracking_code=tracking_code,
        shop_id=payload.shop_id,
        shop_name=shop_name,
        product_id=payload.product_id,
        product_title=payload.product_title,
        recorded_price_toman=payload.recorded_price_toman or 0,
        status="ACTIVE",
        created_at=now_iso,
        expires_at=expires_iso,
        remaining_seconds=600,
        user_note=payload.user_note,
        customer_name=payload.customer_name or "کاربر ترب",
        seen=False
    )


# =========================================================================
# 2. CUSTOMER PROFILE & PREFERENCES
# =========================================================================

@router.get("/customer/profile", response_model=CustomerProfileDto)
def get_customer_profile(customer_id: str = Query("cust_demo_01")):
    """Get persisted customer profile and shopping preferences."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()

    if not row:
        # Create default demo profile
        cursor.execute("""
        INSERT INTO customer_profiles (customer_id, display_name, phone, email, preferred_city, default_travel_mode)
        VALUES (?, 'مهدی رضایی', '09121234567', 'customer@torob.demo', 'Tehran', 'DRIVING')
        """, (customer_id,))
        conn.commit()
        cursor.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
        row = cursor.fetchone()

    prefs = json.loads(row["preferences_json"]) if row["preferences_json"] else {}
    return CustomerProfileDto(
        customer_id=row["customer_id"],
        display_name=row["display_name"],
        phone=row["phone"],
        email=row["email"],
        preferred_city=row["preferred_city"] or "Tehran",
        default_travel_mode=row["default_travel_mode"] or "DRIVING",
        plan_tier=row["plan_tier"] or "free",
        photo_url=row["photo_url"] or "img/avatar.svg",
        preferences=prefs
    )


@router.put("/customer/profile", response_model=CustomerProfileDto)
def update_customer_profile(
    payload: CustomerProfileUpdateDto,
    customer_id: str = Query("cust_demo_01")
):
    """Update persisted customer profile and shopping preferences."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()

    if not row:
        cursor.execute("""
        INSERT INTO customer_profiles (customer_id, display_name) VALUES (?, 'کاربر ترب')
        """, (customer_id,))
        conn.commit()
        cursor.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
        row = cursor.fetchone()

    updates = []
    params = []
    if payload.display_name is not None:
        updates.append("display_name = ?")
        params.append(payload.display_name)
    if payload.phone is not None:
        updates.append("phone = ?")
        params.append(payload.phone)
    if payload.email is not None:
        updates.append("email = ?")
        params.append(payload.email)
    if payload.preferred_city is not None:
        updates.append("preferred_city = ?")
        params.append(payload.preferred_city)
    if payload.default_travel_mode is not None:
        updates.append("default_travel_mode = ?")
        params.append(payload.default_travel_mode)
    if payload.photo_url is not None:
        updates.append("photo_url = ?")
        params.append(payload.photo_url)
    if payload.preferences is not None:
        existing_prefs = json.loads(row["preferences_json"]) if row["preferences_json"] else {}
        existing_prefs.update(payload.preferences)
        updates.append("preferences_json = ?")
        params.append(json.dumps(existing_prefs))

    if updates:
        params.append(customer_id)
        cursor.execute(f"UPDATE customer_profiles SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE customer_id = ?", params)
        conn.commit()

    return get_customer_profile(customer_id)


# =========================================================================
# 3. SAVED SHOPPING PLANS & VISIT CHECKLISTS
# =========================================================================

@router.get("/customer/saved-plans", response_model=List[SavedPlanDto])
def list_saved_plans(customer_id: str = Query("cust_demo_01")):
    """List customer's saved shopping itineraries and stop checklists."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM customer_saved_plans
    WHERE customer_id = ?
    ORDER BY updated_at DESC
    """, (customer_id,))
    rows = cursor.fetchall()

    plans = []
    for r in rows:
        stops_raw = json.loads(r["stops_json"]) if r["stops_json"] else []
        plan_data = json.loads(r["plan_data_json"]) if r["plan_data_json"] else {}
        stops = [PlanStopDto(**s) for s in stops_raw]
        plans.append(SavedPlanDto(
            saved_plan_id=r["saved_plan_id"],
            customer_id=r["customer_id"],
            plan_id=r["plan_id"],
            title=r["title"],
            mode=r["mode"] or "smart",
            depart_time=r["depart_time"],
            stops=stops,
            plan_data=plan_data,
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"])
        ))
    return plans


@router.post("/customer/saved-plans", response_model=SavedPlanDto)
def save_shopping_plan(payload: SavedPlanCreateDto):
    """Save or update a shopping plan itinerary and stop checklist."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    saved_plan_id = f"sp_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    stops_data = [s.model_dump() for s in payload.stops]
    cursor.execute("""
    INSERT INTO customer_saved_plans (
        saved_plan_id, customer_id, plan_id, title, mode, depart_time, stops_json, plan_data_json, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        saved_plan_id, payload.customer_id, payload.plan_id, payload.title, payload.mode,
        payload.depart_time, json.dumps(stops_data), json.dumps(payload.plan_data or {}), now_iso, now_iso
    ))
    conn.commit()

    return SavedPlanDto(
        saved_plan_id=saved_plan_id,
        customer_id=payload.customer_id or "cust_demo_01",
        plan_id=payload.plan_id,
        title=payload.title,
        mode=payload.mode,
        depart_time=payload.depart_time,
        stops=payload.stops,
        plan_data=payload.plan_data or {},
        created_at=now_iso,
        updated_at=now_iso
    )


@router.patch("/customer/saved-plans/{saved_plan_id}/stops/{stop_id}/status")
def toggle_stop_status(
    saved_plan_id: str,
    stop_id: str,
    payload: StopStatusUpdateDto,
    customer_id: str = Query("cust_demo_01")
):
    """Toggle completed checklist flag (done: true/false) on a specific store stop."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM customer_saved_plans
    WHERE saved_plan_id = ? AND customer_id = ?
    """, (saved_plan_id, customer_id))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="برنامهٔ خرید یافت نشد.")

    stops_raw = json.loads(row["stops_json"]) if row["stops_json"] else []
    found = False
    for s in stops_raw:
        if s.get("stop_id") == stop_id or s.get("shop_id") == stop_id:
            s["done"] = payload.done
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="توقف مورد نظر در برنامه یافت نشد.")

    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE customer_saved_plans
    SET stops_json = ?, updated_at = ?
    WHERE saved_plan_id = ?
    """, (json.dumps(stops_raw), now_iso, saved_plan_id))
    conn.commit()

    return {"success": True, "saved_plan_id": saved_plan_id, "stop_id": stop_id, "done": payload.done}


@router.delete("/customer/saved-plans/{saved_plan_id}")
def delete_saved_plan(saved_plan_id: str, customer_id: str = Query("cust_demo_01")):
    """Delete a saved shopping plan."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM customer_saved_plans
    WHERE saved_plan_id = ? AND customer_id = ?
    """, (saved_plan_id, customer_id))
    conn.commit()
    return {"success": True, "message": "برنامه با موفقیت حذف شد."}


# =========================================================================
# 4. MAP STORE DISCOVERY
# =========================================================================

@router.get("/map/stores", response_model=List[MapStoreDto])
def get_map_stores(
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    center_lat: Optional[float] = Query(None),
    center_lon: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(10.0),
    is_open_only: bool = Query(False),
    query: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """
    Search stores with geographic bounding box or center radius for Leaflet map display.
    Calculates dynamic open/closed status based on current Asia/Tehran time.
    """
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    conditions = ["lat IS NOT NULL", "lon IS NOT NULL"]
    params = []

    if min_lat is not None and max_lat is not None:
        conditions.append("lat >= ? AND lat <= ?")
        params.extend([min_lat, max_lat])

    if min_lon is not None and max_lon is not None:
        conditions.append("lon >= ? AND lon <= ?")
        params.extend([min_lon, max_lon])

    if query:
        conditions.append("(shop_name LIKE ? OR address LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    sql = f"""
    SELECT shop_id, shop_name, address, phone, lat, lon, is_open, open_time, close_time, holiday_mode, category_names
    FROM shop_settings
    WHERE {' AND '.join(conditions)}
    LIMIT 300
    """
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    results = []
    for r in rows:
        lat = r["lat"]
        lon = r["lon"]
        dist = None

        if center_lat is not None and center_lon is not None:
            dist = haversine_km(center_lat, center_lon, lat, lon)
            if dist > (radius_km or 10.0):
                continue

        eff_open, _, _ = is_shop_effectively_open(
            is_open_setting=bool(r["is_open"]),
            holiday_mode=bool(r["holiday_mode"]),
            open_time=r["open_time"] or "09:00",
            close_time=r["close_time"] or "21:00"
        )

        if is_open_only and not eff_open:
            continue

        cats = []
        if r["category_names"]:
            try:
                cats = json.loads(r["category_names"]) if isinstance(r["category_names"], str) else []
            except Exception:
                cats = [r["category_names"]]

        results.append(MapStoreDto(
            shop_id=r["shop_id"],
            shop_name=r["shop_name"] or "فروشگاه",
            address=r["address"] or "تهران",
            phone=r["phone"],
            lat=lat,
            lon=lon,
            is_open=eff_open,
            open_time=r["open_time"] or "09:00",
            close_time=r["close_time"] or "21:00",
            rating=4.5,
            distance_km=round(dist, 2) if dist is not None else None,
            categories=cats[:3],
            active_offers_count=1
        ))

    if center_lat is not None and center_lon is not None:
        results.sort(key=lambda s: s.distance_km if s.distance_km is not None else 9999)

    return results[:limit]


# =========================================================================
# 5. CATALOG STORE COMPARISON
# =========================================================================

@router.post("/catalog/compare-stores", response_model=List[CompareStoreItemDto])
def compare_stores_side_by_side(payload: CompareStoresRequest):
    """
    Side-by-side store comparison matrix for customer product decision.
    Compares price, stock confidence, travel time, and reliability rating.
    """
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    items = []
    for sid in payload.shop_ids:
        cursor.execute("""
        SELECT s.shop_id, s.shop_name, s.address, s.phone, s.lat, s.lon, s.is_open, s.open_time, s.close_time, s.holiday_mode,
               r.composite_reliability_score, r.stock_accuracy_score
        FROM shop_settings s
        LEFT JOIN shop_reliability_state r ON s.shop_id = r.shop_id
        WHERE s.shop_id = ?
        """, (sid,))
        row = cursor.fetchone()

        if not row:
            continue

        eff_open, _, _ = is_shop_effectively_open(
            is_open_setting=bool(row["is_open"]),
            holiday_mode=bool(row["holiday_mode"]),
            open_time=row["open_time"] or "09:00",
            close_time=row["close_time"] or "21:00"
        )

        dist_km = None
        travel_min = None
        if payload.origin_lat is not None and payload.origin_lon is not None and row["lat"] and row["lon"]:
            dist_km = round(haversine_km(payload.origin_lat, payload.origin_lon, row["lat"], row["lon"]), 2)
            # Estimate travel time: driving ~25 km/h in urban traffic -> 2.4 min per km + 3 min fixed
            travel_min = int(round(dist_km * 2.4 + 3))

        rel_score = float(row["composite_reliability_score"]) if row["composite_reliability_score"] is not None else 0.85
        stock_conf = float(row["stock_accuracy_score"]) if row["stock_accuracy_score"] is not None else 0.80

        badges = []
        if rel_score >= 0.85:
            badges.append("فروشگاه ممتاز ترب")
        if eff_open:
            badges.append("اکنون باز است")
        if travel_min and travel_min <= 15:
            badges.append("دسترسی سریع")

        items.append(CompareStoreItemDto(
            shop_id=row["shop_id"],
            shop_name=row["shop_name"] or "فروشگاه",
            address=row["address"] or "تهران",
            phone=row["phone"],
            lat=row["lat"],
            lon=row["lon"],
            price_toman=None,
            stock_confidence=round(stock_conf, 2),
            travel_minutes=travel_min,
            distance_km=dist_km,
            reliability_score=round(rel_score, 2),
            is_open=eff_open,
            badges=badges
        ))

    return items


# =========================================================================
# 6. ASSISTANT CHAT SESSIONS
# =========================================================================

@router.get("/assistant/sessions")
def list_assistant_sessions(user_id: str = Query("cust_demo_01")):
    """List historical conversational shopping sessions for user."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT session_id, user_id, detected_intent, created_at, updated_at
    FROM shopping_sessions
    WHERE user_id = ? OR user_id IS NULL
    ORDER BY updated_at DESC
    LIMIT 20
    """, (user_id,))
    rows = cursor.fetchall()

    return [
        {
            "session_id": r["session_id"],
            "user_id": r["user_id"],
            "detected_intent": r["detected_intent"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        }
        for r in rows
    ]


# =========================================================================
# 7. CUSTOMER SUPPORT & FEEDBACK SUBMISSION
# =========================================================================

@router.post("/customer/support")
def submit_customer_support(payload: SupportSubmissionRequest):
    """Submit customer support message, feedback, or dispute report."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    sub_id = f"sub_{uuid.uuid4().hex[:10]}"
    cursor.execute("""
    INSERT INTO support_submissions (
        submission_id, customer_id, ticket_type, subject, description, contact_info
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        sub_id, payload.customer_id, payload.ticket_type,
        payload.subject, payload.description, payload.contact_info
    ))
    conn.commit()

    return {
        "submission_id": sub_id,
        "status": "received",
        "message": "پیام شما با موفقیت ثبت شد و توسط تیم پشتیبانی ترب بررسی خواهد شد."
    }
