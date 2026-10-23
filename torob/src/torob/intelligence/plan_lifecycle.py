"""Shopping Plan Invalidation, Re-evaluation & Evidence Lifecycle Management.

Tracks generated shopping plans across dynamic lifecycle events:
1. Baseline Offer & Evidence Version Snapshot:
   - Records product IDs, offer IDs, prices, and stock states at the moment of plan creation.
2. Grouped Seller Inquiries:
   - Dispatches authorized grouped inquiries to verify multiple basket items simultaneously.
3. Seller Response Integration:
   - Processes seller answers (confirmed stock, out-of-stock, price updates).
   - Updates item-level evidence states: listed_in_catalog -> seller_confirmed or confirmed_unavailable.
4. Plan Invalidation & Confidence Reassessment:
   - Re-evaluates composite plan scores, warnings, and guarantee status without erasing original history.
   - Provides full audit trail of evidence updates.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from torob.domain.plans import BasketItemMatch, MultiStoreBasketPlan, ShopBasketCoverage
from torob.domain.enums import InquiryPriority, InquiryStatus, StockState
from torob.inquiries.service import InquiryService
from torob.intelligence.plan_recovery import AdaptivePlanRecoveryEngine, PlanAdaptationResult
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.intelligence.plan_lifecycle")


class ShoppingPlanLifecycleManager:
    def __init__(
        self,
        inquiry_service: Optional[InquiryService] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        catalog_repo: Optional[CatalogRepository] = None,
        recovery_engine: Optional[AdaptivePlanRecoveryEngine] = None,
    ):
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.inquiry_service = inquiry_service or InquiryService(ledger_repo=self.ledger_repo)
        self.recovery_engine = recovery_engine or AdaptivePlanRecoveryEngine(
            catalog_repo=self.catalog_repo, ledger_repo=self.ledger_repo
        )
        # Store plans in memory/ledger session cache: plan_id -> (plan, audit_history)
        self._plan_registry: Dict[str, Tuple[MultiStoreBasketPlan, List[Dict[str, Any]]]] = {}

    def register_plan(self, plan: MultiStoreBasketPlan) -> MultiStoreBasketPlan:
        """Registers a newly generated plan and snapshots its initial evidence state."""
        snapshot = {
            "version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "plan_created",
            "all_items_covered": plan.all_items_covered,
            "composite_score": plan.composite_score,
            "guarantee_status": plan.guarantee_status,
        }
        self._plan_registry[plan.plan_id] = (plan.model_copy(deep=True), [snapshot])
        return plan

    def get_plan(self, plan_id: str) -> Optional[MultiStoreBasketPlan]:
        if plan_id in self._plan_registry:
            return self._plan_registry[plan_id][0]
        return None

    def get_audit_history(self, plan_id: str) -> List[Dict[str, Any]]:
        if plan_id in self._plan_registry:
            return self._plan_registry[plan_id][1]
        return []

    def dispatch_authorized_basket_inquiry(
        self,
        plan_id: str,
        shop_id: str,
        user_authorized: bool = True,
        priority: InquiryPriority = InquiryPriority.HIGH,
    ) -> Dict[str, Any]:
        """Creates a consolidated inquiry for unverified basket items at a shop with explicit user authorization."""
        if not user_authorized:
            raise PermissionError("User authorization required before contacting seller")

        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Find target shop in plan
        target_store = next((s for s in plan.stores if s.shop_id == shop_id), None)
        if not target_store:
            raise ValueError(f"Shop {shop_id} is not part of plan {plan_id}")

        unverified_items = [m for m in target_store.matched_items if not m.is_verified_in_store]
        if not unverified_items:
            return {
                "inquiry_id": None,
                "status": "already_verified",
                "message": "All items at this store are already confirmed by seller",
            }

        question_scope = {
            "type": "multi_item_basket",
            "plan_id": plan_id,
            "product_ids": [m.matched_product_id for m in unverified_items],
            "product_titles": [m.matched_product_title for m in unverified_items],
            "total_listed_price_toman": sum(m.price_toman or 0.0 for m in unverified_items),
        }

        inquiry, is_new = self.inquiry_service.create_inquiry(
            shop_id=shop_id,
            product_id=unverified_items[0].matched_product_id,
            offer_id=unverified_items[0].offer_id,
            question_scope=question_scope,
            priority=priority,
        )

        history = self._plan_registry[plan_id][1]
        history.append({
            "version": len(history) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "inquiry_dispatched",
            "inquiry_id": inquiry.inquiry_id,
            "shop_id": shop_id,
            "items_count": len(unverified_items),
        })

        return {
            "inquiry_id": inquiry.inquiry_id,
            "status": inquiry.status.value,
            "items_queried": len(unverified_items),
            "is_new": is_new,
        }

    def process_seller_response_and_update_plan(
        self,
        plan_id: str,
        inquiry_id: str,
        actor_id: str,
        item_stock_results: Dict[str, bool],  # product_id -> bool
        confirmed_price_toman: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> MultiStoreBasketPlan:
        """Processes seller response, persists evidence, updates item statuses, and re-evaluates plan validity."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Record response in inquiry service
        first_confirmed = all(item_stock_results.values()) if item_stock_results else False
        stock_state = StockState.IN_STORE_SELLABLE if first_confirmed else StockState.UNKNOWN
        self.inquiry_service.submit_seller_response(
            inquiry_id=inquiry_id,
            actor_id=actor_id,
            confirmed_price=confirmed_price_toman,
            confirmed_stock_state=stock_state,
            shop_is_open=True,
            notes=notes,
        )

        updated_plan = plan.model_copy(deep=True)
        any_rejected = False
        all_confirmed = True

        for store in updated_plan.stores:
            for item in store.matched_items:
                if item.matched_product_id in item_stock_results:
                    is_in_stock = item_stock_results[item.matched_product_id]
                    if is_in_stock:
                        item.stock_evidence = "seller_confirmed"
                        item.is_verified_in_store = True
                        item.evidence_status = "verified_in_store"
                        item.verification_recommendation = "موجودی در انبار فروشگاه توسط فروشنده تایید گردید."
                        if confirmed_price_toman:
                            item.price_toman = confirmed_price_toman
                    else:
                        item.stock_evidence = "confirmed_unavailable"
                        item.is_verified_in_store = False
                        item.evidence_status = "confirmed_unavailable"
                        any_rejected = True
                        all_confirmed = False
                        item.verification_recommendation = "فروشنده عدم موجودی این کالا را اعلام کرد."
                        updated_plan.warnings.append(f"عدم موجودی: {item.matched_product_title[:30]}")

        # Reassess plan
        if any_rejected:
            updated_plan.all_items_covered = False
            updated_plan.guarantee_status = "item_confirmed_unavailable"
            updated_plan.composite_score = round(updated_plan.composite_score * 0.35, 3)
            updated_plan.trade_off_explanation += " ⚠️ هشدار: طبق پاسخ جدید فروشنده، کالا در انبار موجود نیست."
        elif all_confirmed:
            updated_plan.guarantee_status = "seller_confirmed_in_store"
            updated_plan.composite_score = min(1.0, round(updated_plan.composite_score + 0.15, 3))
            updated_plan.trade_off_explanation += " 🛡️ تاییدیه: موجودی انبار فروشگاه توسط فروشنده تایید شد."

        # Audit history snapshot
        history = self._plan_registry[plan_id][1]
        history.append({
            "version": len(history) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "evidence_updated_via_seller",
            "inquiry_id": inquiry_id,
            "all_confirmed": all_confirmed,
            "any_rejected": any_rejected,
            "new_composite_score": updated_plan.composite_score,
            "new_guarantee_status": updated_plan.guarantee_status,
        })

        self._plan_registry[plan_id] = (updated_plan, history)
        return updated_plan

    def adaptive_replan_after_stock_rejection(
        self,
        plan_id: str,
        unavailable_item: str,
        failed_shop_id: Optional[str] = None,
        max_budget_toman: Optional[float] = None,
        max_stops: Optional[int] = None,
    ) -> PlanAdaptationResult:
        """Invokes adaptive plan recovery to replace unavailable item with explainable revision."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found in registry")

        res = self.recovery_engine.recover_after_seller_rejection(
            original_plan=plan,
            unavailable_query_or_title=unavailable_item,
            failed_shop_id=failed_shop_id,
            max_budget_toman=max_budget_toman,
            max_stops=max_stops,
        )

        if res.is_recovered and res.revised_plan:
            # Register the revised plan
            history = self._plan_registry[plan_id][1]
            history.append(res.audit_event)
            self._plan_registry[res.revised_plan.plan_id] = (res.revised_plan, list(history))

        return res

    def adaptive_replan_after_restock(
        self,
        plan_id: str,
        restocked_product_id: str,
        shop_id: str,
    ) -> PlanAdaptationResult:
        """Restores an invalidated plan when a previously unavailable item is restocked."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found in registry")

        res = self.recovery_engine.recover_after_restock(
            invalid_plan=plan,
            restocked_product_id=restocked_product_id,
            shop_id=shop_id,
        )

        if res.is_recovered and res.revised_plan:
            history = self._plan_registry[plan_id][1]
            history.append(res.audit_event)
            self._plan_registry[res.revised_plan.plan_id] = (res.revised_plan, list(history))

        return res

    def adaptive_replan_after_store_rejection(
        self,
        plan_id: str,
        rejected_shop_id: str,
        max_budget_toman: Optional[float] = None,
        max_stops: Optional[int] = None,
    ) -> PlanAdaptationResult:
        """Adapts plan when user requests excluding a particular store."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found in registry")

        res = self.recovery_engine.recover_after_store_rejection(
            original_plan=plan,
            rejected_shop_id=rejected_shop_id,
            max_budget_toman=max_budget_toman,
            max_stops=max_stops,
        )

        if res.is_recovered and res.revised_plan:
            history = self._plan_registry[plan_id][1]
            history.append({"event": "store_rejected_replan", "timestamp": datetime.now(timezone.utc).isoformat()})
            self._plan_registry[res.revised_plan.plan_id] = (res.revised_plan, list(history))

        return res

    def invalidate_plans_for_discrepancy(
        self,
        shop_id: str,
        offer_id: Optional[str] = None,
        issue_type: Optional[str] = None,
    ) -> List[str]:
        """Invalidate or degrade active shopping plans affected by a verified discrepancy."""
        affected_plan_ids = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for plan_id, (plan, history) in list(self._plan_registry.items()):
            plan_shops = [s.shop_id for s in plan.stores]
            if shop_id in plan_shops:
                affected_plan_ids.append(plan_id)
                updated_stores = []
                for s in plan.stores:
                    if s.shop_id == shop_id:
                        updated_matches = []
                        for m in s.matched_items:
                            updated_matches.append(
                                BasketItemMatch(
                                    query=m.query,
                                    matched_product_id=m.matched_product_id,
                                    matched_product_title=m.matched_product_title,
                                    price_toman=m.price_toman,
                                    offer_id=m.offer_id,
                                    seller_confirmed=False,
                                    stock_state=StockState.UNKNOWN if issue_type != "shop_closed" else StockState.OUT_OF_STOCK,
                                )
                            )
                        updated_stores.append(
                            ShopBasketCoverage(
                                shop_id=s.shop_id,
                                shop_name=s.shop_name,
                                shop_address=s.shop_address,
                                lat=s.lat,
                                lon=s.lon,
                                items_covered_count=s.items_covered_count,
                                total_items_requested=s.total_items_requested,
                                covers_entire_basket=s.covers_entire_basket,
                                matched_items=updated_matches,
                                total_listed_price_toman=s.total_listed_price_toman,
                                shop_reliability_score=max(0.1, s.shop_reliability_score - 0.2),
                            )
                        )
                    else:
                        updated_stores.append(s)

                degraded_plan = MultiStoreBasketPlan(
                    plan_id=plan.plan_id,
                    version=plan.version,
                    is_adapted=plan.is_adapted,
                    original_plan_id=plan.original_plan_id,
                    adaptation_reason=f"Degraded due to verified discrepancy: {issue_type or 'unspecified'}",
                    strategy=plan.strategy,
                    stores=updated_stores,
                    total_product_cost_toman=plan.total_product_cost_toman,
                    total_stops=plan.total_stops,
                    all_items_covered=plan.all_items_covered,
                    composite_score=round(max(0.1, plan.composite_score - 0.35), 2),
                    guarantee_status="discrepancy_invalidated_replan_required",
                    warnings=plan.warnings + [f"برنامه به علت گزارش تأییدشده مغایرت در فروشگاه ({shop_id}) نیازمند بازنگری است."],
                )

                history.append({
                    "event": "discrepancy_invalidated",
                    "shop_id": shop_id,
                    "issue_type": issue_type,
                    "timestamp": now_iso,
                })
                self._plan_registry[plan_id] = (degraded_plan, history)

        logger.info(f"Invalidated {len(affected_plan_ids)} active plans for shop {shop_id} discrepancy.")
        return affected_plan_ids

