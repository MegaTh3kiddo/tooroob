"""On-Route Shopping & Minimum-Detour Purchasing Engine.

Solves the real-world shopping problem:
"I am traveling from Origin to Destination and want to purchase a product (or multi-item basket)
along the way without significant detour."

Algorithms:
1. Baseline Route Evaluation:
   - Uses real road network routing (when provider configured) or calibrated urban corridor heuristic.
   - Extracts baseline route geometry, distance, and duration.
2. Two-Stage Spatial Corridor Filtering:
   - Longitudinal endpoint check: Rejects shops located behind the origin or beyond the destination.
   - Cross-track perpendicular / polyline distance: Uses route geometry polyline when available,
     otherwise finite line segment projection.
3. Fine Detour & Route Evaluation:
   - Measures pure additional travel time: T(O -> S) + T(S -> D) - T(O -> D).
   - Separates pure travel detour, shopping dwell time (T_dwell), and total additional journey time.
   - Tracks arrival at shop and expected final arrival at destination.
   - Evaluates opening hours and stock survival hazard at expected arrival time.
4. Road-Network Verification & Quality:
   - Distinguishes "verified_road_network" from "approximate_heuristic".
   - Flags approximate detour warning when external road provider is not available.
5. Multi-Criteria Pareto Trade-Off Labeling:
   - minimum_detour, cheapest_stop, most_trusted, best_overall.
"""

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from torob.domain.entities import Offer, Product, Shop
from torob.domain.plans import OnRoutePlanResult, OnRouteShopStop
from torob.intelligence.inventory import InventoryIntelligenceEngine
from torob.intelligence.pricing import PriceIntelligenceEngine
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.distance import (
    DistanceRouter,
    haversine_km,
    point_is_beyond_segment,
    point_to_polyline_distance_km,
    point_to_segment_distance_km,
)
from torob.routing.hours import BusinessHoursEvaluator
from torob.storage.repository_catalog import CatalogRepository

logger = logging.getLogger("torob.routing.on_route")


def cross_track_distance_km(
    lat_p: float, lon_p: float,
    lat_start: float, lon_start: float,
    lat_end: float, lon_end: float,
) -> float:
    """Calculates perpendicular spherical distance from point P to line segment Start->End in km.
    
    Uses finite segment projection so points beyond endpoints reflect distance to the endpoint.
    """
    dist_km, _ = point_to_segment_distance_km(lat_p, lon_p, lat_start, lon_start, lat_end, lon_end)
    return dist_km


class OnRouteShoppingEngine:
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

    def find_on_route_purchases(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        product_query: str,
        basket_queries: Optional[List[str]] = None,
        max_detour_minutes: Optional[float] = None,
        max_price_toman: Optional[float] = None,
        min_shop_reliability: Optional[float] = None,
        departure_time: Optional[datetime] = None,
        dwell_minutes: float = 10.0,
        corridor_width_km: float = 8.0,
        limit: int = 5,
    ) -> OnRoutePlanResult:
        """Finds shops along the route from Origin to Destination that offer the requested product with minimal detour."""
        now = departure_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Baseline Route Evaluation
        base_route = self.router.get_detailed_route(origin_lat, origin_lon, dest_lat, dest_lon)
        base_dist_km = base_route.distance_km
        base_duration_mins = base_route.duration_minutes
        routing_source = base_route.routing_provider_name
        is_verified_network = base_route.is_verified_road_network
        route_geom = base_route.geometry or [(origin_lat, origin_lon), (dest_lat, dest_lon)]

        warnings = []
        if routing_source == "synthetic_road_graph":
            warnings.append("انحراف مسیر بر اساس گراف شبیه‌سازی‌شده معابر شهری محاسبه شده است.")
        elif not is_verified_network:
            warnings.append("انحراف مسیر بر اساس برآورد هندسی تخمین زده شده و قطعی نیست.")

        # Edge case: Origin and destination are practically identical
        if base_dist_km < 0.1:
            warnings.append("مبدا و مقصد سفر عملاً یکسان هستند؛ جستجو به شعاع اطراف موقعیت مبدا محدود شد.")

        # 2. Retrieve Candidate Products & Offers
        # If basket_queries supplied or multi-item query present
        effective_queries = basket_queries or []
        if not effective_queries:
            if " و " in product_query and not any(w in product_query for w in ["لپ تاپ و نوت بوک", "گوشی و تبلت"]):
                effective_queries = [q.strip() for q in product_query.split(" و ") if len(q.strip()) > 1]
            elif "،" in product_query:
                effective_queries = [q.strip() for q in product_query.split("،") if len(q.strip()) > 1]
            else:
                effective_queries = [product_query.strip()]

        products_by_query: Dict[str, List[Product]] = {}
        for q in effective_queries:
            prods, _ = self.catalog_repo.search_products(q=q, limit=15)
            if prods:
                products_by_query[q] = prods

        if not products_by_query:
            return OnRoutePlanResult(
                origin={"lat": origin_lat, "lon": origin_lon},
                destination={"lat": dest_lat, "lon": dest_lon},
                baseline_distance_km=base_dist_km,
                baseline_duration_minutes=base_duration_mins,
                routing_source=routing_source,
                is_verified_road_network=is_verified_network,
                route_geometry=route_geom,
                recommended_stops=[],
                trade_off_summary=f"کالایی منطبق با «{product_query}» در کاتالوگ یافت نشد.",
                is_feasible=False,
                warnings=warnings + ["محصول منطبق در کاتالوگ موجود نیست"],
            )

        # 3. Spatial Corridor Filter (Stage 1)
        # Bounding box with buffer
        min_lat = min(origin_lat, dest_lat) - (corridor_width_km / 111.0)
        max_lat = max(origin_lat, dest_lat) + (corridor_width_km / 111.0)
        mean_lat = (origin_lat + dest_lat) / 2.0
        cos_lat = max(0.2, math.cos(math.radians(mean_lat)))
        min_lon = min(origin_lon, dest_lon) - (corridor_width_km / (111.0 * cos_lat))
        max_lon = max(origin_lon, dest_lon) + (corridor_width_km / (111.0 * cos_lat))

        candidate_stops: List[OnRouteShopStop] = []

        # Iterate over matching products across queries
        all_products = []
        for prods in products_by_query.values():
            all_products.extend(prods)
        seen_pids = set()
        unique_products = [p for p in all_products if not (p.product_id in seen_pids or seen_pids.add(p.product_id))]

        for product in unique_products:
            offers = self.catalog_repo.get_offers_by_product(product.product_id, limit=30)
            peer_offers = [o for o in offers if o.price_toman and o.price_toman > 1]

            for offer in offers:
                if not offer.price_toman or offer.price_toman <= 1:
                    continue
                if max_price_toman is not None and offer.price_toman > max_price_toman:
                    continue

                shop = self.catalog_repo.get_shop(offer.shop_id)
                if not shop or shop.lat is None or shop.lon is None:
                    continue

                # Bounding box pre-check
                if not (min_lat <= shop.lat <= max_lat and min_lon <= shop.lon <= max_lon):
                    continue

                # Longitudinal endpoint check: reject shops behind origin or beyond destination
                if base_dist_km >= 0.5:
                    if point_is_beyond_segment(shop.lat, shop.lon, origin_lat, origin_lon, dest_lat, dest_lon, margin_ratio=0.10):
                        continue

                # Route geometry / Cross-track corridor distance check
                if len(route_geom) > 2:
                    dist_to_route, _, _ = point_to_polyline_distance_km(shop.lat, shop.lon, route_geom)
                else:
                    dist_to_route, _ = point_to_segment_distance_km(shop.lat, shop.lon, origin_lat, origin_lon, dest_lat, dest_lon)

                if dist_to_route > corridor_width_km:
                    continue

                # Reliability filter
                rel = self.reliability_engine.assess_shop(shop)
                if min_shop_reliability is not None and rel.composite_reliability_score < min_shop_reliability:
                    continue

                # 4. Fine Route & Detour Evaluation (Stage 2)
                # Leg 1: Origin -> Shop
                leg1_route = self.router.get_detailed_route(origin_lat, origin_lon, shop.lat, shop.lon)
                leg1_dist = leg1_route.distance_km
                leg1_mins = leg1_route.duration_minutes

                # Leg 2: Shop -> Destination
                leg2_route = self.router.get_detailed_route(shop.lat, shop.lon, dest_lat, dest_lon)
                leg2_dist = leg2_route.distance_km
                leg2_mins = leg2_route.duration_minutes

                # Pure additional travel time (without dwell)
                additional_travel_mins = max(0.0, round(leg1_mins + leg2_mins - base_duration_mins, 1))
                detour_dist_km = max(0.0, round(leg1_dist + leg2_dist - base_dist_km, 2))

                # Total additional journey time (including dwell inside store)
                total_additional_journey_mins = round(additional_travel_mins + dwell_minutes, 1)
                total_journey_via_shop_mins = round(leg1_mins + dwell_minutes + leg2_mins, 1)

                # Hard constraint: Max Detour Minutes (enforced on pure travel detour)
                if max_detour_minutes is not None and additional_travel_mins > max_detour_minutes:
                    continue

                # Expected arrival timestamps
                arrival_shop_time = now + timedelta(minutes=leg1_mins)
                arrival_dest_time = now + timedelta(minutes=total_journey_via_shop_mins)

                # Opening hours evaluation at shop arrival
                is_open, open_h, close_h, hours_desc = BusinessHoursEvaluator.evaluate_hours(shop.weekly_hours, arrival_shop_time)

                stop_warnings = []
                if not is_open:
                    stop_warnings.append(f"فروشگاه در زمان تخمینی رسیدن ({arrival_shop_time.strftime('%H:%M')}) بسته است.")
                if not is_verified_network:
                    stop_warnings.append("انحراف مسیر بر اساس برآورد هندسی تخمین زده شده است.")

                # Price Assessment
                peers_loso = [p for p in peer_offers if p.shop_id != offer.shop_id]
                price_assess = self.pricing_engine.assess_offer_price(offer, peers_loso, product=product, now=now)

                # Inventory Hazard Survival at Arrival
                stock_assess = self.inventory_engine.assess_stock(
                    travel_time_minutes=leg1_mins,
                    now=now,
                )

                candidate_stops.append(
                    OnRouteShopStop(
                        shop_id=shop.shop_id,
                        shop_name=shop.name,
                        shop_address=shop.address,
                        lat=shop.lat,
                        lon=shop.lon,
                        product_id=product.product_id,
                        product_title=product.persian_title,
                        offer_id=offer.offer_id,
                        price_toman=offer.price_toman,
                        baseline_travel_minutes=base_duration_mins,
                        trip_via_shop_minutes=total_journey_via_shop_mins,
                        detour_minutes=additional_travel_mins,
                        detour_distance_km=detour_dist_km,
                        additional_travel_minutes=additional_travel_mins,
                        dwell_minutes=dwell_minutes,
                        total_additional_journey_minutes=total_additional_journey_mins,
                        arrival_at=arrival_shop_time.isoformat(),
                        arrival_at_destination=arrival_dest_time.isoformat(),
                        is_open_at_arrival=is_open,
                        shop_reliability_score=round(rel.composite_reliability_score, 3),
                        stock_survival_at_arrival=stock_assess.survival_probability_at_arrival,
                        is_detour_verified=is_verified_network and leg1_route.is_verified_road_network and leg2_route.is_verified_road_network,
                        routing_quality=(
                            "verified_road_network" if (is_verified_network and leg1_route.is_verified_road_network and leg2_route.is_verified_road_network)
                            else ("synthetic_road_graph" if (routing_source == "synthetic_road_graph" or leg1_route.routing_provider_name == "synthetic_road_graph")
                            else "approximate_heuristic")
                        ),
                        warnings=stop_warnings,
                    )
                )

        if not candidate_stops:
            return OnRoutePlanResult(
                origin={"lat": origin_lat, "lon": origin_lon},
                destination={"lat": dest_lat, "lon": dest_lon},
                baseline_distance_km=base_dist_km,
                baseline_duration_minutes=base_duration_mins,
                routing_source=routing_source,
                is_verified_road_network=is_verified_network,
                route_geometry=route_geom,
                recommended_stops=[],
                trade_off_summary="هیچ فروشگاه معتبری در مسیر مستقیم مبدا تا مقصد با شرایط درخواستی یافت نشد. افزایش سقف انحراف از مسیر پیشنهاد می‌شود.",
                is_feasible=False,
                warnings=warnings + ["عدم وجود فروشگاه منطبق در کریدور مسیر"],
            )

        # 5. Multi-Criteria Scoring & Trade-Off Assignment
        min_p = min(s.price_toman for s in candidate_stops)
        max_p = max(s.price_toman for s in candidate_stops)
        p_range = max(1.0, max_p - min_p)

        max_detour = max(s.detour_minutes for s in candidate_stops)
        d_range = max(1.0, max_detour)

        for stop in candidate_stops:
            norm_price = (stop.price_toman - min_p) / p_range
            norm_detour = stop.detour_minutes / d_range
            open_bonus = 0.20 if stop.is_open_at_arrival else -0.40

            utility = (
                0.35 * (1.0 - norm_detour)
                + 0.25 * (1.0 - norm_price)
                + 0.25 * stop.shop_reliability_score
                + open_bonus
            )
            setattr(stop, "_score", utility)

        candidate_stops.sort(key=lambda s: getattr(s, "_score"), reverse=True)
        top_candidates = candidate_stops[:limit]

        # 6. Assign Mathematically Verified Trade-Off Labels
        self._assign_on_route_trade_off_labels(top_candidates)
        summary = self._generate_on_route_summary(top_candidates, base_duration_mins)

        return OnRoutePlanResult(
            origin={"lat": origin_lat, "lon": origin_lon},
            destination={"lat": dest_lat, "lon": dest_lon},
            baseline_distance_km=base_dist_km,
            baseline_duration_minutes=base_duration_mins,
            routing_source=routing_source,
            is_verified_road_network=is_verified_network,
            route_geometry=route_geom,
            recommended_stops=top_candidates,
            trade_off_summary=summary,
            is_feasible=True,
            warnings=warnings,
        )

    def _assign_on_route_trade_off_labels(self, candidates: List[OnRouteShopStop]) -> None:
        if not candidates:
            return

        # 1. Best overall: top ranked candidate
        candidates[0].trade_off_label = "best_overall"

        # 2. Minimum detour stop
        min_detour = min(s.detour_minutes for s in candidates)
        min_detour_stops = [s for s in candidates if s.detour_minutes == min_detour]
        for s in min_detour_stops:
            if s.trade_off_label is None:
                s.trade_off_label = "minimum_detour"

        # 3. Cheapest stop among viable candidates
        min_price = min(s.price_toman for s in candidates)
        cheapest_stops = [s for s in candidates if s.price_toman == min_price]
        for s in cheapest_stops:
            if s.trade_off_label is None:
                s.trade_off_label = "cheapest_stop"

        # 4. Most trusted stop
        max_trust = max(s.shop_reliability_score for s in candidates)
        trusted_stops = [s for s in candidates if s.shop_reliability_score == max_trust]
        for s in trusted_stops:
            if s.trade_off_label is None:
                s.trade_off_label = "most_trusted"

    def _generate_on_route_summary(self, candidates: List[OnRouteShopStop], base_mins: float) -> str:
        if not candidates:
            return ""

        best = candidates[0]
        verified_note = " (مسیر شبکه معابر تاییدشده)" if best.is_detour_verified else " (برآورد تقریبی شهری)"
        parts = [
            f"بهترین توقف در مسیر{verified_note}: فروشگاه «{best.shop_name}» با قیمت {best.price_toman:,.0f} تومان و "
            f"فقط {best.detour_minutes:.0f} دقیقه انحراف زمانی از مسیر مستقیم (کل زمان سفر با توقف: {best.trip_via_shop_minutes:.0f} دقیقه در مقایسه با {base_mins:.0f} دقیقه مستقیم)."
        ]

        for s in candidates[1:]:
            if s.trade_off_label == "minimum_detour":
                parts.append(
                    f"کمترین انحراف: «{s.shop_name}» با انحراف {s.detour_minutes:.0f} دقیقه ({s.price_toman:,.0f} تومان)."
                )
            elif s.trade_off_label == "cheapest_stop":
                parts.append(
                    f"اقتصادی‌ترین توقف: «{s.shop_name}» به قیمت {s.price_toman:,.0f} تومان ({s.detour_minutes:.0f} دقیقه انحراف)."
                )
            elif s.trade_off_label == "most_trusted":
                parts.append(
                    f"بالاترین اعتبار: «{s.shop_name}» با نمره اعتماد {int(s.shop_reliability_score*100)}٪."
                )

        return " ".join(parts)
