from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional

from torob.domain.entities import (
    EvidenceEvent,
    FeedbackCase,
    FeedbackCaseEvent,
    Inquiry,
    InquiryResponse,
    ShopReliability,
)
from torob.domain.enums import CaseOutcome, CaseStatus, FeedbackIssueType, InquiryPriority, InquiryStatus
from torob.storage.db import db_manager


class LedgerRepository:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return db_manager.get_sqlite()

    # --- Evidence Events ---
    def append_evidence_event(self, event: EvidenceEvent):
        query = """
        INSERT INTO evidence_events 
        (event_id, event_type, scope_json, observed_at, ingested_at, source_code, actor_id, payload_json, external_event_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                event.event_id,
                event.event_type,
                json.dumps(event.scope),
                event.observed_at.isoformat() if event.observed_at else None,
                event.ingested_at.isoformat(),
                event.source_code.value,
                event.actor_id,
                json.dumps(event.payload),
                event.external_event_id,
            ),
        )
        self.conn.commit()

    def get_evidence_events(self, event_type: Optional[str] = None, limit: int = 50) -> List[EvidenceEvent]:
        if event_type:
            cursor = self.conn.execute(
                "SELECT * FROM evidence_events WHERE event_type = ? ORDER BY ingested_at DESC LIMIT ?",
                (event_type, limit),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM evidence_events ORDER BY ingested_at DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            EvidenceEvent(
                event_id=r["event_id"],
                event_type=r["event_type"],
                scope=json.loads(r["scope_json"]),
                observed_at=datetime.fromisoformat(r["observed_at"]) if r["observed_at"] else None,
                ingested_at=datetime.fromisoformat(r["ingested_at"]),
                source_code=r["source_code"],
                actor_id=r["actor_id"],
                payload=json.loads(r["payload_json"]),
                external_event_id=r["external_event_id"],
            )
            for r in rows
        ]

    def get_evidence_events_for_offer(self, offer_id: str, limit: int = 100) -> List[EvidenceEvent]:
        """Fetch all evidence events affecting a specific offer, ordered chronologically."""
        cursor = self.conn.execute(
            "SELECT * FROM evidence_events WHERE json_extract(scope_json, '$.offer_id') = ? ORDER BY ingested_at ASC LIMIT ?",
            (offer_id, limit),
        )
        rows = cursor.fetchall()
        return [
            EvidenceEvent(
                event_id=r["event_id"],
                event_type=r["event_type"],
                scope=json.loads(r["scope_json"]),
                observed_at=datetime.fromisoformat(r["observed_at"]) if r["observed_at"] else None,
                ingested_at=datetime.fromisoformat(r["ingested_at"]),
                source_code=r["source_code"],
                actor_id=r["actor_id"],
                payload=json.loads(r["payload_json"]),
                external_event_id=r["external_event_id"],
            )
            for r in rows
        ]

    def get_evidence_events_for_shop(self, shop_id: str, limit: int = 100) -> List[EvidenceEvent]:
        """Fetch all evidence events affecting a specific shop, ordered chronologically."""
        cursor = self.conn.execute(
            "SELECT * FROM evidence_events WHERE json_extract(scope_json, '$.shop_id') = ? ORDER BY ingested_at ASC LIMIT ?",
            (shop_id, limit),
        )
        rows = cursor.fetchall()
        return [
            EvidenceEvent(
                event_id=r["event_id"],
                event_type=r["event_type"],
                scope=json.loads(r["scope_json"]),
                observed_at=datetime.fromisoformat(r["observed_at"]) if r["observed_at"] else None,
                ingested_at=datetime.fromisoformat(r["ingested_at"]),
                source_code=r["source_code"],
                actor_id=r["actor_id"],
                payload=json.loads(r["payload_json"]),
                external_event_id=r["external_event_id"],
            )
            for r in rows
        ]

    # --- Inquiries ---
    def create_inquiry(self, inquiry: Inquiry):
        query = """
        INSERT INTO inquiries
        (inquiry_id, shop_id, offer_id, product_id, question_scope_json, status, priority, dedupe_key, requested_at, deadline_at, policy_version, delivery_attempts, cancellation_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                inquiry.inquiry_id,
                inquiry.shop_id,
                inquiry.offer_id,
                inquiry.product_id,
                json.dumps(inquiry.question_scope),
                inquiry.status.value,
                inquiry.priority.value,
                inquiry.dedupe_key,
                inquiry.requested_at.isoformat(),
                inquiry.deadline_at.isoformat(),
                inquiry.policy_version,
                inquiry.delivery_attempts,
                inquiry.cancellation_reason,
            ),
        )
        self.conn.commit()

    def get_inquiry(self, inquiry_id: str) -> Optional[Inquiry]:
        cursor = self.conn.execute("SELECT * FROM inquiries WHERE inquiry_id = ?", (inquiry_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_inquiry(row)

    def find_inquiry_by_dedupe_key(self, dedupe_key: str) -> Optional[Inquiry]:
        cursor = self.conn.execute(
            """
            SELECT * FROM inquiries 
            WHERE dedupe_key = ? 
              AND status IN ('created', 'queued', 'delivered')
            ORDER BY requested_at DESC LIMIT 1
            """,
            (dedupe_key,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_inquiry(row)

    def get_active_inquiries_for_shop(self, shop_id: str) -> List[Inquiry]:
        cursor = self.conn.execute(
            "SELECT * FROM inquiries WHERE shop_id = ? AND status IN ('created', 'queued', 'delivered') ORDER BY requested_at DESC",
            (shop_id,),
        )
        return [self._row_to_inquiry(r) for r in cursor.fetchall()]

    def update_inquiry_status(self, inquiry_id: str, status: InquiryStatus, cancellation_reason: Optional[str] = None):
        self.conn.execute(
            "UPDATE inquiries SET status = ?, cancellation_reason = ? WHERE inquiry_id = ?",
            (status.value, cancellation_reason, inquiry_id),
        )
        self.conn.commit()

    def record_delivery_attempt(self, attempt_id: str, inquiry_id: str, provider: str, status: str, failure_reason: Optional[str] = None):
        now_str = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO inquiry_delivery_attempts (attempt_id, inquiry_id, provider, status, queued_at, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (attempt_id, inquiry_id, provider, status, now_str, failure_reason),
        )
        self.conn.execute("UPDATE inquiries SET delivery_attempts = delivery_attempts + 1 WHERE inquiry_id = ?", (inquiry_id,))
        self.conn.commit()

    def save_inquiry_response(self, response: InquiryResponse):
        query = """
        INSERT INTO inquiry_responses
        (response_id, inquiry_id, actor_id, observed_at, ingested_at, status, scope_json, answer_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                response.response_id,
                response.inquiry_id,
                response.actor_id,
                response.observed_at.isoformat() if response.observed_at else None,
                response.ingested_at.isoformat(),
                response.status,
                json.dumps(response.scope),
                json.dumps(response.answer),
            ),
        )
        self.conn.commit()

    def get_inquiry_responses(self, inquiry_id: str) -> List[InquiryResponse]:
        cursor = self.conn.execute(
            "SELECT * FROM inquiry_responses WHERE inquiry_id = ? ORDER BY ingested_at DESC",
            (inquiry_id,),
        )
        return [
            InquiryResponse(
                response_id=r["response_id"],
                inquiry_id=r["inquiry_id"],
                actor_id=r["actor_id"],
                observed_at=datetime.fromisoformat(r["observed_at"]) if r["observed_at"] else None,
                ingested_at=datetime.fromisoformat(r["ingested_at"]),
                status=r["status"],
                scope=json.loads(r["scope_json"]),
                answer=json.loads(r["answer_json"]),
            )
            for r in cursor.fetchall()
        ]

    # --- Feedback Cases ---
    def create_feedback_case(self, case: FeedbackCase):
        query = """
        INSERT INTO feedback_cases
        (case_id, shop_id, offer_id, product_id, visit_at, opened_at, case_status, outcome, issue_type, reporter_token, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                case.case_id,
                case.shop_id,
                case.offer_id,
                case.product_id,
                case.visit_at.isoformat() if case.visit_at else None,
                case.opened_at.isoformat(),
                case.case_status.value,
                case.outcome.value,
                case.issue_type.value,
                case.reporter_token,
                case.notes,
            ),
        )
        self.conn.commit()

    def get_feedback_case(self, case_id: str) -> Optional[FeedbackCase]:
        cursor = self.conn.execute("SELECT * FROM feedback_cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return FeedbackCase(
            case_id=row["case_id"],
            shop_id=row["shop_id"],
            offer_id=row["offer_id"],
            product_id=row["product_id"],
            visit_at=datetime.fromisoformat(row["visit_at"]) if row["visit_at"] else None,
            opened_at=datetime.fromisoformat(row["opened_at"]),
            case_status=CaseStatus(row["case_status"]),
            outcome=CaseOutcome(row["outcome"]),
            issue_type=FeedbackIssueType(row["issue_type"]),
            reporter_token=row["reporter_token"],
            notes=row["notes"],
        )

    def update_case_status(self, case_id: str, status: CaseStatus, outcome: CaseOutcome, notes: Optional[str] = None):
        self.conn.execute(
            "UPDATE feedback_cases SET case_status = ?, outcome = ?, notes = COALESCE(?, notes) WHERE case_id = ?",
            (status.value, outcome.value, notes, case_id),
        )
        self.conn.commit()

    def append_case_event(self, event: FeedbackCaseEvent):
        query = """
        INSERT INTO feedback_case_events
        (case_event_id, case_id, event_type, actor_role, observed_at, recorded_at, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                event.case_event_id,
                event.case_id,
                event.event_type,
                event.actor_role,
                event.observed_at.isoformat() if event.observed_at else None,
                event.recorded_at.isoformat(),
                json.dumps(event.payload),
            ),
        )
        self.conn.commit()

    def get_case_events(self, case_id: str) -> List[FeedbackCaseEvent]:
        cursor = self.conn.execute(
            "SELECT * FROM feedback_case_events WHERE case_id = ? ORDER BY recorded_at ASC",
            (case_id,),
        )
        return [
            FeedbackCaseEvent(
                case_event_id=r["case_event_id"],
                case_id=r["case_id"],
                event_type=r["event_type"],
                actor_role=r["actor_role"],
                observed_at=datetime.fromisoformat(r["observed_at"]) if r["observed_at"] else None,
                recorded_at=datetime.fromisoformat(r["recorded_at"]),
                payload=json.loads(r["payload_json"]),
            )
            for r in cursor.fetchall()
        ]

    # --- Shop Reliability State ---
    def get_shop_reliability(self, shop_id: str) -> Optional[ShopReliability]:
        cursor = self.conn.execute(
            "SELECT * FROM shop_reliability_state WHERE shop_id = ?",
            (shop_id,),
        )
        r = cursor.fetchone()
        if not r:
            return None
        return ShopReliability(
            shop_id=r["shop_id"],
            commercial_trust_score=r["commercial_trust_score"],
            price_fidelity_score=r["price_fidelity_score"],
            stock_accuracy_score=r["stock_accuracy_score"],
            physical_presence_score=r["physical_presence_score"],
            inquiry_responsiveness_score=r["inquiry_responsiveness_score"],
            address_accuracy_score=r["address_accuracy_score"],
            composite_reliability_score=r["composite_reliability_score"],
            observation_count=r["observation_count"],
            last_updated_at=datetime.fromisoformat(r["last_updated_at"]),
        )

    def upsert_shop_reliability(self, rel: ShopReliability):
        query = """
        INSERT INTO shop_reliability_state 
        (shop_id, commercial_trust_score, price_fidelity_score, stock_accuracy_score, physical_presence_score, inquiry_responsiveness_score, address_accuracy_score, composite_reliability_score, observation_count, last_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(shop_id) DO UPDATE SET
            commercial_trust_score = excluded.commercial_trust_score,
            price_fidelity_score = excluded.price_fidelity_score,
            stock_accuracy_score = excluded.stock_accuracy_score,
            physical_presence_score = excluded.physical_presence_score,
            inquiry_responsiveness_score = excluded.inquiry_responsiveness_score,
            address_accuracy_score = excluded.address_accuracy_score,
            composite_reliability_score = excluded.composite_reliability_score,
            observation_count = excluded.observation_count,
            last_updated_at = excluded.last_updated_at
        """
        self.conn.execute(
            query,
            (
                rel.shop_id,
                rel.commercial_trust_score,
                rel.price_fidelity_score,
                rel.stock_accuracy_score,
                rel.physical_presence_score,
                rel.inquiry_responsiveness_score,
                rel.address_accuracy_score,
                rel.composite_reliability_score,
                rel.observation_count,
                rel.last_updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def _row_to_inquiry(self, row: sqlite3.Row) -> Inquiry:
        return Inquiry(
            inquiry_id=row["inquiry_id"],
            shop_id=row["shop_id"],
            offer_id=row["offer_id"],
            product_id=row["product_id"],
            question_scope=json.loads(row["question_scope_json"]),
            status=InquiryStatus(row["status"]),
            priority=InquiryPriority(row["priority"]),
            dedupe_key=row["dedupe_key"],
            requested_at=datetime.fromisoformat(row["requested_at"]),
            deadline_at=datetime.fromisoformat(row["deadline_at"]),
            policy_version=row["policy_version"],
            delivery_attempts=row["delivery_attempts"],
            cancellation_reason=row["cancellation_reason"],
        )

    # --- Snapshot Manifests & Offer Observations ---
    def record_snapshot_manifest(
        self,
        snapshot_id: str,
        source_name: str,
        record_count: int,
        checksum: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        query = """
        INSERT INTO snapshot_manifests (snapshot_id, source_name, created_at, record_count, checksum, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET
            record_count = excluded.record_count,
            checksum = excluded.checksum,
            metadata_json = excluded.metadata_json
        """
        self.conn.execute(
            query,
            (snapshot_id, source_name, ts, record_count, checksum, json.dumps(metadata or {})),
        )
        self.conn.commit()

    def record_offer_observations(self, observations: List[Dict[str, Any]]):
        if not observations:
            return
        query = """
        INSERT INTO offer_observations 
        (observation_id, snapshot_id, offer_id, shop_id, product_id, price_toman, availability_status, observed_at, is_price_changed, previous_price_toman, observation_interval_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(observation_id) DO NOTHING
        """
        params = [
            (
                obs["observation_id"],
                obs["snapshot_id"],
                obs["offer_id"],
                obs["shop_id"],
                obs["product_id"],
                obs.get("price_toman"),
                obs.get("availability_status", "unknown"),
                obs["observed_at"],
                1 if obs.get("is_price_changed") else 0,
                obs.get("previous_price_toman"),
                obs.get("observation_interval_hours"),
            )
            for obs in observations
        ]
        self.conn.executemany(query, params)
        self.conn.commit()

    def get_offer_observations(self, offer_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM offer_observations WHERE offer_id = ? ORDER BY observed_at ASC LIMIT ?",
            (offer_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    def get_shop_observations(self, shop_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM offer_observations WHERE shop_id = ? ORDER BY observed_at DESC LIMIT ?",
            (shop_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    # --- Policy Decisions ---
    def record_policy_decision(
        self,
        decision_id: str,
        scope: Dict[str, Any],
        action_code: str,
        reason_codes: List[str],
        policy_version: str,
        selection_probability: Optional[float] = None,
        selection_trigger: str = "heuristic_risk",
        expected_benefit: Optional[float] = None,
        expected_cost: Optional[float] = None,
        risk_features: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        query = """
        INSERT INTO policy_decisions 
        (decision_id, created_at, scope_json, action_code, reason_codes_json, policy_version, selection_probability, selection_trigger, expected_benefit, expected_cost, risk_features_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(
            query,
            (
                decision_id,
                ts,
                json.dumps(scope),
                action_code,
                json.dumps(reason_codes),
                policy_version,
                selection_probability,
                selection_trigger,
                expected_benefit,
                expected_cost,
                json.dumps(risk_features or {}),
            ),
        )
        self.conn.commit()

    def get_policy_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM policy_decisions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["scope"] = json.loads(d.pop("scope_json"))
            d["reason_codes"] = json.loads(d.pop("reason_codes_json"))
            d["risk_features"] = json.loads(d.pop("risk_features_json", "{}") or "{}")
            results.append(d)
        return results

    # --- Quality Alerts ---
    def record_quality_alert(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        entity_type: str,
        entity_id: str,
        payload: Dict[str, Any],
        created_at: Optional[datetime] = None,
    ):
        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        query = """
        INSERT INTO quality_alerts (alert_id, alert_type, severity, entity_type, entity_id, created_at, payload_json, is_resolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """
        self.conn.execute(
            query,
            (alert_id, alert_type, severity, entity_type, entity_id, ts, json.dumps(payload)),
        )
        self.conn.commit()

    def get_quality_alerts(self, unresolved_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        if unresolved_only:
            cursor = self.conn.execute(
                "SELECT * FROM quality_alerts WHERE is_resolved = 0 ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM quality_alerts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json"))
            results.append(d)
        return results

    def resolve_quality_alert(self, alert_id: str):
        self.conn.execute("UPDATE quality_alerts SET is_resolved = 1 WHERE alert_id = ?", (alert_id,))
        self.conn.commit()

    # --- External Trust Evidence ---
    def record_external_trust_evidence(
        self,
        trust_evidence_id: str,
        shop_id: str,
        source_name: str,
        scope: str,
        verified_at: datetime,
        expires_at: Optional[datetime] = None,
        verification_method: Optional[str] = None,
        raw_evidence: Optional[Dict[str, Any]] = None,
        branch_id: Optional[str] = None,
    ):
        query = """
        INSERT INTO external_trust_evidence 
        (trust_evidence_id, shop_id, branch_id, source_name, scope, verified_at, expires_at, verification_method, raw_evidence_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trust_evidence_id) DO NOTHING
        """
        self.conn.execute(
            query,
            (
                trust_evidence_id,
                shop_id,
                branch_id,
                source_name,
                scope,
                verified_at.isoformat(),
                expires_at.isoformat() if expires_at else None,
                verification_method,
                json.dumps(raw_evidence or {}),
            ),
        )
        self.conn.commit()

    def get_external_trust_evidence(self, shop_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM external_trust_evidence WHERE shop_id = ? ORDER BY verified_at DESC",
            (shop_id,),
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["raw_evidence"] = json.loads(d.pop("raw_evidence_json", "{}") or "{}")
            results.append(d)
        return results

    # --- Recommendation Decisions & Outcomes ---
    def record_recommendation_decision(
        self,
        decision_id: str,
        session_id: str,
        objective: str,
        constraints: Dict[str, Any],
        candidate_product_ids: List[str],
        selected_product_ids: List[str],
        ranking_policy_version: str,
        warnings: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ):
        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        query = """
        INSERT INTO recommendation_decisions
        (decision_id, session_id, created_at, objective, constraints_json, candidate_product_ids_json, selected_product_ids_json, ranking_policy_version, warnings_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(decision_id) DO NOTHING
        """
        self.conn.execute(
            query,
            (
                decision_id,
                session_id,
                ts,
                objective,
                json.dumps(constraints),
                json.dumps(candidate_product_ids),
                json.dumps(selected_product_ids),
                ranking_policy_version,
                json.dumps(warnings or []),
            ),
        )
        self.conn.commit()

    def record_recommendation_outcome(
        self,
        outcome_id: str,
        decision_id: str,
        session_id: str,
        outcome_type: str,
        product_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        recorded_at: Optional[datetime] = None,
    ):
        ts = (recorded_at or datetime.now(timezone.utc)).isoformat()
        query = """
        INSERT INTO recommendation_outcomes
        (outcome_id, decision_id, session_id, outcome_type, product_id, recorded_at, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(outcome_id) DO NOTHING
        """
        self.conn.execute(
            query,
            (outcome_id, decision_id, session_id, outcome_type, product_id, ts, json.dumps(payload or {})),
        )
        self.conn.commit()

    def get_recommendation_outcomes_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM recommendation_outcomes WHERE session_id = ? ORDER BY recorded_at ASC",
            (session_id,),
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json", "{}") or "{}")
            results.append(d)
        return results

