from datetime import datetime, timezone
import math
from typing import List, Optional
import numpy as np
from pydantic import BaseModel, Field


class PriceObservation(BaseModel):
    observation_id: str
    offer_id: str
    price_toman: float
    observed_at: datetime
    source: str = "crawler"


class PricePathMetrics(BaseModel):
    observations_count: int
    first_price_toman: float
    last_price_toman: float
    net_change_pct: float
    total_abs_movement_pct: float
    realized_volatility: Optional[float] = None
    jump_count: int = 0
    volatility_regime: str  # INSUFFICIENT_DATA, STABLE, MODERATE_VOLATILITY, HIGH_VOLATILITY, SHOCKED
    is_path_volatile_despite_low_net_change: bool = False
    observation_window_days: float


class PriceVolatilityCalculator:
    """Calculates path volatility, log returns, and market regime from historical price observations."""

    @staticmethod
    def calculate_path_metrics(
        observations: List[PriceObservation],
        jump_threshold_pct: float = 0.10,
    ) -> PricePathMetrics:
        if len(observations) < 2:
            first_p = observations[0].price_toman if observations else 0.0
            return PricePathMetrics(
                observations_count=len(observations),
                first_price_toman=first_p,
                last_price_toman=first_p,
                net_change_pct=0.0,
                total_abs_movement_pct=0.0,
                realized_volatility=None,
                jump_count=0,
                volatility_regime="INSUFFICIENT_DATA",
                is_path_volatile_despite_low_net_change=False,
                observation_window_days=0.0,
            )

        # Sort chronologically
        sorted_obs = sorted(
            observations,
            key=lambda o: o.observed_at.astimezone(timezone.utc)
            if o.observed_at.tzinfo
            else o.observed_at.replace(tzinfo=timezone.utc),
        )

        first_p = sorted_obs[0].price_toman
        last_p = sorted_obs[-1].price_toman

        window_days = max(
            0.1,
            (sorted_obs[-1].observed_at - sorted_obs[0].observed_at).total_seconds() / 86400.0,
        )

        net_change = (last_p - first_p) / first_p if first_p > 0 else 0.0

        # Calculate step-by-step path movement and log returns
        total_abs_delta = 0.0
        log_returns: List[float] = []
        jumps = 0

        for i in range(1, len(sorted_obs)):
            p_prev = sorted_obs[i - 1].price_toman
            p_curr = sorted_obs[i].price_toman
            total_abs_delta += abs(p_curr - p_prev)

            if p_prev > 0 and p_curr > 0:
                ret = math.log(p_curr / p_prev)
                log_returns.append(ret)
                if abs(ret) >= jump_threshold_pct:
                    jumps += 1

        total_abs_pct = total_abs_delta / first_p if first_p > 0 else 0.0

        if len(log_returns) >= 2:
            vol = float(np.std(log_returns, ddof=1))
        else:
            vol = None

        # Classify regime
        if len(sorted_obs) < 3:
            regime = "INSUFFICIENT_DATA"
        elif jumps >= 3 or (vol is not None and vol > 0.25):
            regime = "SHOCKED"
        elif vol is not None and vol > 0.12:
            regime = "HIGH_VOLATILITY"
        elif vol is not None and vol > 0.04:
            regime = "MODERATE_VOLATILITY"
        else:
            regime = "STABLE"

        # Detect the classic hidden volatility case: Low net change (< 5%), but high path movement (> 20%)
        is_path_volatile = abs(net_change) < 0.05 and total_abs_pct >= 0.20

        return PricePathMetrics(
            observations_count=len(sorted_obs),
            first_price_toman=first_p,
            last_price_toman=last_p,
            net_change_pct=round(net_change * 100, 2),
            total_abs_movement_pct=round(total_abs_pct * 100, 2),
            realized_volatility=round(vol, 4) if vol is not None else None,
            jump_count=jumps,
            volatility_regime=regime,
            is_path_volatile_despite_low_net_change=is_path_volatile,
            observation_window_days=round(window_days, 1),
        )
