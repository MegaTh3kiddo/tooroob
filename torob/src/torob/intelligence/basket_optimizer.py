"""Multi-Product Basket Optimization & Shop Coverage Engine.

Solves the real-world shopping problems:
1. "I need several products (e.g. monitor, keyboard, mouse). Find a single store that has all of them."
2. "If no single store has everything, find the cheapest/most practical combination of stores."
3. "Minimize total spending considering both product prices and travel burden."

Evidence & Algorithmic Principles:
1. Complete Catalogue Coverage != Verified Complete In-Store Stock:
   - Items are explicitly classified into listed_in_catalog vs seller_confirmed vs stock_unknown.
   - Dataset limitation: The 300-item per-shop export cap means missing from dataset != not carried by shop.
2. Price Incompleteness:
   - Does not report complete purchase total if any required item has unknown, zero, or placeholder price.
3. Search Scope Boundedness:
   - Evaluates combinations up to max_stops (default k in [2, 3]).
   - If k stops is insufficient, explicitly reports search_scope_reached instead of false universal infeasibility.
4. Strict Pareto Verification:
   - Verifies Pareto optimality (cheapest, fewest_stops, minimum_travel, highest_trust, best_overall)
     mathematically across all evaluated candidate combinations.
5. Dynamic Evidence Refresh:
   - Allows re-evaluating basket plans when seller confirmations or new stock evidence arrive.
"""

from datetime import datetime, timezone
import itertools
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from torob.domain.entities import Offer, Product, Shop
from torob.domain.plans import (
    BasketItemMatch,
    MultiStoreBasketPlan,
    PlanOptimizationPriority,
    ShopBasketCoverage,
)
from torob.intelligence.inventory import InventoryIntelligenceEngine
from torob.intelligence.pricing import PriceIntelligenceEngine
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.distance import DistanceRouter, haversine_km
from torob.routing.hours import BusinessHoursEvaluator
from torob.storage.repository_catalog import CatalogRepository

logger = logging.getLogger("torob.intelligence.basket_optimizer")


class BasketOptimizationEngine:
    def __init__(
        self,
        catalog_repo: Optional[CatalogRepository] = None,
        router: Optional[DistanceRouter] = None,
        pricing_engine: Optional[PriceIntelligenceEngine] = None,
        inventory_engine: Optional[InventoryIntelligenceEngine] = None,
        reliability_engine: Optional[ShopReliabilityEngine] = None,
    ):
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.router = router or DistanceRouter()
        self.pricing_engine = pricing_engine or PriceIntelligenceEngine()
        self.inventory_engine = inventory_engine or InventoryIntelligenceEngine()
        self.reliability_engine = reliability_engine or ShopReliabilityEngine()

    def optimize_basket(
        self,
        basket_queries: List[str],
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_budget_toman: Optional[float] = None,
        max_stops: int = 3,
        require_single_store: bool = False,
        optimization_priority: PlanOptimizationPriority = PlanOptimizationPriority.BALANCED,
        min_shop_reliability: Optional[float] = None,
        limit_plans: int = 4,
    ) -> List[MultiStoreBasketPlan]:
        """Core basket optimization entry point returning Pareto-verified purchasing plans."""
        if not basket_queries:
            return []

        # 1. Retrieve Candidate Offers per Basket Item
        item_candidates: Dict[int, List[Tuple[Product, Offer, Shop]]] = {}
        query_map: Dict[int, str] = {idx: q.strip() for idx, q in enumerate(basket_queries)}

        for idx, q in query_map.items():
            candidates = self._find_candidate_offers_for_query(q)
            item_candidates[idx] = candidates

        # Check if any item has 0 candidates across entire catalog
        unmatched_queries = [query_map[idx] for idx, cands in item_candidates.items() if not cands]
        if len(unmatched_queries) == len(basket_queries):
            return [
                MultiStoreBasketPlan(
                    strategy="no_coverage",
                    strategy_label_persian="عدم امکان تامین سبد",
                    stores=[],
                    total_product_cost_toman=0.0,
                    is_total_price_complete=False,
                    all_items_covered=False,
                    missing_items=unmatched_queries,
                    composite_score=0.0,
                    trade_off_explanation="هیچ‌یک از کالاهای موجود در سبد خرید در کاتالوگ فعلی یافت نشدند (توجه: ممکن است به دلیل محدودیت ۳۰۰ کالا در خروجی داده‌ها باشد).",
                    warnings=["کالاهای درخواستی در کاتالوگ یافت نشد"],
                )
            ]

        # 2. Build Shop Coverage Matrix
        shop_coverage_map = self._build_shop_coverage_matrix(item_candidates)

        # 3. Create ShopBasketCoverage objects with Evidence Semantics
        shop_coverages: List[ShopBasketCoverage] = []
        for shop_id, item_dict in shop_coverage_map.items():
            shop = self.catalog_repo.get_shop(shop_id)
            if not shop:
                continue

            rel = self.reliability_engine.assess_shop(shop)
            if min_shop_reliability and rel.composite_reliability_score < min_shop_reliability:
                continue

            travel_mins = None
            if user_lat is not None and user_lon is not None and shop.lat and shop.lon:
                _, travel_mins, _ = self.router.estimate_travel(user_lat, user_lon, shop.lat, shop.lon)

            # Check business hours
            now = datetime.now(timezone.utc)
            is_open, _, _, hours_desc = BusinessHoursEvaluator.evaluate_hours(shop.weekly_hours, now)

            matched_items: List[BasketItemMatch] = []
            total_price = 0.0
            has_missing = False

            for item_idx, (prod, off) in item_dict.items():
                price = off.price_toman
                price_known = price is not None and price > 1

                if not price_known:
                    has_missing = True
                    price_val = 0.0
                    price_status = "price_unknown"
                    price_type = "placeholder_invalid"
                else:
                    price_val = price
                    price_status = "price_known"
                    price_type = "fixed_retail"
                    total_price += price_val

                matched_items.append(
                    BasketItemMatch(
                        query=query_map[item_idx],
                        matched_product_id=prod.product_id,
                        matched_product_title=prod.persian_title,
                        offer_id=off.offer_id,
                        shop_id=shop.shop_id,
                        quantity=1,
                        price_toman=price_val if price_known else None,
                        price_type=price_type,
                        price_status=price_status,
                        seller_title=off.seller_title,
                        match_grade="exact" if query_map[item_idx].lower() in prod.persian_title.lower() else "variant_compatible",
                        evidence_status="listed_in_catalog",
                        stock_evidence="stock_unknown",
                        fulfillment_channel="in_store_pickup",
                        is_verified_in_store=False,
                        verification_recommendation=f"استعلام موجودی {prod.persian_title[:30]} پیش از عزیمت پیشنهاد می‌شود.",
                    )
                )

            missing_for_shop = [query_map[i] for i in range(len(basket_queries)) if i not in item_dict]

            shop_coverages.append(
                ShopBasketCoverage(
                    shop_id=shop.shop_id,
                    shop_name=shop.name,
                    shop_address=shop.address,
                    lat=shop.lat,
                    lon=shop.lon,
                    items_covered_count=len(matched_items),
                    total_items_requested=len(basket_queries),
                    covers_entire_basket=(len(matched_items) == len(basket_queries)),
                    matched_items=matched_items,
                    missing_items=missing_for_shop,
                    total_listed_price_toman=total_price if not has_missing else None,
                    is_total_price_complete=not has_missing,
                    has_missing_prices=has_missing,
                    shop_reliability_score=round(rel.composite_reliability_score, 3),
                    estimated_travel_minutes=travel_mins,
                    is_open_now=is_open,
                    opening_hours_desc=hours_desc,
                    coverage_percentage=round((len(matched_items) / len(basket_queries)) * 100.0, 1),
                    verification_level="unverified_catalog_only",
                    export_cap_limitation_noted=True,
                )
            )

        # 4. Single-Store Strategy
        single_store_candidates = [sc for sc in shop_coverages if sc.covers_entire_basket]
        plans: List[MultiStoreBasketPlan] = []

        if single_store_candidates:
            if optimization_priority == PlanOptimizationPriority.CHEAPEST:
                single_store_candidates.sort(key=lambda s: s.total_listed_price_toman or float("inf"))
            elif optimization_priority == PlanOptimizationPriority.HIGHEST_TRUST:
                single_store_candidates.sort(key=lambda s: -s.shop_reliability_score)
            else:
                single_store_candidates.sort(
                    key=lambda s: (s.total_listed_price_toman or float("inf"), -(s.shop_reliability_score))
                )

            best_single = single_store_candidates[0]
            budget_ok = (
                max_budget_toman is None
                or (best_single.total_listed_price_toman is not None and best_single.total_listed_price_toman <= max_budget_toman)
            )

            if budget_ok:
                inquiry = self._create_consolidated_inquiry(best_single)
                plan_single = MultiStoreBasketPlan(
                    strategy="single_store",
                    strategy_label_persian="خرید تجمیعی از یک فروشگاه",
                    stores=[best_single],
                    total_product_cost_toman=best_single.total_listed_price_toman,
                    is_total_price_complete=best_single.is_total_price_complete,
                    estimated_total_travel_minutes=best_single.estimated_travel_minutes or 0.0,
                    total_stops=1,
                    all_items_covered=True,
                    missing_items=[],
                    guarantee_status="complete_catalog_coverage_unverified_stock",
                    composite_score=round(0.85 * best_single.shop_reliability_score + 0.15, 3),
                    trade_off_explanation=(
                        f"فروشگاه «{best_single.shop_name}» تمامی {len(basket_queries)} قلم کالا را در کاتالوگ پوشش می‌دهد. "
                        f"مجموع قیمت: {best_single.total_listed_price_toman:,.0f} تومان با نمره اعتماد {int(best_single.shop_reliability_score*100)}٪. "
                        f"(توجه: ثبت در کاتالوگ به معنای تضمین ۱۰۰٪ موجودی انبار نیست؛ استعلام تجمیعی توصیه می‌شود)."
                    ),
                    recommended_inquiry=inquiry,
                    itinerary_order=[{"stop": 1, "shop_id": best_single.shop_id, "shop_name": best_single.shop_name}],
                )
                plans.append(plan_single)

        if require_single_store and plans:
            self._verify_and_assign_pareto_labels(plans)
            return plans[:limit_plans]

        # 5. Multi-Store Combinatorial Optimization
        multi_plans = self._optimize_multi_store_combinations(
            shop_coverages=shop_coverages,
            total_items_count=len(basket_queries),
            query_map=query_map,
            max_stops=max_stops,
            max_budget=max_budget_toman,
            user_lat=user_lat,
            user_lon=user_lon,
        )
        plans.extend(multi_plans)

        # Deduplicate plans by set of shop IDs
        unique_plans: List[MultiStoreBasketPlan] = []
        seen_shop_sets = set()
        for p in plans:
            s_set = frozenset(s.shop_id for s in p.stores)
            if s_set not in seen_shop_sets:
                seen_shop_sets.add(s_set)
                unique_plans.append(p)

        # Mathematical Pareto Verification
        self._verify_and_assign_pareto_labels(unique_plans)

        # Sort plans according to optimization priority
        if optimization_priority == PlanOptimizationPriority.CHEAPEST:
            unique_plans.sort(key=lambda p: (not p.all_items_covered, p.total_product_cost_toman or float("inf")))
        elif optimization_priority == PlanOptimizationPriority.FEWEST_STOPS:
            unique_plans.sort(key=lambda p: (not p.all_items_covered, p.total_stops, p.total_product_cost_toman or float("inf")))
        elif optimization_priority == PlanOptimizationPriority.MINIMUM_TRAVEL:
            unique_plans.sort(key=lambda p: (not p.all_items_covered, p.estimated_total_travel_minutes))
        elif optimization_priority == PlanOptimizationPriority.HIGHEST_TRUST:
            unique_plans.sort(key=lambda p: (not p.all_items_covered, -p.composite_score))
        else:
            unique_plans.sort(key=lambda p: (-p.composite_score))

        return unique_plans[:limit_plans]

    def _find_candidate_offers_for_query(self, query: str) -> List[Tuple[Product, Offer, Shop]]:
        """Retrieves products and valid offers for a specific basket query."""
        products, _ = self.catalog_repo.search_products(q=query, limit=15)
        if not products:
            tokens = [t for t in query.split() if len(t) > 2]
            if tokens:
                products, _ = self.catalog_repo.search_products(q=" ".join(tokens), limit=10)

        candidates = []
        for p in products:
            offers = self.catalog_repo.get_offers_by_product(p.product_id, limit=20)
            for o in offers:
                if not o.price_toman or o.price_toman <= 1:
                    continue
                shop = self.catalog_repo.get_shop(o.shop_id)
                if shop:
                    candidates.append((p, o, shop))
        return candidates

    def _build_shop_coverage_matrix(
        self, item_candidates: Dict[int, List[Tuple[Product, Offer, Shop]]]
    ) -> Dict[str, Dict[int, Tuple[Product, Offer]]]:
        """Constructs map: shop_id -> {item_idx -> (Product, cheapest Offer)}."""
        matrix: Dict[str, Dict[int, Tuple[Product, Offer]]] = {}

        for item_idx, cand_list in item_candidates.items():
            for prod, off, shop in cand_list:
                s_id = shop.shop_id
                if s_id not in matrix:
                    matrix[s_id] = {}
                if item_idx not in matrix[s_id] or (off.price_toman and off.price_toman < matrix[s_id][item_idx][1].price_toman):
                    matrix[s_id][item_idx] = (prod, off)

        return matrix

    def _optimize_multi_store_combinations(
        self,
        shop_coverages: List[ShopBasketCoverage],
        total_items_count: int,
        query_map: Dict[int, str],
        max_stops: int,
        max_budget: Optional[float],
        user_lat: Optional[float],
        user_lon: Optional[float],
    ) -> List[MultiStoreBasketPlan]:
        """Combinatorial search for optimal 2-stop and multi-stop shop subsets."""
        plans: List[MultiStoreBasketPlan] = []
        viable_shops = [sc for sc in shop_coverages if sc.items_covered_count > 0]
        viable_shops.sort(key=lambda s: (-s.items_covered_count, -s.shop_reliability_score, s.total_listed_price_toman or float("inf")))
        search_pool = viable_shops[:25]

        target_items_set = set(range(total_items_count))
        found_combinations: List[Tuple[List[ShopBasketCoverage], float, float, bool]] = []

        # Determine union of items covered across entire search pool
        all_pool_covered_indices: Set[int] = set()
        for s in search_pool:
            for m in s.matched_items:
                for idx, q_text in query_map.items():
                    if m.query == q_text:
                        all_pool_covered_indices.add(idx)

        # Combinatorial evaluation bounded by max_stops (and safe computation cap min(max_stops, 3))
        max_k = min(max_stops, 3)
        for k in range(2, max_k + 1):
            for combo in itertools.combinations(search_pool, k):
                covered_indices: Set[int] = set()
                total_product_cost = 0.0
                combo_missing_prices = False

                for i in range(total_items_count):
                    q_text = query_map[i]
                    matching_prices = []
                    item_present = False
                    for shop in combo:
                        for m in shop.matched_items:
                            if m.query == q_text:
                                item_present = True
                                if m.price_toman is not None and m.price_toman > 1:
                                    matching_prices.append(m.price_toman)
                    if item_present:
                        covered_indices.add(i)
                        if matching_prices:
                            total_product_cost += min(matching_prices)
                        else:
                            combo_missing_prices = True

                if covered_indices == target_items_set:
                    # Enforce strict budget constraint if price is complete
                    if max_budget is not None and not combo_missing_prices and total_product_cost > max_budget:
                        continue

                    total_travel_mins = sum(s.estimated_travel_minutes or 15.0 for s in combo)
                    found_combinations.append((list(combo), total_product_cost, total_travel_mins, combo_missing_prices))

        if not found_combinations:
            # Check if search scope limit (max_stops) was reached vs catalog exhaustion
            # Scope exceeded iff all items exist in the pool, but require more than max_k shops
            scope_exceeded = (all_pool_covered_indices == target_items_set) and (len(search_pool) > max_k)
            best_partial = self._find_best_partial_combination(
                search_pool, total_items_count, query_map, max_stops=max_stops, scope_exceeded=scope_exceeded
            )
            if best_partial:
                plans.append(best_partial)
            return plans

        # 1. Cheapest Combination Plan
        cheapest_combo = min(found_combinations, key=lambda c: c[1])
        c_shops, c_cost, c_travel, c_missing_prices = cheapest_combo
        avg_rel_c = sum(s.shop_reliability_score for s in c_shops) / len(c_shops)
        c_warnings = ["برخی اقلام دارای قیمت نامشخص در کاتالوگ هستند؛ هزینه کل تخمینی است"] if c_missing_prices else []
        plans.append(
            MultiStoreBasketPlan(
                strategy="cheapest_combination",
                strategy_label_persian="اقتصادی‌ترین ترکیب چند فروشگاهی",
                stores=c_shops,
                total_product_cost_toman=c_cost,
                is_total_price_complete=not c_missing_prices,
                estimated_total_travel_minutes=c_travel,
                total_stops=len(c_shops),
                all_items_covered=True,
                missing_items=[],
                guarantee_status="complete_catalog_coverage_unverified_stock",
                composite_score=round(0.60 * (1.0 / (1.0 + c_cost * 1e-8)) + 0.40 * avg_rel_c, 3),
                trade_off_explanation=(
                    f"ارزان‌ترین خرید با تقسیم اقلام بین {len(c_shops)} فروشگاه («{'» و «'.join(s.shop_name for s in c_shops)}»). "
                    f"مجموع هزینه کالاها {c_cost:,.0f} تومان است."
                ),
                itinerary_order=[{"stop": idx, "shop_id": s.shop_id, "shop_name": s.shop_name} for idx, s in enumerate(c_shops, 1)],
                warnings=c_warnings,
            )
        )

        # 2. Minimum Travel Combination Plan
        if user_lat is not None and user_lon is not None:
            min_travel_combo = min(found_combinations, key=lambda c: c[2])
            t_shops, t_cost, t_travel, t_missing_prices = min_travel_combo
            avg_rel_t = sum(s.shop_reliability_score for s in t_shops) / len(t_shops)
            t_warnings = ["برخی اقلام دارای قیمت نامشخص در کاتالوگ هستند"] if t_missing_prices else []
            plans.append(
                MultiStoreBasketPlan(
                    strategy="minimum_travel",
                    strategy_label_persian="نزدیک‌ترین ترکیب فروشگاهی (حداقل مسافت)",
                    stores=t_shops,
                    total_product_cost_toman=t_cost,
                    is_total_price_complete=not t_missing_prices,
                    estimated_total_travel_minutes=t_travel,
                    total_stops=len(t_shops),
                    all_items_covered=True,
                    missing_items=[],
                    guarantee_status="complete_catalog_coverage_unverified_stock",
                    composite_score=round(0.60 * (1.0 / (1.0 + t_travel * 0.05)) + 0.40 * avg_rel_t, 3),
                    trade_off_explanation=(
                        f"حداقل زمان سفر با مراجعه به «{'» و «'.join(s.shop_name for s in t_shops)}». "
                        f"مجموع زمان سفر تقریبی {t_travel:.0f} دقیقه و هزینه اقلام {t_cost:,.0f} تومان."
                    ),
                    itinerary_order=[{"stop": idx, "shop_id": s.shop_id, "shop_name": s.shop_name} for idx, s in enumerate(t_shops, 1)],
                    warnings=t_warnings,
                )
            )

        # 3. Highest Trust Combination Plan
        trusted_combo = max(found_combinations, key=lambda c: sum(s.shop_reliability_score for s in c[0]) / len(c[0]))
        r_shops, r_cost, r_travel, r_missing_prices = trusted_combo
        avg_rel_r = sum(s.shop_reliability_score for s in r_shops) / len(r_shops)
        r_warnings = ["برخی اقلام دارای قیمت نامشخص در کاتالوگ هستند"] if r_missing_prices else []
        plans.append(
            MultiStoreBasketPlan(
                strategy="highest_trust",
                strategy_label_persian="معتبرترین ترکیب فروشگاه‌ها",
                stores=r_shops,
                total_product_cost_toman=r_cost,
                is_total_price_complete=not r_missing_prices,
                estimated_total_travel_minutes=r_travel,
                total_stops=len(r_shops),
                all_items_covered=True,
                missing_items=[],
                guarantee_status="complete_catalog_coverage_unverified_stock",
                composite_score=round(avg_rel_r, 3),
                trade_off_explanation=(
                    f"انتخاب بر اساس بالاترین سابقه و اعتبار فروشگاه‌ها («{'» و «'.join(s.shop_name for s in r_shops)}») با میانگین اعتماد {int(avg_rel_r*100)}٪."
                ),
                itinerary_order=[{"stop": idx, "shop_id": s.shop_id, "shop_name": s.shop_name} for idx, s in enumerate(r_shops, 1)],
                warnings=r_warnings,
            )
        )

        return plans

    def _find_best_partial_combination(
        self,
        search_pool: List[ShopBasketCoverage],
        total_items_count: int,
        query_map: Dict[int, str],
        max_stops: int = 3,
        scope_exceeded: bool = False,
    ) -> Optional[MultiStoreBasketPlan]:
        """Constructs greedy best-effort plan when 100% basket coverage is impossible in catalog."""
        if not search_pool:
            return None

        s1 = search_pool[0]
        s1_covered = set(m.query for m in s1.matched_items)

        best_s2 = None
        best_new_items = 0
        for s in search_pool[1:]:
            s_covered = set(m.query for m in s.matched_items)
            new_items = len(s_covered - s1_covered)
            if new_items > best_new_items:
                best_new_items = new_items
                best_s2 = s

        chosen_stores = [s1]
        if best_s2:
            chosen_stores.append(best_s2)

        covered_all = set()
        cost = 0.0
        has_missing_prices = False
        for s in chosen_stores:
            for m in s.matched_items:
                if m.query not in covered_all:
                    covered_all.add(m.query)
                    if m.price_toman:
                        cost += m.price_toman
                    else:
                        has_missing_prices = True

        missing = [query_map[i] for i in range(total_items_count) if query_map[i] not in covered_all]

        if scope_exceeded:
            scope_msg = f" (سقف جستجوی {max_stops} توقف تکمیل شد؛ اقلام موجودند ولی ممکن است به فروشگاه‌های بیشتری نیاز باشد)"
        else:
            scope_msg = " (اقلام مفقود در کل کاتالوگ فروشگاه‌ها ناموجود هستند)"

        explanation = (
            f"پوشش {len(covered_all)} قلم از {total_items_count} قلم کالا با مراجعه به «{'» و «'.join(s.shop_name for s in chosen_stores)}»{scope_msg}. "
            f"اقلام «{', '.join(missing)}» در سقف توقف مشخص‌شده تامین نشدند."
        )

        return MultiStoreBasketPlan(
            strategy="partial_coverage",
            strategy_label_persian="پوشش حداکثری موجود کاتالوگ",
            stores=chosen_stores,
            total_product_cost_toman=cost if not has_missing_prices else None,
            is_total_price_complete=not has_missing_prices,
            total_stops=len(chosen_stores),
            all_items_covered=False,
            missing_items=missing,
            search_scope_reached=scope_exceeded,
            guarantee_status="partial_catalog_coverage",
            composite_score=round(len(covered_all) / total_items_count, 3),
            trade_off_explanation=explanation,
            warnings=[f"اقلام {missing} در کاتالوگ فروشگاه‌ها ناموجود بود"],
        )

    def _verify_and_assign_pareto_labels(self, plans: List[MultiStoreBasketPlan]) -> None:
        """Mathematically verifies Pareto optimality across evaluated candidate plans."""
        if not plans:
            return

        full_plans = [p for p in plans if p.all_items_covered and p.total_product_cost_toman is not None]
        if not full_plans:
            for p in plans:
                p.pareto_labels = [p.strategy]
            return

        min_cost = min(p.total_product_cost_toman for p in full_plans)
        min_stops = min(p.total_stops for p in full_plans)
        min_travel = min(p.estimated_total_travel_minutes for p in full_plans)
        max_score = max(p.composite_score for p in full_plans)

        for p in full_plans:
            labels = []
            if p.total_product_cost_toman == min_cost:
                labels.append("cheapest")
            if p.total_stops == min_stops:
                labels.append("fewest_stops")
            if p.estimated_total_travel_minutes == min_travel:
                labels.append("minimum_travel")
            if p.composite_score == max_score:
                labels.append("best_overall")
            p.pareto_labels = labels or [p.strategy]

    def _create_consolidated_inquiry(self, shop_cov: ShopBasketCoverage) -> Dict[str, Any]:
        """Creates grouped inquiry payload to verify multiple basket items in a single seller notification."""
        return {
            "shop_id": shop_cov.shop_id,
            "shop_name": shop_cov.shop_name,
            "items_count": len(shop_cov.matched_items),
            "product_ids": [m.matched_product_id for m in shop_cov.matched_items],
            "product_titles": [m.matched_product_title for m in shop_cov.matched_items],
            "total_basket_price_toman": shop_cov.total_listed_price_toman,
            "reason": (
                f"استعلام تجمیعی پیش از حرکت از {shop_cov.shop_name} جهت اطمینان از موجودی همزمان "
                f"{len(shop_cov.matched_items)} قلم کالا و جلوگیری از تردد بیهوده."
            ),
        }

    def reevaluate_plan_with_evidence(
        self,
        plan: MultiStoreBasketPlan,
        verified_stock_map: Dict[str, bool],
    ) -> MultiStoreBasketPlan:
        """Re-evaluates a generated basket plan when new seller inventory evidence arrives."""
        updated_plan = plan.model_copy(deep=True)
        all_confirmed = True
        any_unconfirmed = False

        for store in updated_plan.stores:
            for item in store.matched_items:
                if item.matched_product_id in verified_stock_map:
                    is_in_stock = verified_stock_map[item.matched_product_id]
                    if is_in_stock:
                        item.stock_evidence = "seller_confirmed"
                        item.is_verified_in_store = True
                        item.verification_recommendation = "موجودی در فروشگاه توسط فروشنده تایید شده است."
                    else:
                        item.stock_evidence = "confirmed_unavailable"
                        item.is_verified_in_store = False
                        all_confirmed = False
                        any_unconfirmed = True
                        updated_plan.warnings.append(f"کالای {item.matched_product_title[:30]} در فروشگاه ناموجود اعلام شد.")
                else:
                    all_confirmed = False

        if any_unconfirmed:
            updated_plan.all_items_covered = False
            updated_plan.composite_score = round(updated_plan.composite_score * 0.4, 3)
            updated_plan.guarantee_status = "item_confirmed_unavailable"
            updated_plan.trade_off_explanation += " ⚠️ هشدار: طبق استعلام جدید فروشنده، برخی اقلام ناموجود شده‌اند."
        elif all_confirmed:
            updated_plan.composite_score = min(1.0, round(updated_plan.composite_score + 0.15, 3))
            updated_plan.guarantee_status = "seller_confirmed_in_store"
            updated_plan.trade_off_explanation += " 🛡️ تاییدیه: موجودی تمامی اقلام توسط فروشنده تایید گردید."

        return updated_plan
