import uuid
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.error

from config import settings
from services.voice.models import (
    GeneratedAudio,
    OutboundCallOptions,
    OutboundCallResult,
    CallStatus,
    CallScenario
)
from services.voice.phone_utils import normalize_phone_number, mask_phone_number

logger = logging.getLogger("outbound_call_provider")


class OutboundCallProvider(ABC):
    """
    Abstract Base Class for Outbound Telephony Providers.
    Abstracts provider-specific API payloads and network protocols.
    """

    @abstractmethod
    async def place_call(
        self,
        destination_number: str,
        audio: GeneratedAudio,
        options: Optional[OutboundCallOptions] = None
    ) -> OutboundCallResult:
        """
        Initiate an outbound call to the given destination number.
        """
        pass


class MockOutboundCallProvider(OutboundCallProvider):
    """
    In-memory Mock Outbound Call Provider for safe automated testing and local development.
    Guarantees that NO real cellular or PSTN telephone calls are made during tests or CI.
    """

    def __init__(self):
        self.dispatched_calls: List[Dict[str, Any]] = []
        self.force_failure_code: Optional[str] = None

    async def place_call(
        self,
        destination_number: str,
        audio: GeneratedAudio,
        options: Optional[OutboundCallOptions] = None
    ) -> OutboundCallResult:
        clean_num = normalize_phone_number(destination_number)
        call_id = f"mock_call_{uuid.uuid4().hex[:10]}"
        provider_call_id = f"poshtyar_mock_{uuid.uuid4().hex[:8]}"
        opts = options or OutboundCallOptions()

        if self.force_failure_code:
            logger.warning(f"[MOCK CALL] Simulating forced provider failure: {self.force_failure_code}")
            return OutboundCallResult(
                call_id=call_id,
                provider="mock",
                status=CallStatus.FAILED,
                message=f"Simulated failure ({self.force_failure_code})",
                provider_call_id=None,
                error_code=self.force_failure_code
            )

        call_record = {
            "call_id": call_id,
            "provider_call_id": provider_call_id,
            "destination_number": clean_num,
            "options": opts,
            "audio_format": audio.format,
            "audio_duration": audio.duration_seconds,
            "audio_text": audio.text,
            "status": CallStatus.CALL_REQUESTED
        }
        self.dispatched_calls.append(call_record)

        logger.info(
            f"[MOCK CALL] Initiated call {call_id} to {mask_phone_number(clean_num)} "
            f"via Mock Provider for scenario: {opts.scenario.value}"
        )

        return OutboundCallResult(
            call_id=call_id,
            provider="mock",
            status=CallStatus.CALL_REQUESTED,
            message="تماس آزمایشی با موفقیت در صف شبیه‌سازی قرار گرفت",
            provider_call_id=provider_call_id,
            raw_response={"status": "success", "mock": True, "call_id": provider_call_id}
        )


class PoshteyarOutboundCallProvider(OutboundCallProvider):
    """
    Poshteyar Outbound Telephony Provider.
    Implements official 'originate-api' endpoint:
    POST https://api.poshtyar.com/api/v1/external/calls/originate
    Headers:
      Content-Type: application/json
      X-API-KEY: {POSHTYAR_API_KEY}
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        operator_id: Optional[str] = None
    ):
        self.api_url = api_url or settings.POSHTYAR_API_URL
        self.api_key = api_key or settings.POSHTYAR_API_KEY
        self.operator_id = operator_id or settings.POSHTYAR_OPERATOR_ID

    def _sync_http_post(self, payload: dict) -> Dict[str, Any]:
        """Execute synchronous HTTP POST request with proper Poshteyar headers."""
        if not self.api_key:
            raise ValueError("POSHTYAR_API_KEY is not configured on server.")
        if not self.operator_id:
            raise ValueError("POSHTYAR_OPERATOR_ID is not configured on server.")

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
            "User-Agent": "TorobSellerBackend/1.0"
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                resp_body = resp.read().decode("utf-8")
                return {
                    "status_code": resp.status,
                    "body": json.loads(resp_body) if resp_body else {}
                }
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8") if he.fp else ""
            try:
                parsed_err = json.loads(err_body)
            except Exception:
                parsed_err = {"raw_error": err_body}
            return {
                "status_code": he.code,
                "error": parsed_err
            }
        except Exception as e:
            logger.error(f"Network error connecting to Poshteyar originate API: {e}")
            return {
                "status_code": 0,
                "error": {"message": str(e)}
            }

    async def place_call(
        self,
        destination_number: str,
        audio: GeneratedAudio,
        options: Optional[OutboundCallOptions] = None
    ) -> OutboundCallResult:
        clean_num = normalize_phone_number(destination_number)
        call_id = f"poshtyar_{uuid.uuid4().hex[:10]}"
        opts = options or OutboundCallOptions()

        # Build official Poshteyar request payload according to documentation
        payload: Dict[str, Any] = {
            "phone_number": clean_num,
            "operator_id": self.operator_id,
            "recipient_name": opts.recipient_name or "",
            "topic": opts.topic or "اعلان صوتی ترب",
            "description": opts.description or f"سناریوی تماس: {opts.scenario.value}",
            "opener_text": audio.text,
            "outbound_type": opts.outbound_type or "announcement"
        }

        if opts.retry_policy:
            payload["retry_policy"] = opts.retry_policy

        if audio.audio_key:
            payload["audio_key"] = audio.audio_key

        logger.info(
            f"[POSHTYAR] Initiating outbound call to {mask_phone_number(clean_num)} "
            f"(scenario={opts.scenario.value}, type={payload['outbound_type']})"
        )

        # Execute network call in async thread pool
        resp = await asyncio.to_thread(self._sync_http_post, payload)
        status_code = resp.get("status_code", 0)

        if status_code == 200:
            body = resp.get("body", {})
            provider_call_id = body.get("call_id") or body.get("id")
            logger.info(f"[POSHTYAR] Call successfully queued by provider. ProviderCallID: {provider_call_id}")
            return OutboundCallResult(
                call_id=call_id,
                provider="poshteyar",
                status=CallStatus.CALL_REQUESTED,
                message=body.get("message", "تماس خروجی با موفقیت در صف پشتیار قرار گرفت"),
                provider_call_id=provider_call_id,
                raw_response=body
            )
        else:
            err_dict = resp.get("error", {})
            err_msg = err_dict.get("error") or err_dict.get("message") or f"HTTP {status_code}"
            logger.error(f"[POSHTYAR] Call origination failed with status {status_code}: {err_msg}")
            
            error_code = "HTTP_ERROR"
            if status_code == 400:
                error_code = "BAD_REQUEST"
            elif status_code == 401:
                error_code = "UNAUTHORIZED"
            elif status_code == 403:
                error_code = "FORBIDDEN"
            elif status_code == 500:
                error_code = "INSUFFICIENT_CREDIT_OR_SERVER_ERROR"
            elif status_code == 0:
                error_code = "NETWORK_TIMEOUT"

            return OutboundCallResult(
                call_id=call_id,
                provider="poshteyar",
                status=CallStatus.FAILED,
                message=str(err_msg),
                error_code=error_code,
                raw_response=err_dict
            )


# Global mock provider instance for testing inspection
_mock_provider_instance: Optional[MockOutboundCallProvider] = None


def get_outbound_call_provider(provider_name: Optional[str] = None) -> OutboundCallProvider:
    """Factory to retrieve configured Outbound Call Provider."""
    global _mock_provider_instance
    chosen = (provider_name or settings.OUTBOUND_CALL_PROVIDER).lower()

    if chosen == "poshteyar" and settings.POSHTYAR_ENABLED:
        return PoshteyarOutboundCallProvider()
    else:
        if _mock_provider_instance is None:
            _mock_provider_instance = MockOutboundCallProvider()
        return _mock_provider_instance
