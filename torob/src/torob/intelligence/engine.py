from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from torob.core.config import load_policy
from torob.domain.assessment import OfferAssessmentResult
from torob.domain.entities import Offer, Shop, ShopReliability
from torob.domain.enums import StockState, UserIntent
from torob.intelligence.inquiry_policy import InquiryPolicyEngine
from torob.intelligence.inventory import InventoryIntelligenceEngine
from torob.intelligence.pricing import PriceIntelligenceEngine
from torob.intelligence.shop_reliability import ShopReliabilityEngine


class TorobIntelligenceEngine:
    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.policy = policy or load_policy()
        self.pricing = PriceIntelligenceEngine(self.policy)
        self.inventory = InventoryIntelligenceEngine(self.policy)
        self.shop_reliability = ShopReliabilityEngine(self.policy)
        self.inquiry = InquiryPolicyEngine(self.policy)

    def assess_offer(
        self,
        offer: Offer,
        shop: Shop,
        peer_offers: List[Offer],
        user_intent: UserIntent = UserIntent.VISIT,
        travel_minutes: float = 0.0,
        stock_status: StockState = StockState.UNKNOWN,
        quantity_bucket: str = "unknown",
        last_stock_verified_at: Optional[datetime] = None,
        shop_reliability_state: Optional[ShopReliability] = None,
        active_inquiries_today: int = 0,
        now: Optional[datetime] = None,
    ) -> OfferAssessmentResult:
        now = now or datetime.now(timezone.utc)

        # 1. Price assessment
        price_assessment = self.pricing.assess_offer_price(
            offer=offer,
            peer_offers=peer_offers,
            now=now,
        )

        # 2. Stock assessment (with arrival ETA survival)
        stock_assessment = self.inventory.assess_stock(
            stock_status=stock_status,
            quantity_bucket=quantity_bucket,
            last_verified_at=last_stock_verified_at,
            travel_time_minutes=travel_minutes,
            now=now,
        )

        # 3. Shop reliability assessment
        shop_assessment = self.shop_reliability.assess_shop(
            shop=shop,
            reliability_state=shop_reliability_state,
        )

        # 4. Inquiry recommendation
        inquiry_rec = self.inquiry.evaluate_inquiry_need(
            price_assessment=price_assessment,
            stock_assessment=stock_assessment,
            shop_assessment=shop_assessment,
            user_intent=user_intent,
            active_inquiries_count_today=active_inquiries_today,
            now=now,
        )

        return OfferAssessmentResult(
            offer_id=offer.offer_id,
            product_id=offer.product_id,
            shop_id=offer.shop_id,
            price_assessment=price_assessment,
            stock_assessment=stock_assessment,
            shop_reliability=shop_assessment,
            inquiry_recommendation=inquiry_rec,
            evaluated_at=now,
            policy_version=self.policy.get("policy_version", "1.0.0"),
        )
