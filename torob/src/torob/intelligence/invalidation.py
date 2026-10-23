"""Incremental Assessment & Targeted Invalidation Tracker.

When new observations or evidence arrive, determine which assessments, offers,
shopping plans, and inquiry priorities have become stale or invalid, without
recomputing the entire catalog unnecessarily.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger("torob.intelligence.invalidation")


@dataclass
class InvalidationReport:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    affected_offer_ids: Set[str] = field(default_factory=set)
    affected_product_ids: Set[str] = field(default_factory=set)
    affected_shop_ids: Set[str] = field(default_factory=set)
    invalidated_plan_ids: Set[str] = field(default_factory=set)
    stale_inquiry_ids: Set[str] = field(default_factory=set)
    reason: str = "observation_update"


class IncrementalAssessmentTracker:
    def __init__(self):
        self._stale_offers: Set[str] = set()
        self._stale_shops: Set[str] = set()
        self._stale_products: Set[str] = set()

    def mark_offer_stale(self, offer_id: str, product_id: Optional[str] = None, shop_id: Optional[str] = None):
        self._stale_offers.add(offer_id)
        if product_id:
            self._stale_products.add(product_id)
        if shop_id:
            self._stale_shops.add(shop_id)

    def mark_shop_stale(self, shop_id: str):
        self._stale_shops.add(shop_id)

    def track_snapshot_changes(
        self,
        changed_observations: List[Dict],
        all_new_observations: List[Dict],
    ) -> InvalidationReport:
        """Compute targeted invalidation delta following snapshot ingestion."""
        report = InvalidationReport(reason="snapshot_ingestion")
        for obs in changed_observations:
            report.affected_offer_ids.add(obs["offer_id"])
            report.affected_shop_ids.add(obs["shop_id"])
            report.affected_product_ids.add(obs["product_id"])

        self._stale_offers.update(report.affected_offer_ids)
        self._stale_shops.update(report.affected_shop_ids)
        self._stale_products.update(report.affected_product_ids)

        logger.info(
            f"Invalidation tracker identified {len(report.affected_offer_ids)} stale offers, "
            f"{len(report.affected_shop_ids)} stale shops, {len(report.affected_product_ids)} stale products."
        )
        return report

    def flush_stale_entities(self) -> Dict[str, Set[str]]:
        result = {
            "offers": set(self._stale_offers),
            "shops": set(self._stale_shops),
            "products": set(self._stale_products),
        }
        self._stale_offers.clear()
        self._stale_shops.clear()
        self._stale_products.clear()
        return result


invalidation_tracker = IncrementalAssessmentTracker()
