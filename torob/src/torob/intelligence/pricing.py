from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import numpy as np

from torob.core.config import load_policy
from torob.domain.assessment import PriceAssessment
from torob.domain.entities import Offer, Product
from torob.domain.enums import EvidenceQuality, PriceAssessmentStatus, RiskBand
from torob.intelligence.matching import CompatibilityGrade, VariantCompatibilityMatcher
from torob.intelligence.volatility import PriceObservation, PriceVolatilityCalculator


class PriceIntelligenceEngine:
    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.policy = policy or load_policy()
        pricing_cfg = self.policy.get("pricing", {})
        self.block_sentinels = set(pricing_cfg.get("block_sentinel_values", [0, 1]))
        self.extreme_max = pricing_cfg.get("extreme_absolute_max_toman", 1000000000000)
        self.extreme_min = pricing_cfg.get("extreme_absolute_min_toman", 1000)
        self.dev_high_mult = pricing_cfg.get("relative_peer_deviation_high_multiplier", 3.0)
        self.dev_low_mult = pricing_cfg.get("relative_peer_deviation_low_multiplier", 0.3333)
        self.stale_warn_days = pricing_cfg.get("stale_warning_threshold_days", 30)
        self.stale_crit_days = pricing_cfg.get("stale_critical_threshold_days", 90)

    def assess_offer_price(
        self,
        offer: Offer,
        peer_offers: List[Offer],
        product: Optional[Product] = None,
        price_observations: Optional[List[PriceObservation]] = None,
        now: Optional[datetime] = None,
    ) -> PriceAssessment:
        now = now or datetime.now(timezone.utc)
        reasons: List[str] = []
        risk_score = 0
        status = PriceAssessmentStatus.VALID_ESTIMATE
        evidence_quality = EvidenceQuality.LIMITED

        # 1. Quality Gates: Missing Price
        if offer.price_toman is None or not math.isfinite(offer.price_toman):
            return PriceAssessment(
                status=PriceAssessmentStatus.MISSING_PRICE,
                price_toman=None,
                risk_score=90,
                risk_band=RiskBand.CRITICAL,
                reasons=["قیمت برای این پیشنهاد ثبت نشده است (null یا نامعتبر)"],
                evidence_quality=EvidenceQuality.UNKNOWN,
            )

        price = offer.price_toman

        # 2. Quality Gates: Sentinel values (e.g. 1 Toman)
        if int(price) in self.block_sentinels or price <= 1.0:
            reasons.append("قیمت واردشده مقدار ساختگی/پوچ است (۱ تومان یا صفر)")
            return PriceAssessment(
                status=PriceAssessmentStatus.SENTINEL_ANOMALY,
                price_toman=price,
                risk_score=95,
                risk_band=RiskBand.CRITICAL,
                reasons=reasons,
                evidence_quality=EvidenceQuality.UNKNOWN,
            )

        # 3. Quality Gates: Extreme Values
        if price > self.extreme_max:
            reasons.append(f"قیمت بیش از سقف نامتعارف ۱ تریلیون تومان است ({price:,.0f} تومان)")
            return PriceAssessment(
                status=PriceAssessmentStatus.EXTREME_VALUE,
                price_toman=price,
                risk_score=90,
                risk_band=RiskBand.CRITICAL,
                reasons=reasons,
                evidence_quality=EvidenceQuality.UNKNOWN,
            )
        elif price < self.extreme_min:
            reasons.append(f"قیمت کمتر از کف متعارف ۱٬۰۰۰ تومان است ({price:,.0f} تومان)")
            risk_score += 40
            status = PriceAssessmentStatus.EXTREME_VALUE

        # 4. Filter Peer Offers by Variant Compatibility (LOSO)
        # Exclude evaluated shop and incompatible variants (e.g. storage/condition mismatch)
        compatible_peers: List[Offer] = []
        for p in peer_offers:
            if p.shop_id == offer.shop_id or p.price_toman is None or p.price_toman <= 1:
                continue
            grade, _ = VariantCompatibilityMatcher.evaluate_compatibility(offer, p, product)
            if grade in (CompatibilityGrade.EXACT, CompatibilityGrade.COMPATIBLE_DIFFERENT_COLOR):
                compatible_peers.append(p)

        valid_peer_prices = [p.price_toman for p in compatible_peers if p.price_toman is not None]
        peer_count = len(set(p.shop_id for p in compatible_peers))

        peer_median: Optional[float] = None
        dev_ratio: Optional[float] = None

        if valid_peer_prices and peer_count >= 2:
            peer_median = float(np.median(valid_peer_prices))
            if peer_median > 0:
                dev_ratio = round(price / peer_median, 3)

                # Check potential 10x Rial/Toman error
                if 9.0 <= dev_ratio <= 11.0:
                    status = PriceAssessmentStatus.CURRENCY_MISMATCH_SUSPECT
                    reasons.append(
                        f"احتمال درج قیمت به ریال به جای تومان (قیمت {dev_ratio} برابر میانه بازار است)"
                    )
                    risk_score += 65
                elif 0.09 <= dev_ratio <= 0.11:
                    status = PriceAssessmentStatus.CURRENCY_MISMATCH_SUSPECT
                    reasons.append(
                        f"احتمال اشتباه تبدیل واحد پول (قیمت حدود یک‌دهم میانه بازار است)"
                    )
                    risk_score += 65
                elif dev_ratio >= self.dev_high_mult:
                    status = PriceAssessmentStatus.PEER_DEVIATION_HIGH
                    reasons.append(
                        f"قیمت بیش از {self.dev_high_mult} برابر میانه رقبای هم‌تراز در بازار است ({dev_ratio}x)"
                    )
                    risk_score += 50
                elif dev_ratio <= self.dev_low_mult:
                    status = PriceAssessmentStatus.PEER_DEVIATION_LOW
                    reasons.append(
                        f"قیمت به شکل غیرعادی پایین‌تر از میانه بازار است ({dev_ratio}x)"
                    )
                    risk_score += 40
                else:
                    reasons.append("قیمت با رقبای هم‌تراز در بازار همخوانی دارد")

            if peer_count >= 3:
                evidence_quality = EvidenceQuality.MODERATE
            if peer_count >= 5:
                evidence_quality = EvidenceQuality.HIGH
        else:
            reasons.append("تعداد همتایان هم‌تراز در بازار برای مقایسه مستقیم کافی نیست (تک‌فروشنده یا کم‌عرضه)")
            risk_score += 15

        # 5. Historical Path Volatility Analysis (if historical observations present)
        if price_observations and len(price_observations) >= 2:
            vol_metrics = PriceVolatilityCalculator.calculate_path_metrics(price_observations)
            if vol_metrics.is_path_volatile_despite_low_net_change:
                reasons.append(
                    f"نوسان شدید مسیر قیمتی ({vol_metrics.total_abs_movement_pct}٪) علی‌رغم تغییر خالص اندک ({vol_metrics.net_change_pct}٪)"
                )
                risk_score += 25
            elif vol_metrics.volatility_regime == "SHOCKED":
                reasons.append(f"بازار این کالا اخیراً شوک قیمتی یا جهش‌های ناگهانی را تجربه کرده است ({vol_metrics.jump_count} جهش)")
                risk_score += 30
            elif vol_metrics.volatility_regime == "HIGH_VOLATILITY":
                reasons.append("بازار این کالا دارای نوسان قیمتی بالاست")
                risk_score += 15

        # 6. Timestamp and Staleness Analysis
        if offer.last_price_changed_at is not None:
            changed_at = offer.last_price_changed_at
            if changed_at.tzinfo is None:
                changed_at = changed_at.replace(tzinfo=timezone.utc)
            
            age_days = (now - changed_at).total_seconds() / 86400.0
            if age_days >= self.stale_crit_days:
                if status == PriceAssessmentStatus.VALID_ESTIMATE:
                    status = PriceAssessmentStatus.STALE
                reasons.append(f"بیش از {int(age_days)} روز از آخرین تغییر ثبت‌شده قیمت گذشته است")
                risk_score += 35
            elif age_days >= self.stale_warn_days:
                reasons.append(f"{int(age_days)} روز از آخرین تغییر قیمت گذشته است (نیازمند اعتبارسنجی)")
                risk_score += 20
        else:
            reasons.append("تاریخچه تغییر قیمت برای این پیشنهاد ثبت نشده است")
            risk_score += 20

        # Cap risk score between 0 and 100
        risk_score = min(100, max(0, risk_score))

        # Assign risk band
        if risk_score >= 75:
            risk_band = RiskBand.CRITICAL
        elif risk_score >= 50:
            risk_band = RiskBand.HIGH
        elif risk_score >= 25:
            risk_band = RiskBand.MEDIUM
        else:
            risk_band = RiskBand.LOW

        return PriceAssessment(
            status=status,
            price_toman=price,
            reference_peer_price=peer_median,
            peer_shops_count=peer_count,
            price_deviation_ratio=dev_ratio,
            risk_score=risk_score,
            risk_band=risk_band,
            risk_score_type="heuristic",
            calibrated_probability=None,  # NEVER invent fake probabilities
            reasons=reasons,
            evidence_quality=evidence_quality,
        )
