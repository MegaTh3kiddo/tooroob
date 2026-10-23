from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid

from torob.core.config import load_policy
from torob.domain.entities import EvidenceEvent, Inquiry, InquiryResponse, ShopReliability
from torob.domain.enums import EvidenceSource, InquiryPriority, InquiryStatus, StockState
from torob.inquiries.transport_simulator import NotificationTransportSimulator
from torob.storage.repository_ledger import LedgerRepository


class InquiryService:
    def __init__(
        self,
        ledger_repo: Optional[LedgerRepository] = None,
        policy: Optional[Dict[str, Any]] = None,
    ):
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.policy = policy or load_policy()
        self.transport = NotificationTransportSimulator(self.ledger_repo)
        notif_cfg = self.policy.get("notifications", {})
        self.expire_seconds = notif_cfg.get("inquiry_expire_after_seconds", 900)

    def create_inquiry(
        self,
        shop_id: str,
        offer_id: Optional[str] = None,
        product_id: Optional[str] = None,
        question_scope: Optional[Dict[str, Any]] = None,
        priority: InquiryPriority = InquiryPriority.MEDIUM,
        simulate_transport_failure: bool = False,
        now: Optional[datetime] = None,
    ) -> tuple[Inquiry, bool]:
        now = now or datetime.now(timezone.utc)
        scope = question_scope or {"type": "price_and_stock"}

        # Deduplication key
        dedupe_key = f"{shop_id}:{product_id or 'none'}:{offer_id or 'none'}"

        # Check existing active inquiry
        existing = self.ledger_repo.find_inquiry_by_dedupe_key(dedupe_key)
        if existing and existing.status in (
            InquiryStatus.CREATED,
            InquiryStatus.QUEUED,
            InquiryStatus.DELIVERED,
        ):
            # Check if not expired
            if existing.deadline_at > now:
                # Coalesce / deduplicate
                return existing, False

        inquiry_id = f"inq_{uuid.uuid4().hex[:12]}"
        deadline = now + timedelta(seconds=self.expire_seconds)

        inquiry = Inquiry(
            inquiry_id=inquiry_id,
            shop_id=shop_id,
            offer_id=offer_id,
            product_id=product_id,
            question_scope=scope,
            status=InquiryStatus.CREATED,
            priority=priority,
            dedupe_key=dedupe_key,
            requested_at=now,
            deadline_at=deadline,
            policy_version=self.policy.get("policy_version", "1.0.0"),
        )
        self.ledger_repo.create_inquiry(inquiry)

        # Append evidence event to ledger
        ev = EvidenceEvent(
            event_id=f"ev_{uuid.uuid4().hex[:12]}",
            event_type="inquiry_created",
            scope={"inquiry_id": inquiry_id, "shop_id": shop_id, "offer_id": offer_id},
            observed_at=now,
            source_code=EvidenceSource.SYSTEM_RULE,
            payload={"priority": priority.value, "scope": scope},
        )
        self.ledger_repo.append_evidence_event(ev)

        # Dispatch simulated notification
        delivered = self.transport.send_notification(
            inquiry_id=inquiry_id,
            simulate_failure=simulate_transport_failure,
        )
        new_status = InquiryStatus.DELIVERED if delivered else InquiryStatus.QUEUED
        self.ledger_repo.update_inquiry_status(inquiry_id, new_status)
        inquiry.status = new_status

        return inquiry, True

    def get_inquiry(self, inquiry_id: str) -> Optional[Inquiry]:
        return self.ledger_repo.get_inquiry(inquiry_id)

    def list_shop_inquiries(self, shop_id: str) -> List[Inquiry]:
        return self.ledger_repo.get_active_inquiries_for_shop(shop_id)

    def submit_seller_response(
        self,
        inquiry_id: str,
        actor_id: str,
        confirmed_price: Optional[float] = None,
        confirmed_stock_state: Optional[StockState] = None,
        shop_is_open: Optional[bool] = None,
        notes: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        inquiry = self.ledger_repo.get_inquiry(inquiry_id)
        if not inquiry:
            raise ValueError(f"Inquiry {inquiry_id} not found")

        if inquiry.status == InquiryStatus.EXPIRED:
            raise ValueError("Inquiry has already expired")
        if inquiry.status == InquiryStatus.CANCELLED:
            raise ValueError("Inquiry has been cancelled")

        answer_payload = {
            "confirmed_price": confirmed_price,
            "confirmed_stock_state": confirmed_stock_state.value if confirmed_stock_state else None,
            "shop_is_open": shop_is_open,
            "notes": notes,
        }

        response_id = f"resp_{uuid.uuid4().hex[:12]}"
        resp = InquiryResponse(
            response_id=response_id,
            inquiry_id=inquiry_id,
            actor_id=actor_id,
            observed_at=now,
            status="accepted",
            scope=inquiry.question_scope,
            answer=answer_payload,
        )
        self.ledger_repo.save_inquiry_response(resp)

        # Update inquiry status to ANSWERED
        self.ledger_repo.update_inquiry_status(inquiry_id, InquiryStatus.ANSWERED)

        # Record Evidence Events
        if confirmed_price is not None:
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="seller_price_confirmation",
                    scope={"shop_id": inquiry.shop_id, "offer_id": inquiry.offer_id},
                    observed_at=now,
                    source_code=EvidenceSource.SELLER_CONFIRMATION,
                    actor_id=actor_id,
                    payload={"confirmed_price": confirmed_price},
                )
            )

        if confirmed_stock_state is not None:
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="seller_stock_confirmation",
                    scope={"shop_id": inquiry.shop_id, "offer_id": inquiry.offer_id, "product_id": inquiry.product_id},
                    observed_at=now,
                    source_code=EvidenceSource.SELLER_CONFIRMATION,
                    actor_id=actor_id,
                    payload={"stock_state": confirmed_stock_state.value},
                )
            )

        if shop_is_open is not None:
            # Reusable at branch level! (As per architectural rule 8)
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="seller_branch_open_confirmation",
                    scope={"shop_id": inquiry.shop_id},
                    observed_at=now,
                    source_code=EvidenceSource.SELLER_CONFIRMATION,
                    actor_id=actor_id,
                    payload={"is_open": shop_is_open},
                )
            )

        # Update Shop Reliability state (Seller responded promptly!)
        rel = self.ledger_repo.get_shop_reliability(inquiry.shop_id)
        if not rel:
            rel = ShopReliability(
                shop_id=inquiry.shop_id,
                inquiry_responsiveness_score=0.55,
                observation_count=1,
                last_updated_at=now,
            )
        else:
            rel.observation_count += 1
            rel.inquiry_responsiveness_score = min(1.0, rel.inquiry_responsiveness_score + 0.05)
            rel.last_updated_at = now
        self.ledger_repo.upsert_shop_reliability(rel)

        return {
            "inquiry_id": inquiry_id,
            "response_id": response_id,
            "status": "answered",
            "answer": answer_payload,
        }

    def expire_stale_inquiries(self, now: Optional[datetime] = None) -> int:
        now = now or datetime.now(timezone.utc)
        cursor = self.ledger_repo.conn.execute(
            """
            SELECT inquiry_id FROM inquiries 
            WHERE status IN ('created', 'queued', 'delivered') 
              AND deadline_at < ?
            """,
            (now.isoformat(),),
        )
        expired_ids = [r[0] for r in cursor.fetchall()]
        for inq_id in expired_ids:
            self.ledger_repo.update_inquiry_status(
                inq_id, InquiryStatus.EXPIRED, cancellation_reason="deadline_exceeded"
            )
            # Record audit event: Note that no response is NOT proof of out-of-stock
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="inquiry_expired",
                    scope={"inquiry_id": inq_id},
                    observed_at=now,
                    source_code=EvidenceSource.SYSTEM_RULE,
                    payload={"note": "no_response_is_not_stock_out"},
                )
            )
        return len(expired_ids)


# Helper tuple type
Tuple_Inquiry_IsNew = tuple[Inquiry, bool]
