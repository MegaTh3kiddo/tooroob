from torob.merchant.models import MetricsDto
from torob.storage.db import db_manager


def _to_persian_digits(num_or_str) -> str:
    persian_digits = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    return "".join(persian_digits.get(c, c) for c in str(num_or_str))


def _format_duration_persian(seconds: int) -> str:
    if seconds <= 0:
        return "کمتر از ۱ دقیقه"
    minutes = seconds // 60
    rem_seconds = seconds % 60
    if minutes == 0:
        return f"{_to_persian_digits(rem_seconds)} ثانیه"
    if rem_seconds == 0:
        return f"{_to_persian_digits(minutes)} دقیقه"
    return f"{_to_persian_digits(minutes)} دقیقه و {_to_persian_digits(rem_seconds)} ثانیه"


def compute_store_metrics(shop_id: str) -> MetricsDto:
    """Compute performance and response rate statistics for a merchant store."""
    conn = db_manager.get_sqlite()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status IN ('ANSWERED', 'answered') THEN 1 ELSE 0 END) as answered,
        SUM(CASE WHEN status IN ('EXPIRED', 'expired') THEN 1 ELSE 0 END) as expired,
        SUM(CASE WHEN status IN ('ACTIVE', 'created', 'queued', 'delivered') THEN 1 ELSE 0 END) as active
    FROM inquiries
    WHERE shop_id = ?
    """, (shop_id,))
    counts = cursor.fetchone()

    total = counts["total"] or 0
    answered = counts["answered"] or 0
    expired = counts["expired"] or 0
    active = counts["active"] or 0

    response_rate = round((answered / total * 100), 1) if total > 0 else 100.0

    # Average response latency from timelines
    cursor.execute("""
    SELECT AVG(response_time_seconds) as avg_time
    FROM inquiry_timelines t
    JOIN inquiries i ON t.inquiry_id = i.inquiry_id
    WHERE i.shop_id = ? AND t.response_time_seconds IS NOT NULL
    """, (shop_id,))
    avg_row = cursor.fetchone()
    avg_secs = int(avg_row["avg_time"]) if avg_row and avg_row["avg_time"] else 120

    return MetricsDto(
        shop_id=shop_id,
        total_inquiries=total,
        answered_inquiries=answered,
        expired_inquiries=expired,
        active_inquiries=active,
        response_rate_percent=response_rate,
        average_response_time_seconds=avg_secs,
        average_response_time_formatted=_format_duration_persian(avg_secs)
    )
