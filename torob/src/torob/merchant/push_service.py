import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from torob.storage.db import db_manager

logger = logging.getLogger("push_service")


class PushService:
    def __init__(self):
        self.enabled = True

    async def send_to_shop(
        self,
        shop_id: str,
        inquiry_id: str,
        notification_type: str,
        title: str,
        body: str,
        data_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Sends Android-compatible FCM push notification to all active registered devices of a shop.
        Records dispatch attempt, payload, and audit status in push_audit_logs.
        """
        conn = db_manager.get_sqlite()
        cursor = conn.cursor()

        # Find active devices registered for sellers of this shop
        cursor.execute("""
        SELECT d.device_id, d.seller_id, d.fcm_token, d.notifications_enabled
        FROM seller_devices d
        JOIN sellers s ON d.seller_id = s.seller_id
        WHERE s.shop_id = ? AND d.notifications_enabled = 1
        """, (shop_id,))
        devices = cursor.fetchall()

        dispatched_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        serialized_payload = {k: str(v) for k, v in data_payload.items()}

        if not devices:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
            INSERT INTO push_audit_logs 
            (log_id, inquiry_id, shop_id, fcm_token, notification_type, title, body, payload_json, status, error_detail, dispatched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, inquiry_id, shop_id, None, notification_type, title, body,
                json.dumps(serialized_payload), "SKIPPED_NO_DEVICES", "Seller has no registered active push tokens", dispatched_at
            ))
            conn.commit()
            logger.info(f"Push skipped for shop {shop_id}: no active devices registered.")
            return [{
                "log_id": log_id,
                "status": "SKIPPED_NO_DEVICES",
                "notification_type": notification_type
            }]

        results = []
        for dev in devices:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            token = dev["fcm_token"]

            # Format Android FCM message payload
            fcm_payload = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "data": {
                        **serialized_payload,
                        "inquiry_id": str(inquiry_id or ""),
                        "notification_type": str(notification_type),
                        "title": title,
                        "body": body,
                        "click_action": "FLUTTER_NOTIFICATION_CLICK"
                    },
                    "android": {
                        "priority": "HIGH"
                    }
                }
            }

            status = "SIMULATED"
            cursor.execute("""
            INSERT INTO push_audit_logs 
            (log_id, inquiry_id, shop_id, fcm_token, notification_type, title, body, payload_json, status, error_detail, dispatched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, inquiry_id, shop_id, token, notification_type, title, body,
                json.dumps(fcm_payload), status, None, dispatched_at
            ))
            results.append({
                "log_id": log_id,
                "fcm_token": token,
                "status": status,
                "notification_type": notification_type
            })

        conn.commit()
        return results


push_service = PushService()
