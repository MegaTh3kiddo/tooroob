import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from models import PushTokenRegisterRequest, PushPreferenceRequest, PushLogDto, SellerDto
from routers.auth import get_current_seller
from services.push_service import push_service

router = APIRouter(prefix="/seller/push", tags=["Seller Push Notifications"])

@router.post("/register-token")
def register_push_token(
    payload: PushTokenRegisterRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    """Register or update device FCM push token."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if token exists
    cursor.execute("SELECT device_id FROM seller_devices WHERE fcm_token = ?", (payload.fcm_token,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
        UPDATE seller_devices
        SET seller_id = ?, device_model = ?, os_version = ?, app_version = ?,
            notifications_enabled = ?, updated_at = CURRENT_TIMESTAMP
        WHERE fcm_token = ?
        """, (
            seller.seller_id, payload.device_model, payload.os_version, payload.app_version,
            1 if payload.notifications_enabled else 0, payload.fcm_token
        ))
        device_id = row["device_id"]
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
    conn.close()

    return {"success": True, "device_id": device_id, "message": "توکن پوش نوتیفیکیشن با موفقیت ثبت شد"}

@router.put("/preferences")
def update_push_preferences(
    payload: PushPreferenceRequest,
    seller: SellerDto = Depends(get_current_seller)
):
    """Enable or disable push notifications for this seller."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE seller_devices
    SET notifications_enabled = ?, updated_at = CURRENT_TIMESTAMP
    WHERE seller_id = ?
    """, (1 if payload.notifications_enabled else 0, seller.seller_id))
    conn.commit()
    conn.close()

    return {"success": True, "notifications_enabled": payload.notifications_enabled}

@router.post("/test")
async def trigger_test_push(seller: SellerDto = Depends(get_current_seller)):
    """Trigger a real test push notification to seller's active registered devices."""
    results = await push_service.send_to_shop(
        shop_id=seller.shop_id,
        inquiry_id="test_inq_123",
        notification_type="TEST_PING",
        title="تست اتصال نوتیفیکیشن ترب",
        body="ارتباط دستگاه شما با سرور ارسال پوش‌نوتیفیکیشن با موفقیت برقرار شد.",
        data_payload={"action": "test_ping"}
    )
    return {"success": True, "results": results}

@router.get("/logs", response_model=List[PushLogDto])
def get_push_logs(seller: SellerDto = Depends(get_current_seller)):
    """Get audit logs of all notifications sent to this seller's shop."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM push_audit_logs
    WHERE shop_id = ?
    ORDER BY dispatched_at DESC
    LIMIT 50
    """, (seller.shop_id,))
    rows = cursor.fetchall()
    conn.close()

    return [
        PushLogDto(
            log_id=r["log_id"],
            inquiry_id=r["inquiry_id"],
            shop_id=r["shop_id"],
            fcm_token=r["fcm_token"],
            notification_type=r["notification_type"],
            title=r["title"],
            body=r["body"],
            payload_json=r["payload_json"],
            status=r["status"],
            error_detail=r["error_detail"],
            dispatched_at=r["dispatched_at"]
        ) for r in rows
    ]
