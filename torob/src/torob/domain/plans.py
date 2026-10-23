"""Domain models for Contextual Shopping Plans, On-Route Purchasing, Basket Optimization & Shop Clustering.

These models define structured, typed representations for:
1. On-route shopping with minimum detour calculation and road-network verification
2. Single-store and multi-store basket coverage with explicit inventory evidence semantics
3. Geographic shop clustering with walking transit analysis
4. Multi-criteria personalized comparison with explicit missing specification flags
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid

from pydantic import BaseModel, Field


class PlanOptimizationPriority(str, Enum):
    BALANCED = "balanced"
    CHEAPEST = "cheapest"
    FEWEST_STOPS = "fewest_stops"
    MINIMUM_TRAVEL = "minimum_travel"
    HIGHEST_TRUST = "highest_trust"
    FASTEST = "fastest"


class OnRouteShopStop(BaseModel):
    shop_id: str
    shop_name: str
    shop_address: Optional[str] = None
    lat: float
    lon: float
    product_id: str
    product_title: str
    offer_id: str
    price_toman: float
    baseline_travel_minutes: float
    trip_via_shop_minutes: float
    detour_minutes: float  # Additional travel time without dwell
    detour_distance_km: float
    additional_travel_minutes: float = 0.0  # Pure driving/walking deviation without dwell
    dwell_minutes: float = 10.0  # Time spent inside shop
    total_additional_journey_minutes: float = 0.0  # additional_travel_minutes + dwell_minutes
    arrival_at: Optional[str] = None  # Expected arrival at shop
    arrival_at_destination: Optional[str] = None  # Expected final arrival at destination via shop
    is_open_at_arrival: bool = True
    shop_reliability_score: float = Field(ge=0.0, le=1.0)
    stock_survival_at_arrival: Optional[float] = None
    trade_off_label: Optional[str] = None  # "minimum_detour", "cheapest_stop", "most_trusted", "best_overall"
    is_detour_verified: bool = False  # True only if computed via real road-network routing
    routing_quality: str = "approximate_heuristic"  # "verified_road_network" vs "approximate_heuristic"
    warnings: List[str] = Field(default_factory=list)


class OnRoutePlanResult(BaseModel):
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    baseline_distance_km: float
    baseline_duration_minutes: float
    routing_source: str  # "road_network_graph", "osrm_network", "calibrated_urban_corridor", "estimated_proximity"
    is_verified_road_network: bool = False
    route_geometry: Optional[List[Tuple[float, float]]] = None
    recommended_stops: List[OnRouteShopStop] = Field(default_factory=list)
    trade_off_summary: str = ""
    is_feasible: bool = True
    warnings: List[str] = Field(default_factory=list)


class BasketItemMatch(BaseModel):
    query: str
    matched_product_id: str
    matched_product_title: str
    offer_id: str
    shop_id: Optional[str] = None
    quantity: int = 1
    price_toman: Optional[float] = None
    price_type: str = "fixed_retail"  # "fixed_retail", "quote_dependent", "placeholder_invalid"
    price_status: str = "price_known"  # "price_known", "price_unknown", "quote_required"
    seller_title: Optional[str] = None
    match_grade: str = "exact"  # "exact", "variant_compatible", "uncertain_match"
    is_price_anomaly: bool = False
    stock_survival: Optional[float] = None
    stock_evidence: str = "stock_unknown"  # "seller_confirmed", "stock_unknown", "confirmed_unavailable", "stale_catalog_entry"
    evidence_status: str = "listed_in_catalog"  # "verified_in_store", "listed_in_catalog", "uncertain_stock"
    fulfillment_channel: str = "in_store_pickup"  # "in_store_pickup", "delivery_only", "uncertain"
    is_verified_in_store: bool = False
    verification_recommendation: Optional[str] = None


class ShopBasketCoverage(BaseModel):
    shop_id: str
    shop_name: str
    shop_address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    items_covered_count: int
    total_items_requested: int
    covers_entire_basket: bool
    matched_items: List[BasketItemMatch] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)
    total_listed_price_toman: Optional[float] = 0.0
    is_total_price_complete: bool = True
    has_missing_prices: bool = False
    shop_reliability_score: float = Field(ge=0.0, le=1.0)
    estimated_travel_minutes: Optional[float] = None
    is_open_now: bool = True
    opening_hours_desc: Optional[str] = None
    coverage_percentage: float = 0.0
    verification_level: str = "unverified_catalog_only"  # "unverified_catalog_only", "partially_verified", "fully_verified"
    export_cap_limitation_noted: bool = True  # Notes that items absent may simply not be in 300-item dataset export


class MultiStoreBasketPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    version: int = 1
    is_adapted: bool = False
    original_plan_id: Optional[str] = None
    adaptation_reason: Optional[str] = None
    strategy: str  # "single_store", "fewest_stops", "cheapest_combination", "minimum_travel", "highest_trust", "partial_coverage", "no_coverage"
    strategy_label_persian: str = ""
    stores: List[ShopBasketCoverage] = Field(default_factory=list)
    total_product_cost_toman: Optional[float] = 0.0
    is_total_price_complete: bool = True
    estimated_total_travel_minutes: float = 0.0
    total_stops: int = 0
    all_items_covered: bool = True
    missing_items: List[str] = Field(default_factory=list)
    search_scope_reached: bool = False  # True when search was bounded at max_stops but basket might require more
    guarantee_status: str = "evidence_estimate_not_guaranteed"  # Clarifies complete catalog coverage != guaranteed stock
    composite_score: float = Field(ge=0.0, le=1.0)
    pareto_labels: List[str] = Field(default_factory=list)  # Verified mathematically against other evaluated plans
    trade_off_explanation: str = ""
    recommended_inquiry: Optional[Dict[str, Any]] = None
    itinerary_order: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ShopCluster(BaseModel):
    cluster_id: str
    cluster_name: str
    center_lat: float
    center_lon: float
    radius_km: float
    shops_count: int
    shops: List[ShopBasketCoverage] = Field(default_factory=list)
    collective_items_covered: List[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0  # 1.0 when all items are covered
    covers_entire_basket: bool = False
    average_reliability: float = 0.0
    total_estimated_price_toman: float = 0.0
    is_total_price_complete: bool = True
    inter_shop_walk_minutes: float = 0.0
    summary: str = ""


class ProductSuitabilityScore(BaseModel):
    product_id: str
    product_title: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    specs: Dict[str, Any] = Field(default_factory=dict)
    min_price_toman: Optional[float] = None
    suitability_score: float = Field(ge=0.0, le=1.0)
    hard_requirements_met: bool = True
    preference_match_score: float = Field(ge=0.0, le=1.0)
    value_for_money_score: float = Field(ge=0.0, le=1.0)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    trade_off_notes: str = ""
    uncertain_or_missing_specs: List[str] = Field(default_factory=list)


class PersonalizedComparisonResult(BaseModel):
    comparison_criteria: List[str] = Field(default_factory=list)
    user_priorities: Dict[str, float] = Field(default_factory=dict)
    evaluated_products: List[ProductSuitabilityScore] = Field(default_factory=list)
    top_choice_product_id: Optional[str] = None
    top_choice_summary: str = ""
    trade_off_matrix: str = ""
    unmet_or_uncertain_specs: List[str] = Field(default_factory=list)
