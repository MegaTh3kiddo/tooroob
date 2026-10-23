import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from torob.merchant.push_service import push_service
from torob.merchant.working_hours import is_within_working_hours
from torob.storage.db import db_manager

logger = logging.getLogger("inquiry_scheduler")


class InquiryScheduler:
    def __init__(self):
        self.is_running = False

    def get_timeouts(self) -> Tuple[int, int, int]:
        """Fetch dynamic reminder (5min), expiration (10min), and urgent alert (2min left) timeouts from DB."""
        conn = db_manager.get_sqlite()
        cursor = conn.cursor()
        cursor.execute("SELECT config_key, config_value FROM scheduler_configs")
        configs = {r["config_key"]: r["config_value"] for r in cursor.fetchall()}

        reminder_secs = int(float(configs.get("reminder_timeout_seconds", 300)))
        expiry_secs = int(float(configs.get("expiration_timeout_seconds", 600)))
        urgent_secs = int(float(configs.get("urgent_call_remaining_seconds", 120)))
        return reminder_secs, expiry_secs, urgent_secs

    async def register_inquiry_time_zero(self, inquiry_id: str, shop_id: str, product_title: str):
        """Time Zero: Register SLA timeline and immediately dispatch initial push notification."""
        conn = db_manager.get_sqlite()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT OR REPLACE INTO inquiry_timelines (inquiry_id, registered_at, initial_push_at)
        VALUES (?, ?, ?)
        """, (inquiry_id, now_iso, now_iso))
        conn.commit()

        # Immediate Push Dispatch
        title = "استعلام جدید قیمت و موجودی در ترب"
        body = f"مشتری برای کالای «{product_title}» منتظر پاسخ شماست. لطفاً موجودی و قیمت را بررسی نمایید."
        data = {
            "inquiry_id": str(inquiry_id),
            "action": "open_inquiry_detail",
            "type": "INITIAL_INQUIRY",
            "product_title": str(product_title or "")
        }
        await push_service.send_to_shop(
            shop_id=shop_id,
            inquiry_id=inquiry_id,
            notification_type="INITIAL_INQUIRY",
            title=title,
            body=body,
            data_payload=data
        )

    def find_alternative_shop(self, current_shop_id: str) -> Optional[str]:
        """Find an open alternative shop if current shop times out."""
        conn = db_manager.get_sqlite()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT shop_id, open_time, close_time, holiday_mode, is_open
        FROM shop_settings
        WHERE shop_id != ? AND is_open = 1 AND accept_inquiries = 1 AND holiday_mode = 0
        LIMIT 20
        """, (current_shop_id,))
        rows = cursor.fetchall()

        for r in rows:
            if is_within_working_hours(r["open_time"] or "09:00", r["close_time"] or "21:00"):
                return r["shop_id"]
        return None

    async def run_scheduler_tick(self) -> dict:
        """
        Execute one deterministic scheduler check cycle:
        1. Evaluates all ACTIVE inquiries.
        2. Dispatches 5-min reminders.
        3. Dispatches 2-min remaining URGENT_CALL alerts.
        4. Expires past-due inquiries and dispatches EXPIRATION_ALERT.
        """
        reminder_secs, expiry_secs, urgent_secs = self.get_timeouts()
        conn = db_manager.get_sqlite()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT i.inquiry_id, i.shop_id, i.product_title, i.created_at, i.requested_at,
               t.initial_push_at, t.reminder_push_at, t.urgent_call_push_at
        FROM inquiries i
        LEFT JOIN inquiry_timelines t ON i.inquiry_id = t.inquiry_id
        WHERE i.status IN ('ACTIVE', 'created', 'queued', 'delivered')
        """)
        active_inquiries = cursor.fetchall()
        now = datetime.utcnow()

        reminders_sent = 0
        urgent_sent = 0
        expired_count = 0

        for inq in active_inquiries:
            inquiry_id = inq["inquiry_id"]
            shop_id = inq["shop_id"]
            product_title = inq["product_title"] or "کالای درخواستی"
            created_str = inq["created_at"] or inq["requested_at"]

            if not created_str:
                continue

            try:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if created_dt.tzinfo is not None:
                    created_dt = created_dt.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                try:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

            elapsed_seconds = (now - created_dt).total_seconds()

            # 1. Check Reminder (+5 minutes)
            if elapsed_seconds >= reminder_secs and not inq["reminder_push_at"] and elapsed_seconds < expiry_secs:
                remind_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                UPDATE inquiry_timelines
                SET reminder_push_at = ?
                WHERE inquiry_id = ?
                """, (remind_iso, inquiry_id))
                conn.commit()

                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="REMINDER_5MIN",
                    title="یادآوری استعلام قیمت و موجودی",
                    body=f"فرصت پاسخ‌گویی به استعلام «{product_title}» رو به پایان است. لطفاً پاسخ دهید.",
                    data_payload={
                        "inquiry_id": str(inquiry_id),
                        "action": "open_inquiry_detail",
                        "type": "REMINDER_5MIN"
                    }
                )
                reminders_sent += 1

            # 2. Check Urgent Call (2 minutes remaining before expiration)
            urgent_threshold = max(0, expiry_secs - urgent_secs)
            if elapsed_seconds >= urgent_threshold and not inq["urgent_call_push_at"] and elapsed_seconds < expiry_secs:
                urgent_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                UPDATE inquiry_timelines
                SET urgent_call_push_at = ?
                WHERE inquiry_id = ?
                """, (urgent_iso, inquiry_id))
                conn.commit()

                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="URGENT_CALL",
                    title="تماس فوری استعلام ترب",
                    body=f"فقط ۲ دقیقه تا پایان مهلت پاسخ به استعلام «{product_title}» باقی مانده است!",
                    data_payload={
                        "inquiry_id": str(inquiry_id),
                        "action": "open_inquiry_call",
                        "type": "URGENT_CALL",
                        "product_title": str(product_title),
                        "duration_seconds": str(urgent_secs)
                    }
                )
                urgent_sent += 1

            # 3. Check Expiration (+10 minutes)
            if elapsed_seconds >= expiry_secs:
                expire_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                alt_shop_id = self.find_alternative_shop(shop_id)

                cursor.execute("""
                UPDATE inquiries
                SET status = 'EXPIRED'
                WHERE inquiry_id = ?
                """, (inquiry_id,))

                cursor.execute("""
                UPDATE inquiry_timelines
                SET expired_at = ?, alternative_shop_id = ?
                WHERE inquiry_id = ?
                """, (expire_iso, alt_shop_id, inquiry_id))
                conn.commit()

                # Dispatch Expiration push (stops urgent alarm on device)
                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="EXPIRATION_ALERT",
                    title="پایان مهلت استعلام ترب",
                    body=f"مهلت پاسخ‌گویی به استعلام «{product_title}» منقضی شد.",
                    data_payload={
                        "inquiry_id": str(inquiry_id),
                        "action": "open_inquiry_detail",
                        "type": "EXPIRATION_ALERT"
                    }
                )

                # Record inquiry timeout evidence in central ledger
                ev_id = f"ev_inq_exp_{uuid.uuid4().hex[:10]}"
                cursor.execute("""
                INSERT INTO evidence_events
                (event_id, event_type, scope_json, observed_at, ingested_at, source_code, actor_id, payload_json)
                VALUES (?, 'seller_inquiry_timeout', ?, ?, ?, 'system_scheduler', ?, ?)
                """, (
                    ev_id,
                    json.dumps({"shop_id": shop_id, "inquiry_id": inquiry_id}),
                    expire_iso,
                    expire_iso,
                    shop_id,
                    json.dumps({"reason": "merchant_unresponsive", "timeout_seconds": expiry_secs})
                ))
                conn.commit()
                expired_count += 1

        return {
            "evaluated_inquiries": len(active_inquiries),
            "reminders_sent": reminders_sent,
            "urgent_alerts_sent": urgent_sent,
            "expired_count": expired_count
        }


inquiry_scheduler = InquiryScheduler()
