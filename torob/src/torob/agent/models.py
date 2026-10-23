from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field

from torob.domain.plans import (
    BasketItemMatch,
    MultiStoreBasketPlan,
    OnRoutePlanResult,
    OnRouteShopStop,
    PersonalizedComparisonResult,
    PlanOptimizationPriority,
    ProductSuitabilityScore,
    ShopBasketCoverage,
    ShopCluster,
)


class ShoppingIntent(str, Enum):
    EXACT_SEARCH = "exact_search"
    NEEDS_BASED = "needs_based"
    BUDGET_SEARCH = "budget_search"
    LOCAL_PHYSICAL = "local_physical"
    PRODUCT_COMPARISON = "product_comparison"
    MULTI_PRODUCT = "multi_product"
    REFINEMENT = "refinement"
    GENERAL_CHAT = "general_chat"
    # Advanced Contextual Intents
    ON_ROUTE_PURCHASE = "on_route_purchase"
    SINGLE_STORE_BASKET = "single_store_basket"
    MULTI_STORE_BASKET = "multi_store_basket"
    NEARBY_STORE_CLUSTER = "nearby_store_cluster"
    PERSONALIZED_SELECTION = "personalized_product_selection"
    ADAPTIVE_REPLAN = "adaptive_replan"


class ShoppingConstraints(BaseModel):
    budget_min_toman: Optional[float] = None
    budget_max_toman: Optional[float] = None
    budget_is_strict: bool = True
    budget_confidence: str = "exact"  # "exact", "colloquial_inferred", "ambiguous"
    target_product_title: Optional[str] = None
    target_category: Optional[str] = None
    target_brand: Optional[str] = None
    excluded_brands: List[str] = Field(default_factory=list)
    color: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    condition: Optional[str] = None  # new, used, refurbished
    warranty_required: Optional[bool] = None
    urgency: str = "normal"  # normal, urgent_today
    location_name: Optional[str] = None
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None
    max_travel_minutes: Optional[float] = None
    min_shop_reliability: Optional[float] = None
    battery_preference: Optional[str] = None  # "high", "normal"
    newer_models_only: bool = False
    preferred_specs: Dict[str, Any] = Field(default_factory=dict)
    rejected_product_ids: List[str] = Field(default_factory=list)
    comparison_product_ids: List[str] = Field(default_factory=list)
    multi_product_basket: List[Dict[str, Any]] = Field(default_factory=list)
    # Advanced Contextual & Routing Constraints
    origin_name: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_name: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    max_detour_minutes: Optional[float] = None
    max_stops: Optional[int] = None
    deadline_iso: Optional[str] = None
    optimization_priority: str = "balanced"  # "cheapest", "fastest", "fewest_stops", "most_trusted", "balanced"
    basket_queries: List[str] = Field(default_factory=list)
    require_single_store: bool = False
    allow_substitutes: bool = True
    rejected_shop_ids: List[str] = Field(default_factory=list)
    reported_unavailable_items: List[str] = Field(default_factory=list)
    active_plan_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClarificationState(BaseModel):
    clarification_budget: int = 2
    questions_asked_count: int = 0
    asked_questions: List[str] = Field(default_factory=list)
    resolved_aspects: List[str] = Field(default_factory=list)
    active_clarification_question: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)


class CandidateOfferRecommendation(BaseModel):
    product_id: str
    product_title: str
    offer_id: str
    shop_id: str
    shop_name: str
    shop_address: Optional[str] = None
    price_toman: float
    reference_market_price: Optional[float] = None
    is_price_anomaly: bool = False
    suitability_score: float = Field(ge=0.0, le=1.0)
    shop_reliability_score: float = Field(ge=0.0, le=1.0)
    stock_survival_at_arrival: Optional[float] = None
    evidence_quality: str = "limited"
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    uncertainty_warnings: List[str] = Field(default_factory=list)
    trade_off_label: Optional[str] = None  # "best_overall", "budget_pick", "verified_confidence", "pareto_alternative"
    is_shop_open: bool = True
    shop_hours_desc: Optional[str] = None
    product_highlights: List[str] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    intent: ShoppingIntent
    total_candidates_found: int
    top_recommendations: List[CandidateOfferRecommendation] = Field(default_factory=list)
    trade_off_summary: str = ""
    hard_constraints_satisfied: bool = True
    violated_constraints: List[str] = Field(default_factory=list)
    retrieval_insufficient: bool = False
    recommended_inquiry: Optional[Dict[str, Any]] = None
    purchase_itinerary: Optional[Dict[str, Any]] = None
    compatibility_report: Optional[Dict[str, Any]] = None
    on_route_plan: Optional[Dict[str, Any]] = None
    basket_plan: Optional[Dict[str, Any]] = None
    adapted_plan: Optional[Dict[str, Any]] = None
    shop_clusters: Optional[List[Dict[str, Any]]] = None
    personalized_comparison: Optional[Dict[str, Any]] = None


class ProposedAction(BaseModel):
    action_type: str  # "confirm_inquiry", "plan_route", "adjust_budget"
    description: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ShoppingSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = None
    detected_intent: ShoppingIntent = ShoppingIntent.GENERAL_CHAT
    constraints: ShoppingConstraints = Field(default_factory=ShoppingConstraints)
    clarification_state: ClarificationState = Field(default_factory=ClarificationState)
    messages: List[ChatMessage] = Field(default_factory=list)
    latest_recommendations: Optional[RecommendationResult] = None
    proposed_actions: List[ProposedAction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
