"""Evidence-Grounded Agent Tools.

Strictly typed tool adapters wrapping Torob catalog repositories,
intelligence engines, routing services, and verification ledger.
All tool outputs are sanitized to protect against prompt injection from untrusted seller texts.
"""

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from torob.agent.compatibility import PCCompatibilityEngine
from torob.agent.location import LocationResolver
from torob.domain.entities import Offer, Product, Shop
from torob.intelligence.basket_optimizer import BasketOptimizationEngine
from torob.intelligence.personalized_recommender import PersonalizedProductSelector
from torob.routing.clustering import ShopClusterEngine
from torob.routing.on_route import OnRouteShoppingEngine
from torob.domain.enums import SortMode, UserIntent
from torob.ingestion.normalizer import normalize_digits, normalize_persian_text
from torob.intelligence.engine import TorobIntelligenceEngine
from torob.intelligence.matching import VariantCompatibilityMatcher
from torob.intelligence.shop_reliability import ShopReliabilityEngine
from torob.routing.distance import DistanceRouter, haversine_km
from torob.routing.feasibility import VisitFeasibilityEngine
from torob.routing.hours import BusinessHoursEvaluator
from torob.routing.itinerary import ItineraryPlanner
from torob.storage.db import db_manager
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.agent.tools")


def sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize seller/customer text to neutralize prompt injection sequences."""
    if not text:
        return ""
    # Strip potential prompt injection framing like "Ignore previous instructions", "<SYSTEM>", etc.
    cleaned = re.sub(
        r"(ignore previous instructions|system instruction|you are now|forget instructions|<system>|</system>)",
        "[REDACTED_SUSPICIOUS_PHRASE]",
        text,
        flags=re.IGNORECASE,
    )
    # Remove control characters
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch in ("\n", " ", "\t"))
    return cleaned.strip()[:400]  # bounded length


class AgentToolRegistry:
    def __init__(
        self,
        catalog_repo: Optional[CatalogRepository] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        intel_engine: Optional[TorobIntelligenceEngine] = None,
        reliability_engine: Optional[ShopReliabilityEngine] = None,
        feasibility_engine: Optional[VisitFeasibilityEngine] = None,
        itinerary_planner: Optional[ItineraryPlanner] = None,
    ):
        self.catalog_repo = catalog_repo or CatalogRepository()
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.intel_engine = intel_engine or TorobIntelligenceEngine()
        self.reliability_engine = reliability_engine or ShopReliabilityEngine()
        self.feasibility_engine = feasibility_engine or VisitFeasibilityEngine()
        self.itinerary_planner = itinerary_planner or ItineraryPlanner()
        self.router = DistanceRouter()
        self.compatibility_engine = PCCompatibilityEngine()
        self.location_resolver = LocationResolver()
        self.on_route_engine = OnRouteShoppingEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
            pricing_engine=self.intel_engine.pricing,
            inventory_engine=self.intel_engine.inventory,
            reliability_engine=self.reliability_engine,
        )
        self.basket_engine = BasketOptimizationEngine(
            catalog_repo=self.catalog_repo,
            router=self.router,
            pricing_engine=self.intel_engine.pricing,
            inventory_engine=self.intel_engine.inventory,
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

        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Dict[str, Any]],
    ) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns OpenAPI/JSON schema tool definitions for LLMs."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Safely executes an agent tool with error handling and bounded outputs."""
        if name not in self._tools:
            return {"success": False, "error": f"Unknown tool '{name}'."}

        tool_meta = self._tools[name]
        func = tool_meta["func"]
        try:
            result = func(**arguments)
            return {"success": True, "data": result}
        except TypeError as te:
            logger.warning(f"Tool {name} argument mismatch: {te}")
            return {"success": False, "error": f"Invalid arguments for {name}: {str(te)}"}
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            return {"success": False, "error": f"Execution failed for {name}: {str(e)}"}

    def _register_default_tools(self) -> None:
        # Tool 1: search_products
        self.register_tool(
            name="search_products",
            description="Search products in Torob catalog by Persian or English keywords, category, or brand.",
            parameters={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search keyword (e.g. 'گوشی سامسونگ s23', 'لپ تاپ ایسوس')"},
                    "category": {"type": "string", "description": "Category filter (optional)"},
                    "brand": {"type": "string", "description": "Brand name filter (optional)"},
                    "limit": {"type": "integer", "description": "Max results to return (default 10, max 25)"},
                },
                "required": ["q"],
            },
            func=self._search_products,
        )

        # Tool 2: get_product_details
        self.register_tool(
            name="get_product_details",
            description="Get full specifications and details for a product by its exact product_id.",
            parameters={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The unique product_id"}
                },
                "required": ["product_id"],
            },
            func=self._get_product_details,
        )

        # Tool 3: search_offers
        self.register_tool(
            name="search_offers",
            description="Find seller offers for a product, optionally filtering by maximum price.",
            parameters={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The unique product_id"},
                    "max_price": {"type": "number", "description": "Maximum budget ceiling in Toman"},
                    "limit": {"type": "integer", "description": "Max offers to return (default 15)"},
                },
                "required": ["product_id"],
            },
            func=self._search_offers,
        )

        # Tool 4: get_offer_assessment
        self.register_tool(
            name="get_offer_assessment",
            description="Runs full price anomaly, stock survival, and risk intelligence assessment on an offer.",
            parameters={
                "type": "object",
                "properties": {
                    "offer_id": {"type": "string", "description": "The unique offer_id"},
                    "user_intent": {"type": "string", "description": "User intent: 'browse', 'online_purchase', or 'visit'"},
                    "travel_minutes": {"type": "number", "description": "Estimated travel minutes if physical visit (default 0)"},
                },
                "required": ["offer_id"],
            },
            func=self._get_offer_assessment,
        )

        # Tool 5: get_shop_reliability
        self.register_tool(
            name="get_shop_reliability",
            description="Fetch multi-dimensional reliability and trust score of a physical shop.",
            parameters={
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string", "description": "The unique shop_id"}
                },
                "required": ["shop_id"],
            },
            func=self._get_shop_reliability,
        )

        # Tool 6: find_nearby_shops
        self.register_tool(
            name="find_nearby_shops",
            description="Find physical shops near given coordinates within a radius in kilometers.",
            parameters={
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "User latitude (e.g. 35.700)"},
                    "lon": {"type": "number", "description": "User longitude (e.g. 51.400)"},
                    "max_distance_km": {"type": "number", "description": "Maximum distance in km (default 10.0)"},
                    "limit": {"type": "integer", "description": "Max shops to return (default 10)"},
                },
                "required": ["lat", "lon"],
            },
            func=self._find_nearby_shops,
        )

        # Tool 7: check_shop_hours
        self.register_tool(
            name="check_shop_hours",
            description="Check if a physical shop is open now or at a given time in Tehran local time.",
            parameters={
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string", "description": "The unique shop_id"},
                    "iso_time": {"type": "string", "description": "ISO 8601 timestamp to evaluate (default now)"},
                },
                "required": ["shop_id"],
            },
            func=self._check_shop_hours,
        )

        # Tool 8: assess_visit_feasibility
        self.register_tool(
            name="assess_visit_feasibility",
            description="Assesses physical visit feasibility including travel ETA, opening hours, and stock survival.",
            parameters={
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string", "description": "The unique shop_id"},
                    "offer_id": {"type": "string", "description": "Optional offer_id to verify stock"},
                    "user_lat": {"type": "number", "description": "User latitude"},
                    "user_lon": {"type": "number", "description": "User longitude"},
                },
                "required": ["shop_id", "user_lat", "user_lon"],
            },
            func=self._assess_visit_feasibility,
        )

        # Tool 9: plan_purchase_route
        self.register_tool(
            name="plan_purchase_route",
            description="Plans an optimized itinerary visiting multiple shops, prioritizing early closing stores.",
            parameters={
                "type": "object",
                "properties": {
                    "origin_lat": {"type": "number", "description": "Origin latitude"},
                    "origin_lon": {"type": "number", "description": "Origin longitude"},
                    "shop_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of shop IDs to visit",
                    },
                    "sort_mode": {"type": "string", "description": "Sort mode: 'smart', 'near', or 'closing'"},
                },
                "required": ["origin_lat", "origin_lon", "shop_ids"],
            },
            func=self._plan_purchase_route,
        )

        # Tool 10: check_active_inquiry
        self.register_tool(
            name="check_active_inquiry",
            description="Checks if an active, unexpired inquiry is already pending for a shop and product.",
            parameters={
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string", "description": "Shop ID"},
                    "product_id": {"type": "string", "description": "Product ID"},
                    "offer_id": {"type": "string", "description": "Optional Offer ID"},
                },
                "required": ["shop_id", "product_id"],
            },
            func=self._check_active_inquiry,
        )

        # Tool 11: check_variant_compatibility
        self.register_tool(
            name="check_variant_compatibility",
            description="Evaluates variant compatibility (condition, storage, ram, color) between two offers.",
            parameters={
                "type": "object",
                "properties": {
                    "offer_id_a": {"type": "string", "description": "First Offer ID"},
                    "offer_id_b": {"type": "string", "description": "Second Offer ID"},
                },
                "required": ["offer_id_a", "offer_id_b"],
            },
            func=self._check_variant_compatibility,
        )

        # Tool 12: check_pc_component_compatibility
        self.register_tool(
            name="check_pc_component_compatibility",
            description="Evaluates hardware compatibility (socket, DDR generation, PSU wattage, form-factor) for custom PC parts.",
            parameters={
                "type": "object",
                "properties": {
                    "components": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of components with category, title, specs, and price_toman",
                    },
                    "budget_toman": {"type": "number", "description": "Optional basket budget ceiling in Toman"},
                },
                "required": ["components"],
            },
            func=self._check_pc_component_compatibility,
        )

        # Tool 13: resolve_location
        self.register_tool(
            name="resolve_location",
            description="Resolves Iranian urban neighborhoods, shopping hubs, districts, or coordinates to lat/lon.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Location name, landmark, or coordinates"}
                },
                "required": ["text"],
            },
            func=self._resolve_location,
        )

        # Tool 14: find_on_route_purchases
        self.register_tool(
            name="find_on_route_purchases",
            description="Finds stores along a travel route from Origin to Destination that sell a product with minimal detour.",
            parameters={
                "type": "object",
                "properties": {
                    "origin_lat": {"type": "number", "description": "Origin latitude"},
                    "origin_lon": {"type": "number", "description": "Origin longitude"},
                    "dest_lat": {"type": "number", "description": "Destination latitude"},
                    "dest_lon": {"type": "number", "description": "Destination longitude"},
                    "product_query": {"type": "string", "description": "Product search term (e.g. SSD 2TB)"},
                    "max_detour_minutes": {"type": "number", "description": "Maximum extra travel minutes allowed (e.g. 15)"},
                    "max_price_toman": {"type": "number", "description": "Maximum budget ceiling in Toman"},
                },
                "required": ["origin_lat", "origin_lon", "dest_lat", "dest_lon", "product_query"],
            },
            func=self._find_on_route_purchases,
        )

        # Tool 15: optimize_multi_product_basket
        self.register_tool(
            name="optimize_multi_product_basket",
            description="Finds optimal single-store or multi-store purchasing plans for a multi-item shopping basket.",
            parameters={
                "type": "object",
                "properties": {
                    "basket_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product queries in basket (e.g. ['مانیتور', 'کیبورد', 'موس'])",
                    },
                    "user_lat": {"type": "number", "description": "Optional customer latitude"},
                    "user_lon": {"type": "number", "description": "Optional customer longitude"},
                    "max_budget_toman": {"type": "number", "description": "Total basket budget ceiling"},
                    "max_stops": {"type": "integer", "description": "Max number of shops to visit (default 3)"},
                    "require_single_store": {"type": "boolean", "description": "Whether all items must be from 1 shop"},
                    "optimization_priority": {
                        "type": "string",
                        "description": "Priority: 'cheapest', 'fewest_stops', 'minimum_travel', 'highest_trust', or 'balanced'",
                    },
                },
                "required": ["basket_queries"],
            },
            func=self._optimize_multi_product_basket,
        )

        # Tool 16: find_nearby_shop_clusters
        self.register_tool(
            name="find_nearby_shop_clusters",
            description="Identifies dense commercial areas/clusters of nearby shops covering the requested basket.",
            parameters={
                "type": "object",
                "properties": {
                    "basket_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product queries in basket",
                    },
                    "user_lat": {"type": "number", "description": "Optional user latitude"},
                    "user_lon": {"type": "number", "description": "Optional user longitude"},
                    "max_cluster_radius_km": {"type": "number", "description": "Max cluster radius in km (default 1.5)"},
                },
                "required": ["basket_queries"],
            },
            func=self._find_nearby_shop_clusters,
        )

        # Tool 17: compare_personalized_products
        self.register_tool(
            name="compare_personalized_products",
            description="Performs multi-criteria personalized comparison across candidate products based on user priorities.",
            parameters={
                "type": "object",
                "properties": {
                    "product_ids_or_titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product IDs or titles to compare",
                    },
                    "use_case": {"type": "string", "description": "Target use case: 'programming', 'gaming', 'mobility'"},
                    "user_priorities": {
                        "type": "object",
                        "description": "Weights dict e.g. {'battery': 0.4, 'weight': 0.3, 'gpu': 0.1}",
                    },
                    "max_budget_toman": {"type": "number", "description": "Optional budget ceiling"},
                },
                "required": ["product_ids_or_titles"],
            },
            func=self._compare_personalized_products,
        )

    # --- Tool Implementations ---

    def _search_products(
        self, q: str, category: Optional[str] = None, brand: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        lim = min(25, max(1, limit))
        products, total = self.catalog_repo.search_products(q=q, category=category, brand=brand, limit=lim)
        return {
            "query": q,
            "total_matches": total,
            "items": [
                {
                    "product_id": p.product_id,
                    "persian_title": p.persian_title,
                    "brand_name": p.brand_name,
                    "category_name": p.category_name,
                    "model": p.model,
                    "specs": p.specs,
                }
                for p in products
            ],
        }

    def _get_product_details(self, product_id: str) -> Dict[str, Any]:
        p = self.catalog_repo.get_product(product_id)
        if not p:
            return {"found": False, "product_id": product_id}
        offers = self.catalog_repo.get_offers_by_product(product_id, limit=10)
        return {
            "found": True,
            "product_id": p.product_id,
            "persian_title": p.persian_title,
            "brand_name": p.brand_name,
            "category_name": p.category_name,
            "model": p.model,
            "specs": p.specs,
            "active_offers_count": len(offers),
            "min_price_toman": min([o.price_toman for o in offers if o.price_toman and o.price_toman > 1], default=None),
        }

    def _search_offers(
        self, product_id: str, max_price: Optional[float] = None, limit: int = 15
    ) -> Dict[str, Any]:
        lim = min(30, max(1, limit))
        offers = self.catalog_repo.get_offers_by_product(product_id, limit=50)
        
        filtered = []
        for o in offers:
            if not o.price_toman or o.price_toman <= 1:
                continue
            if max_price is not None and o.price_toman > max_price:
                continue
            shop = self.catalog_repo.get_shop(o.shop_id)
            filtered.append({
                "offer_id": o.offer_id,
                "shop_id": o.shop_id,
                "shop_name": shop.name if shop else "فروشگاه",
                "shop_address": shop.address if shop else None,
                "price_toman": o.price_toman,
                "seller_title": sanitize_untrusted_text(o.seller_title),
                "warranty": sanitize_untrusted_text(o.warranty),
                "last_price_changed_at": o.last_price_changed_at.isoformat() if o.last_price_changed_at else None,
            })
            if len(filtered) >= lim:
                break

        return {"product_id": product_id, "offers_found": len(filtered), "offers": filtered}

    def _get_offer_assessment(
        self, offer_id: str, user_intent: str = "browse", travel_minutes: float = 0.0
    ) -> Dict[str, Any]:
        intent_enum = UserIntent(user_intent) if user_intent in [e.value for e in UserIntent] else UserIntent.BROWSE
        assessment = self.intel_engine.assess_offer(
            offer_id=offer_id,
            catalog_repo=self.catalog_repo,
            user_intent=intent_enum,
            travel_time_minutes=travel_minutes,
        )
        if not assessment:
            return {"found": False, "offer_id": offer_id}

        return {
            "found": True,
            "offer_id": offer_id,
            "overall_risk_band": assessment.overall_risk_band.value,
            "overall_risk_score": assessment.overall_risk_score,
            "price_assessment": {
                "status": assessment.price_assessment.status.value,
                "price_toman": assessment.price_assessment.price_toman,
                "reference_peer_price": assessment.price_assessment.reference_peer_price,
                "reasons": assessment.price_assessment.reasons,
                "risk_band": assessment.price_assessment.risk_band.value,
            },
            "stock_assessment": {
                "status": assessment.stock_assessment.status.value,
                "survival_probability_at_arrival": assessment.stock_assessment.survival_probability_at_arrival,
                "reasons": assessment.stock_assessment.reasons,
            },
            "shop_reliability": {
                "composite_score": assessment.shop_reliability.composite_reliability_score,
                "reasons": assessment.shop_reliability.reasons,
            },
            "inquiry_recommendation": {
                "recommended": assessment.inquiry_recommendation.recommended,
                "priority": assessment.inquiry_recommendation.priority.value,
                "reason": assessment.inquiry_recommendation.reason,
            },
        }

    def _get_shop_reliability(self, shop_id: str) -> Dict[str, Any]:
        shop = self.catalog_repo.get_shop(shop_id)
        if not shop:
            return {"found": False, "shop_id": shop_id}
        rel = self.reliability_engine.assess_shop(shop)
        return {
            "found": True,
            "shop_id": shop.shop_id,
            "shop_name": shop.name,
            "composite_score": rel.composite_reliability_score,
            "dimensions": rel.dimensions,
            "reasons": rel.reasons,
        }

    def _find_nearby_shops(
        self, lat: float, lon: float, max_distance_km: float = 10.0, limit: int = 10
    ) -> Dict[str, Any]:
        lim = min(25, max(1, limit))
        shops, _ = self.catalog_repo.search_shops(limit=300)
        
        nearby = []
        for s in shops:
            if s.lat is None or s.lon is None:
                continue
            dist_km = haversine_km(lat, lon, s.lat, s.lon)
            if dist_km <= max_distance_km:
                nearby.append({
                    "shop_id": s.shop_id,
                    "name": s.name,
                    "address": s.address,
                    "distance_km": round(dist_km, 2),
                    "supports_fast_delivery": s.supports_fast_delivery,
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return {"origin": {"lat": lat, "lon": lon}, "shops": nearby[:lim]}

    def _check_shop_hours(self, shop_id: str, iso_time: Optional[str] = None) -> Dict[str, Any]:
        shop = self.catalog_repo.get_shop(shop_id)
        if not shop:
            return {"found": False, "shop_id": shop_id}

        at_dt = None
        if iso_time:
            try:
                at_dt = datetime.fromisoformat(iso_time)
            except Exception:
                pass

        is_open, open_h, close_h, desc = BusinessHoursEvaluator.evaluate_hours(shop.weekly_hours, at_dt)
        mins_left = BusinessHoursEvaluator.minutes_until_close(close_h, at_dt) if close_h else None

        return {
            "shop_id": shop_id,
            "shop_name": shop.name,
            "is_open": is_open,
            "open_hour": open_h,
            "close_hour": close_h,
            "minutes_until_close": mins_left,
            "schedule_description": desc,
        }

    def _assess_visit_feasibility(
        self, shop_id: str, user_lat: float, user_lon: float, offer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        shop = self.catalog_repo.get_shop(shop_id)
        if not shop:
            return {"feasible": False, "error": f"Shop {shop_id} not found"}

        offer = self.catalog_repo.get_offer(offer_id) if offer_id else None
        res = self.feasibility_engine.assess_visit_feasibility(
            origin_lat=user_lat,
            origin_lon=user_lon,
            shop=shop,
            offer=offer,
        )
        return {
            "shop_id": shop_id,
            "shop_name": shop.name,
            "is_feasible": res.is_feasible,
            "travel_distance_km": res.travel_distance_km,
            "travel_minutes": res.travel_minutes,
            "travel_mode": res.travel_mode,
            "shop_open_now": res.shop_open_now,
            "shop_open_at_arrival": res.shop_open_at_arrival,
            "minutes_until_close": res.minutes_until_close,
            "risk_band": res.risk_band.value,
            "warnings": res.warnings,
        }

    def _plan_purchase_route(
        self, origin_lat: float, origin_lon: float, shop_ids: List[str], sort_mode: str = "smart"
    ) -> Dict[str, Any]:
        stops_candidates = []
        for s_id in shop_ids:
            shop = self.catalog_repo.get_shop(s_id)
            if shop:
                stops_candidates.append({"shop": shop, "product_ids": []})

        if not stops_candidates:
            return {"error": "No valid shops found to plan route"}

        mode = SortMode(sort_mode) if sort_mode in [e.value for e in SortMode] else SortMode.SMART
        plan = self.itinerary_planner.plan(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            candidate_stops=stops_candidates,
            sort_mode=mode,
        )
        return {
            "total_stops": plan.total_stops,
            "total_distance_km": plan.total_distance_km,
            "total_duration_minutes": plan.total_duration_minutes,
            "sort_mode": plan.sort_mode.value,
            "stops": [
                {
                    "order": s.order,
                    "shop_id": s.shop_id,
                    "shop_name": s.shop_name,
                    "address": s.address,
                    "leg_distance_km": s.leg_distance_km,
                    "leg_travel_minutes": s.leg_travel_minutes,
                    "is_open_at_arrival": s.is_open_at_arrival,
                    "warnings": s.warnings,
                }
                for s in plan.stops
            ],
            "overall_warnings": plan.overall_warnings,
        }

    def _check_active_inquiry(
        self, shop_id: str, product_id: str, offer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        dedupe_key = f"{shop_id}:{product_id}:{offer_id or 'none'}"
        inquiry = self.ledger_repo.find_inquiry_by_dedupe_key(dedupe_key)
        if not inquiry:
            return {"has_active_inquiry": False}

        now = datetime.now(timezone.utc)
        is_active = inquiry.deadline_at > now and inquiry.status.value in ("created", "queued", "delivered")
        return {
            "has_active_inquiry": is_active,
            "inquiry_id": inquiry.inquiry_id,
            "status": inquiry.status.value,
            "requested_at": inquiry.requested_at.isoformat(),
            "deadline_at": inquiry.deadline_at.isoformat(),
        }

    def _check_variant_compatibility(self, offer_id_a: str, offer_id_b: str) -> Dict[str, Any]:
        offer_a = self.catalog_repo.get_offer(offer_id_a)
        offer_b = self.catalog_repo.get_offer(offer_id_b)
        if not offer_a or not offer_b:
            return {"success": False, "error": "One or both offers not found in catalog"}
        product = self.catalog_repo.get_product(offer_a.product_id)
        grade, note = VariantCompatibilityMatcher.evaluate_compatibility(offer_a, offer_b, product)
        return {
            "success": True,
            "offer_id_a": offer_id_a,
            "offer_id_b": offer_id_b,
            "product_id": offer_a.product_id,
            "compatibility_grade": grade.value,
            "is_directly_comparable": grade.value in ("exact", "compatible_different_color"),
            "explanation": note,
        }

    def _check_pc_component_compatibility(
        self, components: List[Dict[str, Any]], budget_toman: Optional[float] = None
    ) -> Dict[str, Any]:
        report = self.compatibility_engine.evaluate_basket(components, budget_toman=budget_toman)
        return report.model_dump()

    def _resolve_location(self, text: str) -> Dict[str, Any]:
        loc = self.location_resolver.resolve(text)
        if not loc:
            return {"found": False, "query_text": text}
        return {
            "found": True,
            "query_text": loc.query_text,
            "canonical_name": loc.canonical_name,
            "lat": loc.lat,
            "lon": loc.lon,
            "city": loc.city,
            "district": loc.district,
            "confidence": loc.confidence,
            "resolution_source": loc.resolution_source,
        }

    def _find_on_route_purchases(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        product_query: str,
        max_detour_minutes: Optional[float] = None,
        max_price_toman: Optional[float] = None,
    ) -> Dict[str, Any]:
        result = self.on_route_engine.find_on_route_purchases(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            product_query=product_query,
            max_detour_minutes=max_detour_minutes,
            max_price_toman=max_price_toman,
        )
        return result.model_dump()

    def _optimize_multi_product_basket(
        self,
        basket_queries: List[str],
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_budget_toman: Optional[float] = None,
        max_stops: int = 3,
        require_single_store: bool = False,
        optimization_priority: str = "balanced",
    ) -> Dict[str, Any]:
        from torob.domain.plans import PlanOptimizationPriority
        try:
            priority_enum = PlanOptimizationPriority(optimization_priority)
        except Exception:
            priority_enum = PlanOptimizationPriority.BALANCED

        plans = self.basket_engine.optimize_basket(
            basket_queries=basket_queries,
            user_lat=user_lat,
            user_lon=user_lon,
            max_budget_toman=max_budget_toman,
            max_stops=max_stops,
            require_single_store=require_single_store,
            optimization_priority=priority_enum,
        )
        return {"plans_found": len(plans), "plans": [p.model_dump() for p in plans]}

    def _find_nearby_shop_clusters(
        self,
        basket_queries: List[str],
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        max_cluster_radius_km: float = 1.5,
    ) -> Dict[str, Any]:
        # First gather shop coverage
        plans = self.basket_engine.optimize_basket(
            basket_queries=basket_queries,
            user_lat=user_lat,
            user_lon=user_lon,
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
            total_items_requested=basket_queries,
            user_lat=user_lat,
            user_lon=user_lon,
            max_cluster_radius_km=max_cluster_radius_km,
        )
        return {"clusters_found": len(clusters), "clusters": [c.model_dump() for c in clusters]}

    def _compare_personalized_products(
        self,
        product_ids_or_titles: List[str],
        use_case: str = "general",
        user_priorities: Optional[Dict[str, float]] = None,
        max_budget_toman: Optional[float] = None,
    ) -> Dict[str, Any]:
        res = self.personalized_selector.compare_and_rank_products(
            product_ids_or_titles=product_ids_or_titles,
            use_case=use_case,
            user_priorities=user_priorities,
            max_budget_toman=max_budget_toman,
        )
        return res.model_dump()
