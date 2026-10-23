from fastapi import APIRouter, Depends, HTTPException

from torob.api.dependencies import (
    get_catalog_repo,
    get_itinerary_planner,
    get_visit_feasibility_engine,
)
from torob.api.v1.schemas import RoutePlanRequest, VisitAssessRequest
from torob.domain.assessment import VisitFeasibility
from torob.routing.feasibility import VisitFeasibilityEngine
from torob.routing.itinerary import ItineraryPlanner, VisitItineraryPlan
from torob.storage.repository_catalog import CatalogRepository

router = APIRouter(tags=["Visits & Itinerary Routing"])


@router.post("/visits/assess", response_model=VisitFeasibility)
def assess_single_visit(
    body: VisitAssessRequest,
    catalog_repo: CatalogRepository = Depends(get_catalog_repo),
    feasibility_engine: VisitFeasibilityEngine = Depends(get_visit_feasibility_engine),
):
    """Assess whether a customer can physically reach the shop before it closes and buy the product."""
    shop = catalog_repo.get_shop(body.shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {body.shop_id} not found")

    offer = catalog_repo.get_offer(body.offer_id) if body.offer_id else None

    return feasibility_engine.assess_visit_feasibility(
        origin_lat=body.origin_lat,
        origin_lon=body.origin_lon,
        shop=shop,
        offer=offer,
        stock_status=body.stock_status,
        quantity_bucket=body.quantity_bucket,
    )


@router.post("/routes/plan", response_model=VisitItineraryPlan)
def plan_multi_stop_route(
    body: RoutePlanRequest,
    catalog_repo: CatalogRepository = Depends(get_catalog_repo),
    planner: ItineraryPlanner = Depends(get_itinerary_planner),
):
    """Generate an optimized visit plan for multiple shops based on distance and closing urgency."""
    candidate_stops = []
    for s_input in body.stops:
        shop = catalog_repo.get_shop(s_input.shop_id)
        if not shop:
            raise HTTPException(status_code=404, detail=f"Shop {s_input.shop_id} not found")
        candidate_stops.append({"shop": shop, "product_ids": s_input.product_ids})

    return planner.plan(
        origin_lat=body.origin_lat,
        origin_lon=body.origin_lon,
        candidate_stops=candidate_stops,
        departure_time=body.departure_time,
        sort_mode=body.sort_mode,
        dwell_minutes=body.dwell_minutes_per_stop,
    )
