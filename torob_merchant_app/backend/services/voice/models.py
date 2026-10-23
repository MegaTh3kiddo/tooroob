from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class CallScenario(str, Enum):
    LANDLINE_OTP = "LANDLINE_OTP"
    UNANSWERED_INQUIRY_REMINDER = "UNANSWERED_INQUIRY_REMINDER"


class CallStatus(str, Enum):
    PENDING = "PENDING"
    AUDIO_GENERATION = "AUDIO_GENERATION"
    CALL_REQUESTED = "CALL_REQUESTED"
    CALLING = "CALLING"
    ANSWERED = "ANSWERED"
    BUSY = "BUSY"
    NO_ANSWER = "NO_ANSWER"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class DeliveryMethod(str, Enum):
    SMS = "sms"
    VOICE_CALL = "voice_call"


@dataclass
class TtsOptions:
    language: str = "fa-IR"
    speaking_rate: float = 0.95
    voice_name: Optional[str] = None
    audio_format: str = "wav"  # "wav" or "mp3"
    sample_rate: int = 16000


@dataclass
class GeneratedAudio:
    audio_content: bytes = b""
    format: str = "wav"
    duration_seconds: float = 0.0
    sample_rate: int = 16000
    text: str = ""
    file_path: Optional[str] = None
    audio_key: Optional[str] = None
    audio_url: Optional[str] = None


@dataclass
class OutboundCallOptions:
    recipient_name: Optional[str] = None
    topic: Optional[str] = None
    description: Optional[str] = None
    retry_policy: Optional[List[int]] = None
    outbound_type: str = "announcement"  # "announcement", "audio_file", "ai"
    store_id: Optional[str] = None
    scenario: CallScenario = CallScenario.LANDLINE_OTP


@dataclass
class OutboundCallResult:
    call_id: str
    provider: str
    status: CallStatus
    message: str
    provider_call_id: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
