from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from torob.ingestion.normalizer import normalize_digits

TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def parse_split_intervals(text: str) -> List[Tuple[int, int, int, int]]:
    """Parse string with one or more hour ranges like '10:00-14:00, 16:30-21:00' or '۹ تا ۲۱'.
    
    Returns a list of intervals: [(open_hour, open_min, close_hour, close_min), ...]
    """
    norm = normalize_digits(text).strip()
    intervals: List[Tuple[int, int, int, int]] = []
    
    # Split on comma, slash, or semicolon for split shifts
    parts = re.split(r"[,;/]+", norm)
    for p in parts:
        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(?:-|تا|to)\s*(\d{1,2})(?::(\d{2}))?", p.strip())
        if m:
            o_h = min(23, max(0, int(m.group(1))))
            o_m = min(59, max(0, int(m.group(2) or 0)))
            c_h = min(23, max(0, int(m.group(3))))
            c_m = min(59, max(0, int(m.group(4) or 0)))
            intervals.append((o_h, o_m, c_h, c_m))
    return intervals


def parse_hour_range(text: str) -> Optional[Tuple[int, int]]:
    """Parse primary hour range like '9-21' or '09:00 - 21:00' into (open_hour, close_hour)."""
    intervals = parse_split_intervals(text)
    if intervals:
        return intervals[0][0], intervals[0][2]
    return None


class BusinessHoursEvaluator:
    @staticmethod
    def evaluate_hours(
        weekly_hours: Optional[Dict[str, Any]],
        at_datetime: Optional[datetime] = None,
        min_service_buffer_minutes: int = 10,
    ) -> Tuple[bool, Optional[int], Optional[int], str]:
        """Evaluate if the shop is open at the given datetime in Tehran local time.
        
        Returns:
            (is_open, next_or_current_open_hour, next_or_current_close_hour, description)
        """
        at_time = at_datetime or datetime.now(timezone.utc)
        # Convert to Asia/Tehran local time
        tehran_time = at_time.astimezone(TEHRAN_TZ) if at_time.tzinfo else at_time.replace(tzinfo=timezone.utc).astimezone(TEHRAN_TZ)
        current_minute_of_day = tehran_time.hour * 60 + tehran_time.minute

        if not weekly_hours or not isinstance(weekly_hours, dict):
            # Missing hours: Default assumption is open during standard hours (10-20), flagged as unverified
            is_open = 10 * 60 <= current_minute_of_day < 20 * 60
            return is_open, 10, 20, "ساعات کاری ثبت نشده است (پیش‌فرض ۱۰:۰۰ تا ۲۰:۰۰ فرض شد)"

        intervals: List[Tuple[int, int, int, int]] = []

        # Check direct keys like openH/closeH
        if "openH" in weekly_hours and "closeH" in weekly_hours:
            try:
                o_h = int(weekly_hours["openH"])
                c_h = int(weekly_hours["closeH"])
                intervals.append((o_h, 0, c_h, 0))
            except Exception:
                pass

        if not intervals:
            # Map Tehran local day of week
            # Python weekday: Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
            day_map = {
                5: ["sat", "saturday", "شنبه"],
                6: ["sun", "sunday", "یکشنبه"],
                0: ["mon", "monday", "دوشنبه"],
                1: ["tue", "tuesday", "سه‌شنبه", "سه شنبه"],
                2: ["wed", "wednesday", "چهارشنبه"],
                3: ["thu", "thursday", "پنج‌شنبه", "پنج شنبه"],
                4: ["fri", "friday", "جمعه"],
            }
            possible_keys = day_map.get(tehran_time.weekday(), [])
            for k in possible_keys:
                if k in weekly_hours:
                    val = str(weekly_hours[k])
                    parsed = parse_split_intervals(val)
                    if parsed:
                        intervals = parsed
                        break

        # Fallback to any range found in the dict values
        if not intervals:
            for v in weekly_hours.values():
                parsed = parse_split_intervals(str(v))
                if parsed:
                    intervals = parsed
                    break

        if not intervals:
            intervals = [(10, 0, 21, 0)]

        # Check if current time falls within any open interval
        is_open = False
        active_close_h = None
        active_open_h = None

        for o_h, o_m, c_h, c_m in intervals:
            start_min = o_h * 60 + o_m
            end_min = c_h * 60 + c_m
            if start_min <= current_minute_of_day < end_min:
                is_open = True
                active_open_h = o_h
                active_close_h = c_h
                break

        if not is_open:
            # Find next upcoming interval today
            upcoming = [
                (o_h, c_h)
                for o_h, o_m, c_h, c_m in intervals
                if o_h * 60 + o_m > current_minute_of_day
            ]
            if upcoming:
                active_open_h, active_close_h = upcoming[0]
            else:
                active_open_h, active_close_h = intervals[0][0], intervals[0][2]

        desc_parts = [f"{o:02d}:{om:02d} الی {c:02d}:{cm:02d}" for o, om, c, cm in intervals]
        desc = f"ساعات کاری (تهران): {', '.join(desc_parts)}"
        return is_open, active_open_h, active_close_h, desc

    @staticmethod
    def minutes_until_close(
        close_h: int,
        at_datetime: Optional[datetime] = None,
    ) -> int:
        at_time = at_datetime or datetime.now(timezone.utc)
        tehran_time = at_time.astimezone(TEHRAN_TZ) if at_time.tzinfo else at_time.replace(tzinfo=timezone.utc).astimezone(TEHRAN_TZ)
        current_minute = tehran_time.hour * 60 + tehran_time.minute
        close_minute = close_h * 60
        return max(0, close_minute - current_minute)
