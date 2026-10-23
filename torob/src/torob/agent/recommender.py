"""Deterministic Recommendation and Ranking Engine for Torob Shopping Agent.

Executes a multi-stage pipeline:
1. Candidate retrieval from actual DuckDB catalog
2. Strict hard-constraint enforcement (budget ceiling, condition, brand, variant)
3. Multi-dimensional evidence-aware offer evaluation
4. Explainable scoring (pros, cons, uncertainty warnings)
5. Structured trade-offs (best_overall, budget_pick, verified_confidence)
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from torob.agent.compatibility import BasketCompatibilityReport, PCCompatibilityEngine
from torob.agent.models import (
    CandidateOfferRecommendation,
    RecommendationResult,
    ShoppingConstraints,
    ShoppingIntent,
)
from torob.domain.entities import Offer, Product, Shop
from torob.domain.enums import RiskBand, StockState, UserIntent
from torob.domain.plans import PlanOptimizationPriority
from torob.ingestion.normalizer import (
    extract_variant_attributes,
    normalize_digits,
    normalize_persian_text,
)
from torob.intelligence.basket_optimizer import BasketOptimizationEngine
from torob.intelligence.inventory import InventoryIntelligenceEngine
from torob.intelligence.matching import CompatibilityGrade, VariantCompatibilityMatcher
from torob.intelligence.personalized_recommender import PersonalizedProductSelector
from torob.intelligence.pricing import PriceIntelligenceEngine
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.clustering import ShopClusterEngine
from torob.routing.distance import DistanceRouter, haversine_km
from torob.routing.feasibility import VisitFeasibilityEngine
from torob.routing.on_route import OnRouteShoppingEngine
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.agent.recommender")


BRAND_SYNONYMS: Dict[str, Set[str]] = {
    "samsung": {"samsung", "سامسونگ"},
    "apple": {"apple", "اپل", "آیفون", "ایفون"},
    "xiaomi": {"xiaomi", "شیائومی", "شیاومی"},
    "asus": {"asus", "ایسوس", "اسوس"},
    "lenovo": {"lenovo", "لنوو", "لنووو"},
    "hp": {"hp", "اچ پی", "اچ‌پی"},
    "huawei": {"huawei", "هواوی", "هوآوی"},
    "sony": {"sony", "سونی"},
    "nokia": {"nokia", "نوکیا"},
    "anker": {"anker", "انکر"},
    "logitech": {"logitech", "لاجیتک"},
}


class ShoppingRecommender:
    def __init__(
        self,
        catalog_repo: Optional[CatalogRepository] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        pricing_engine: Optional[PriceIntelligenceEngine] = None,
        inventory_engine: Optional[InventoryIntelligenceEngine] = None,
        reliability_engine: Optional[ShopReliabilityEngine] = None,
        feasibility_engine: Optional[VisitFeasibilityEngine] = None,
    ):
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.pricing_engine = pricing_engine or PriceIntelligenceEngine()
        self.inventory_engine = inventory_engine or InventoryIntelligenceEngine()
        self.reliability_engine = reliability_engine or ShopReliabilityEngine()
        self.feasibility_engine = feasibility_engine or VisitFeasibilityEngine()
        self.router = DistanceRouter()
        self.pc_engine = PCCompatibilityEngine()
        self.on_route_engine = OnRouteShoppingEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
            pricing_engine=self.pricing_engine,
            inventory_engine=self.inventory_engine,
            reliability_engine=self.reliability_engine,
        )
        self.basket_engine = BasketOptimizationEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
            pricing_engine=self.pricing_engine,
            inventory_engine=self.inventory_engine,
            reliability_engine=self.reliability_engine,
        )
        self.cluster_engine = ShopClusterEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
            reliability_engine=self.reliability_engine,
        )
        self.personalized_selector = PersonalizedProductSelector(
            catalog_repo=self.catalog_repo
        )

    def recommend(
        self,
        constraints: ShoppingConstraints,
        intent: ShoppingIntent = ShoppingIntent.NEEDS_BASED,
        limit: int = 5,
    ) -> RecommendationResult:
        """Executes the full retrieval, filtering, evaluation, and ranking pipeline."""
        # Advanced Branch 1: On-Route Purchasing Engine
        if intent == ShoppingIntent.ON_ROUTE_PURCHASE or (constraints.origin_lat and constraints.destination_lat):
            return self._recommend_on_route(constraints, intent, limit)

        # Advanced Branch 2: Nearby Commercial Shop Clustering
        if intent == ShoppingIntent.NEARBY_STORE_CLUSTER:
            return self._recommend_shop_clusters(constraints, intent, limit)

        # Advanced Branch 3: Multi-Item Basket Optimization
        if intent in (ShoppingIntent.SINGLE_STORE_BASKET, ShoppingIntent.MULTI_STORE_BASKET) or len(constraints.basket_queries) >= 2:
            return self._recommend_basket_optimization(constraints, intent, limit)

        # Advanced Branch 4: Personalized Multi-Criteria Selection
        if intent == ShoppingIntent.PERSONALIZED_SELECTION:
            return self._recommend_personalized_selection(constraints, intent, limit)

        # Step 1: Candidate Retrieval
        candidate_products = self._retrieve_candidate_products(constraints)
        if not candidate_products:
            return RecommendationResult(
                intent=intent,
                total_candidates_found=0,
                top_recommendations=[],
                trade_off_summary="هیچ کالایی متناسب با مشخصات و فیلترهای جستجوی شما در کاتالوگ یافت نشد.",
                hard_constraints_satisfied=False,
                violated_constraints=["کالای منطبق در کاتالوگ یافت نشد"],
            )

        # Step 2 & 3: Hard-Constraint Enforcement and Offer Evaluation
        evaluated_recommendations: List[CandidateOfferRecommendation] = []
        violated_constraints: List[str] = []

        now = datetime.now(timezone.utc)
        user_intent_enum = (
            UserIntent.VISIT if (intent == ShoppingIntent.LOCAL_PHYSICAL or constraints.urgency == "urgent_today")
            else UserIntent.BUY
        )

        for product in candidate_products:
            # Check rejected products
            if product.product_id in constraints.rejected_product_ids:
                continue

            offers = self.catalog_repo.get_offers_by_product(product.product_id, limit=30)
            peer_offers = [o for o in offers if o.price_toman and o.price_toman > 1]

            for offer in offers:
                if not offer.price_toman or offer.price_toman <= 1:
                    continue

                # Hard constraint: Budget ceiling
                if constraints.budget_max_toman is not None and constraints.budget_is_strict:
                    if offer.price_toman > constraints.budget_max_toman:
                        violated_constraints.append(f"قیمت بیش از سقف بودجه ({offer.price_toman:,} > {constraints.budget_max_toman:,})")
                        continue

                # Hard constraint: Budget floor (filter sentinels or unreasonable min)
                if constraints.budget_min_toman is not None:
                    if offer.price_toman < constraints.budget_min_toman:
                        continue

                shop = self.catalog_repo.get_shop(offer.shop_id)
                if not shop:
                    continue

                # Hard constraint: Shop reliability minimum
                rel = self.reliability_engine.assess_shop(shop)
                if constraints.min_shop_reliability is not None:
                    if rel.composite_reliability_score < constraints.min_shop_reliability:
                        continue

                # Extract variant attributes for hard-constraint matching
                full_text = f"{offer.seller_title or ''} {offer.description or ''}"
                extracted_attrs = extract_variant_attributes(full_text, product.specs)

                # Hard constraint: Condition (new vs used)
                if constraints.condition:
                    if extracted_attrs.get("condition") != constraints.condition:
                        continue

                # Hard constraint: Storage & RAM if strictly requested
                if constraints.storage:
                    if extracted_attrs.get("storage") and extracted_attrs["storage"] != constraints.storage:
                        continue
                if constraints.ram:
                    if extracted_attrs.get("ram") and extracted_attrs["ram"] != constraints.ram:
                        continue

                # Intelligence Assessments
                peers_loso = [p for p in peer_offers if p.shop_id != offer.shop_id]
                price_assess = self.pricing_engine.assess_offer_price(offer, peers_loso, product=product, now=now)

                # Stock & Travel feasibility
                travel_mins = 0.0
                survival_at_arrival = None
                feasibility_warnings: List[str] = []

                if constraints.user_lat is not None and constraints.user_lon is not None and shop.lat and shop.lon:
                    _, travel_mins, _ = self.router.estimate_travel(
                        constraints.user_lat, constraints.user_lon, shop.lat, shop.lon
                    )
                    if constraints.max_travel_minutes and travel_mins > constraints.max_travel_minutes:
                        continue  # Exceeded travel distance

                    feasibility = self.feasibility_engine.assess_visit_feasibility(
                        origin_lat=constraints.user_lat,
                        origin_lon=constraints.user_lon,
                        shop=shop,
                        offer=offer,
                        now=now,
                    )
                    feasibility_warnings.extend(feasibility.warnings)

                stock_assess = self.inventory_engine.assess_stock(
                    stock_status=StockState.IN_STORE_SELLABLE,
                    quantity_bucket="unknown",
                    travel_time_minutes=travel_mins,
                    now=now,
                )
                survival_at_arrival = stock_assess.survival_probability_at_arrival

                # Step 4: Scoring & Reasoning
                pros: List[str] = []
                cons: List[str] = []
                uncertainty_warnings: List[str] = []

                suitability = self._calculate_suitability(
                    product=product,
                    offer=offer,
                    extracted_attrs=extracted_attrs,
                    constraints=constraints,
                    price_assess=price_assess,
                    shop_reliability=rel.composite_reliability_score,
                    pros=pros,
                    cons=cons,
                    warnings=uncertainty_warnings,
                )

                uncertainty_warnings.extend(feasibility_warnings)

                rec = CandidateOfferRecommendation(
                    product_id=product.product_id,
                    product_title=product.persian_title,
                    offer_id=offer.offer_id,
                    shop_id=shop.shop_id,
                    shop_name=shop.name,
                    shop_address=shop.address,
                    price_toman=offer.price_toman,
                    reference_market_price=price_assess.reference_peer_price,
                    is_price_anomaly=(price_assess.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL)),
                    suitability_score=round(suitability, 3),
                    shop_reliability_score=round(rel.composite_reliability_score, 3),
                    stock_survival_at_arrival=survival_at_arrival,
                    evidence_quality=price_assess.evidence_quality.value,
                    pros=pros,
                    cons=cons,
                    uncertainty_warnings=uncertainty_warnings,
                )
                evaluated_recommendations.append(rec)

        if not evaluated_recommendations:
            return RecommendationResult(
                intent=intent,
                total_candidates_found=0,
                top_recommendations=[],
                trade_off_summary="کالایی با شرایط و سقف بودجه مشخص‌شده یافت نشد. افزایش بودجه یا تغییر فیلترها پیشنهاد می‌شود.",
                hard_constraints_satisfied=False,
                violated_constraints=list(set(violated_constraints)),
            )

        # Step 5: Ranking and Trade-off Assignment
        # Sort primarily by suitability_score descending, secondarily by price ascending
        evaluated_recommendations.sort(key=lambda r: (-r.suitability_score, r.price_toman))
        # Prefer distinct products (best offer each) so the list is a real choice, then fill with extra offers
        seen_products: Set[str] = set()
        distinct, extra = [], []
        for r in evaluated_recommendations:
            (extra if r.product_id in seen_products else distinct).append(r)
            seen_products.add(r.product_id)
        top_candidates = (distinct + extra)[:limit]

        self._assign_trade_off_labels(top_candidates)
        summary = self._generate_trade_off_summary(top_candidates, constraints)

        # Check PC basket / multi-product compatibility
        compat_report_data = None
        if intent == ShoppingIntent.MULTI_PRODUCT or any(c in (constraints.target_product_title or "") for c in ["مادربرد", "سی پی یو", "cpu", "ram", "رم", "پاور", "گرافیک"]):
            basket_components = []
            for c in top_candidates[:4]:
                cat = "other"
                lower_title = c.product_title.lower()
                if "cpu" in lower_title or "پردازنده" in lower_title:
                    cat = "cpu"
                elif "motherboard" in lower_title or "مادربرد" in lower_title or "مین برد" in lower_title:
                    cat = "motherboard"
                elif "ram" in lower_title or "رم" in lower_title:
                    cat = "ram"
                elif "گرافیک" in lower_title or "gpu" in lower_title:
                    cat = "gpu"
                basket_components.append({
                    "product_id": c.product_id,
                    "title": c.product_title,
                    "category": cat,
                    "price_toman": c.price_toman,
                })
            if basket_components:
                report = self.pc_engine.evaluate_basket(basket_components, budget_toman=constraints.budget_max_toman)
                compat_report_data = report.model_dump()

        # Suggest inquiry if the best candidate has unverified stock or price anomaly
        recommended_inquiry = None
        if top_candidates:
            best = top_candidates[0]
            if best.is_price_anomaly or best.evidence_quality in ("limited", "unknown"):
                recommended_inquiry = {
                    "shop_id": best.shop_id,
                    "shop_name": best.shop_name,
                    "offer_id": best.offer_id,
                    "product_id": best.product_id,
                    "reason": f"استعلام پیش از حرکت از {best.shop_name} جهت اطمینان ۱۰۰٪ از موجودی و قیمت {best.price_toman:,} تومان توصیه می‌شود.",
                }

        return RecommendationResult(
            intent=intent,
            total_candidates_found=len(evaluated_recommendations),
            top_recommendations=top_candidates,
            trade_off_summary=summary,
            hard_constraints_satisfied=True,
            recommended_inquiry=recommended_inquiry,
            compatibility_report=compat_report_data,
        )

    def _recommend_on_route(
        self, constraints: ShoppingConstraints, intent: ShoppingIntent, limit: int
    ) -> RecommendationResult:
        orig_lat = constraints.origin_lat or constraints.user_lat or 35.7005
        orig_lon = constraints.origin_lon or constraints.user_lon or 51.3912
        dest_lat = constraints.destination_lat or (orig_lat + 0.05)
        dest_lon = constraints.destination_lon or (orig_lon + 0.05)
        if constraints.basket_queries:
            q = " و ".join(constraints.basket_queries)
        else:
            q = constraints.target_product_title or constraints.target_category or "SSD"

        plan = self.on_route_engine.find_on_route_purchases(
            origin_lat=orig_lat,
            origin_lon=orig_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            product_query=q,
            basket_queries=constraints.basket_queries,
            max_detour_minutes=constraints.max_detour_minutes,
            max_price_toman=constraints.budget_max_toman,
            min_shop_reliability=constraints.min_shop_reliability,
            limit=limit,
        )

        recs: List[CandidateOfferRecommendation] = []
        for s in plan.recommended_stops:
            if s.product_id in constraints.rejected_product_ids:
                continue
            r = CandidateOfferRecommendation(
                product_id=s.product_id,
                product_title=s.product_title,
                offer_id=s.offer_id,
                shop_id=s.shop_id,
                shop_name=s.shop_name,
                shop_address=s.shop_address,
                price_toman=s.price_toman,
                suitability_score=round(1.0 / (1.0 + s.detour_minutes * 0.05), 3),
                shop_reliability_score=s.shop_reliability_score,
                stock_survival_at_arrival=s.stock_survival_at_arrival,
                trade_off_label=s.trade_off_label,
                pros=[f"انحراف فقط {s.detour_minutes:.0f} دقیقه از مسیر اصلی"],
                uncertainty_warnings=s.warnings,
            )
            recs.append(r)

        return RecommendationResult(
            intent=intent,
            total_candidates_found=len(recs),
            top_recommendations=recs,
            trade_off_summary=plan.trade_off_summary,
            hard_constraints_satisfied=plan.is_feasible and len(recs) > 0,
            violated_constraints=[] if plan.is_feasible and len(recs) > 0 else ["توقف منطبق در مسیر یافت نشد"],
            on_route_plan=plan.model_dump(),
        )

    def _recommend_basket_optimization(
        self, constraints: ShoppingConstraints, intent: ShoppingIntent, limit: int
    ) -> RecommendationResult:
        queries = constraints.basket_queries
        if not queries:
            if constraints.target_product_title and " و " in constraints.target_product_title:
                queries = [x.strip() for x in constraints.target_product_title.split(" و ") if len(x.strip()) > 1]
            else:
                queries = ["مانیتور", "کیبورد", "موس"]

        try:
            priority_enum = PlanOptimizationPriority(constraints.optimization_priority)
        except Exception:
            priority_enum = PlanOptimizationPriority.BALANCED

        plans = self.basket_engine.optimize_basket(
            basket_queries=queries,
            user_lat=constraints.user_lat,
            user_lon=constraints.user_lon,
            max_budget_toman=constraints.budget_max_toman,
            max_stops=constraints.max_stops or 3,
            require_single_store=constraints.require_single_store or (intent == ShoppingIntent.SINGLE_STORE_BASKET),
            optimization_priority=priority_enum,
            min_shop_reliability=constraints.min_shop_reliability,
            limit_plans=limit,
        )

        if not plans or not plans[0].stores:
            return RecommendationResult(
                intent=intent,
                total_candidates_found=0,
                top_recommendations=[],
                trade_off_summary="امکان تامین سبد خرید با شرایط و محدودیت‌های مشخص‌شده وجود ندارد.",
                hard_constraints_satisfied=False,
                violated_constraints=["عدم امکان پوشش کامل سبد خرید"],
            )

        best_plan = plans[0]
        recs: List[CandidateOfferRecommendation] = []
        for shop in best_plan.stores:
            for item in shop.matched_items:
                r = CandidateOfferRecommendation(
                    product_id=item.matched_product_id,
                    product_title=item.matched_product_title,
                    offer_id=item.offer_id,
                    shop_id=shop.shop_id,
                    shop_name=shop.shop_name,
                    shop_address=shop.shop_address,
                    price_toman=item.price_toman,
                    suitability_score=round(best_plan.composite_score, 3),
                    shop_reliability_score=shop.shop_reliability_score,
                    trade_off_label=best_plan.strategy,
                    pros=[f"تامین از فروشگاه {shop.shop_name} ({shop.shop_address or 'تهران'})"],
                )
                recs.append(r)

        return RecommendationResult(
            intent=intent,
            total_candidates_found=len(recs),
            top_recommendations=recs,
            trade_off_summary=best_plan.trade_off_explanation,
            hard_constraints_satisfied=best_plan.all_items_covered,
            violated_constraints=[] if best_plan.all_items_covered else [f"اقلام ناموجود: {best_plan.missing_items}"],
            basket_plan={"primary_plan": best_plan.model_dump(), "all_plans": [p.model_dump() for p in plans]},
            recommended_inquiry=best_plan.recommended_inquiry,
        )

    def _recommend_shop_clusters(
        self, constraints: ShoppingConstraints, intent: ShoppingIntent, limit: int
    ) -> RecommendationResult:
        queries = constraints.basket_queries or ["مانیتور", "کیبورد", "موس"]
        # Retrieve candidate coverages
        plans = self.basket_engine.optimize_basket(
            basket_queries=queries,
            user_lat=constraints.user_lat,
            user_lon=constraints.user_lon,
            max_budget_toman=constraints.budget_max_toman,
        )
        all_coverages = []
        seen = set()
        for p in plans:
            for s in p.stores:
                if s.shop_id not in seen:
                    seen.add(s.shop_id)
                    all_coverages.append(s)

        clusters = self.cluster_engine.identify_clusters_for_basket(
            candidate_coverages=all_coverages,
            total_items_requested=queries,
            user_lat=constraints.user_lat,
            user_lon=constraints.user_lon,
            limit_clusters=limit,
        )

        if not clusters:
            return RecommendationResult(
                intent=intent,
                total_candidates_found=0,
                top_recommendations=[],
                trade_off_summary="هیچ خوشه تجاری همجواری برای خرید اقلام سبد یافت نشد.",
                hard_constraints_satisfied=False,
                violated_constraints=["خوشه تجاری همجوار یافت نشد"],
            )

        best_cluster = clusters[0]
        recs: List[CandidateOfferRecommendation] = []
        for shop in best_cluster.shops:
            for item in shop.matched_items:
                r = CandidateOfferRecommendation(
                    product_id=item.matched_product_id,
                    product_title=item.matched_product_title,
                    offer_id=item.offer_id,
                    shop_id=shop.shop_id,
                    shop_name=shop.shop_name,
                    shop_address=shop.shop_address,
                    price_toman=item.price_toman,
                    suitability_score=round(best_cluster.average_reliability, 3),
                    shop_reliability_score=shop.shop_reliability_score,
                    trade_off_label="cluster_pick",
                    pros=[f"واقع در {best_cluster.cluster_name}"],
                )
                recs.append(r)

        return RecommendationResult(
            intent=intent,
            total_candidates_found=len(recs),
            top_recommendations=recs,
            trade_off_summary=best_cluster.summary,
            hard_constraints_satisfied=best_cluster.covers_entire_basket,
            shop_clusters=[c.model_dump() for c in clusters],
        )

    def _recommend_personalized_selection(
        self, constraints: ShoppingConstraints, intent: ShoppingIntent, limit: int
    ) -> RecommendationResult:
        refs = constraints.comparison_product_ids
        if not refs:
            if not constraints.target_category and not constraints.target_product_title:
                constraints.target_category = "لپ تاپ و نوت بوک"
            prods = self._retrieve_candidate_products(constraints)
            refs = [p.product_id for p in prods[:5]]

        use_case = "general"
        title_lower = (constraints.target_product_title or "").lower()
        if any(w in title_lower for w in ["برنامه نویسی", "برنامه‌نویسی", "کدنویسی", "مهندسی"]):
            use_case = "programming"
        elif any(w in title_lower for w in ["گیمینگ", "بازی"]):
            use_case = "gaming"
        elif any(w in title_lower for w in ["حمل", "سبک", "مسافرت", "دانشجویی"]):
            use_case = "mobility"

        user_priorities = {}
        if constraints.battery_preference == "high_battery_life":
            user_priorities["battery"] = 0.35
        if constraints.preferred_specs.get("weight") == "lightweight":
            user_priorities["weight"] = 0.35
        if constraints.preferred_specs.get("user_priorities"):
            user_priorities.update(constraints.preferred_specs["user_priorities"])

        comp_res = self.personalized_selector.compare_and_rank_products(
            product_ids_or_titles=refs,
            use_case=use_case,
            user_priorities=user_priorities,
            max_budget_toman=constraints.budget_max_toman,
            excluded_brands=constraints.excluded_brands,
        )

        recs: List[CandidateOfferRecommendation] = []
        for s in comp_res.evaluated_products:
            if s.product_id in constraints.rejected_product_ids:
                continue
            r = CandidateOfferRecommendation(
                product_id=s.product_id,
                product_title=s.product_title,
                offer_id=f"off_{s.product_id[:8]}",
                shop_id="best_shop",
                shop_name="فروشگاه برتر",
                price_toman=s.min_price_toman or 0.0,
                suitability_score=s.suitability_score,
                shop_reliability_score=0.85,
                pros=s.pros,
                cons=s.cons,
                trade_off_label="top_personalized" if s.product_id == comp_res.top_choice_product_id else None,
            )
            recs.append(r)

        return RecommendationResult(
            intent=intent,
            total_candidates_found=len(recs),
            top_recommendations=recs,
            trade_off_summary=comp_res.top_choice_summary,
            hard_constraints_satisfied=len(recs) > 0 and (recs[0].suitability_score > 0.4),
            personalized_comparison=comp_res.model_dump(),
        )

    def _retrieve_candidate_products(self, constraints: ShoppingConstraints) -> List[Product]:
        """Retrieves candidate products from catalog repository based on constraints."""
        # 0. Check explicit comparison IDs
        if constraints.comparison_product_ids:
            explicit_products = []
            for pid in constraints.comparison_product_ids:
                p = self.catalog_repo.get_product(pid)
                if p:
                    explicit_products.append(p)
            if explicit_products:
                return explicit_products

        # Category should only be passed if it does not contain hierarchy markers
        cat_filter = None
        if constraints.target_category and ">" not in constraints.target_category:
            cat_filter = constraints.target_category

        # Explicit model-vs-model comparison in text ("مقایسه A و B", "A یا B") takes precedence
        compared_brands = constraints.preferred_specs.get("compared_brands")
        text_cmp = self._retrieve_text_comparison(constraints.target_product_title, cat_filter)
        if text_cmp:
            return text_cmp

        # Check multi-brand comparison
        if compared_brands and len(compared_brands) > 1:
            multi_brand_products = []
            seen_ids = set()
            brand_map = {
                "Samsung": "سامسونگ", "Apple": "اپل", "Xiaomi": "شیائومی",
                "Asus": "ایسوس", "Lenovo": "لنوو", "HP": "اچ پی",
                "Sony": "سونی", "Anker": "انکر", "Logitech": "لاجیتک", "Huawei": "هواوی"
            }
            dev = constraints.preferred_specs.get("device_type") or ""
            for b in compared_brands:
                fa_b = brand_map.get(b, b)
                b_query = f"{fa_b} {dev}".strip() if dev else fa_b
                b_prods, _ = self.catalog_repo.search_products(q=b_query, category=cat_filter, limit=8)
                if not b_prods and dev:
                    b_prods, _ = self.catalog_repo.search_products(q=fa_b, category=cat_filter, limit=8)
                for bp in b_prods:
                    if bp.product_id not in seen_ids:
                        seen_ids.add(bp.product_id)
                        multi_brand_products.append(bp)
            if multi_brand_products:
                return multi_brand_products

        query = constraints.target_product_title
        if not query:
            if constraints.target_brand and constraints.preferred_specs.get("device_type"):
                query = f"{constraints.target_brand} {constraints.preferred_specs['device_type']}"
            elif constraints.target_brand:
                query = constraints.target_brand
            elif constraints.preferred_specs.get("device_type"):
                query = constraints.preferred_specs["device_type"]
            else:
                query = ""

        # Clean query tokens
        query_norm = normalize_digits(normalize_persian_text(query)).replace("\u200c", " ").strip()

        if not cat_filter:
            dev_type = constraints.preferred_specs.get("device_type")
            if dev_type == "لپ‌تاپ" or "لپ" in query_norm:
                cat_filter = "لپ تاپ و نوت بوک"
            elif dev_type == "گوشی موبایل" or "گوشی" in query_norm:
                cat_filter = "گوشی موبایل"

        # If there is no query, no category filter, and no budget, we have no basis to search
        if not query_norm and not cat_filter and not constraints.budget_max_toman:
            return []

        # Check comparison in query string (e.g. "A یا B" or "مقایسه A با B")
        if " یا " in query_norm or " vs " in query_norm or ("مقایسه" in query_norm and " با " in query_norm):
            delims = [" یا ", " vs ", " با "]
            parts = [query_norm]
            for delim in delims:
                if delim in query_norm:
                    parts = query_norm.split(delim, 1)
                    break
            if len(parts) > 1:
                combined = []
                seen = set()
                for part in parts:
                    sub_q = part.replace("مقایسه", "").strip()
                    if sub_q:
                        sub_prods, _ = self.catalog_repo.search_products(q=sub_q, category=cat_filter, limit=10)
                        for sp in sub_prods:
                            if sp.product_id not in seen:
                                seen.add(sp.product_id)
                                combined.append(sp)
                if combined:
                    return combined

        # Check for distinctive model tokens (e.g. s23, ultra, 15, x1504va)
        model_tokens = [t for t in query_norm.split() if any(ch.isdigit() for ch in t) or t.lower() in ("pro", "ultra", "plus", "max", "mini", "lite")]
        products = []
        if model_tokens:
            model_q = " ".join(model_tokens)
            products, _ = self.catalog_repo.search_products(q=model_q, category=cat_filter, limit=30)

        if not products:
            products, total = self.catalog_repo.search_products(
                q=query_norm,
                category=cat_filter,
                limit=30,
            )

        # If zero matches and multi-word query, strip stop words and retry with distinctive keywords
        if not products:
            stop_words = {"گوشی", "موبایل", "مدل", "خرید", "حدود", "برای", "قیمت", "نو", "اصل", "گلکسی", "galaxy"}
            tokens = [t for t in query_norm.split() if t.lower() not in stop_words]
            if tokens:
                relaxed_q = " ".join(tokens)
                products, _ = self.catalog_repo.search_products(q=relaxed_q, category=cat_filter, limit=30)

        # If zero matches or budget constrained query with generic need, use budget-aware retrieval
        generic_noun = None
        if not cat_filter and not constraints.target_product_title:
            generic_noun = constraints.preferred_specs.get("device_type")
        if (not products or (constraints.budget_max_toman and not constraints.target_product_title)) and (cat_filter or constraints.target_brand or generic_noun):
            budget_prods = self._search_products_within_budget(
                category=cat_filter,
                brand=constraints.target_brand,
                max_price=constraints.budget_max_toman,
                limit=30,
                title_prefix=generic_noun,
            )
            if budget_prods:
                if not products:
                    return budget_prods
                # Merge budget prods with found products
                seen_ids = set(p.product_id for p in products)
                for bp in budget_prods:
                    if bp.product_id not in seen_ids:
                        products.append(bp)

        # If still zero matches, try searching brand + device type
        if not products and constraints.target_brand:
            brand_q = f"{constraints.target_brand} {constraints.preferred_specs.get('device_type', '')}".strip()
            products, _ = self.catalog_repo.search_products(q=brand_q, category=cat_filter, limit=30)

        # Filter brand strictly if brand was explicitly provided and not comparing
        if constraints.target_brand and not compared_brands:
            raw_brand = constraints.target_brand.lower().strip()
            synonyms = BRAND_SYNONYMS.get(raw_brand, {raw_brand})
            products = [
                p for p in products
                if any(syn in (p.brand_name or "").lower() for syn in synonyms)
                or any(syn in p.persian_title.lower() for syn in synonyms)
            ]

        # Filter out excluded brands
        if constraints.excluded_brands:
            excluded_synonyms = set()
            for b in constraints.excluded_brands:
                raw_b = b.lower().strip()
                syns = BRAND_SYNONYMS.get(raw_b, {raw_b})
                excluded_synonyms.update(syns)
            products = [
                p for p in products
                if not any(syn in (p.brand_name or "").lower() for syn in excluded_synonyms)
                and not any(syn in p.persian_title.lower() for syn in excluded_synonyms)
            ]

        # Filter out rejected products
        if constraints.rejected_product_ids:
            products = [p for p in products if p.product_id not in constraints.rejected_product_ids]

        # Generic product noun (e.g. یخچال): prefer items that ARE the product, not parts/accessories for it
        dev_type = constraints.preferred_specs.get("device_type")
        if dev_type and not cat_filter and not constraints.target_product_title:
            heads = [p for p in products if normalize_persian_text(p.persian_title).replace("\u200c", " ").strip().startswith(dev_type)]
            if heads:
                products = heads

        # Prioritize actual devices over accessories if looking for mobile or laptop
        if cat_filter == "گوشی موبایل" or dev_type == "گوشی موبایل" or (query_norm and ("گوشی" in query_norm or "موبایل" in query_norm)):
            phone_prods = [p for p in products if not any(w in p.persian_title for w in ["باتری", "کاور", "قاب", "گلس", "تاچ", "قلم", "شیشه"])]
            if phone_prods:
                products = phone_prods

        return products

    ACCESSORY_WORDS = ("کیف", "قاب", "کاور", "گلس", "محافظ", "باتری", "دوربین پشت", "شیشه", "تاچ", "قلم", "فلت", "ال سی دی", "lcd", "بند", "طرح")

    def _retrieve_text_comparison(self, title: Optional[str], cat_filter: Optional[str]) -> List[Product]:
        """Splits "مقایسه A و/با/یا B" into sub-queries and returns the best devices for each side."""
        if not title:
            return []
        q = normalize_digits(normalize_persian_text(title)).replace("\u200c", " ").strip()
        is_cmp = "مقایسه" in q or " یا " in q or " vs " in q.lower()
        if not is_cmp:
            return []
        q = q.replace("مقایسه", " ").replace(" vs ", " یا ").replace(" VS ", " یا ")
        parts: List[str] = []
        for delim in (" یا ", " با ", " و "):
            if delim in f" {q} ":
                parts = [x.strip() for x in f" {q} ".split(delim, 1)]
                break
        parts = [x for x in parts if x]
        if len(parts) < 2:
            return []
        combined: List[Product] = []
        for part in parts:
            sub_q = part.replace("گوشی", "").strip() or part
            found: List[Product] = []
            for cat in ([cat_filter] if cat_filter else ["گوشی موبایل", "لپ تاپ و نوت بوک", None]):
                prods, _ = self.catalog_repo.search_products(q=sub_q, category=cat, limit=15)
                prods = [p for p in prods if not any(w in p.persian_title.lower() for w in self.ACCESSORY_WORDS)]
                if prods:
                    found = prods[:5]
                    break
            combined.extend(p for p in found if p.product_id not in {c.product_id for c in combined})
        return combined

    def _search_products_within_budget(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 30,
        title_prefix: Optional[str] = None,
    ) -> List[Product]:
        """Directly retrieves products having offers meeting the budget constraint."""
        query_parts = [
            "SELECT DISTINCT p.product_id, p.persian_title, p.brand_name, p.category_name, p.model, p.image_urls, p.specs "
            "FROM products p JOIN offers o ON p.product_id = o.product_id WHERE o.price_toman > 1"
        ]
        params: List[Any] = []
        if max_price:
            query_parts.append("AND o.price_toman <= ?")
            params.append(max_price)
        if category:
            query_parts.append("AND p.category_name = ?")
            params.append(category)
        if title_prefix:
            query_parts.append("AND p.persian_title LIKE ?")
            params.append(f"{title_prefix}%")
        if brand:
            raw_brand = brand.lower().strip()
            synonyms = BRAND_SYNONYMS.get(raw_brand, {raw_brand})
            syn_clauses = " OR ".join(["LOWER(p.brand_name) LIKE ? OR LOWER(p.persian_title) LIKE ?" for _ in synonyms])
            query_parts.append(f"AND ({syn_clauses})")
            for syn in synonyms:
                params.extend([f"%{syn}%", f"%{syn}%"])

        # With a price cap, the most capable items sit near the cap (not the cheapest ones)
        query_parts.append("ORDER BY o.price_toman DESC LIMIT ?" if max_price else "ORDER BY o.price_toman ASC LIMIT ?")
        params.append(limit)

        sql = " ".join(query_parts)
        rows = self.catalog_repo.con.execute(sql, params).fetchall()
        return [self.catalog_repo._row_to_product(r) for r in rows]

    def _calculate_suitability(
        self,
        product: Product,
        offer: Offer,
        extracted_attrs: Dict[str, Any],
        constraints: ShoppingConstraints,
        price_assess: Any,
        shop_reliability: float,
        pros: List[str],
        cons: List[str],
        warnings: List[str],
    ) -> float:
        """Computes deterministic suitability score in [0.0, 1.0]."""
        score = 0.55

        # 1. Budget proximity / advantage
        if constraints.budget_max_toman:
            ratio = offer.price_toman / constraints.budget_max_toman
            # Near the cap = the class of product the user is shopping for; far below = likely a lower class
            if 0.70 <= ratio <= 1.0:
                score += 0.20
                pros.append(f"قیمت کاملاً متناسب با بودجه: {offer.price_toman:,} تومان")
            elif 0.40 <= ratio < 0.70:
                score += 0.15
                saved = int(constraints.budget_max_toman - offer.price_toman)
                pros.append(f"صرفه‌جویی عالی در بودجه (حدود {saved:,} تومان کمتر از سقف)")
            elif ratio < 0.40:
                score += 0.05
                saved = int(constraints.budget_max_toman - offer.price_toman)
                pros.append(f"صرفه‌جویی عالی در بودجه (حدود {saved:,} تومان کمتر از سقف)")
            else:
                score -= 0.30
                cons.append("فراتر از سقف بودجه مشخص‌شده")

        # 2. Market price plausibility
        if price_assess.reference_peer_price:
            dev = offer.price_toman / price_assess.reference_peer_price
            if 0.90 <= dev <= 1.05:
                score += 0.10
                pros.append("قیمت کاملاً منطبق بر میانه بازار")
            elif dev < 0.70 and price_assess.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL):
                score -= 0.25
                cons.append("قیمت به طور مشکوکی پایین‌تر از میانه بازار است")
                warnings.append("احتمال خطای قیمت‌گذاری یا ثبت اشتباه واحد پول (تومان/ریال)")

        # 3. Shop reliability
        if shop_reliability >= 0.60:
            score += 0.10
            pros.append("فروشگاه دارای امتیاز اعتماد و ثبات عملکرد بالا")
        elif shop_reliability < 0.40:
            score -= 0.15
            cons.append("سابقه آماری فروشگاه محدود یا دارای گزارش مغایرت است")

        # 4. Color / Specs matching
        if constraints.color and extracted_attrs.get("color"):
            if extracted_attrs["color"] == constraints.color:
                score += 0.05
                pros.append(f"رنگ درخواستی موجود: {constraints.color}")

        # 5. Technical reasoning for laptops / devices
        full_specs_text = f"{product.persian_title} {product.specs or {}} {offer.seller_title or ''}".lower()
        if constraints.preferred_specs.get("device_type") == "لپ‌تاپ" or (product.category_name and "لپ تاپ" in product.category_name):
            if any(cpu in full_specs_text for cpu in ["core i7", "i7", "core i9", "i9", "ryzen 7", "ryzen 9"]):
                score += 0.06
                pros.append("پردازنده قدرتمند رده‌بالا مناسب برنامه‌نویسی و پردازش سنگین")
            if any(r in full_specs_text for r in ["16gb", "16 gb", "32gb", "32 gb", "۱۶ گیگابایت", "۳۲ گیگابایت"]):
                score += 0.06
                pros.append("حافظه رم ۱۶ گیگابایت یا بالاتر مناسب اجرای همزمان نرم‌افزارها")
            if any(g in full_specs_text for g in ["rtx", "geforce", "radeon", "4060", "4050", "3050"]):
                score += 0.06
                pros.append("دارای پردازشگر گرافیکی مجزا مناسب کارهای تصویری و بازی")

        # 6. Battery life preference
        if constraints.battery_preference == "high_battery_life":
            if any(term in full_specs_text for term in ["macbook", "m1", "m2", "m3", "5000mah", "6000mah", "باتری قوی"]):
                score += 0.08
                pros.append("شارژدهی طولانی و مصرف انرژی بهینه")

        # 7. Newer generation preference
        if constraints.newer_models_only:
            if any(m in full_specs_text for m in ["2024", "2023", "14th", "13th", "gen 4", "gen 5", "s24", "iphone 15", "iphone 16"]):
                score += 0.06
                pros.append("مدل جدید از نسل‌های اخیر بازار")

        # Bounded between 0.05 and 0.98
        return float(np.clip(score, 0.05, 0.98))

    def _assign_trade_off_labels(self, candidates: List[CandidateOfferRecommendation]) -> None:
        """Assigns labels: best_overall, budget_pick, verified_confidence."""
        if not candidates:
            return

        # 1. Best overall: top suitability score
        candidates[0].trade_off_label = "best_overall"

        # 2. Budget pick: cheapest among remaining candidates
        if len(candidates) > 1:
            cheapest = min(candidates[1:], key=lambda c: c.price_toman)
            if cheapest.price_toman < candidates[0].price_toman:
                cheapest.trade_off_label = "budget_pick"

        # 3. Verified confidence: highest reliability and evidence quality
        remaining = [c for c in candidates if c.trade_off_label is None]
        if remaining:
            most_trusted = max(remaining, key=lambda c: c.shop_reliability_score)
            if most_trusted.shop_reliability_score > 0.50:
                most_trusted.trade_off_label = "verified_confidence"

    def _generate_trade_off_summary(
        self, candidates: List[CandidateOfferRecommendation], constraints: ShoppingConstraints
    ) -> str:
        if not candidates:
            return ""

        if constraints.preferred_specs.get("compared_brands") or "مقایسه" in (constraints.target_product_title or ""):
            if len(candidates) >= 2:
                c1, c2 = candidates[0], candidates[1]
                diff = abs(c1.price_toman - c2.price_toman)
                return (
                    f"تحلیل مقایسه‌ای: «{c1.product_title}» ({c1.price_toman:,.0f} تومان) در برابر "
                    f"«{c2.product_title}» ({c2.price_toman:,.0f} تومان). "
                    f"اختلاف قیمت {diff:,.0f} تومان است. گزینه «{c1.shop_name}» شایستگی {int(c1.suitability_score*100)}٪ و "
                    f"گزینه «{c2.shop_name}» شایستگی {int(c2.suitability_score*100)}٪ را ارائه می‌دهند."
                )

        parts = []
        best = candidates[0]
        parts.append(
            f"گزینه پیشنهادی اصلی: «{best.product_title}» از فروشگاه «{best.shop_name}» به قیمت {best.price_toman:,} تومان با امتیاز شایستگی {int(best.suitability_score*100)}٪."
        )

        for c in candidates[1:]:
            if c.trade_off_label == "budget_pick":
                diff = int(best.price_toman - c.price_toman)
                parts.append(
                    f"گزینه اقتصادی‌تر: «{c.shop_name}» با قیمت {c.price_toman:,} تومان ({diff:,} تومان ارزان‌تر)."
                )
            elif c.trade_off_label == "verified_confidence":
                parts.append(
                    f"گزینه با بالاترین اتکا: «{c.shop_name}» با امتیاز اعتماد {int(c.shop_reliability_score*100)}٪."
                )

        return " ".join(parts)
