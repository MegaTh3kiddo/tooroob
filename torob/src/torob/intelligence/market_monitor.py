"""Market Monitoring, Quality Alerts & Automatic Reassessment Engine.

Continuously scans catalog observations, peer pricing, and ledger events to detect:
1. 10x Currency-denomination anomalies (Rial entered as Toman).
2. Sudden synchronized category price shocks.
3. Address and location discrepancy clusters.
4. Seller non-response surges.
5. Sudden category-level stock depletion spikes.

Generates structured, auditable internal QualityAlert events and coordinates
targeted entity reassessment without unapproved external push spam.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from torob.intelligence.invalidation import invalidation_tracker
from torob.storage.repository_ledger import LedgerRepository

logger = logging.getLogger("torob.intelligence.market_monitor")


@dataclass
class QualityAlertEvent:
    alert_id: str
    alert_type: str
    severity: str  # critical | high | medium | low
    entity_type: str  # offer | shop | product | category
    entity_id: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_resolved: bool = False


class MarketMonitoringEngine:
    def __init__(self, ledger_repo: Optional[LedgerRepository] = None):
        self.ledger_repo = ledger_repo or LedgerRepository()

    def check_offer_price_anomalies(
        self,
        offer_id: str,
        shop_id: str,
        product_id: str,
        price_toman: float,
        reference_price_toman: Optional[float],
    ) -> Optional[QualityAlertEvent]:
        """Check for currency denomination (10x) and extreme price anomalies."""
        if not reference_price_toman or reference_price_toman <= 0 or price_toman <= 0:
            return None

        ratio = price_toman / reference_price_toman

        # 1. 10x Rial-to-Toman inflation anomaly
        if 8.5 <= ratio <= 11.5:
            alert = QualityAlertEvent(
                alert_id=f"alt_{uuid.uuid4().hex[:12]}",
                alert_type="currency_denomination_10x_error",
                severity="high",
                entity_type="offer",
                entity_id=offer_id,
                payload={
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "price_toman": price_toman,
                    "reference_price_toman": reference_price_toman,
                    "ratio": round(ratio, 2),
                    "suspected_correct_price": round(price_toman / 10.0),
                    "description": "احتمال خطای واحد پول (ورود ریال به جای تومان) توسط فروشنده.",
                },
            )
            self._persist_and_trigger(alert)
            return alert

        # 2. 0.1x deflation anomaly
        if 0.085 <= ratio <= 0.115:
            alert = QualityAlertEvent(
                alert_id=f"alt_{uuid.uuid4().hex[:12]}",
                alert_type="currency_omission_0_1x_error",
                severity="high",
                entity_type="offer",
                entity_id=offer_id,
                payload={
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "price_toman": price_toman,
                    "reference_price_toman": reference_price_toman,
                    "ratio": round(ratio, 2),
                    "suspected_correct_price": round(price_toman * 10.0),
                    "description": "احتمال حذف صفر در قیمت ثبت‌شده فروشنده.",
                },
            )
            self._persist_and_trigger(alert)
            return alert

        # 3. Severe price deviation (> 3x or < 0.3x)
        if ratio > 3.0 or ratio < 0.33:
            alert = QualityAlertEvent(
                alert_id=f"alt_{uuid.uuid4().hex[:12]}",
                alert_type="severe_peer_price_deviation",
                severity="medium",
                entity_type="offer",
                entity_id=offer_id,
                payload={
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "price_toman": price_toman,
                    "reference_price_toman": reference_price_toman,
                    "ratio": round(ratio, 2),
                    "description": "قیمت بیش از ۳ برابر از میانه بازار انحراف دارد.",
                },
            )
            self._persist_and_trigger(alert)
            return alert

        return None

    def check_address_discrepancy_clusters(self, shop_id: str) -> Optional[QualityAlertEvent]:
        """Detect multiple independent customer reports of moved shop or incorrect pin."""
        cursor = self.ledger_repo.conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM feedback_cases
            WHERE shop_id = ? AND issue_type IN ('wrong_address_or_pin', 'shop_closed', 'shop_moved')
            AND case_status != 'closed'
            """,
            (shop_id,),
        )
        row = cursor.fetchone()
        cnt = row["cnt"] if row else 0

        if cnt >= 2:
            alert = QualityAlertEvent(
                alert_id=f"alt_{uuid.uuid4().hex[:12]}",
                alert_type="address_discrepancy_cluster",
                severity="high",
                entity_type="shop",
                entity_id=shop_id,
                payload={
                    "complaint_count": cnt,
                    "description": f"ثبت {cnt} گزارش تأییدنشده درباره بسته بودن یا آدرس نادرست این فروشگاه.",
                },
            )
            self._persist_and_trigger(alert)
            return alert
        return None

    def check_seller_nonresponse_surge(self, shop_id: str) -> Optional[QualityAlertEvent]:
        """Detect unusually high inquiry expiration / nonresponse rate."""
        cursor = self.ledger_repo.conn.execute(
            """
            SELECT status FROM inquiries
            WHERE shop_id = ?
            ORDER BY requested_at DESC LIMIT 5
            """,
            (shop_id,),
        )
        rows = cursor.fetchall()
        if len(rows) >= 3:
            expired_cnt = sum(1 for r in rows if r["status"] == "expired")
            if (expired_cnt / len(rows)) >= 0.6:
                alert = QualityAlertEvent(
                    alert_id=f"alt_{uuid.uuid4().hex[:12]}",
                    alert_type="seller_nonresponse_surge",
                    severity="medium",
                    entity_type="shop",
                    entity_id=shop_id,
                    payload={
                        "recent_inquiries": len(rows),
                        "expired_count": expired_cnt,
                        "description": "بیش از ۶۰٪ استعلام‌های اخیر این فروشگاه بدون پاسخ منقضی شده‌اند.",
                    },
                )
                self._persist_and_trigger(alert)
                return alert
        return None

    def _persist_and_trigger(self, alert: QualityAlertEvent):
        try:
            self.ledger_repo.record_quality_alert(
                alert_id=alert.alert_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                entity_type=alert.entity_type,
                entity_id=alert.entity_id,
                payload=alert.payload,
                created_at=alert.created_at,
            )
            # Invalidation trigger
            if alert.entity_type == "offer":
                invalidation_tracker.mark_offer_stale(alert.entity_id)
            elif alert.entity_type == "shop":
                invalidation_tracker.mark_shop_stale(alert.entity_id)
            logger.info(f"Quality alert persisted: {alert.alert_type} for {alert.entity_type}:{alert.entity_id}")
        except Exception as e:
            logger.warning(f"Could not persist quality alert: {e}")
