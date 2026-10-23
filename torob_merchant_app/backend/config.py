import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = "Torob Seller Backend"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "torob-seller-secret-key-production-change-me-32chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "chatapp_seller.db"))
    MAIN_TOROB_DB: str = os.getenv("MAIN_TOROB_DB", os.path.join(os.path.dirname(__file__), "..", "..", "torob_agent.db"))

    # Scheduler Timeouts (in seconds)
    INITIAL_PUSH_TIMEOUT_SECONDS: int = int(os.getenv("INITIAL_PUSH_TIMEOUT_SECONDS", "0"))
    REMINDER_TIMEOUT_SECONDS: int = int(os.getenv("REMINDER_TIMEOUT_SECONDS", "300"))  # 5 minutes
    EXPIRATION_TIMEOUT_SECONDS: int = int(os.getenv("EXPIRATION_TIMEOUT_SECONDS", "600"))  # 10 minutes

    # Push Notification Service
    FCM_ENABLED: bool = os.getenv("FCM_ENABLED", "true").lower() in ("true", "1", "yes")
    FCM_PROJECT_ID: Optional[str] = os.getenv("FCM_PROJECT_ID", "torob-seller-app")
    FCM_SERVICE_ACCOUNT_FILE: Optional[str] = os.getenv("FCM_SERVICE_ACCOUNT_FILE", None)

    # SMS OTP Service
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "mock")  # mock, kavenegar, sms_ir
    SMS_API_KEY: Optional[str] = os.getenv("SMS_API_KEY", None)
    MOCK_OTP_CODE: str = os.getenv("MOCK_OTP_CODE", "12345")

    # Poshteyar Outbound Telephony Provider
    OUTBOUND_CALL_PROVIDER: str = os.getenv("OUTBOUND_CALL_PROVIDER", "mock")  # "mock", "poshteyar"
    POSHTYAR_ENABLED: bool = os.getenv("POSHTYAR_ENABLED", "false").lower() in ("true", "1", "yes")
    POSHTYAR_API_URL: str = os.getenv("POSHTYAR_API_URL", "https://api.poshtyar.com/api/v1/external/calls/originate")
    POSHTYAR_API_KEY: Optional[str] = os.getenv("POSHTYAR_API_KEY", None)
    POSHTYAR_OPERATOR_ID: str = os.getenv("POSHTYAR_OPERATOR_ID", "torob_seller_voice_operator")

    # Persian Text-To-Speech (TTS) Provider
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "mock")  # "mock", "poshteyar", "gtts"
    TTS_DEFAULT_LANGUAGE: str = "fa-IR"
    TTS_DEFAULT_SPEAKING_RATE: float = float(os.getenv("TTS_DEFAULT_SPEAKING_RATE", "0.95"))

    # Voice OTP Policy & Rate Limits
    VOICE_OTP_COOLDOWN_SECONDS: int = int(os.getenv("VOICE_OTP_COOLDOWN_SECONDS", "120"))  # 2 minutes cooldown
    VOICE_OTP_MAX_ATTEMPTS_PER_HOUR: int = int(os.getenv("VOICE_OTP_MAX_ATTEMPTS_PER_HOUR", "5"))
    VOICE_OTP_TEMPLATE: str = os.getenv(
        "VOICE_OTP_TEMPLATE",
        "سلام. کد ورود شما به سامانه ترب، {otp_code} است. این کد را در اختیار دیگران قرار ندهید."
    )

    # Scenario B: Unanswered Inquiry Voice Reminder Policy Defaults
    VOICE_REMINDERS_ENABLED: bool = os.getenv("VOICE_REMINDERS_ENABLED", "true").lower() in ("true", "1", "yes")
    VOICE_REMINDER_EVALUATION_WINDOW_MINUTES: int = int(os.getenv("VOICE_REMINDER_EVALUATION_WINDOW_MINUTES", "1440"))  # 24 hours
    VOICE_REMINDER_MIN_ELIGIBLE_INQUIRIES: int = int(os.getenv("VOICE_REMINDER_MIN_ELIGIBLE_INQUIRIES", "10"))
    VOICE_REMINDER_MIN_UNANSWERED_INQUIRIES: int = int(os.getenv("VOICE_REMINDER_MIN_UNANSWERED_INQUIRIES", "6"))
    VOICE_REMINDER_MIN_UNANSWERED_RATE: float = float(os.getenv("VOICE_REMINDER_MIN_UNANSWERED_RATE", "0.6"))  # 60%
    VOICE_REMINDER_MIN_INTERVAL_MINUTES: int = int(os.getenv("VOICE_REMINDER_MIN_INTERVAL_MINUTES", "1440"))  # 24 hours cooldown
    VOICE_REMINDER_MAX_CALLS_PER_DAY: int = int(os.getenv("VOICE_REMINDER_MAX_CALLS_PER_DAY", "1"))
    VOICE_REMINDER_TEMPLATE: str = os.getenv(
        "VOICE_REMINDER_TEMPLATE",
        "سلام. این تماس از سامانه ترب است. فروشگاه شما در {time_window} گذشته، تعداد {unanswered_count} استعلام از مجموع {total_inquiries} استعلام را بدون پاسخ گذاشته است. لطفاً برای پاسخگویی به استعلامهای جدید، برنامه ترب را بررسی کنید. با تشکر."
    )

settings = Settings()
