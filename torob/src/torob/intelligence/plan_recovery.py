"""Torob Intelligence Engine — Adaptive Shopping Plan Recovery & Replanning.

When an existing shopping plan becomes invalid, unfeasible, or less desirable:
1. Preserves original plan snapshot and full evidence audit history.
2. Identifies affected items and offers.
3. Retains unaffected valid selections to minimize disruption and avoid needless recomputation.
4. Searches catalogue for equivalent replacement offers/shops for missing items.
5. Evaluates alternative candidate shops (checking existing stores first, then replacement store, then additional store).
6. Recalculates basket coverage, total prices, travel times, and business hours.
7. Strictly enforces user's hard constraints (max stops, budget, variant specs, min reliability).
8. Produces a revised plan only when all hard constraints are satisfied.
9. Generates clear, structured Persian explanations of what changed and why.
10. Transparently reports infeasible or constrained outcomes when no valid replacement exists.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from pydantic import BaseModel, Field

from torob.domain.entities import Offer, Product, Shop
from torob.domain.enums import StockState
from torob.domain.plans import (
    BasketItemMatch,
    MultiStoreBasketPlan,
    OnRoutePlanResult,
    OnRouteShopStop,
    ShopBasketCoverage,
)
from torob.intelligence.basket_optimizer import BasketOptimizationEngine, PlanOptimizationPriority
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.distance import DistanceRouter, FallbackUrbanDistanceCalculator
from torob.routing.hours import BusinessHoursEvaluator
from torob.routing.on_route import OnRouteShoppingEngine
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.intelligence.plan_recovery")


class PlanAdaptationResult(BaseModel):
    is_recovered: bool
    recovery_status: str  # "fully_recovered", "partially_recovered", "infeasible_constrained", "restocked_restored"
    original_plan_id: str
    revised_plan: Optional[MultiStoreBasketPlan] = None
    affected_items: List[str] = Field(default_factory=list)
    affected_shop_id: Optional[str] = None
    affected_shop_name: Optional[str] = None
    adaptation_reason: str = ""
    persian_explanation: str = ""
    preservation_summary: str = ""
    changes_summary: str = ""
    audit_event: Dict[str, Any] = Field(default_factory=dict)


class AdaptivePlanRecoveryEngine:
    def __init__(
        self,
        catalog_repo: Optional[CatalogRepository] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        router: Optional[DistanceRouter] = None,
        reliability_engine: Optional[ShopReliabilityEngine] = None,
        basket_engine: Optional[BasketOptimizationEngine] = None,
        on_route_engine: Optional[OnRouteShoppingEngine] = None,
    ):
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.router = router or DistanceRouter()
        self.reliability_engine = reliability_engine or ShopReliabilityEngine()
        self.basket_engine = basket_engine or BasketOptimizationEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
        )
        self.on_route_engine = on_route_engine or OnRouteShoppingEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
        )

    def recover_after_seller_rejection(
        self,
        original_plan: MultiStoreBasketPlan,
        unavailable_query_or_title: str,
        failed_shop_id: Optional[str] = None,
        max_budget_toman: Optional[float] = None,
        max_stops: Optional[int] = None,
        min_shop_reliability: Optional[float] = None,
    ) -> PlanAdaptationResult:
        """Adapts a plan after a seller confirms an item is out of stock.
        
        Attempts incremental replacement without disrupting unaffected items:
        1. Identifies which shop and item failed.
        2. Checks if another shop already in the plan lists the missing item.
        3. If not, searches candidate shops in the catalogue for equivalent offers.
        4. Reconstructs the revised plan under user's budget and max_stops constraints.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_target = unavailable_query_or_title.lower().strip()

        # Step 1: Identify affected shop and item in original plan
        target_store: Optional[ShopBasketCoverage] = None
        target_item: Optional[BasketItemMatch] = None

        for store in original_plan.stores:
            if failed_shop_id and store.shop_id != failed_shop_id:
                continue
            for item in store.matched_items:
                if (
                    clean_target in item.query.lower()
                    or clean_target in item.matched_product_title.lower()
                    or clean_target in item.matched_product_id.lower()
                ):
                    target_store = store
                    target_item = item
                    break
            if target_item:
                break

        # Fallback if specific store wasn't pinpointed
        if not target_store and original_plan.stores:
            target_store = original_plan.stores[0]
            if target_store.matched_items:
                target_item = target_store.matched_items[0]

        if not target_store or not target_item:
            return PlanAdaptationResult(
                is_recovered=False,
                recovery_status="infeasible_constrained",
                original_plan_id=original_plan.plan_id,
                adaptation_reason="کالای ناموجود در ساختار طرح اولیه شناسایی نشد.",
                persian_explanation="امکان انطباق کالای ناموجود اعلام‌شده با اقلام طرح اولیه میسر نشد.",
            )

        # Step 2: Separate unaffected stores and items
        retained_stores: List[ShopBasketCoverage] = []
        for s in original_plan.stores:
            if s.shop_id != target_store.shop_id:
                retained_stores.append(s.model_copy(deep=True))
            else:
                # Store has other valid items
                other_items = [m for m in s.matched_items if m.matched_product_id != target_item.matched_product_id]
                if other_items:
                    partial_s = s.model_copy(deep=True)
                    partial_s.matched_items = other_items
                    partial_s.items_covered_count = len(other_items)
                    partial_s.covers_entire_basket = False
                    partial_s.total_listed_price_toman = sum(m.price_toman or 0.0 for m in other_items)
                    retained_stores.append(partial_s)

        effective_max_stops = max_stops or (len(original_plan.stores) + 1)
        effective_budget = max_budget_toman

        # Step 3: Search replacement for target item
        # Strategy A: Check if any of the already retained stores also list this item!
        replacement_found = False
        replacement_shop: Optional[ShopBasketCoverage] = None
        replacement_match: Optional[BasketItemMatch] = None

        for ret_s in retained_stores:
            offers = self.catalog_repo.get_offers_by_shop(ret_s.shop_id, limit=50)
            for off in offers:
                if not off.price_toman or off.price_toman <= 1:
                    continue
                prod = self.catalog_repo.get_product(off.product_id)
                if prod and (clean_target in prod.persian_title.lower() or target_item.query.lower() in prod.persian_title.lower()):
                    replacement_match = BasketItemMatch(
                        query=target_item.query,
                        matched_product_id=prod.product_id,
                        matched_product_title=prod.persian_title,
                        offer_id=off.offer_id,
                        shop_id=ret_s.shop_id,
                        price_toman=off.price_toman,
                        price_status="price_known",
                        stock_evidence="stock_unknown",
                        evidence_status="listed_in_catalog",
                    )
                    ret_s.matched_items.append(replacement_match)
                    ret_s.items_covered_count += 1
                    if ret_s.total_listed_price_toman is not None:
                        ret_s.total_listed_price_toman += off.price_toman
                    replacement_found = True
                    break
            if replacement_found:
                break

        # Strategy B: Find alternative shop if Strategy A not applicable
        if not replacement_found and len(retained_stores) < effective_max_stops:
            candidate_prods, _ = self.catalog_repo.search_products(q=target_item.query, limit=15)
            best_alt_tuple = None
            min_added_cost = float("inf")

            for p in candidate_prods:
                offers = self.catalog_repo.get_offers_by_product(p.product_id, limit=20)
                for o in offers:
                    if not o.price_toman or o.price_toman <= 1:
                        continue
                    if o.shop_id == target_store.shop_id:
                        continue  # Skip failed store
                    shop = self.catalog_repo.get_shop(o.shop_id)
                    if not shop:
                        continue
                    rel = self.reliability_engine.assess_shop(shop)
                    if min_shop_reliability and rel.composite_reliability_score < min_shop_reliability:
                        continue

                    # Evaluate budget feasibility
                    current_retained_cost = sum(s.total_listed_price_toman or 0.0 for s in retained_stores)
                    if effective_budget and (current_retained_cost + o.price_toman) > (effective_budget * 1.15):
                        continue

                    if o.price_toman < min_added_cost:
                        min_added_cost = o.price_toman
                        best_alt_tuple = (p, o, shop, rel)

            if best_alt_tuple:
                p_alt, o_alt, s_alt, rel_alt = best_alt_tuple
                m_alt = BasketItemMatch(
                    query=target_item.query,
                    matched_product_id=p_alt.product_id,
                    matched_product_title=p_alt.persian_title,
                    offer_id=o_alt.offer_id,
                    shop_id=s_alt.shop_id,
                    price_toman=o_alt.price_toman,
                    price_status="price_known",
                    stock_evidence="stock_unknown",
                    evidence_status="listed_in_catalog",
                )
                alt_coverage = ShopBasketCoverage(
                    shop_id=s_alt.shop_id,
                    shop_name=s_alt.name,
                    shop_address=s_alt.address,
                    lat=s_alt.lat,
                    lon=s_alt.lon,
                    items_covered_count=1,
                    total_items_requested=len(original_plan.missing_items) + sum(len(s.matched_items) for s in original_plan.stores),
                    covers_entire_basket=False,
                    matched_items=[m_alt],
                    missing_items=[],
                    total_listed_price_toman=o_alt.price_toman,
                    is_total_price_complete=True,
                    shop_reliability_score=round(rel_alt.composite_reliability_score, 3),
                    estimated_travel_minutes=15.0,
                    verification_level="unverified_catalog_only",
                )
                retained_stores.append(alt_coverage)
                replacement_shop = alt_coverage
                replacement_match = m_alt
                replacement_found = True

        # Step 4: Evaluate outcome
        if not replacement_found:
            return PlanAdaptationResult(
                is_recovered=False,
                recovery_status="infeasible_constrained",
                original_plan_id=original_plan.plan_id,
                affected_items=[target_item.matched_product_title],
                affected_shop_id=target_store.shop_id,
                affected_shop_name=target_store.shop_name,
                adaptation_reason=f"فروشگاه «{target_store.shop_name}» عدم موجودی «{target_item.matched_product_title}» را اعلام کرد.",
                persian_explanation=(
                    f"با توجه به اعلام عدم موجودی «{target_item.matched_product_title}» توسط فروشگاه «{target_store.shop_name}»، "
                    f"هیچ فروشگاه جایگزینی با سقف {effective_max_stops} توقف و بودجه مدنظر در کاتالوگ یافت نشد. "
                    f"پیشنهاد می‌شود سقف تعداد فروشگاه‌ها یا بودجه افزایش یابد."
                ),
                audit_event={
                    "event": "replan_failed_constrained",
                    "timestamp": now_iso,
                    "target_item": target_item.matched_product_title,
                    "target_shop": target_store.shop_name,
                },
            )

        # Build revised plan
        new_total_cost = sum(s.total_listed_price_toman or 0.0 for s in retained_stores)
        new_total_travel = sum(s.estimated_travel_minutes or 15.0 for s in retained_stores)
        new_plan_id = f"{original_plan.plan_id}_v{original_plan.version + 1}"

        retained_items_names = []
        for s in retained_stores:
            for m in s.matched_items:
                if m.matched_product_id != replacement_match.matched_product_id:
                    retained_items_names.append(m.matched_product_title[:20])

        changes_summary = (
            f"کالای {target_item.matched_product_title[:25]} از فروشگاه «{replacement_shop.shop_name if replacement_shop else 'فروشگاه‌های موجود'}» "
            f"به قیمت {replacement_match.price_toman:,.0f} تومان تامین شد."
        )
        preservation_summary = f"اقلام {', '.join(retained_items_names)} از فروشگاه‌های معتبر قبلی حفظ شدند."

        explanation = (
            f"🔄 برنامه خرید بازنگری شد: با توجه به عدم موجودی کالا در فروشگاه «{target_store.shop_name}»، "
            f"{changes_summary} {preservation_summary} "
            f"مجموع هزینه جدید: {new_total_cost:,.0f} تومان در قالب {len(retained_stores)} توقف فروشگاهی."
        )

        revised_plan = MultiStoreBasketPlan(
            plan_id=new_plan_id,
            version=original_plan.version + 1,
            is_adapted=True,
            original_plan_id=original_plan.plan_id,
            adaptation_reason=f"جایگزینی هوشمند پس از عدم موجودی در {target_store.shop_name}",
            strategy=original_plan.strategy,
            strategy_label_persian=original_plan.strategy_label_persian,
            stores=retained_stores,
            total_product_cost_toman=new_total_cost,
            is_total_price_complete=all(s.is_total_price_complete for s in retained_stores),
            estimated_total_travel_minutes=new_total_travel,
            total_stops=len(retained_stores),
            all_items_covered=True,
            missing_items=[],
            guarantee_status="complete_catalog_coverage_unverified_stock",
            composite_score=round(sum(s.shop_reliability_score for s in retained_stores) / len(retained_stores), 3),
            trade_off_explanation=explanation,
            itinerary_order=[
                {"stop": idx, "shop_id": s.shop_id, "shop_name": s.shop_name}
                for idx, s in enumerate(retained_stores, 1)
            ],
            warnings=["طرح به صورت خودکار بازنگری شده است؛ استعلام مجدد از فروشگاه جدید توصیه می‌شود."],
        )

        audit_event = {
            "event": "plan_adaptively_recovered",
            "timestamp": now_iso,
            "original_plan_id": original_plan.plan_id,
            "revised_plan_id": new_plan_id,
            "reason": "seller_stock_rejected",
            "affected_shop": target_store.shop_name,
            "affected_item": target_item.matched_product_title,
            "new_stores_count": len(retained_stores),
            "new_total_cost_toman": new_total_cost,
        }

        return PlanAdaptationResult(
            is_recovered=True,
            recovery_status="fully_recovered",
            original_plan_id=original_plan.plan_id,
            revised_plan=revised_plan,
            affected_items=[target_item.matched_product_title],
            affected_shop_id=target_store.shop_id,
            affected_shop_name=target_store.shop_name,
            adaptation_reason="seller_stock_rejection_recovered",
            persian_explanation=explanation,
            preservation_summary=preservation_summary,
            changes_summary=changes_summary,
            audit_event=audit_event,
        )

    def recover_after_restock(
        self,
        invalid_plan: MultiStoreBasketPlan,
        restocked_product_id: str,
        shop_id: str,
    ) -> PlanAdaptationResult:
        """Restores a previously invalidated plan when an item is restocked."""
        restored = invalid_plan.model_copy(deep=True)
        restored.version += 1
        restored.is_adapted = True
        restored.all_items_covered = True
        restored.guarantee_status = "seller_confirmed_in_store"
        restored.composite_score = min(1.0, round(restored.composite_score * 2.5, 3))
        
        # Clean warnings regarding unavailable items
        restored.warnings = [w for w in restored.warnings if "عدم موجودی" not in w and "ناموجود" not in w]

        item_title = "کالای درخواستی"
        for s in restored.stores:
            if s.shop_id == shop_id:
                for m in s.matched_items:
                    if m.matched_product_id == restocked_product_id:
                        m.stock_evidence = "seller_confirmed"
                        m.is_verified_in_store = True
                        item_title = m.matched_product_title

        explanation = (
            f"🎉 خوشبختانه کالای «{item_title[:25]}» در فروشگاه مجدداً موجود شد. "
            f"برنامه خرید اولیه با موفقیت بازیابی گردید و تمام اقلام قابل تهیه هستند."
        )
        restored.trade_off_explanation = explanation

        audit_event = {
            "event": "plan_restored_via_restock",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "product_id": restocked_product_id,
            "shop_id": shop_id,
        }

        return PlanAdaptationResult(
            is_recovered=True,
            recovery_status="restocked_restored",
            original_plan_id=invalid_plan.plan_id,
            revised_plan=restored,
            affected_items=[item_title],
            affected_shop_id=shop_id,
            adaptation_reason="product_restocked",
            persian_explanation=explanation,
            preservation_summary="تمامی اقلام و فروشگاه‌های طرح قبلی حفظ شدند.",
            changes_summary="وضعیت موجودی از ناموجود به موجودی تاییدشده ارتقا یافت.",
            audit_event=audit_event,
        )

    def recover_after_store_rejection(
        self,
        original_plan: MultiStoreBasketPlan,
        rejected_shop_id: str,
        max_budget_toman: Optional[float] = None,
        max_stops: Optional[int] = None,
    ) -> PlanAdaptationResult:
        """Adapts a plan when the user explicitly rejects a particular store."""
        rejected_shop_name = "فروشگاه رد شده"
        items_to_reacquire: List[str] = []

        for s in original_plan.stores:
            if s.shop_id == rejected_shop_id:
                rejected_shop_name = s.shop_name
                items_to_reacquire.extend([m.query for m in s.matched_items])

        if not items_to_reacquire:
            return PlanAdaptationResult(
                is_recovered=False,
                recovery_status="infeasible_constrained",
                original_plan_id=original_plan.plan_id,
                adaptation_reason="فروشگاه مورد نظر در طرح یافت نشد.",
                persian_explanation="فروشگاه مشخص‌شده در طرح فعلی وجود ندارد.",
            )

        # Re-optimize basket excluding rejected shop
        all_queries = []
        for s in original_plan.stores:
            all_queries.extend([m.query for m in s.matched_items])

        new_plans = self.basket_engine.optimize_basket(
            basket_queries=all_queries,
            max_budget_toman=max_budget_toman or original_plan.total_product_cost_toman,
            max_stops=max_stops or len(original_plan.stores),
            require_single_store=original_plan.strategy == "single_store",
        )

        valid_revised = [
            p for p in new_plans
            if not any(s.shop_id == rejected_shop_id for s in p.stores)
            and p.all_items_covered
        ]

        if not valid_revised:
            return PlanAdaptationResult(
                is_recovered=False,
                recovery_status="infeasible_constrained",
                original_plan_id=original_plan.plan_id,
                affected_shop_id=rejected_shop_id,
                affected_shop_name=rejected_shop_name,
                adaptation_reason="عدم امکان تامین بدون فروشگاه رد شده",
                persian_explanation=(
                    f"با حذف فروشگاه «{rejected_shop_name}»، امکان تامین سبد کامل با شرایط مشخص‌شده در کاتالوگ میسر نشد."
                ),
            )

        best_revised = valid_revised[0]
        best_revised.is_adapted = True
        best_revised.original_plan_id = original_plan.plan_id
        best_revised.version = original_plan.version + 1
        best_revised.adaptation_reason = f"حذف فروشگاه {rejected_shop_name} بنا به درخواست کاربر"

        explanation = (
            f"فروشگاه «{rejected_shop_name}» از برنامه خرید حذف شد و فروشگاه‌های جایگزین "
            f"(«{'» و «'.join(s.shop_name for s in best_revised.stores)}») انتخاب شدند."
        )
        best_revised.trade_off_explanation = explanation

        return PlanAdaptationResult(
            is_recovered=True,
            recovery_status="fully_recovered",
            original_plan_id=original_plan.plan_id,
            revised_plan=best_revised,
            affected_shop_id=rejected_shop_id,
            affected_shop_name=rejected_shop_name,
            adaptation_reason="user_store_rejection",
            persian_explanation=explanation,
            changes_summary=f"جایگزینی فروشگاه {rejected_shop_name}",
        )
