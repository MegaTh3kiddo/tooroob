from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from torob.core.config import load_policy
from torob.domain.entities import EvidenceEvent, FeedbackCase, FeedbackCaseEvent, ShopReliability
from torob.domain.enums import CaseOutcome, CaseStatus, EvidenceSource, FeedbackIssueType
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.feedback.service")


class FeedbackService:
    def __init__(
        self,
        ledger_repo: Optional[LedgerRepository] = None,
        policy: Optional[Dict[str, Any]] = None,
        plan_lifecycle_manager: Optional[Any] = None,
    ):
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.policy = policy or load_policy()
        self.plan_lifecycle_manager = plan_lifecycle_manager

    def submit_customer_feedback(
        self,
        shop_id: str,
        issue_type: FeedbackIssueType,
        offer_id: Optional[str] = None,
        product_id: Optional[str] = None,
        reporter_token: Optional[str] = None,
        visit_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> FeedbackCase:
        now = now or datetime.now(timezone.utc)
        case_id = f"case_{uuid.uuid4().hex[:12]}"

        # Positive feedback handling
        if issue_type == FeedbackIssueType.SUCCESSFUL_PURCHASE:
            case = FeedbackCase(
                case_id=case_id,
                shop_id=shop_id,
                offer_id=offer_id,
                product_id=product_id,
                visit_at=visit_at,
                opened_at=now,
                case_status=CaseStatus.CLOSED,
                outcome=CaseOutcome.RESOLVED_CORRECT,
                issue_type=issue_type,
                reporter_token=reporter_token,
                notes=notes,
            )
            self.ledger_repo.create_feedback_case(case)

            # Record positive evidence
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="customer_positive_purchase",
                    scope={"shop_id": shop_id, "offer_id": offer_id},
                    observed_at=visit_at or now,
                    source_code=EvidenceSource.CUSTOMER_REPORT,
                    actor_id=reporter_token,
                    payload={"notes": notes},
                )
            )

            # Update shop reliability via Bayesian engine
            self._update_shop_reliability_from_ledger(shop_id, now)

            return case

        # Negative feedback: Opened under review (NO immediate automatic penalty)
        case = FeedbackCase(
            case_id=case_id,
            shop_id=shop_id,
            offer_id=offer_id,
            product_id=product_id,
            visit_at=visit_at,
            opened_at=now,
            case_status=CaseStatus.TRIAGED,
            outcome=CaseOutcome.NOT_YET_DETERMINED,
            issue_type=issue_type,
            reporter_token=reporter_token,
            notes=notes,
        )
        self.ledger_repo.create_feedback_case(case)

        # Log case event
        self.ledger_repo.append_case_event(
            FeedbackCaseEvent(
                case_event_id=f"cev_{uuid.uuid4().hex[:12]}",
                case_id=case_id,
                event_type="feedback_reported",
                actor_role="customer",
                observed_at=visit_at or now,
                recorded_at=now,
                payload={"issue_type": issue_type.value, "notes": notes},
            )
        )

        # Log evidence ledger event
        self.ledger_repo.append_evidence_event(
            EvidenceEvent(
                event_id=f"ev_{uuid.uuid4().hex[:12]}",
                event_type="customer_discrepancy_reported",
                scope={"shop_id": shop_id, "offer_id": offer_id, "issue_type": issue_type.value},
                observed_at=visit_at or now,
                source_code=EvidenceSource.CUSTOMER_REPORT,
                actor_id=reporter_token,
                payload={"issue_type": issue_type.value, "notes": notes},
            )
        )

        return case

    def submit_seller_case_response(
        self,
        case_id: str,
        actor_id: str,
        response_text: str,
        proof_details: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> FeedbackCase:
        now = now or datetime.now(timezone.utc)
        case = self.ledger_repo.get_feedback_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Record seller response event
        self.ledger_repo.append_case_event(
            FeedbackCaseEvent(
                case_event_id=f"cev_{uuid.uuid4().hex[:12]}",
                case_id=case_id,
                event_type="seller_defense_response",
                actor_role="seller",
                observed_at=now,
                recorded_at=now,
                payload={"response_text": response_text, "proof_details": proof_details or {}},
            )
        )

        # Update case status
        self.ledger_repo.update_case_status(
            case_id=case_id,
            status=CaseStatus.SELLER_RESPONDED,
            outcome=case.outcome,
            notes=f"Seller responded: {response_text[:100]}",
        )
        case.case_status = CaseStatus.SELLER_RESPONDED
        return case

    def resolve_case(
        self,
        case_id: str,
        outcome: CaseOutcome,
        resolution_notes: str,
        attribution_cause: str = "seller_misstatement",
        now: Optional[datetime] = None,
    ) -> FeedbackCase:
        now = now or datetime.now(timezone.utc)
        case = self.ledger_repo.get_feedback_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        self.ledger_repo.append_case_event(
            FeedbackCaseEvent(
                case_event_id=f"cev_{uuid.uuid4().hex[:12]}",
                case_id=case_id,
                event_type="case_resolved",
                actor_role="operator",
                observed_at=now,
                recorded_at=now,
                payload={
                    "outcome": outcome.value,
                    "resolution_notes": resolution_notes,
                    "attribution_cause": attribution_cause,
                },
            )
        )

        self.ledger_repo.update_case_status(
            case_id=case_id,
            status=CaseStatus.CLOSED,
            outcome=outcome,
            notes=f"[{attribution_cause}] {resolution_notes}",
        )
        case.case_status = CaseStatus.CLOSED
        case.outcome = outcome

        # If confirmed price/stock error on seller side, adjust shop reliability
        # STRICT MERCHANT FAIRNESS:
        # A merchant is ONLY penalized if:
        # 1. The case outcome confirms an actual price/stock mismatch (RESOLVED_PRICE_UPDATED, RESOLVED_STOCK_UPDATED)
        # 2. AND the causal attribution is definitively proven as 'seller_misstatement'
        # Attribution causes like 'customer_misunderstanding', 'catalogue_sync_delay',
        # 'matching_error', or 'unknown' NEVER reduce seller reliability scores!
        seller_fault = attribution_cause == "seller_misstatement"
        if seller_fault and outcome in (
            CaseOutcome.RESOLVED_PRICE_UPDATED,
            CaseOutcome.RESOLVED_STOCK_UPDATED,
        ):
            if outcome == CaseOutcome.RESOLVED_PRICE_UPDATED:
                dim_key = "price_fidelity"
            elif case.issue_type == FeedbackIssueType.SHOP_CLOSED:
                dim_key = "physical_presence"
            else:
                dim_key = "stock_accuracy"

            # Append verified evidence event to ledger
            self.ledger_repo.append_evidence_event(
                EvidenceEvent(
                    event_id=f"ev_{uuid.uuid4().hex[:12]}",
                    event_type="verified_discrepancy",
                    scope={
                        "shop_id": case.shop_id,
                        "offer_id": case.offer_id,
                        "issue_type": case.issue_type.value,
                        "outcome": outcome.value,
                        "dimension": dim_key,
                    },
                    observed_at=now,
                    source_code=EvidenceSource.OPERATOR_AUDIT,
                    actor_id="operator",
                    payload={"attribution_cause": attribution_cause, "notes": resolution_notes},
                )
            )

            # Update shop reliability using Bayesian conjugate engine
            self._update_shop_reliability_from_ledger(case.shop_id, now)

        # Propagate: Invalidate affected active shopping plans
        if self.plan_lifecycle_manager and outcome in (
            CaseOutcome.RESOLVED_PRICE_UPDATED,
            CaseOutcome.RESOLVED_STOCK_UPDATED,
        ):
            try:
                self.plan_lifecycle_manager.invalidate_plans_for_discrepancy(
                    shop_id=case.shop_id,
                    offer_id=case.offer_id,
                    issue_type=case.issue_type.value,
                )
            except Exception as e:
                logger.warning(f"Could not invalidate plans during feedback resolution: {e}")

        return case

    def _update_shop_reliability_from_ledger(self, shop_id: str, now: datetime):
        """Recompute and persist shop reliability from historical ledger evidence."""
        try:
            from torob.domain.entities import Shop
            from torob.intelligence.shop_reliability import BayesianShopReliabilityEngine

            rel_engine = BayesianShopReliabilityEngine(policy=self.policy)
            rel = self.ledger_repo.get_shop_reliability(shop_id)
            if not rel:
                rel = ShopReliability(shop_id=shop_id, observation_count=0, last_updated_at=now)

            ev_events = self.ledger_repo.get_evidence_events_for_shop(shop_id)
            outcomes_list = []
            for ev in ev_events:
                dim = ev.scope.get("dimension") if isinstance(ev.scope, dict) else None
                is_succ = ev.event_type == "customer_positive_purchase"
                if ev.event_type in ("customer_positive_purchase", "verified_discrepancy"):
                    outcomes_list.append({
                        "dimension": dim or "price_fidelity",
                        "is_success": is_succ,
                        "observed_at": ev.observed_at or now,
                    })

            dummy_shop = Shop(shop_id=shop_id, name="Shop", address="Tehran")
            assessment = rel_engine.assess_shop_reliability(
                shop=dummy_shop,
                reliability_state=rel,
                verified_outcomes=outcomes_list,
                as_of=now,
            )
            rel.observation_count += 1
            rel.price_fidelity_score = assessment.dimensions.get("price_fidelity", rel.price_fidelity_score)
            rel.stock_accuracy_score = assessment.dimensions.get("stock_accuracy", rel.stock_accuracy_score)
            rel.physical_presence_score = assessment.dimensions.get("physical_presence", rel.physical_presence_score)
            rel.last_updated_at = now
            self.ledger_repo.upsert_shop_reliability(rel)
        except Exception as e:
            logger.warning(f"Could not recompute Bayesian shop reliability from ledger: {e}")

    def get_case_with_history(self, case_id: str) -> Dict[str, Any]:
        case = self.ledger_repo.get_feedback_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        events = self.ledger_repo.get_case_events(case_id)
        return {
            "case": case,
            "events": events,
        }
