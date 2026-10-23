import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from config import settings
from database import get_db
from services.working_hours import is_shop_effectively_open
from services.voice.phone_utils import normalize_phone_number, is_valid_phone
from services.voice.models import CallScenario

logger = logging.getLogger("inquiry_reminder_policy")


@dataclass
class ReminderEvaluationResult:
    shop_id: str
    shop_name: str
    phone: str
    eligible: bool
    reason: str
    total_inquiries: int = 0
    unanswered_count: int = 0
    unanswered_rate: float = 0.0
    time_window_label: str = "۲۴ ساعت"


class InquiryReminderPolicy:
    """
    Configurable evaluation engine to determine whether a store should receive
    an automated voice reminder for excessive unanswered inquiries.
    """

    def __init__(self):
        pass

    def get_policy_configs(self) -> Dict[str, Any]:
        """Fetch dynamic policy thresholds from DB with fallback to settings."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT config_key, config_value FROM scheduler_configs")
        db_configs = {row["config_key"]: row["config_value"] for row in cursor.fetchall()}
        conn.close()

        def _get_int(key: str, default: int) -> int:
            try:
                return int(db_configs.get(key, default))
            except Exception:
                return default

        def _get_float(key: str, default: float) -> float:
            try:
                return float(db_configs.get(key, default))
            except Exception:
                return default

        return {
            "eval_window_minutes": _get_int("voice_reminder_eval_window_minutes", settings.VOICE_REMINDER_EVALUATION_WINDOW_MINUTES),
            "min_eligible": _get_int("voice_reminder_min_eligible", settings.VOICE_REMINDER_MIN_ELIGIBLE_INQUIRIES),
            "min_unanswered": _get_int("voice_reminder_min_unanswered", settings.VOICE_REMINDER_MIN_UNANSWERED_INQUIRIES),
            "min_unanswered_rate": _get_float("voice_reminder_min_unanswered_rate", settings.VOICE_REMINDER_MIN_UNANSWERED_RATE),
            "cooldown_minutes": _get_int("voice_reminder_cooldown_minutes", settings.VOICE_REMINDER_MIN_INTERVAL_MINUTES),
            "max_calls_per_day": settings.VOICE_REMINDER_MAX_CALLS_PER_DAY
        }

    def evaluate_store(self, shop_id: str) -> ReminderEvaluationResult:
        """
        Evaluate a single store against the policy criteria.
        Checks:
        1. Store existence and active state
        2. Consent / Opt-out flag (voice_reminders_enabled)
        3. Operating hours & holiday mode
        4. Valid destination phone number
        5. Total & unanswered inquiries in evaluation window
        6. Cooldown interval since last reminder
        7. Maximum daily call limit
        """
        policy = self.get_policy_configs()
        conn = get_db()
        cursor = conn.cursor()

        # 1. Fetch store profile
        cursor.execute("""
        SELECT shop_id, shop_name, phone, is_open, open_time, close_time,
               accept_inquiries, holiday_mode, voice_reminders_enabled
        FROM shop_settings
        WHERE shop_id = ?
        """, (shop_id,))
        shop = cursor.fetchone()

        if not shop:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name="نامشخص",
                phone="",
                eligible=False,
                reason="فروشگاه در سیستم یافت نشد"
            )

        shop_name = shop["shop_name"] or "فروشگاه"
        raw_phone = shop["phone"] or ""
        clean_phone = normalize_phone_number(raw_phone)

        # 2. Check Opt-Out status
        reminders_enabled = bool(shop["voice_reminders_enabled"] if shop["voice_reminders_enabled"] is not None else 1)
        if not reminders_enabled or not settings.VOICE_REMINDERS_ENABLED:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason="فروشگاه دریافت تماس‌های صوتی یادآوری را غیرفعال کرده است (Opt-Out)"
            )

        # 3. Check Operating Hours & Store Status
        is_open_setting = bool(shop["is_open"])
        holiday_mode = bool(shop["holiday_mode"])
        open_time = shop["open_time"] or "09:00"
        close_time = shop["close_time"] or "21:00"

        is_open, within_hours, status_msg = is_shop_effectively_open(
            is_open_setting=is_open_setting,
            holiday_mode=holiday_mode,
            open_time=open_time,
            close_time=close_time
        )
        if not is_open:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason=f"فروشگاه در حال حاضر فعال نیست: {status_msg}"
            )

        # 4. Check Phone Validity
        if not clean_phone or not is_valid_phone(clean_phone):
            # Check if seller has a registered phone
            cursor.execute("SELECT phone_number FROM sellers WHERE shop_id = ? LIMIT 1", (shop_id,))
            seller_row = cursor.fetchone()
            if seller_row:
                clean_phone = normalize_phone_number(seller_row["phone_number"])

        if not clean_phone or not is_valid_phone(clean_phone):
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason="شماره تماس معتبری برای فروشگاه ثبت نشده است"
            )

        # 5. Check Inquiries in Evaluation Window
        eval_window_mins = policy["eval_window_minutes"]
        window_modifier = f"-{eval_window_mins} minutes"
        cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'EXPIRED' THEN 1 ELSE 0 END) as unanswered
        FROM inquiries
        WHERE shop_id = ?
          AND created_at >= datetime('now', ?)
        """, (shop_id, window_modifier))
        row = cursor.fetchone()

        total = row["total"] or 0
        unanswered = row["unanswered"] or 0
        unanswered_rate = round(unanswered / total, 2) if total > 0 else 0.0

        if total < policy["min_eligible"]:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason=f"تعداد استعلام‌ها ({total}) کمتر از حداقل آستانه مشمول ({policy['min_eligible']}) است",
                total_inquiries=total,
                unanswered_count=unanswered,
                unanswered_rate=unanswered_rate
            )

        if unanswered < policy["min_unanswered"]:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason=f"تعداد استعلام‌های بی‌پاسخ ({unanswered}) کمتر از حد نصاب ({policy['min_unanswered']}) است",
                total_inquiries=total,
                unanswered_count=unanswered,
                unanswered_rate=unanswered_rate
            )

        if unanswered_rate < policy["min_unanswered_rate"]:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason=f"نرخ استعلام‌های بی‌پاسخ ({unanswered_rate * 100:.0f}٪) کمتر از آستانه مجاز ({policy['min_unanswered_rate'] * 100:.0f}٪) است",
                total_inquiries=total,
                unanswered_count=unanswered,
                unanswered_rate=unanswered_rate
            )

        # 6. Check Cooldown Interval
        cooldown_mins = policy["cooldown_minutes"]
        cooldown_modifier = f"-{cooldown_mins} minutes"
        cursor.execute("""
        SELECT COUNT(*) as recent_calls
        FROM outbound_call_logs
        WHERE shop_id = ?
          AND scenario_type = ?
          AND status IN ('CALL_REQUESTED', 'CALLING', 'ANSWERED', 'COMPLETED')
          AND created_at >= datetime('now', ?)
        """, (shop_id, CallScenario.UNANSWERED_INQUIRY_REMINDER.value, cooldown_modifier))
        recent_count = cursor.fetchone()["recent_calls"] or 0

        if recent_count > 0:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason="فروشگاه اخیراً در بازه کول‌داون تماس یادآوری دریافت کرده است",
                total_inquiries=total,
                unanswered_count=unanswered,
                unanswered_rate=unanswered_rate
            )

        # 7. Check Daily Limit
        cursor.execute("""
        SELECT COUNT(*) as today_calls
        FROM outbound_call_logs
        WHERE shop_id = ?
          AND scenario_type = ?
          AND status IN ('CALL_REQUESTED', 'CALLING', 'ANSWERED', 'COMPLETED')
          AND created_at >= datetime('now', '-1 day')
        """, (shop_id, CallScenario.UNANSWERED_INQUIRY_REMINDER.value))
        today_count = cursor.fetchone()["today_calls"] or 0

        if today_count >= policy["max_calls_per_day"]:
            conn.close()
            return ReminderEvaluationResult(
                shop_id=shop_id,
                shop_name=shop_name,
                phone=clean_phone,
                eligible=False,
                reason="سقف مجاز تماس یادآوری روزانه برای این فروشگاه تکمیل شده است",
                total_inquiries=total,
                unanswered_count=unanswered,
                unanswered_rate=unanswered_rate
            )

        conn.close()

        # Format friendly Persian time window
        hours = eval_window_mins // 60
        time_label = f"{hours} ساعت" if hours > 0 else f"{eval_window_mins} دقیقه"

        return ReminderEvaluationResult(
            shop_id=shop_id,
            shop_name=shop_name,
            phone=clean_phone,
            eligible=True,
            reason="فروشگاه واجد شرایط دریافت تماس صوتی یادآوری است",
            total_inquiries=total,
            unanswered_count=unanswered,
            unanswered_rate=unanswered_rate,
            time_window_label=time_label
        )

    def evaluate_all_active_stores(self) -> List[ReminderEvaluationResult]:
        """Evaluate all stores that accept inquiries."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT shop_id FROM shop_settings
        WHERE accept_inquiries = 1 AND is_open = 1 AND holiday_mode = 0
        """)
        shops = cursor.fetchall()
        conn.close()

        results = []
        for s in shops:
            res = self.evaluate_store(s["shop_id"])
            results.append(res)
        return results


reminder_policy = InquiryReminderPolicy()
