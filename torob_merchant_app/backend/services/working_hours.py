import logging
from datetime import datetime, time
from typing import Optional, Tuple
import zoneinfo

logger = logging.getLogger("working_hours")

try:
    TEHRAN_TZ = zoneinfo.ZoneInfo("Asia/Tehran")
except Exception:
    TEHRAN_TZ = None


def parse_time_str(time_str: str) -> time:
    """Parse time string like '09:00', '9:30', or '21:30:00' into a datetime.time object."""
    if not time_str:
        return time(9, 0)
    parts = time_str.strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return time(hour=hour, minute=minute)


def get_current_tehran_time(now_dt: Optional[datetime] = None) -> time:
    """Get the current time in Tehran timezone."""
    if now_dt is None:
        if TEHRAN_TZ:
            now_dt = datetime.now(TEHRAN_TZ)
        else:
            now_dt = datetime.now()
    elif now_dt.tzinfo is None:
        if TEHRAN_TZ:
            now_dt = now_dt.replace(tzinfo=TEHRAN_TZ)
    else:
        if TEHRAN_TZ:
            now_dt = now_dt.astimezone(TEHRAN_TZ)
    return now_dt.time()


def is_within_working_hours(
    open_time_str: str,
    close_time_str: str,
    current_time: Optional[time] = None
) -> bool:
    """
    Check if the given current_time falls within [open_time, close_time].
    Supports:
    - Normal daytime shifts (e.g. 09:00 to 21:00)
    - Overnight shifts spanning midnight (e.g. 18:00 to 02:00)
    - 24-hour operations (e.g. 00:00 to 23:59 or 00:00 to 00:00)
    """
    try:
        t_open = parse_time_str(open_time_str or "09:00")
        t_close = parse_time_str(close_time_str or "21:00")
    except Exception as e:
        logger.warning(f"Error parsing working hours ('{open_time_str}', '{close_time_str}'): {e}")
        return True

    if current_time is None:
        current_time = get_current_tehran_time()

    if t_open <= t_close:
        # Standard day shift, e.g. 09:00 to 21:00
        return t_open <= current_time <= t_close
    else:
        # Overnight shift spanning midnight, e.g. 18:00 to 02:00
        return current_time >= t_open or current_time <= t_close


def is_shop_effectively_open(
    is_open_setting: bool,
    holiday_mode: bool,
    open_time: str,
    close_time: str,
    current_time: Optional[time] = None
) -> Tuple[bool, bool, str]:
    """
    Determine if a shop is effectively open right now.
    Returns:
    (is_open: bool, is_within_hours: bool, status_message: str)
    """
    within_hours = is_within_working_hours(open_time, close_time, current_time)

    if not is_open_setting:
        return False, within_hours, "فروشگاه توسط فروشنده بسته شده است"
    if holiday_mode:
        return False, within_hours, "فروشگاه در حالت تعطیلات موقت است"
    if not within_hours:
        return False, False, f"خارج از ساعات کاری (ساعت کاری: {open_time} الی {close_time})"

    return True, True, "فروشگاه باز و دایر است"
