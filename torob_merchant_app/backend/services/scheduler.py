import asyncio
import logging
import sqlite3
import json
from datetime import datetime
from typing import Optional
from database import get_db
from services.push_service import push_service
from services.working_hours import is_within_working_hours

logger = logging.getLogger("scheduler")

class InquiryScheduler:
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    def get_timeouts(self) -> tuple[int, int]:
        """Fetch dynamic reminder and expiration timeouts in seconds from DB."""
        conn = get_db()
        cursor = conn.cursor()
        configs = {}
        for row in cursor.fetchall():
            key = row["config_key"]
            val = row["config_value"]
            try:
                configs[key] = int(float(val))
            except (ValueError, TypeError):
                configs[key] = val
        conn.close()

        reminder_secs = int(configs.get("reminder_timeout_seconds", 300))
        expiry_secs = int(configs.get("expiration_timeout_seconds", 600))
        return reminder_secs, expiry_secs

    async def register_inquiry_time_zero(self, inquiry_id: str, shop_id: str, product_title: str):
        """Time Zero: Record timeline and immediately dispatch initial push."""
        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT OR REPLACE INTO inquiry_timelines (inquiry_id, registered_at, initial_push_at)
        VALUES (?, ?, ?)
        """, (inquiry_id, now_iso, now_iso))
        conn.commit()
        conn.close()

        # Immediate Push Dispatch
        title = "استعلام جدید قیمت و موجودی"
        body = f"مشتری برای کالای «{product_title}» منتظر پاسخ شماست. لمس کنید تا قیمت و موجودی را ثبت نمایید."
        data = {
            "inquiry_id": str(inquiry_id),
            "action": "open_inquiry_detail",
            "type": "INITIAL_INQUIRY"
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
        """Select an alternative candidate store if the inquiry expires (must be currently open within working hours)."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT shop_id, open_time, close_time, holiday_mode, is_open
        FROM shop_settings
        WHERE shop_id != ? AND is_open = 1 AND accept_inquiries = 1 AND holiday_mode = 0
        """, (current_shop_id,))
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            if is_within_working_hours(r["open_time"] or "09:00", r["close_time"] or "21:00"):
                return r["shop_id"]
        return None

    async def run_scheduler_tick(self):
        """Single check cycle evaluating all active inquiries."""
        reminder_secs, expiry_secs = self.get_timeouts()
        conn = get_db()
        cursor = conn.cursor()

        # Find all ACTIVE inquiries
        cursor.execute("""
        SELECT i.inquiry_id, i.shop_id, i.product_title, i.created_at,
               t.initial_push_at, t.reminder_push_at, t.urgent_call_push_at
        FROM inquiries i
        LEFT JOIN inquiry_timelines t ON i.inquiry_id = t.inquiry_id
        WHERE i.status = 'ACTIVE'
        """)
        active_inquiries = cursor.fetchall()
        now = datetime.utcnow()

        for inq in active_inquiries:
            inquiry_id = inq["inquiry_id"]
            shop_id = inq["shop_id"]
            product_title = inq["product_title"]
            created_str = inq["created_at"]

            try:
                created_dt = datetime.fromisoformat(created_str.replace("Z", ""))
            except Exception:
                created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")

            elapsed_seconds = (now - created_dt).total_seconds()

            # 1. Check Reminder (+5 minutes)
            if elapsed_seconds >= reminder_secs and not inq["reminder_push_at"]:
                remind_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                UPDATE inquiry_timelines
                SET reminder_push_at = ?
                WHERE inquiry_id = ?
                """, (remind_iso, inquiry_id))
                conn.commit()

                # Dispatch Reminder Push
                rem_title = "یادآوری استعلام قیمت و موجودی"
                rem_body = f"فرصت پاسخ‌گویی به استعلام «{product_title}» رو به اتمام است! لطفا بررسی کنید."
                rem_data = {
                    "inquiry_id": str(inquiry_id),
                    "action": "open_inquiry_detail",
                    "type": "REMINDER_5MIN"
                }
                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="REMINDER_5MIN",
                    title=rem_title,
                    body=rem_body,
                    data_payload=rem_data
                )
                logger.info(f"Dispatched 5-min reminder for inquiry {inquiry_id}")

            # 2. Check Urgent Call (2 minutes remaining before expiration, e.g. at 8 minutes)
            urgent_threshold = max(0, expiry_secs - 120)
            if elapsed_seconds >= urgent_threshold and not inq["urgent_call_push_at"] and elapsed_seconds < expiry_secs:
                urgent_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                UPDATE inquiry_timelines
                SET urgent_call_push_at = ?
                WHERE inquiry_id = ?
                """, (urgent_iso, inquiry_id))
                conn.commit()

                urgent_title = "تماس فوری استعلام ترب"
                urgent_body = f"فقط ۲ دقیقه تا پایان مهلت پاسخ به استعلام «{product_title}» باقی مانده است!"
                urgent_data = {
                    "inquiry_id": str(inquiry_id),
                    "action": "open_inquiry_call",
                    "type": "URGENT_CALL",
                    "product_title": str(product_title),
                    "duration_seconds": "120"
                }
                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="URGENT_CALL",
                    title=urgent_title,
                    body=urgent_body,
                    data_payload=urgent_data
                )
                logger.info(f"Dispatched URGENT_CALL alert for inquiry {inquiry_id} (remaining <= 120s)")

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

                # Dispatch Expiration Notification
                exp_title = "استعلام منقضی شد"
                exp_body = f"به دلیل عدم ثبت پاسخ در مهلت مقرر، استعلام «{product_title}» منقضی و به فروشگاه دیگری ارجاع شد."
                exp_data = {
                    "inquiry_id": str(inquiry_id),
                    "action": "open_history",
                    "type": "EXPIRATION_ALERT"
                }
                await push_service.send_to_shop(
                    shop_id=shop_id,
                    inquiry_id=inquiry_id,
                    notification_type="EXPIRATION_ALERT",
                    title=exp_title,
                    body=exp_body,
                    data_payload=exp_data
                )
                logger.info(f"Inquiry {inquiry_id} expired after {elapsed_seconds:.0f}s. Assigned alt shop: {alt_shop_id}")

        conn.close()

    async def run_voice_reminders_evaluation(self):
        """Evaluate stores eligible for automated unanswered inquiry voice reminder calls."""
        if not settings.VOICE_REMINDERS_ENABLED:
            return

        try:
            from services.voice.inquiry_reminder_policy import reminder_policy
            from services.voice.voice_service import voice_service

            results = reminder_policy.evaluate_all_active_stores()
            for res in results:
                if res.eligible:
                    logger.info(
                        f"[VOICE REMINDER] Triggering reminder call for store {res.shop_id} "
                        f"({res.unanswered_count}/{res.total_inquiries} unanswered in {res.time_window_label})"
                    )
                    await voice_service.dispatch_unanswered_inquiry_reminder(res)
        except Exception as e:
            logger.error(f"Error in store voice reminders evaluation: {e}", exc_info=True)

    async def start(self):
        """Start scheduler background loop."""
        self.is_running = True
        logger.info("Starting Inquiry Scheduler engine (checking every 5 seconds)...")
        tick_count = 0
        while self.is_running:
            try:
                await self.run_scheduler_tick()

                # Run store voice reminders evaluation every 60 seconds (every 12 ticks)
                tick_count += 1
                if tick_count % 12 == 0:
                    await self.run_voice_reminders_evaluation()
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)
            await asyncio.sleep(5)

    def stop(self):
        """Stop scheduler."""
        self.is_running = False

scheduler = InquiryScheduler()
