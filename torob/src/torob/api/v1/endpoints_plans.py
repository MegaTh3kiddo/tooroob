"""Contextual Shopping Plans & Optimization REST Endpoints v1.

Provides versioned REST APIs for future frontend integration:
1. POST /api/v1/shopping-plans/on-route
2. POST /api/v1/shopping-plans/basket
3. POST /api/v1/shopping-plans/nearby-clusters
4. POST /api/v1/shopping-plans/compare-products
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from torob.domain.plans import (
    MultiStoreBasketPlan,
    OnRoutePlanResult,
    PersonalizedComparisonResult,
    PlanOptimizationPriority,
    ShopCluster,
)
from torob.intelligence.basket_optimizer import BasketOptimizationEngine
from torob.intelligence.personalized_recommender import PersonalizedProductSelector
from torob.routing.clustering import ShopClusterEngine
from torob.routing.on_route import OnRouteShoppingEngine

router = APIRouter(prefix="/shopping-plans", tags=["Contextual Shopping Plans"])

# Default singleton engine instances
_on_route_engine = OnRouteShoppingEngine()
_basket_engine = BasketOptimizationEngine()
_cluster_engine = ShopClusterEngine()
_personalized_selector = PersonalizedProductSelector()


class OnRoutePlanRequest(BaseModel):
    origin_lat: float = Field(..., description="Origin latitude")
    origin_lon: float = Field(..., description="Origin longitude")
    dest_lat: float = Field(..., description="Destination latitude")
    dest_lon: float = Field(..., description="Destination longitude")
    product_query: str = Field(..., min_length=2, description="Target product to purchase along route")
    corridor_width_km: float = Field(8.0, ge=1.0, le=30.0, description="Max corridor width in km")
    max_detour_minutes: Optional[float] = Field(None, ge=1.0, description="Max acceptable extra travel time in minutes")
    max_price_toman: Optional[float] = Field(None, ge=1.0, description="Budget ceiling in Toman")
    min_shop_reliability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum shop reliability score")


class BasketOptimizationRequest(BaseModel):
    basket_queries: List[str] = Field(..., min_length=1, description="List of items in basket")
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None
    max_budget_toman: Optional[float] = None
    max_stops: int = Field(3, ge=1, le=5, description="Max number of shop stops allowed")
    require_single_store: bool = False
    optimization_priority: PlanOptimizationPriority = PlanOptimizationPriority.BALANCED
    min_shop_reliability: Optional[float] = None


class ClusterSearchRequest(BaseModel):
    basket_queries: List[str] = Field(..., min_length=1, description="List of items in basket")
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None
    max_cluster_radius_km: float = Field(1.5, ge=0.2, le=10.0, description="Max distance between shops in cluster")


class PersonalizedCompareRequest(BaseModel):
    product_ids_or_titles: List[str] = Field(..., min_length=2, description="Product IDs or names to compare")
    use_case: str = Field("general", description="'programming', 'gaming', 'mobility', or 'general'")
    user_priorities: Optional[Dict[str, float]] = Field(None, description="Criteria weights e.g. {'battery': 0.4}")
    max_budget_toman: Optional[float] = None


@router.post("/on-route", response_model=OnRoutePlanResult)
def plan_on_route_purchase(body: OnRoutePlanRequest):
    """Finds shops offering the product along the route with minimum detour."""
    return _on_route_engine.find_on_route_purchases(
        origin_lat=body.origin_lat,
        origin_lon=body.origin_lon,
        dest_lat=body.dest_lat,
        dest_lon=body.dest_lon,
        product_query=body.product_query,
        corridor_width_km=body.corridor_width_km,
        max_detour_minutes=body.max_detour_minutes,
        max_price_toman=body.max_price_toman,
        min_shop_reliability=body.min_shop_reliability,
    )


@router.post("/basket", response_model=List[MultiStoreBasketPlan])
def optimize_shopping_basket(body: BasketOptimizationRequest):
    """Computes Pareto-relevant single-store and multi-store purchasing plans for a multi-item basket."""
    return _basket_engine.optimize_basket(
        basket_queries=body.basket_queries,
        user_lat=body.user_lat,
        user_lon=body.user_lon,
        max_budget_toman=body.max_budget_toman,
        max_stops=body.max_stops,
        require_single_store=body.require_single_store,
        optimization_priority=body.optimization_priority,
        min_shop_reliability=body.min_shop_reliability,
    )


@router.post("/nearby-clusters", response_model=List[ShopCluster])
def find_nearby_shop_clusters(body: ClusterSearchRequest):
    """Identifies dense commercial areas where 2-3 nearby shops collectively cover the customer's basket."""
    plans = _basket_engine.optimize_basket(
        basket_queries=body.basket_queries,
        user_lat=body.user_lat,
        user_lon=body.user_lon,
    )
    all_coverages = []
    seen = set()
    for p in plans:
        for s in p.stores:
            if s.shop_id not in seen:
                seen.add(s.shop_id)
                all_coverages.append(s)

    return _cluster_engine.identify_clusters_for_basket(
        candidate_coverages=all_coverages,
        total_items_requested=body.basket_queries,
        user_lat=body.user_lat,
        user_lon=body.user_lon,
        max_cluster_radius_km=body.max_cluster_radius_km,
    )


@router.post("/compare-products", response_model=PersonalizedComparisonResult)
def compare_products_personalized(body: PersonalizedCompareRequest):
    """Multi-criteria personalized comparison explaining trade-offs between candidate products."""
    return _personalized_selector.compare_and_rank_products(
        product_ids_or_titles=body.product_ids_or_titles,
        use_case=body.use_case,
        user_priorities=body.user_priorities,
        max_budget_toman=body.max_budget_toman,
    )
