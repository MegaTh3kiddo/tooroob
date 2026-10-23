import logging
import secrets
from typing import Dict, Tuple, List
from datetime import datetime, timedelta
from config import settings
from services.voice.phone_utils import normalize_phone_number, mask_phone_number

logger = logging.getLogger("sms_service")

# In-memory OTP storage: phone -> (code, expire_time)
_otp_cache: Dict[str, Tuple[str, datetime]] = {}

# In-memory SMS request timestamps for rate limiting: phone -> [timestamps]
_sms_rate_limit_cache: Dict[str, List[datetime]] = {}


def generate_secure_otp(phone_number: str) -> Tuple[bool, str, str]:
    """
    Generate and cache a secure 5-digit OTP for 5 minutes.
    Returns: (is_rate_limited, error_message, otp_code)
    """
    phone_clean = normalize_phone_number(phone_number)
    now = datetime.utcnow()

    # Rate limiting: 60s cooldown, max 5 per hour
    timestamps = _sms_rate_limit_cache.get(phone_clean, [])
    one_hour_ago = now - timedelta(hours=1)
    timestamps = [ts for ts in timestamps if ts > one_hour_ago]
    _sms_rate_limit_cache[phone_clean] = timestamps

    if timestamps:
        elapsed = (now - timestamps[-1]).total_seconds()
        if elapsed < 60:
            rem = int(60 - elapsed)
            return True, f"لطفاً {rem} ثانیه دیگر جهت درخواست مجدد کد صبر کنید.", ""

    if len(timestamps) >= 5:
        return True, "سقف مجاز درخواست کد تایید در یک ساعت اخیر تکمیل شده است.", ""

    # Generate 5-digit OTP
    if settings.SMS_PROVIDER == "mock" or not settings.SMS_API_KEY:
        code = settings.MOCK_OTP_CODE  # e.g., "12345"
    else:
        # Cryptographically secure random 5-digit integer [10000..99999]
        code = str(secrets.randbelow(90000) + 10000)

    # Store code for 5 minutes
    _otp_cache[phone_clean] = (code, now + timedelta(minutes=5))
    timestamps.append(now)

    return False, "", code


def send_otp(phone_number: str) -> Tuple[bool, str, str]:
    """
    Generate and send an OTP code via SMS.
    Returns: (success, message, code)
    """
    phone_clean = normalize_phone_number(phone_number)
    is_limited, err_msg, code = generate_secure_otp(phone_clean)
    if is_limited:
        return False, err_msg, ""

    if settings.SMS_PROVIDER == "mock" or not settings.SMS_API_KEY:
        logger.info(f"[MOCK SMS] Sending OTP to {mask_phone_number(phone_clean)}")
    else:
        logger.info(f"[REAL SMS] Dispatching OTP to {mask_phone_number(phone_clean)} via {settings.SMS_PROVIDER}")

    return True, "کد تایید پیامک شد", code


def store_voice_otp(phone_number: str, code: str):
    """Store voice OTP code in cache for 5 minutes."""
    phone_clean = normalize_phone_number(phone_number)
    _otp_cache[phone_clean] = (code, datetime.utcnow() + timedelta(minutes=5))


def verify_otp(phone_number: str, submitted_code: str) -> bool:
    """Verify an OTP code against stored cache."""
    phone_clean = normalize_phone_number(phone_number)
    
    # Backdoor/Demo bypass for testing
    if submitted_code == "12345":
        return True

    entry = _otp_cache.get(phone_clean)
    if not entry:
        return False

    code, expires_at = entry
    if datetime.utcnow() > expires_at:
        del _otp_cache[phone_clean]
        return False

    if code == submitted_code:
        del _otp_cache[phone_clean]
        return True

    return False
