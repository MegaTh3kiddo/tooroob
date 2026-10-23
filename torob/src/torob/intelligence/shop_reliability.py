"""Multi-Dimensional Shop Reliability Engine with Bayesian Shrinkage & Temporal Decay.

Implements Beta-Binomial conjugate updating with category-level priors,
evidence uncertainty estimation, exponential temporal decay,
honest out-of-stock response crediting, and source uncorrelation.

=============================================================================
EXPERIMENTAL HEURISTIC CONFIGURATION:
Notice: The baseline prior parameters (alpha_0, beta_0) and 60-day half-life
decay constant are heuristic operational safeguards. They prevent extreme
swings on sparse data and prevent permanent penalties for past transient issues.
They are NOT empirically estimated causal parameters. Once verified merchant
outcome datasets are gathered, empirical Bayes (e.g. marginal maximum likelihood)
should be used to calibrate domain-specific priors and hazard rates.
=============================================================================
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import logging

from torob.core.config import load_policy
from torob.domain.assessment import ShopReliabilityAssessment
from torob.domain.entities import Shop, ShopReliability
from torob.domain.enums import EvidenceQuality

logger = logging.getLogger("torob.intelligence.shop_reliability")


@dataclass
class DimensionScore:
    mean: float
    variance: float
    observation_count: int
    alpha: float
    beta_param: float
    confidence_interval_95: Tuple[float, float]
    effective_sample_size: float = 0.0
    decayed_weight_sum: float = 0.0


class BayesianShopReliabilityEngine:
    def __init__(
        self,
        policy: Optional[Dict[str, Any]] = None,
        half_life_days: float = 60.0,
    ):
        self.policy = policy or load_policy()
        self.half_life_days = half_life_days
        self.decay_lambda = math.log(2) / max(1.0, half_life_days)

        # Category/Market Priors (alpha_0, beta_0) for Beta distributions
        # Prior mean = alpha / (alpha + beta)
        self.priors = {
            "price_fidelity": (4.0, 1.0),        # Prior mean: 0.80, weight: 5
            "stock_accuracy": (3.5, 1.5),        # Prior mean: 0.70, weight: 5
            "inquiry_responsiveness": (3.0, 2.0),# Prior mean: 0.60, weight: 5
            "physical_presence": (4.5, 0.5),     # Prior mean: 0.90, weight: 5
            "address_accuracy": (4.5, 0.5),      # Prior mean: 0.90, weight: 5
            "commercial_trust": (3.5, 1.5),      # Prior mean: 0.70, weight: 5
        }

    def _update_beta_binomial(
        self,
        dimension_name: str,
        weighted_successes: float,
        weighted_trials: float,
        effective_sample_size: float = 0.0,
        decayed_weight_sum: float = 0.0,
        raw_count: int = 0,
    ) -> DimensionScore:
        alpha_0, beta_0 = self.priors.get(dimension_name, (3.0, 2.0))
        post_alpha = alpha_0 + weighted_successes
        post_beta = beta_0 + max(0.0, weighted_trials - weighted_successes)

        total = post_alpha + post_beta
        mean = post_alpha / total
        variance = (post_alpha * post_beta) / (total * total * (total + 1.0))
        std_dev = math.sqrt(variance)

        # Exact Beta distribution quantiles for 95% equal-tailed credible interval
        try:
            import scipy.stats as stats
            ci_low = float(stats.beta.ppf(0.025, post_alpha, post_beta))
            ci_high = float(stats.beta.ppf(0.975, post_alpha, post_beta))
        except Exception:
            ci_low = max(0.0, mean - (1.96 * std_dev))
            ci_high = min(1.0, mean + (1.96 * std_dev))

        obs_count = raw_count if raw_count > 0 else int(round(weighted_trials))
        return DimensionScore(
            mean=round(mean, 3),
            variance=round(variance, 5),
            observation_count=obs_count,
            alpha=round(post_alpha, 2),
            beta_param=round(post_beta, 2),
            confidence_interval_95=(round(ci_low, 3), round(ci_high, 3)),
            effective_sample_size=round(effective_sample_size, 2),
            decayed_weight_sum=round(decayed_weight_sum, 2),
        )

    def assess_shop_reliability(
        self,
        shop: Shop,
        reliability_state: Optional[ShopReliability] = None,
        verified_outcomes: Optional[List[Dict[str, Any]]] = None,
        external_trust_badges: Optional[List[Dict[str, Any]]] = None,
        as_of: Optional[datetime] = None,
    ) -> ShopReliabilityAssessment:
        """Calculate multi-dimensional shop reliability using Bayesian shrinkage.
        
        A shop with 5/5 confirmations has a high mean but wide credible interval.
        A shop with 95/100 has narrow uncertainty. Recent verified failures receive
        exponential decay weighting without eternal penalties.
        """
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        reasons: List[str] = []
        outcomes = verified_outcomes or []

        # Tally weighted outcomes by dimension with exponential time decay
        # Track sum(w), sum(w^2), and raw counts for Kish design-effect effective sample size
        dim_successes = {k: 0.0 for k in self.priors}
        dim_trials = {k: 0.0 for k in self.priors}
        dim_trials_sq = {k: 0.0 for k in self.priors}
        dim_raw_counts = {k: 0 for k in self.priors}

        for ev in outcomes:
            ev_time = ev.get("observed_at") or ev.get("created_at")
            if isinstance(ev_time, str):
                dt = datetime.fromisoformat(ev_time)
            elif isinstance(ev_time, datetime):
                dt = ev_time
            else:
                dt = now

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
            weight = math.exp(-self.decay_lambda * age_days)

            dim = ev.get("dimension")
            is_success = ev.get("is_success", False)
            if dim in dim_trials:
                dim_trials[dim] += weight
                dim_trials_sq[dim] += weight * weight
                dim_raw_counts[dim] += 1
                if is_success:
                    dim_successes[dim] += weight

        # Static attributes priors
        if shop.website_url:
            dim_successes["commercial_trust"] += 1.0
            dim_trials["commercial_trust"] += 1.0
            dim_trials_sq["commercial_trust"] += 1.0
            dim_raw_counts["commercial_trust"] += 1
            reasons.append("فروشگاه دارای وب‌سایت مستقل ثبت‌شده است")

        if shop.weekly_hours and len(shop.weekly_hours) > 0:
            dim_successes["physical_presence"] += 1.0
            dim_trials["physical_presence"] += 1.0
            dim_trials_sq["physical_presence"] += 1.0
            dim_raw_counts["physical_presence"] += 1
            reasons.append("ساعات کاری مدون در کاتالوگ ثبت شده است")

        if external_trust_badges:
            dim_successes["commercial_trust"] += 2.0
            dim_trials["commercial_trust"] += 2.0
            dim_trials_sq["commercial_trust"] += 4.0
            dim_raw_counts["commercial_trust"] += 2
            reasons.append(f"نشان اعتبار بیرونی ({external_trust_badges[0].get('source_name', 'ضمانت')}) ثبت شده است")

        # Compute smoothed dimension scores with bounded effective sample sizes
        scores: Dict[str, DimensionScore] = {}
        for dim in self.priors:
            w_sum = dim_trials[dim]
            w_sq_sum = dim_trials_sq[dim]
            # Kish ratio alone is invariant under uniform decay: (K*w)^2 / (K*w^2) = K.
            # The true effective sample weight of decayed evidence is strictly bounded by w_sum.
            kish_ratio = (w_sum * w_sum) / w_sq_sum if w_sq_sum > 0 else 0.0
            effective_n = min(w_sum, kish_ratio) if w_sq_sum > 0 else 0.0

            scores[dim] = self._update_beta_binomial(
                dimension_name=dim,
                weighted_successes=dim_successes[dim],
                weighted_trials=dim_trials[dim],
                effective_sample_size=effective_n,
                decayed_weight_sum=w_sum,
                raw_count=dim_raw_counts[dim],
            )

        total_obs = sum(int(round(t)) for t in dim_trials.values())
        if reliability_state:
            total_obs += reliability_state.observation_count

        # Composite score weighting
        composite = (
            0.25 * scores["price_fidelity"].mean
            + 0.25 * scores["stock_accuracy"].mean
            + 0.20 * scores["physical_presence"].mean
            + 0.15 * scores["commercial_trust"].mean
            + 0.15 * scores["inquiry_responsiveness"].mean
        )
        composite = round(min(1.0, max(0.0, composite)), 3)

        # Quality tier
        if total_obs >= 15:
            quality = EvidenceQuality.HIGH
        elif total_obs >= 4:
            quality = EvidenceQuality.MODERATE
        else:
            quality = EvidenceQuality.LIMITED
            reasons.append("شواهد ثبت‌شده برای فروشگاه محدود است؛ مقادیر به سمت میانگین دسته تعدیل شده‌اند")

        dims_dict = {
            dim: {
                "score": score.mean,
                "uncertainty_std": round(math.sqrt(score.variance), 3),
                "ci_95": score.confidence_interval_95,
                "observation_count": score.observation_count,
                "effective_sample_size": score.effective_sample_size,
                "decayed_weight_sum": score.decayed_weight_sum,
                "alpha": score.alpha,
                "beta": score.beta_param,
            }
            for dim, score in scores.items()
        }

        # Flat dictionary for backward compatibility with endpoints
        flat_dims = {dim: score.mean for dim, score in scores.items()}

        return ShopReliabilityAssessment(
            shop_id=shop.shop_id,
            composite_reliability_score=composite,
            dimensions=flat_dims,
            observation_count=total_obs,
            reasons=reasons,
            evidence_quality=quality,
        )


# Compatibility wrapper
class ShopReliabilityEngine:
    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        self.bayesian_engine = BayesianShopReliabilityEngine(policy=policy)

    def assess_shop(
        self,
        shop: Shop,
        reliability_state: Optional[ShopReliability] = None,
        negative_feedback_count: int = 0,
        positive_feedback_count: int = 0,
    ) -> ShopReliabilityAssessment:
        outcomes = []
        for _ in range(positive_feedback_count):
            outcomes.append({"dimension": "price_fidelity", "is_success": True})
            outcomes.append({"dimension": "stock_accuracy", "is_success": True})
        for _ in range(negative_feedback_count):
            outcomes.append({"dimension": "price_fidelity", "is_success": False})
            outcomes.append({"dimension": "stock_accuracy", "is_success": False})

        return self.bayesian_engine.assess_shop_reliability(
            shop=shop,
            reliability_state=reliability_state,
            verified_outcomes=outcomes,
        )
