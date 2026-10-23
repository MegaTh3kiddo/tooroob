import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List

from config import settings
from database import get_db
from services.voice.models import (
    CallScenario,
    CallStatus,
    GeneratedAudio,
    OutboundCallOptions,
    OutboundCallResult
)
from services.voice.phone_utils import normalize_phone_number, mask_phone_number, is_iranian_landline
from services.voice.template_renderer import PersianTemplateRenderer
from services.voice.tts_provider import get_tts_provider
from services.voice.outbound_call_provider import get_outbound_call_provider
from services.voice.inquiry_reminder_policy import ReminderEvaluationResult, reminder_policy

logger = logging.getLogger("voice_service")

# In-memory tracking for OTP rate limiting: phone -> list of request timestamps
_otp_call_timestamps: Dict[str, List[datetime]] = {}


class OutboundVoiceNotificationService:
    """
    Main orchestration service for Persian TTS Outbound Calls via Poshteyar.
    Provides decoupled business workflows for:
    - Scenario A: Landline Login Verification OTP Calls
    - Scenario B: Automated Unanswered Inquiry Voice Reminders
    """

    def __init__(self):
        pass

    def check_otp_rate_limit(self, phone: str) -> Tuple[bool, str]:
        """
        Enforce rate limits on voice OTP requests:
        1. Cooldown window between requests to the same phone (default: 120s).
        2. Maximum attempts per hour (default: 5).
        """
        clean_phone = normalize_phone_number(phone)
        now = datetime.utcnow()
        timestamps = _otp_call_timestamps.get(clean_phone, [])

        # Filter timestamps from the last 1 hour
        one_hour_ago = now - timedelta(hours=1)
        recent_timestamps = [ts for ts in timestamps if ts > one_hour_ago]
        _otp_call_timestamps[clean_phone] = recent_timestamps

        # Check cooldown
        cooldown_secs = settings.VOICE_OTP_COOLDOWN_SECONDS
        if recent_timestamps:
            last_request = recent_timestamps[-1]
            elapsed_seconds = (now - last_request).total_seconds()
            if elapsed_seconds < cooldown_secs:
                remaining = int(cooldown_secs - elapsed_seconds)
                return False, f"لطفاً {remaining} ثانیه دیگر جهت درخواست مجدد تماس صوتی صبر کنید."

        # Check hourly cap
        max_hourly = settings.VOICE_OTP_MAX_ATTEMPTS_PER_HOUR
        if len(recent_timestamps) >= max_hourly:
            return False, "سقف مجاز درخواست تماس صوتی برای این شماره در یک ساعت اخیر تکمیل شده است."

        return True, ""

    def _record_otp_attempt(self, phone: str):
        """Record timestamp of an OTP call attempt."""
        clean_phone = normalize_phone_number(phone)
        now = datetime.utcnow()
        if clean_phone not in _otp_call_timestamps:
            _otp_call_timestamps[clean_phone] = []
        _otp_call_timestamps[clean_phone].append(now)

    def _save_call_log(
        self,
        call_id: str,
        scenario: CallScenario,
        destination_number: str,
        provider: str,
        status: CallStatus,
        shop_id: Optional[str] = None,
        provider_call_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Persist call audit log to SQLite.
        CRITICAL SECURITY REQUIREMENT: Never stores plaintext OTP or sensitive customer PII.
        """
        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO outbound_call_logs (
            call_id, scenario_type, destination_number, provider,
            provider_call_id, status, shop_id, error_code, error_message,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            call_id,
            scenario.value,
            destination_number,
            provider,
            provider_call_id,
            status.value,
            shop_id,
            error_code,
            error_message,
            now_iso,
            now_iso
        ))
        conn.commit()
        conn.close()

    def _update_call_log(
        self,
        call_id: str,
        status: CallStatus,
        provider_call_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update existing call audit record."""
        conn = get_db()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        UPDATE outbound_call_logs
        SET status = ?, provider_call_id = COALESCE(?, provider_call_id),
            error_code = ?, error_message = ?, updated_at = ?
        WHERE call_id = ?
        """, (
            status.value,
            provider_call_id,
            error_code,
            error_message,
            now_iso,
            call_id
        ))
        conn.commit()
        conn.close()

    async def dispatch_landline_otp(
        self,
        phone_number: str,
        otp_code: str,
        shop_id: Optional[str] = None
    ) -> OutboundCallResult:
        """
        Scenario A: Deliver login verification code to a store landline via Persian voice call.
        """
        clean_phone = normalize_phone_number(phone_number)
        call_id = f"call_otp_{uuid.uuid4().hex[:10]}"

        # 1. Rate Limit & Cooldown Check
        allowed, reason = self.check_otp_rate_limit(clean_phone)
        if not allowed:
            logger.warning(f"Voice OTP rate limited for {mask_phone_number(clean_phone)}: {reason}")
            return OutboundCallResult(
                call_id=call_id,
                provider="rate_limiter",
                status=CallStatus.FAILED,
                message=reason,
                error_code="RATE_LIMITED"
            )

        # 2. Render Persian Voice Template
        rendered_text = PersianTemplateRenderer.render_landline_otp(otp_code)

        # 3. Persian TTS Audio Generation
        tts_provider = get_tts_provider()
        audio: GeneratedAudio = await tts_provider.synthesize(rendered_text)

        # 4. Create Initial Audit Record
        call_provider = get_outbound_call_provider()
        provider_name = "poshteyar" if settings.OUTBOUND_CALL_PROVIDER == "poshteyar" else "mock"

        self._save_call_log(
            call_id=call_id,
            scenario=CallScenario.LANDLINE_OTP,
            destination_number=clean_phone,
            provider=provider_name,
            status=CallStatus.AUDIO_GENERATION,
            shop_id=shop_id
        )

        # 5. Place Outbound Call via Provider
        call_options = OutboundCallOptions(
            recipient_name="فروشنده محترم ترب",
            topic="کد ورود به سامانه ترب",
            description="تماس خودکار صوتی جهت اعلام کد ۵ رقمی احراز هویت ورود به پنل فروشندگان",
            outbound_type="announcement",
            store_id=shop_id,
            scenario=CallScenario.LANDLINE_OTP
        )

        result: OutboundCallResult = await call_provider.place_call(
            destination_number=clean_phone,
            audio=audio,
            options=call_options
        )

        # 6. Record Attempt & Update Database Status
        if result.status != CallStatus.FAILED:
            self._record_otp_attempt(clean_phone)

        self._update_call_log(
            call_id=call_id,
            status=result.status,
            provider_call_id=result.provider_call_id,
            error_code=result.error_code,
            error_message=result.message
        )

        return result

    async def dispatch_unanswered_inquiry_reminder(
        self,
        evaluation: ReminderEvaluationResult
    ) -> Optional[OutboundCallResult]:
        """
        Scenario B: Deliver automated aggregate inquiry reminder call to eligible stores.
        """
        if not evaluation.eligible:
            logger.info(f"Store {evaluation.shop_id} not eligible for reminder: {evaluation.reason}")
            return None

        clean_phone = normalize_phone_number(evaluation.phone)
        call_id = f"call_rem_{uuid.uuid4().hex[:10]}"

        # 1. Render Persian Reminder Template
        rendered_text = PersianTemplateRenderer.render_unanswered_inquiry_reminder(
            unanswered_count=evaluation.unanswered_count,
            total_inquiries=evaluation.total_inquiries,
            time_window=evaluation.time_window_label,
            store_name=evaluation.shop_name
        )

        # 2. Persian TTS Audio Generation
        tts_provider = get_tts_provider()
        audio: GeneratedAudio = await tts_provider.synthesize(rendered_text)

        # 3. Create Audit Record
        call_provider = get_outbound_call_provider()
        provider_name = "poshteyar" if settings.OUTBOUND_CALL_PROVIDER == "poshteyar" else "mock"

        self._save_call_log(
            call_id=call_id,
            scenario=CallScenario.UNANSWERED_INQUIRY_REMINDER,
            destination_number=clean_phone,
            provider=provider_name,
            status=CallStatus.AUDIO_GENERATION,
            shop_id=evaluation.shop_id
        )

        # 4. Place Outbound Call via Provider
        call_options = OutboundCallOptions(
            recipient_name=evaluation.shop_name,
            topic="یادآوری استعلام‌های بی‌پاسخ ترب",
            description=f"یادآوری صوتی خودکار به فروشگاه با {evaluation.unanswered_count} استعلام بی‌پاسخ",
            retry_policy=[600, 1800],  # Retry after 10m and 30m if busy/unanswered
            outbound_type="announcement",
            store_id=evaluation.shop_id,
            scenario=CallScenario.UNANSWERED_INQUIRY_REMINDER
        )

        result: OutboundCallResult = await call_provider.place_call(
            destination_number=clean_phone,
            audio=audio,
            options=call_options
        )

        # 5. Update Database Status
        self._update_call_log(
            call_id=call_id,
            status=result.status,
            provider_call_id=result.provider_call_id,
            error_code=result.error_code,
            error_message=result.message
        )

        return result


voice_service = OutboundVoiceNotificationService()
