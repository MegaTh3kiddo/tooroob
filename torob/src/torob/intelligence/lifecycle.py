from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from torob.domain.entities import Offer, Product


class LifecycleStage(str, Enum):
    NEWLY_LAUNCHED = "newly_launched"
    PRICE_DISCOVERY = "price_discovery"
    MATURE_STABLE = "mature_stable"
    END_OF_LIFE = "end_of_life"
    UNKNOWN_INSUFFICIENT_DATA = "unknown_insufficient_data"


class LifecycleAssessment(BaseModel):
    stage: LifecycleStage
    first_seen_days_ago: Optional[float] = None
    active_sellers_count: int
    is_single_seller: bool
    fallback_level_applied: str  # exact_product, category_prior, none
    uncertainty_note: str


class ProductLifecycleClassifier:
    """Classifies product lifecycle and coordinates hierarchical category fallback."""

    @staticmethod
    def classify_lifecycle(
        product: Product,
        offers: List[Offer],
        now: Optional[datetime] = None,
    ) -> LifecycleAssessment:
        now = now or datetime.now(timezone.utc)
        active_sellers = len(set(o.shop_id for o in offers))
        is_single = active_sellers <= 1

        # Check earliest known timestamp among offers
        timestamps = [
            o.last_price_changed_at
            for o in offers
            if o.last_price_changed_at is not None
        ]
        
        if not timestamps:
            return LifecycleAssessment(
                stage=LifecycleStage.UNKNOWN_INSUFFICIENT_DATA,
                first_seen_days_ago=None,
                active_sellers_count=active_sellers,
                is_single_seller=is_single,
                fallback_level_applied="category_prior" if is_single else "exact_product",
                uncertainty_note="دادهٔ زمانی کافی برای تحلیل چرخه عمر در دست نیست",
            )

        earliest = min(timestamps)
        if earliest.tzinfo is None:
            earliest = earliest.replace(tzinfo=timezone.utc)
        
        days_ago = max(0.0, (now - earliest).total_seconds() / 86400.0)

        # Lifecycle logic
        if days_ago < 14:
            stage = LifecycleStage.NEWLY_LAUNCHED
            note = f"کالای تازه‌وارد به سامانه ({int(days_ago)} روز پیش)؛ مرحله کشف قیمت"
        elif days_ago < 45:
            stage = LifecycleStage.PRICE_DISCOVERY
            note = "کالا در مرحله تثبیت و کشف قیمت بازار قرار دارد"
        elif active_sellers <= 1 and days_ago > 180:
            stage = LifecycleStage.END_OF_LIFE
            note = "کالای کمیاب یا انتهای چرخه عمر (تک‌فروشنده با پیشینه طولانی)"
        else:
            stage = LifecycleStage.MATURE_STABLE
            note = "کالای باسابقه و به بلوغ رسیده در بازار"

        fallback = "category_prior" if is_single else "exact_product"

        return LifecycleAssessment(
            stage=stage,
            first_seen_days_ago=round(days_ago, 1),
            active_sellers_count=active_sellers,
            is_single_seller=is_single,
            fallback_level_applied=fallback,
            uncertainty_note=note,
        )
