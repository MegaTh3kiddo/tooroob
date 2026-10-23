import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
from database import get_db
from config import settings

logger = logging.getLogger("push_service")

class PushService:
    def __init__(self):
        self.project_id = settings.FCM_PROJECT_ID
        self.service_account_file = settings.FCM_SERVICE_ACCOUNT_FILE
        self.enabled = settings.FCM_ENABLED

    async def get_fcm_access_token(self) -> Optional[str]:
        """Obtain OAuth2 token from Google Service Account if present."""
        if not self.service_account_file:
            return None
        try:
            # If google-auth is installed and service account is supplied
            from google.oauth2 import service_account
            import google.auth.transport.requests
            scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=scopes
            )
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            return credentials.token
        except Exception as e:
            logger.warning(f"Could not load Google service account credentials: {e}")
            return None

    async def send_to_shop(
        self,
        shop_id: str,
        inquiry_id: str,
        notification_type: str,
        title: str,
        body: str,
        data_payload: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Sends push notification to all active registered devices of a store.
        Records dispatch attempt, latency, and status in push_audit_logs.
        """
        conn = get_db()
        cursor = conn.cursor()

        # Find all active devices for sellers belonging to this shop
        cursor.execute("""
        SELECT d.device_id, d.seller_id, d.fcm_token, d.notifications_enabled
        FROM seller_devices d
        JOIN sellers s ON d.seller_id = s.seller_id
        WHERE s.shop_id = ? AND d.notifications_enabled = 1
        """, (shop_id,))
        devices = cursor.fetchall()

        if not devices:
            logger.info(f"No active notification devices registered for shop {shop_id}")
            # Still record a log entry indicating no active devices
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
            INSERT INTO push_audit_logs (log_id, inquiry_id, shop_id, notification_type, title, body, payload_json, status, error_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, inquiry_id, shop_id, notification_type, title, body, json.dumps(data_payload), "SKIPPED_NO_DEVICES", "Seller has no registered active push tokens"))
            conn.commit()
            conn.close()
            return []

        results = []
        oauth_token = await self.get_fcm_access_token()

        for dev in devices:
            device_id = dev["device_id"]
            token = dev["fcm_token"]
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            status = "SIMULATED"
            error_detail = None

            # High-priority Android FCM payload with deep-link data
            fcm_payload = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "data": {
                        **data_payload,
                        "inquiry_id": str(inquiry_id or ""),
                        "notification_type": notification_type,
                        "click_action": "FLUTTER_NOTIFICATION_CLICK"
                    },
                    "android": {
                        "priority": "HIGH",
                        "notification": {
                            "channel_id": "torob_inquiries_channel",
                            "sound": "default",
                            "default_vibrate_timings": True,
                            "tag": f"inquiry_{inquiry_id}"
                        }
                    }
                }
            }

            if oauth_token and self.project_id:
                # Real FCM v1 HTTP dispatch
                fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
                headers = {
                    "Authorization": f"Bearer {oauth_token}",
                    "Content-Type": "application/json"
                }
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(fcm_url, headers=headers, json=fcm_payload)
                        if resp.status_code == 200:
                            status = "DELIVERED"
                        else:
                            status = "FAILED"
                            error_detail = f"FCM HTTP {resp.status_code}: {resp.text}"
                            # Invalidate token if unregistered
                            if "UNREGISTERED" in resp.text or "INVALID_ARGUMENT" in resp.text:
                                cursor.execute("UPDATE seller_devices SET notifications_enabled = 0 WHERE fcm_token = ?", (token,))
                                error_detail += " [Token Invalidated]"
                except Exception as ex:
                    status = "FAILED"
                    error_detail = f"FCM Connection Error: {str(ex)}"
            else:
                # Logged real simulated dispatch (for local or staging environments without live FCM service account)
                status = "SIMULATED"
                error_detail = "Simulated delivery (FCM service account file not configured in .env; payload recorded and queued for test inspection)"

            # Record in push_audit_logs
            cursor.execute("""
            INSERT INTO push_audit_logs (log_id, inquiry_id, shop_id, fcm_token, notification_type, title, body, payload_json, status, error_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, inquiry_id, shop_id, token, notification_type, title, body, json.dumps(fcm_payload), status, error_detail))

            results.append({
                "log_id": log_id,
                "token": token,
                "status": status,
                "error": error_detail
            })

        conn.commit()
        conn.close()
        return results

push_service = PushService()
