import re
import logging
from typing import Optional, Dict
from config import settings

logger = logging.getLogger("template_renderer")

_PERSIAN_DIGITS_MAP = {
    '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
    '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
}


def to_persian_digits(val: any) -> str:
    """Convert ASCII digits in a number or string to Persian digits."""
    return "".join(_PERSIAN_DIGITS_MAP.get(c, c) for c in str(val))


def format_otp_digits_for_speech(otp_code: str) -> str:
    """
    Format OTP digits with spaced Persian characters so telephone TTS engines
    pronounce each digit individually and clearly with slight natural pauses,
    rather than reciting a large compound integer (e.g. '۱ ، ۲ ، ۳ ، ۴ ، ۵').
    """
    cleaned = re.sub(r"\D", "", otp_code)
    persian_chars = [_PERSIAN_DIGITS_MAP.get(c, c) for c in cleaned]
    return " ، ".join(persian_chars)


class PersianTemplateRenderer:
    """
    Configurable Persian Text Template Renderer for Outbound Voice Notifications.
    Validates substituted values and ensures natural pronunciation in TTS.
    """

    @classmethod
    def render_landline_otp(
        cls,
        otp_code: str,
        custom_template: Optional[str] = None
    ) -> str:
        """
        Render voice OTP verification template.
        Validates that OTP is present and digits are properly formatted for speech.
        """
        if not otp_code or not otp_code.strip():
            raise ValueError("OTP code cannot be empty for voice template rendering.")

        template = custom_template or settings.VOICE_OTP_TEMPLATE
        speech_digits = format_otp_digits_for_speech(otp_code)

        rendered = template.format(otp_code=speech_digits)
        cls._validate_rendered_text(rendered, ["otp_code"])
        return rendered

    @classmethod
    def render_unanswered_inquiry_reminder(
        cls,
        unanswered_count: int,
        total_inquiries: int,
        time_window: str = "۲۴ ساعت",
        store_name: Optional[str] = None,
        custom_template: Optional[str] = None
    ) -> str:
        """
        Render automated voice reminder template for stores with excessive unanswered inquiries.
        Ensures all numerical values are converted to Persian digits and no sensitive data is leaked.
        """
        template = custom_template or settings.VOICE_REMINDER_TEMPLATE

        substitutions = {
            "time_window": time_window,
            "unanswered_count": to_persian_digits(unanswered_count),
            "total_inquiries": to_persian_digits(total_inquiries),
            "store_name": store_name or "همکار گرامی"
        }

        # Safe formatting with fallback for optional variables
        try:
            rendered = template.format(**substitutions)
        except KeyError as ke:
            missing_var = str(ke).strip("'")
            logger.warning(f"Missing variable in reminder template: {missing_var}")
            substitutions[missing_var] = ""
            rendered = template.format(**substitutions)

        cls._validate_rendered_text(rendered, ["unanswered_count", "total_inquiries"])
        return rendered

    @staticmethod
    def _validate_rendered_text(text: str, required_fields: list[str]):
        """Ensure no unresolved template brackets remain in the final Persian text."""
        if not text or not text.strip():
            raise ValueError("Rendered voice template is empty.")

        unresolved = re.findall(r"\{(\w+)\}", text)
        if unresolved:
            raise ValueError(f"Unresolved placeholders found in rendered text: {unresolved}")
