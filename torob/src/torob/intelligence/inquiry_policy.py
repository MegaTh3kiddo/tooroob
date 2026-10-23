"""Adaptive Value-of-Information (VoI) Verification Policy Engine.

Implements decision-theoretic inquiry evaluation, intent & travel burden weighting,
regime-aware freshness thresholds, controlled audit exploration (selection bias mitigation),
shop fatigue budgeting, and auditable propensity & decision context logging.

=============================================================================
EXPERIMENTAL HEURISTIC CONFIGURATION:
Notice: The thresholds, exploration rates, fatigue limits, and cost multipliers
defined here represent initial operational heuristics (derived from sample_policy.yaml).
They are NOT empirically calibrated true probabilities or learned parameters.
In a production deployment, these must be periodically evaluated and tuned
against live merchant responsiveness, customer dispute rates, and GPS arrival logs.
=============================================================================
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import math
from typing import Any, Dict, List, Optional
import uuid

from torob.core.config import load_policy
from torob.domain.assessment import (
    InquiryRecommendation,
    PriceAssessment,
    ShopReliabilityAssessment,
    StockAssessment,
)
from torob.domain.enums import InquiryPriority, ProductRegime, RiskBand, StockState, UserIntent
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.intelligence.inquiry_policy")

# Unit definition: Standard Loss Points (SLP)
# 1 SLP = 10,000 Iranian Toman (~0.1 USD)
SLP_TOMAN_UNIT = 10_000.0


@dataclass
class PolicyDecisionContext:
    decision_id: str
    action_code: str  # enqueue_inquiry | audit_sample_inquiry | show_warning | no_action | decline_or_defer
    reason_codes: List[str]
    selection_probability: float
    selection_trigger: str  # heuristic_risk | user_purchase_intent | audit_sample | market_shock
    expected_benefit: float
    expected_cost: float
    risk_features: Dict[str, Any]
    priority: InquiryPriority = InquiryPriority.MEDIUM
    suggested_scope: List[str] = field(default_factory=list)


class AdaptiveInquiryPolicyEngine:
    def __init__(
        self,
        policy: Optional[Dict[str, Any]] = None,
        ledger_repo: Optional[LedgerRepository] = None,
        audit_sample_rate: float = 0.05,
    ):
        self.policy = policy or load_policy()
        self.ledger_repo = ledger_repo or LedgerRepository()
        self.audit_sample_rate = audit_sample_rate

        notif_cfg = self.policy.get("notifications", {})
        self.quiet_hours_start = notif_cfg.get("quiet_hours_start", 22)
        self.quiet_hours_end = notif_cfg.get("quiet_hours_end", 9)
        self.max_daily = notif_cfg.get("max_daily_inquiries_per_shop", 15)
        self.cooldown_sec = notif_cfg.get("cooldown_between_inquiries_seconds", 120)
        self.policy_version = "voi_adaptive_v2"

    def evaluate_inquiry_decision(
        self,
        offer_id: str,
        shop_id: str,
        product_id: Optional[str],
        price_assessment: PriceAssessment,
        stock_assessment: StockAssessment,
        shop_assessment: ShopReliabilityAssessment,
        user_intent: UserIntent = UserIntent.VISIT,
        travel_burden_min: float = 0.0,
        active_inquiries_count_today: int = 0,
        product_regime: ProductRegime = ProductRegime.ESTABLISHED,
        force_audit_sample: bool = False,
        listed_price_toman: Optional[float] = None,
        now: Optional[datetime] = None,
    ) -> PolicyDecisionContext:
        """Evaluate whether to verify an offer using Value of Information (VoI).
        
        Formula:
          VoI = E[DecisionLossReduction] * P(UsefulResponse) - InterruptionCost - OperationalCost
        
        All losses and costs are expressed in Standard Loss Points (1 SLP = 10,000 Toman).
        This guarantees genuine price-sensitive differentiation without saturation.
        """
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        current_hour = now.hour
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"

        # 1. Quiet Hours check
        is_quiet = False
        if self.quiet_hours_start > self.quiet_hours_end:
            is_quiet = current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end
        else:
            is_quiet = self.quiet_hours_start <= current_hour < self.quiet_hours_end

        if is_quiet:
            context = PolicyDecisionContext(
                decision_id=decision_id,
                action_code="decline_or_defer",
                reason_codes=["quiet_hours_active"],
                selection_probability=0.0,
                selection_trigger="quiet_hours",
                expected_benefit=0.0,
                expected_cost=100.0,
                risk_features={"hour": current_hour},
                priority=InquiryPriority.LOW,
                suggested_scope=[],
            )
            self._log_decision(context, offer_id, shop_id, product_id, now)
            return context

        # 2. Daily Fatigue Budget limit
        if active_inquiries_count_today >= self.max_daily:
            context = PolicyDecisionContext(
                decision_id=decision_id,
                action_code="decline_or_defer",
                reason_codes=["daily_budget_exhausted"],
                selection_probability=0.0,
                selection_trigger="daily_budget",
                expected_benefit=0.0,
                expected_cost=50.0,
                risk_features={"active_inquiries_count_today": active_inquiries_count_today},
                priority=InquiryPriority.LOW,
                suggested_scope=[],
            )
            self._log_decision(context, offer_id, shop_id, product_id, now)
            return context

        # 3. Decision-Theoretic Value of Information (VoI)
        suggested_scope: List[str] = []

        # Determine price in Toman
        price_toman = (
            listed_price_toman
            if listed_price_toman is not None
            else (price_assessment.price_toman or 1_500_000.0)
        )
        price_toman = max(10_000.0, float(price_toman))

        # A. Monetary Price Risk (in SLP: 1 SLP = 10,000 Toman)
        # Using a dimensionally pure, smooth, strictly monotonic logarithmic utility curve:
        # P_eff = P_0 * ln(1 + P / P_0), with anchor P_0 = 25,000,000 Toman.
        # This eliminates dimensional inconsistencies (e.g. adding Toman to sqrt(Toman)),
        # removes artificial derivative kinks at 100M, and preserves continuous sensitivity
        # across luxury workstation items.
        price_risk_fraction = price_assessment.risk_score / 100.0
        p_anchor = 25_000_000.0
        effective_price = p_anchor * math.log(1.0 + (price_toman / p_anchor))
        loss_price_slp = (effective_price * price_risk_fraction * 0.10) / SLP_TOMAN_UNIT

        if price_assessment.risk_band in (RiskBand.CRITICAL, RiskBand.HIGH, RiskBand.MEDIUM):
            if loss_price_slp > 5.0 or price_assessment.risk_band in (RiskBand.CRITICAL, RiskBand.HIGH):
                suggested_scope.append("verify_price")
            if price_assessment.risk_band == RiskBand.MEDIUM:
                loss_price_slp *= 0.6

        # B. Stockout & Wasted Travel Risk (in SLP)
        loss_stock_slp = 0.0
        if stock_assessment.status in (StockState.UNKNOWN, StockState.RESERVED):
            suggested_scope.append("verify_stock")
            # 15.0 SLP base regret (150k Toman) + 0.2 SLP/min travel time cost + value urgency premium
            travel_time_cost_slp = 0.2 * travel_burden_min
            item_urgency_slp = min(50.0, (price_toman * 0.02) / SLP_TOMAN_UNIT)
            unverified_stockout_risk = 0.40
            loss_stock_slp = (15.0 + travel_time_cost_slp + item_urgency_slp) * unverified_stockout_risk

        # C. Market Shock or Discovery Regime override (in SLP)
        loss_regime_slp = 0.0
        if product_regime in (ProductRegime.SHOCK_REGIME, ProductRegime.PRICE_DISCOVERY):
            if "verify_price" not in suggested_scope:
                suggested_scope.append("verify_price")
            loss_regime_slp = max(25.0, (price_toman * 0.03) / SLP_TOMAN_UNIT)

        total_loss_potential = loss_price_slp + loss_stock_slp + loss_regime_slp

        # Intent weight: Visiting customers commit actual physical time; casual browsers do not
        intent_weight = {
            UserIntent.VISIT: 1.6,
            UserIntent.BUY: 1.2,
            UserIntent.BROWSE: 0.3,
        }.get(user_intent, 1.0)

        expected_decision_loss = total_loss_potential * intent_weight

        # Response probability from shop responsiveness score
        p_useful_response = shop_assessment.dimensions.get("inquiry_responsiveness", 0.60)

        # Interruption and Operational Costs in SLP (1 SLP = 10,000 Toman)
        # Base disturbance = 10 SLP (100,000 Toman), escalating by 1.5 SLP per inquiry today
        interruption_cost = 10.0 + (active_inquiries_count_today * 1.5)
        operational_cost = 1.0

        voi = (expected_decision_loss * p_useful_response) - interruption_cost - operational_cost

        risk_features = {
            "price_toman": price_toman,
            "loss_price_slp": round(loss_price_slp, 2),
            "loss_stock_slp": round(loss_stock_slp, 2),
            "loss_regime_slp": round(loss_regime_slp, 2),
            "total_loss_potential": round(total_loss_potential, 2),
            "intent_weight": intent_weight,
            "p_useful_response": round(p_useful_response, 2),
            "interruption_cost": round(interruption_cost, 2),
            "operational_cost": operational_cost,
            "product_regime": product_regime.value,
            "travel_burden_min": travel_burden_min,
        }

        # 4. Controlled Exploration (Audit Sampling)
        if force_audit_sample or (
            voi <= 0
            and self.audit_sample_rate > 0
            and (hash(offer_id + str(now.date())) % 100) < (self.audit_sample_rate * 100)
        ):
            context = PolicyDecisionContext(
                decision_id=decision_id,
                action_code="audit_sample_inquiry",
                reason_codes=["controlled_exploration_audit_sample"],
                selection_probability=self.audit_sample_rate,
                selection_trigger="audit_sample",
                expected_benefit=round(max(voi, 5.0), 2),
                expected_cost=round(interruption_cost, 2),
                risk_features=risk_features,
                priority=InquiryPriority.LOW,
                suggested_scope=["verify_price", "verify_stock"],
            )
            self._log_decision(context, offer_id, shop_id, product_id, now)
            return context

        # 5. Primary Decision
        if voi > 0 and len(suggested_scope) > 0:
            if voi > 50 or user_intent in (UserIntent.VISIT, UserIntent.BUY):
                priority = InquiryPriority.URGENT if voi > 80 else InquiryPriority.HIGH
            else:
                priority = InquiryPriority.MEDIUM

            if product_regime == ProductRegime.SHOCK_REGIME:
                trigger = "market_shock"
            elif user_intent in (UserIntent.VISIT, UserIntent.BUY):
                trigger = "user_purchase_intent"
            else:
                trigger = "heuristic_risk"

            context = PolicyDecisionContext(
                decision_id=decision_id,
                action_code="enqueue_inquiry",
                reason_codes=[f"positive_voi_{voi:.1f}"] + suggested_scope,
                selection_probability=1.0,
                selection_trigger=trigger,
                expected_benefit=round(voi, 2),
                expected_cost=round(interruption_cost, 2),
                risk_features=risk_features,
                priority=priority,
                suggested_scope=suggested_scope,
            )
            self._log_decision(context, offer_id, shop_id, product_id, now)
            return context
            return context

        if len(suggested_scope) > 0:
            # Risk exists but VoI <= 0 (e.g. low intent or high shop fatigue)
            context = PolicyDecisionContext(
                decision_id=decision_id,
                action_code="show_warning",
                reason_codes=["risk_detected_but_inquiry_cost_exceeds_voi"],
                selection_probability=0.0,
                selection_trigger="heuristic_risk",
                expected_benefit=round(voi, 2),
                expected_cost=round(interruption_cost, 2),
                risk_features=risk_features,
                priority=InquiryPriority.LOW,
                suggested_scope=suggested_scope,
            )
            self._log_decision(context, offer_id, shop_id, product_id, now)
            return context

        context = PolicyDecisionContext(
            decision_id=decision_id,
            action_code="no_action",
            reason_codes=["sufficient_evidence_for_intent"],
            selection_probability=0.0,
            selection_trigger="heuristic_risk",
            expected_benefit=0.0,
            expected_cost=0.0,
            risk_features=risk_features,
            priority=InquiryPriority.LOW,
            suggested_scope=[],
        )
        self._log_decision(context, offer_id, shop_id, product_id, now)
        return context

    def _log_decision(
        self,
        ctx: PolicyDecisionContext,
        offer_id: str,
        shop_id: str,
        product_id: Optional[str],
        now: datetime,
    ):
        try:
            scope = {
                "offer_id": offer_id,
                "shop_id": shop_id,
                "product_id": product_id,
                "suggested_scope": ctx.suggested_scope,
            }
            self.ledger_repo.record_policy_decision(
                decision_id=ctx.decision_id,
                scope=scope,
                action_code=ctx.action_code,
                reason_codes=ctx.reason_codes,
                policy_version=self.policy_version,
                selection_probability=ctx.selection_probability,
                selection_trigger=ctx.selection_trigger,
                expected_benefit=ctx.expected_benefit,
                expected_cost=ctx.expected_cost,
                risk_features=ctx.risk_features,
                created_at=now,
            )
        except Exception as e:
            logger.warning(f"Could not persist policy decision context: {e}")


# Retain compatibility wrapper
class InquiryPolicyEngine(AdaptiveInquiryPolicyEngine):
    def evaluate_inquiry_need(
        self,
        price_assessment: PriceAssessment,
        stock_assessment: StockAssessment,
        shop_assessment: ShopReliabilityAssessment,
        user_intent: UserIntent = UserIntent.VISIT,
        active_inquiries_count_today: int = 0,
        now: Optional[datetime] = None,
    ) -> InquiryRecommendation:
        ctx = self.evaluate_inquiry_decision(
            offer_id="compat_offer",
            shop_id="compat_shop",
            product_id=None,
            price_assessment=price_assessment,
            stock_assessment=stock_assessment,
            shop_assessment=shop_assessment,
            user_intent=user_intent,
            active_inquiries_count_today=active_inquiries_count_today,
            now=now,
        )
        if "quiet_hours_active" in ctx.reason_codes:
            reason_text = "در ساعات استراحت فروشگاه (۲۲:۰۰ تا ۰۹:۰۰)، ارسال اعلان خودکار غیرفعال است"
        elif "daily_budget_exhausted" in ctx.reason_codes:
            reason_text = "سقف مجاز استعلام‌های روزانه برای این فروشگاه تکمیل شده است"
        elif ctx.action_code in ("enqueue_inquiry", "audit_sample_inquiry"):
            reason_text = (
                f"ارسال استعلام توصیه می‌شود: ارزش اطلاعات شواهد ({ctx.expected_benefit}) "
                f"بیشتر از هزینه مزاحمت فروشنده است. موضوعات: {', '.join(ctx.suggested_scope)}"
            )
        else:
            reason_text = "; ".join(ctx.reason_codes)

        return InquiryRecommendation(
            recommended=(ctx.action_code in ("enqueue_inquiry", "audit_sample_inquiry")),
            priority=ctx.priority,
            reason=reason_text,
            expected_utility=ctx.expected_benefit,
            suggested_scope=ctx.suggested_scope,
        )
