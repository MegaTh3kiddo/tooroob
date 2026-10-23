from enum import Enum
from typing import Any, Dict, Optional, Tuple

from torob.domain.entities import Offer, Product
from torob.ingestion.normalizer import extract_variant_attributes


class CompatibilityGrade(str, Enum):
    EXACT = "exact"
    COMPATIBLE_DIFFERENT_COLOR = "compatible_different_color"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class VariantCompatibilityMatcher:
    """Evaluates whether two offers are directly comparable for price intelligence.
    
    Prevents comparing 128GB against 256GB, used against new, or disparate warranties.
    """

    @staticmethod
    def evaluate_compatibility(
        offer_a: Offer,
        offer_b: Offer,
        product: Optional[Product] = None,
    ) -> Tuple[CompatibilityGrade, str]:
        # If product_ids do not match, obviously incompatible
        if offer_a.product_id != offer_b.product_id:
            return CompatibilityGrade.INCOMPATIBLE, "شناسه کالا یکسان نیست"

        # Extract attributes from descriptions and titles
        text_a = f"{offer_a.seller_title or ''} {offer_a.description or ''}"
        text_b = f"{offer_b.seller_title or ''} {offer_b.description or ''}"
        
        specs = product.specs if product else None
        attrs_a = extract_variant_attributes(text_a, specs)
        attrs_b = extract_variant_attributes(text_b, specs)

        # 1. Condition check (new vs used/stock)
        cond_a = attrs_a.get("condition", "new")
        cond_b = attrs_b.get("condition", "new")
        if cond_a != cond_b:
            return (
                CompatibilityGrade.INCOMPATIBLE,
                f"عدم تطابق وضعیت کالا: یکی {cond_a} و دیگری {cond_b} است",
            )

        # 2. Storage check
        storage_a = attrs_a.get("storage")
        storage_b = attrs_b.get("storage")
        if storage_a and storage_b and storage_a != storage_b:
            return (
                CompatibilityGrade.INCOMPATIBLE,
                f"عدم تطابق ظرفیت حافظه: {storage_a} در برابر {storage_b}",
            )

        # 3. RAM check
        ram_a = attrs_a.get("ram")
        ram_b = attrs_b.get("ram")
        if ram_a and ram_b and ram_a != ram_b:
            return (
                CompatibilityGrade.INCOMPATIBLE,
                f"عدم تطابق حافظه رم: {ram_a} در برابر {ram_b}",
            )

        # 4. Color check
        color_a = attrs_a.get("color")
        color_b = attrs_b.get("color")
        if color_a and color_b and color_a != color_b:
            return (
                CompatibilityGrade.COMPATIBLE_DIFFERENT_COLOR,
                f"رنگ متفاوت: {color_a} در برابر {color_b}",
            )

        return CompatibilityGrade.EXACT, "واریانت‌های کاملاً قابل مقایسه"
