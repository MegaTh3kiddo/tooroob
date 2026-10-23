import uuid
from typing import Optional

from torob.storage.repository_ledger import LedgerRepository


class NotificationTransportSimulator:
    """Simulates delivery of inquiry notifications to sellers.
    
    In production, this adapter interfaces with FCM, APNS, WebPush, or SMS gateways.
    For local development and testing, it deterministically simulates delivery states.
    """

    def __init__(self, ledger_repo: LedgerRepository):
        self.ledger_repo = ledger_repo

    def send_notification(
        self,
        inquiry_id: str,
        provider: str = "simulated_fcm",
        simulate_failure: bool = False,
    ) -> bool:
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"

        if simulate_failure:
            self.ledger_repo.record_delivery_attempt(
                attempt_id=attempt_id,
                inquiry_id=inquiry_id,
                provider=provider,
                status="failed",
                failure_reason="simulated_device_offline",
            )
            return False

        self.ledger_repo.record_delivery_attempt(
            attempt_id=attempt_id,
            inquiry_id=inquiry_id,
            provider=provider,
            status="delivered",
            failure_reason=None,
        )
        return True
