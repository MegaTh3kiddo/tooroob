from datetime import datetime, timedelta, timezone
from typing import List, Optional

from torob.domain.assessment import VisitFeasibility
from torob.domain.entities import Offer, Shop
from torob.domain.enums import RiskBand, StockState
from torob.intelligence.inventory import InventoryIntelligenceEngine
from torob.routing.distance import DistanceRouter
from torob.routing.hours import BusinessHoursEvaluator


class VisitFeasibilityEngine:
    def __init__(
        self,
        router: Optional[DistanceRouter] = None,
        inventory_engine: Optional[InventoryIntelligenceEngine] = None,
    ):
        self.router = router or DistanceRouter()
        self.inventory = inventory_engine or InventoryIntelligenceEngine()

    def assess_visit_feasibility(
        self,
        origin_lat: float,
        origin_lon: float,
        shop: Shop,
        offer: Optional[Offer] = None,
        stock_status: StockState = StockState.UNKNOWN,
        quantity_bucket: str = "unknown",
        now: Optional[datetime] = None,
    ) -> VisitFeasibility:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        warnings: List[str] = []
        shop_lat = shop.lat or origin_lat
        shop_lon = shop.lon or origin_lon

        # 1. Distance & Travel time
        dist_km, travel_mins, mode = self.router.estimate_travel(
            origin_lat, origin_lon, shop_lat, shop_lon
        )
        arrival_time = now + timedelta(minutes=travel_mins)

        # 2. Hours Check (Now and Arrival)
        open_now, open_h, close_h, _ = BusinessHoursEvaluator.evaluate_hours(shop.weekly_hours, now)
        open_at_arrival, _, _, _ = BusinessHoursEvaluator.evaluate_hours(
            shop.weekly_hours, arrival_time
        )
        mins_until_close = (
            BusinessHoursEvaluator.minutes_until_close(close_h, now) if close_h else None
        )

        if not open_now:
            warnings.append("فروشگاه در حال حاضر بسته است")
        if not open_at_arrival:
            warnings.append(
                f"فروشگاه تا زمان رسیدن شما ({arrival_time.strftime('%H:%M')}) بسته خواهد شد"
            )
        elif mins_until_close is not None and mins_until_close < travel_mins + 15:
            warnings.append(
                f"زمان رسیدن شما نزدیک به ساعت تعطیلی فروشگاه ({close_h}:00) است"
            )

        # 3. Stock Survival at Arrival
        stock_assessment = self.inventory.assess_stock(
            stock_status=stock_status,
            quantity_bucket=quantity_bucket,
            travel_time_minutes=travel_mins,
            now=now,
        )
        survival_prob = stock_assessment.survival_probability_at_arrival

        if stock_status == StockState.OUT_OF_STOCK:
            warnings.append("کالا در فروشگاه ناموجود اعلام شده است")
        elif quantity_bucket in ("1_unit", "single_unit"):
            warnings.append("تنها ۱ عدد در انبار موجود است؛ ریسک اتمام کالا قبل از رسیدن وجود دارد")
        elif survival_prob is not None and survival_prob < 0.6:
            warnings.append(f"احتمال اتمام موجودی کالا تا زمان رسیدن شما بالاست (تخمین بقا {int(survival_prob*100)}%)")

        # 4. Feasibility & Risk Band
        feasible = open_at_arrival and stock_status != StockState.OUT_OF_STOCK

        if not feasible:
            risk_band = RiskBand.CRITICAL
        elif len(warnings) > 0 or (survival_prob is not None and survival_prob < 0.6):
            risk_band = RiskBand.HIGH
        elif survival_prob is not None and survival_prob < 0.8:
            risk_band = RiskBand.MEDIUM
        else:
            risk_band = RiskBand.LOW

        return VisitFeasibility(
            feasible=feasible,
            shop_open_now=open_now,
            shop_open_at_arrival=open_at_arrival,
            distance_km=dist_km,
            travel_minutes=travel_mins,
            transport_mode=mode,
            shop_closing_time=f"{close_h}:00" if close_h else None,
            minutes_until_close=mins_until_close,
            stock_survival_probability=survival_prob,
            risk_band=risk_band,
            warnings=warnings,
        )
