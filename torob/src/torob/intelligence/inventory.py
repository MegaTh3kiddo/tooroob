from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from torob.core.config import load_policy
from torob.domain.assessment import StockAssessment
from torob.domain.enums import EvidenceQuality, StockState


class InventoryIntelligenceEngine:
    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.policy = policy or load_policy()
        stock_cfg = self.policy.get("stock", {})
        self.default_depletion_rate = stock_cfg.get("default_depletion_rate_per_hour", 0.05)
        self.eta_aware = stock_cfg.get("eta_aware_confirmation", true if "eta_aware_confirmation" not in stock_cfg else stock_cfg["eta_aware_confirmation"])

    def assess_stock(
        self,
        stock_status: StockState = StockState.UNKNOWN,
        quantity_bucket: str = "unknown",
        last_verified_at: Optional[datetime] = None,
        travel_time_minutes: float = 0.0,
        now: Optional[datetime] = None,
    ) -> StockAssessment:
        now = now or datetime.now(timezone.utc)
        reasons: List[str] = []
        evidence_quality = EvidenceQuality.LIMITED

        # Hazard rate per hour based on stock quantity bucket
        hazard_multiplier = {
            "1_unit": 2.5,     # Single item in stock: high hazard of being bought by another customer
            "single_unit": 2.5,
            "2_to_5": 1.0,     # Small stock
            "gt_5": 0.3,       # Substantial stock: very low depletion hazard for short trip
            "plenty": 0.3,
            "unknown": 1.2,    # Unknown quantity
        }.get(quantity_bucket, 1.0)

        lambda_depletion = self.default_depletion_rate * hazard_multiplier

        # Check last verification
        hours_since_verification = 0.0
        if last_verified_at is not None:
            if last_verified_at.tzinfo is None:
                last_verified_at = last_verified_at.replace(tzinfo=timezone.utc)
            hours_since_verification = max(0.0, (now - last_verified_at).total_seconds() / 3600.0)
            if hours_since_verification < 4:
                evidence_quality = EvidenceQuality.HIGH
                reasons.append("موجودی در ساعات اخیر مستقیماً تأیید شده است")
            elif hours_since_verification < 24:
                evidence_quality = EvidenceQuality.MODERATE
                reasons.append("موجودی در شبانه‌روز اخیر تأیید شده است")
            else:
                reasons.append(f"بیش از {int(hours_since_verification // 24)} روز از آخرین استعلام موجودی گذشته است")
        else:
            reasons.append("هیچ تأییدیه مستقیمی برای موجودی فیزیکی این کالا در فروشگاه ثبت نشده است")

        # Arrival Survival Probability Estimation (Exponential Survival Baseline)
        survival_prob: Optional[float] = None
        if stock_status in (StockState.IN_STORE_SELLABLE, StockState.UNKNOWN):
            travel_hours = max(0.0, travel_time_minutes / 60.0)
            total_elapsed_hours = hours_since_verification + travel_hours
            
            # S(t) = exp(-lambda * t)
            prob = math.exp(-lambda_depletion * total_elapsed_hours)
            survival_prob = round(min(0.99, max(0.05, prob)), 2)

            if travel_time_minutes > 0:
                reasons.append(
                    f"تخمین بقای موجودی تا زمان رسیدن مشتری ({int(travel_time_minutes)} دقیقه): "
                    f"حدود {int(survival_prob * 100)}٪ (مدل اکتشافی نرخ تخلیه)"
                )
            if quantity_bucket == "1_unit":
                reasons.append("تنها ۱ عدد در انبار اعلام شده؛ احتمال اتمام قبل از رسیدن بالاست")

        if stock_status == StockState.OUT_OF_STOCK:
            survival_prob = 0.0
            reasons.append("فروشگاه اعلام کرده کالا ناموجود است")

        return StockAssessment(
            status=stock_status,
            survival_probability_at_arrival=survival_prob,
            is_calibrated=False,  # Clearly not claimed as calibrated ground truth
            last_verified_at=last_verified_at,
            quantity_bucket=quantity_bucket,
            reasons=reasons,
            evidence_quality=evidence_quality,
        )
