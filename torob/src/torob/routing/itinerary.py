from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from torob.domain.entities import Shop
from torob.domain.enums import SortMode
from torob.routing.distance import DistanceRouter
from torob.routing.hours import BusinessHoursEvaluator


class ItineraryStop(BaseModel):
    order: int
    shop_id: str
    shop_name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    product_ids: List[str] = Field(default_factory=list)
    leg_distance_km: float
    leg_travel_minutes: float
    transport_mode: str
    estimated_arrival_at: str
    estimated_departure_at: str
    is_open_at_arrival: bool
    shop_closing_time: Optional[str] = None
    minutes_until_close_at_arrival: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)


class VisitItineraryPlan(BaseModel):
    total_stops: int
    total_distance_km: float
    total_duration_minutes: float
    departure_time: str
    sort_mode: SortMode
    stops: List[ItineraryStop] = Field(default_factory=list)
    overall_warnings: List[str] = Field(default_factory=list)


class ItineraryPlanner:
    def __init__(self, router: Optional[DistanceRouter] = None):
        self.router = router or DistanceRouter()

    def plan(
        self,
        origin_lat: float,
        origin_lon: float,
        candidate_stops: List[Dict[str, Any]],  # {"shop": Shop, "product_ids": [...]}
        departure_time: Optional[datetime] = None,
        sort_mode: SortMode = SortMode.SMART,
        dwell_minutes: int = 10,
    ) -> VisitItineraryPlan:
        dep_time = departure_time or datetime.now(timezone.utc)
        if dep_time.tzinfo is None:
            dep_time = dep_time.replace(tzinfo=timezone.utc)

        stops_pool = list(candidate_stops)
        ordered_stops: List[ItineraryStop] = []
        overall_warnings: List[str] = []

        curr_lat = origin_lat
        curr_lon = origin_lon
        curr_time = dep_time
        total_dist = 0.0

        # Sort stops based on selected mode
        if sort_mode == SortMode.NEAR:
            # Sort nearest first relative to origin
            stops_pool.sort(
                key=lambda s: self.router.estimate_travel(
                    curr_lat, curr_lon, s["shop"].lat or curr_lat, s["shop"].lon or curr_lon
                )[0]
            )
        elif sort_mode == SortMode.CLOSING:
            # Sort earliest closing first
            stops_pool.sort(
                key=lambda s: BusinessHoursEvaluator.evaluate_hours(
                    s["shop"].weekly_hours, curr_time
                )[2]
                or 24
            )
        else:  # SMART mode
            # Smart mode: Prioritize shops closing within 60 minutes, then sort by distance
            def smart_key(s):
                is_open, open_h, close_h, _ = BusinessHoursEvaluator.evaluate_hours(
                    s["shop"].weekly_hours, curr_time
                )
                close_h = close_h or 21
                mins_left = BusinessHoursEvaluator.minutes_until_close(close_h, curr_time)
                closing_soon_penalty = 0 if mins_left < 60 else 1000
                dist, _, _ = self.router.estimate_travel(
                    curr_lat, curr_lon, s["shop"].lat or curr_lat, s["shop"].lon or curr_lon
                )
                return closing_soon_penalty + dist

            stops_pool.sort(key=smart_key)

        for idx, item in enumerate(stops_pool, start=1):
            shop: Shop = item["shop"]
            p_ids = item.get("product_ids", [])
            shop_lat = shop.lat or curr_lat
            shop_lon = shop.lon or curr_lon

            # Calculate leg travel
            dist_km, travel_mins, mode = self.router.estimate_travel(
                curr_lat, curr_lon, shop_lat, shop_lon
            )
            arrival_time = curr_time + timedelta(minutes=travel_mins)
            dep_stop_time = arrival_time + timedelta(minutes=dwell_minutes)

            # Evaluate shop hours at arrival
            is_open, open_h, close_h, hours_desc = BusinessHoursEvaluator.evaluate_hours(
                shop.weekly_hours, arrival_time
            )
            mins_left = (
                BusinessHoursEvaluator.minutes_until_close(close_h, arrival_time)
                if close_h
                else None
            )

            stop_warnings = []
            if not is_open:
                warn_msg = f"فروشگاه {shop.name} در زمان تخمینی رسیدن شما ({arrival_time.strftime('%H:%M')}) بسته است"
                stop_warnings.append(warn_msg)
                overall_warnings.append(warn_msg)
            elif mins_left is not None and mins_left < 30:
                stop_warnings.append(f"توجه: کمتر از {mins_left} دقیقه تا بسته شدن فروشگاه باقی مانده است")

            ordered_stops.append(
                ItineraryStop(
                    order=idx,
                    shop_id=shop.shop_id,
                    shop_name=shop.name,
                    address=shop.address,
                    lat=shop.lat,
                    lon=shop.lon,
                    product_ids=p_ids,
                    leg_distance_km=dist_km,
                    leg_travel_minutes=travel_mins,
                    transport_mode=mode,
                    estimated_arrival_at=arrival_time.strftime("%H:%M"),
                    estimated_departure_at=dep_stop_time.strftime("%H:%M"),
                    is_open_at_arrival=is_open,
                    shop_closing_time=f"{close_h}:00" if close_h else None,
                    minutes_until_close_at_arrival=mins_left,
                    warnings=stop_warnings,
                )
            )

            total_dist += dist_km
            curr_lat = shop_lat
            curr_lon = shop_lon
            curr_time = dep_stop_time

        total_duration = (curr_time - dep_time).total_seconds() / 60.0

        return VisitItineraryPlan(
            total_stops=len(ordered_stops),
            total_distance_km=round(total_dist, 2),
            total_duration_minutes=round(total_duration, 1),
            departure_time=dep_time.strftime("%H:%M"),
            sort_mode=sort_mode,
            stops=ordered_stops,
            overall_warnings=overall_warnings,
        )
