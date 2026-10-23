from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from torob.api.dependencies import (
    get_catalog_repo,
    get_intelligence_engine,
    get_ledger_repo,
)
from torob.domain.assessment import OfferAssessmentResult, ShopReliabilityAssessment
from torob.domain.enums import StockState, UserIntent
from torob.intelligence.engine import TorobIntelligenceEngine
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository

router = APIRouter(tags=["Intelligence Assessments"])


@router.get("/offers/{offer_id}/assessment", response_model=OfferAssessmentResult)
def assess_offer_intelligence(
    offer_id: str,
    user_intent: UserIntent = Query(UserIntent.VISIT, description="User intent: browse, buy, or visit"),
    travel_minutes: float = Query(0.0, ge=0.0, description="Estimated customer travel time in minutes"),
    stock_status: StockState = Query(StockState.UNKNOWN, description="Known stock status if confirmed"),
    quantity_bucket: str = Query("unknown", description="Quantity bucket: 1_unit, 2_to_5, gt_5, unknown"),
    catalog_repo: CatalogRepository = Depends(get_catalog_repo),
    ledger_repo: LedgerRepository = Depends(get_ledger_repo),
    intel_engine: TorobIntelligenceEngine = Depends(get_intelligence_engine),
):
    """Run the comprehensive explainable intelligence assessment on a specific offer.
    
    Evaluates:
    - Price anomaly, sentinel values, and Leave-One-Shop-Out peer reference comparison.
    - Arrival stock survival probability based on travel time.
    - Multidimensional shop trust (commercial, price, stock, presence, responsiveness).
    - Intelligent inquiry recommendation with expected utility and quiet-hours protection.
    """
    offer = catalog_repo.get_offer(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer {offer_id} not found")

    shop = catalog_repo.get_shop(offer.shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Associated shop {offer.shop_id} not found")

    # Fetch Leave-One-Shop-Out peer offers
    peer_offers = catalog_repo.get_peer_offers_loso(offer.product_id, exclude_shop_id=offer.shop_id)

    # Fetch shop reliability state from ledger
    reliability_state = ledger_repo.get_shop_reliability(shop.shop_id)

    # Active inquiries today
    active_inquiries = ledger_repo.get_active_inquiries_for_shop(shop.shop_id)

    assessment = intel_engine.assess_offer(
        offer=offer,
        shop=shop,
        peer_offers=peer_offers,
        user_intent=user_intent,
        travel_minutes=travel_minutes,
        stock_status=stock_status,
        quantity_bucket=quantity_bucket,
        shop_reliability_state=reliability_state,
        active_inquiries_today=len(active_inquiries),
    )
    return assessment


@router.get("/shops/{shop_id}/reliability", response_model=ShopReliabilityAssessment)
def get_shop_reliability_breakdown(
    shop_id: str,
    catalog_repo: CatalogRepository = Depends(get_catalog_repo),
    ledger_repo: LedgerRepository = Depends(get_ledger_repo),
    intel_engine: TorobIntelligenceEngine = Depends(get_intelligence_engine),
):
    """Retrieve detailed multi-dimensional reliability breakdown for a shop."""
    shop = catalog_repo.get_shop(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_id} not found")

    state = ledger_repo.get_shop_reliability(shop_id)
    return intel_engine.shop_reliability.assess_shop(shop=shop, reliability_state=state)
