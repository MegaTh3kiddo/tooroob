"""Market Behavior, Dynamic Regimes, Multi-Scale Volatility & Price Dynamics.

Implements historical price movement features (path length vs net return),
product lifecycle regime classification with three novelty dates,
hierarchical peer aggregation with single-seller protection,
and currency-denomination anomaly detection (10x Rial/Toman errors).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import logging

from torob.domain.enums import ProductRegime
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.intelligence.market_dynamics")


@dataclass
class MultiScaleVolatilityFeatures:
    offer_id: str
    observation_count: int
    net_change_pct: float
    total_abs_log_movement: float
    realized_log_variance: float
    jump_magnitude_max: float
    price_change_frequency: int
    time_since_last_observation_hours: Optional[float] = None
    time_since_last_verified_hours: Optional[float] = None
    seller_lag_relative_to_peers_days: Optional[float] = None
    observation_sparsity_score: float = 0.0
    evidence_coverage_score: float = 0.0


@dataclass
class ProductLifecycleAssessment:
    product_id: str
    regime: ProductRegime
    global_release_at: Optional[datetime] = None
    local_market_first_seen_at: Optional[datetime] = None
    system_first_seen_at: Optional[datetime] = None
    market_age_days: Optional[float] = None
    system_age_days: Optional[float] = None
    regime_confidence: float = 0.5
    regime_reasons: List[str] = field(default_factory=list)


@dataclass
class MarketReferenceSummary:
    product_id: str
    peer_median_price_toman: Optional[float]
    independent_peer_shops_count: int
    is_single_seller: bool
    price_dispersion_iqr_toman: Optional[float] = None
    market_reference_quality: str = "insufficient_data"  # high | moderate | low | single_seller | none
    warning: Optional[str] = None


class MarketDynamicsEngine:
    def __init__(self, ledger_repo: Optional[LedgerRepository] = None):
        self.ledger_repo = ledger_repo or LedgerRepository()

    def compute_historical_features(
        self,
        offer_id: str,
        observations: Optional[List[Dict[str, Any]]] = None,
        as_of: Optional[datetime] = None,
        last_verified_at: Optional[datetime] = None,
    ) -> MultiScaleVolatilityFeatures:
        """Calculate multi-scale volatility features from chronological offer observations.
        
        Strictly differentiates net price change from path movement. A series:
        100 -> 125 -> 95 -> 135 -> 90 -> 102 has net change +2%, but high realized
        path movement and elevated volatility risk.
        """
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        obs_list = observations
        if obs_list is None:
            obs_list = self.ledger_repo.get_offer_observations(offer_id, limit=200)

        # Filter strictly by as_of to prevent future-data leakage
        valid_obs = []
        for o in obs_list:
            t = datetime.fromisoformat(o["observed_at"])
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t <= now and o.get("price_toman") is not None and o["price_toman"] > 0:
                valid_obs.append((t, float(o["price_toman"])))

        valid_obs.sort(key=lambda x: x[0])

        if not valid_obs:
            return MultiScaleVolatilityFeatures(
                offer_id=offer_id,
                observation_count=0,
                net_change_pct=0.0,
                total_abs_log_movement=0.0,
                realized_log_variance=0.0,
                jump_magnitude_max=0.0,
                price_change_frequency=0,
                observation_sparsity_score=1.0,
            )

        prices = [x[1] for x in valid_obs]
        times = [x[0] for x in valid_obs]
        n = len(prices)

        last_obs_time = times[-1]
        hours_since_last_obs = max(0.0, (now - last_obs_time).total_seconds() / 3600.0)

        hours_since_verified = None
        if last_verified_at:
            v_dt = last_verified_at if last_verified_at.tzinfo else last_verified_at.replace(tzinfo=timezone.utc)
            hours_since_verified = max(0.0, (now - v_dt).total_seconds() / 3600.0)

        if n == 1:
            return MultiScaleVolatilityFeatures(
                offer_id=offer_id,
                observation_count=1,
                net_change_pct=0.0,
                total_abs_log_movement=0.0,
                realized_log_variance=0.0,
                jump_magnitude_max=0.0,
                price_change_frequency=0,
                time_since_last_observation_hours=hours_since_last_obs,
                time_since_last_verified_hours=hours_since_verified,
                observation_sparsity_score=0.8,
            )

        # Calculate path returns
        log_returns = []
        abs_log_returns = []
        price_changes = 0

        for i in range(1, n):
            p_prev = prices[i - 1]
            p_curr = prices[i]
            if p_prev > 0 and p_curr > 0:
                ret = math.log(p_curr / p_prev)
                log_returns.append(ret)
                abs_log_returns.append(abs(ret))
                if abs(p_curr - p_prev) > 0.01:
                    price_changes += 1

        net_change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100.0
        total_abs_movement = sum(abs_log_returns)
        realized_var = sum(r * r for r in log_returns)
        max_jump = max(abs_log_returns) if abs_log_returns else 0.0

        # Sparsity score: based on observation gaps
        total_span_hours = max(1.0, (times[-1] - times[0]).total_seconds() / 3600.0)
        avg_interval = total_span_hours / max(1, n - 1)
        sparsity = min(1.0, avg_interval / 168.0)  # > 1 week gap = sparse

        return MultiScaleVolatilityFeatures(
            offer_id=offer_id,
            observation_count=n,
            net_change_pct=round(net_change_pct, 2),
            total_abs_log_movement=round(total_abs_movement, 4),
            realized_log_variance=round(realized_var, 6),
            jump_magnitude_max=round(max_jump, 4),
            price_change_frequency=price_changes,
            time_since_last_observation_hours=round(hours_since_last_obs, 2),
            time_since_last_verified_hours=round(hours_since_verified, 2) if hours_since_verified else None,
            observation_sparsity_score=round(sparsity, 2),
            evidence_coverage_score=1.0 if hours_since_verified and hours_since_verified < 72.0 else 0.3,
        )

    def classify_product_lifecycle(
        self,
        product_id: str,
        observations_count: int,
        system_first_seen_at: Optional[datetime],
        local_market_first_seen_at: Optional[datetime] = None,
        global_release_at: Optional[datetime] = None,
        volatility_features: Optional[MultiScaleVolatilityFeatures] = None,
        peer_count: int = 1,
        is_market_shock: bool = False,
        as_of: Optional[datetime] = None,
    ) -> ProductLifecycleAssessment:
        """Classify product behavior into distinct regimes preserving three novelty timestamps."""
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        system_age_days = None
        if system_first_seen_at:
            s_dt = system_first_seen_at if system_first_seen_at.tzinfo else system_first_seen_at.replace(tzinfo=timezone.utc)
            system_age_days = max(0.0, (now - s_dt).total_seconds() / 86400.0)

        market_age_days = None
        effective_market_date = local_market_first_seen_at or system_first_seen_at
        if effective_market_date:
            m_dt = effective_market_date if effective_market_date.tzinfo else effective_market_date.replace(tzinfo=timezone.utc)
            market_age_days = max(0.0, (now - m_dt).total_seconds() / 86400.0)

        reasons = []

        # 1. Market Shock Regime
        if is_market_shock:
            reasons.append("Widespread correlated price volatility detected across market peers.")
            return ProductLifecycleAssessment(
                product_id=product_id,
                regime=ProductRegime.SHOCK_REGIME,
                global_release_at=global_release_at,
                local_market_first_seen_at=local_market_first_seen_at,
                system_first_seen_at=system_first_seen_at,
                market_age_days=round(market_age_days, 1) if market_age_days else None,
                system_age_days=round(system_age_days, 1) if system_age_days else None,
                regime_confidence=0.85,
                regime_reasons=reasons,
            )

        # 2. Cold Start Regime (Very few observations in our system)
        if observations_count <= 2:
            reasons.append("Sparse historical observations (<= 2); data maturity is low.")
            return ProductLifecycleAssessment(
                product_id=product_id,
                regime=ProductRegime.COLD_START,
                global_release_at=global_release_at,
                local_market_first_seen_at=local_market_first_seen_at,
                system_first_seen_at=system_first_seen_at,
                market_age_days=round(market_age_days, 1) if market_age_days else None,
                system_age_days=round(system_age_days, 1) if system_age_days else None,
                regime_confidence=0.9,
                regime_reasons=reasons,
            )

        # 3. Price Discovery (New to local market < 30 days or active high variance with multiple peers)
        if market_age_days is not None and market_age_days < 30.0:
            reasons.append(f"Newly introduced to local market ({market_age_days:.1f} days); prices actively settling.")
            return ProductLifecycleAssessment(
                product_id=product_id,
                regime=ProductRegime.PRICE_DISCOVERY,
                global_release_at=global_release_at,
                local_market_first_seen_at=local_market_first_seen_at,
                system_first_seen_at=system_first_seen_at,
                market_age_days=round(market_age_days, 1) if market_age_days else None,
                system_age_days=round(system_age_days, 1) if system_age_days else None,
                regime_confidence=0.8,
                regime_reasons=reasons,
            )

        # 4. Scarcity / End of Life
        if peer_count == 1 and market_age_days and market_age_days > 180.0:
            reasons.append("Mature product with severe seller attrition (only 1 seller remaining).")
            return ProductLifecycleAssessment(
                product_id=product_id,
                regime=ProductRegime.END_OF_LIFE_OR_SCARCITY,
                global_release_at=global_release_at,
                local_market_first_seen_at=local_market_first_seen_at,
                system_first_seen_at=system_first_seen_at,
                market_age_days=round(market_age_days, 1) if market_age_days else None,
                system_age_days=round(system_age_days, 1) if system_age_days else None,
                regime_confidence=0.75,
                regime_reasons=reasons,
            )

        # 5. Stabilizing vs Established
        if volatility_features and volatility_features.total_abs_log_movement > 0.4:
            reasons.append("Path movement remains elevated; product price is stabilizing.")
            regime = ProductRegime.STABILIZING
        else:
            reasons.append("Established market product with stable pricing history.")
            regime = ProductRegime.ESTABLISHED

        return ProductLifecycleAssessment(
            product_id=product_id,
            regime=regime,
            global_release_at=global_release_at,
            local_market_first_seen_at=local_market_first_seen_at,
            system_first_seen_at=system_first_seen_at,
            market_age_days=round(market_age_days, 1) if market_age_days else None,
            system_age_days=round(system_age_days, 1) if system_age_days else None,
            regime_confidence=0.85,
            regime_reasons=reasons,
        )

    def aggregate_market_reference(
        self,
        product_id: str,
        offers: List[Dict[str, Any]],
        target_offer_id: Optional[str] = None,
    ) -> MarketReferenceSummary:
        """Compute robust peer market reference using Leave-One-Shop-Out.
        
        Strictly enforces single-seller protection: if only 1 independent shop offers
        the product, competitor median is NOT fabricated or substituted with category median!
        """
        valid_prices: List[Tuple[str, float]] = []
        for o in offers:
            o_id = o.get("offer_id")
            s_id = o.get("shop_id")
            p_val = o.get("price_toman")
            if target_offer_id and o_id == target_offer_id:
                continue  # Leave-One-Shop-Out
            if p_val is not None and float(p_val) > 0 and s_id:
                valid_prices.append((s_id, float(p_val)))

        # Unique shops count
        unique_shops = set(s for s, _ in valid_prices)
        peer_count = len(unique_shops)

        if peer_count == 0:
            return MarketReferenceSummary(
                product_id=product_id,
                peer_median_price_toman=None,
                independent_peer_shops_count=0,
                is_single_seller=True,
                market_reference_quality="single_seller",
                warning="محصول تک‌فروشنده است. مقایسه قیمت با سایر فروشگاه‌ها امکان‌پذیر نیست و میانگین دسته به عنوان قیمت معتبر معرفی نمی‌گردد.",
            )

        prices_only = sorted([p for _, p in valid_prices])
        median_price = prices_only[len(prices_only) // 2]

        # Calculate IQR if sufficient peers
        iqr = None
        if len(prices_only) >= 4:
            q1 = prices_only[len(prices_only) // 4]
            q3 = prices_only[(3 * len(prices_only)) // 4]
            iqr = q3 - q1

        quality = "high" if peer_count >= 3 else "moderate"
        warning = None if peer_count >= 3 else "تعداد فروشگاه‌های مستقل مقایسه محدود است (کمتر از ۳ فروشگاه)."

        return MarketReferenceSummary(
            product_id=product_id,
            peer_median_price_toman=median_price,
            independent_peer_shops_count=peer_count,
            is_single_seller=False,
            price_dispersion_iqr_toman=iqr,
            market_reference_quality=quality,
            warning=warning,
        )

    def detect_currency_denomination_anomaly(
        self,
        offer_price_toman: float,
        reference_price_toman: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Detect currency denomination mistakes (e.g. 10x factor between Rial and Toman).
        
        Example: Typing 150,000,000 Rial into a Toman field produces a 10x factor error.
        Typing 1,500,000 Toman for a 15,000,000 Toman laptop produces a 0.1x factor error.
        """
        if not reference_price_toman or reference_price_toman <= 0 or offer_price_toman <= 0:
            return None

        ratio = offer_price_toman / reference_price_toman

        # Check for 10x factor (Rial entered as Toman)
        if 8.5 <= ratio <= 11.5:
            return {
                "detected": True,
                "anomaly_type": "rial_to_toman_inflation_10x",
                "severity": "high",
                "ratio": round(ratio, 2),
                "suspected_corrected_price_toman": round(offer_price_toman / 10.0),
                "message": f"احتمال خطای واحد پول (ورود ریال به جای تومان): قیمت {offer_price_toman:,.0f} تقریباً ۱۰ برابر قیمت مرجع ({reference_price_toman:,.0f}) است.",
            }

        # Check for 0.1x factor (Toman divided by 10 or zero omitted)
        if 0.085 <= ratio <= 0.115:
            return {
                "detected": True,
                "anomaly_type": "zero_omission_or_toman_deflation_0_1x",
                "severity": "high",
                "ratio": round(ratio, 2),
                "suspected_corrected_price_toman": round(offer_price_toman * 10.0),
                "message": f"احتمال حذف صفر یا تقسیم اشتباه واحد پول: قیمت {offer_price_toman:,.0f} تقریباً یک‌دهم قیمت مرجع ({reference_price_toman:,.0f}) است.",
            }

        return None
