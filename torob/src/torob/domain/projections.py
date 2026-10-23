from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from torob.domain.entities import EvidenceEvent, Offer
from torob.domain.enums import EvidenceQuality, EvidenceSource, StockState


class OfferStateProjection(BaseModel):
    offer_id: str
    shop_id: str
    verified_price: Optional[float] = None
    price_verified_at: Optional[datetime] = None
    price_verification_source: Optional[EvidenceSource] = None
    stock_state: StockState = StockState.UNKNOWN
    stock_verified_at: Optional[datetime] = None
    quantity_bucket: str = "unknown"
    shop_open_verified: Optional[bool] = None
    shop_open_verified_at: Optional[datetime] = None
    is_conflicted: bool = False
    conflict_reasons: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    last_event_at: Optional[datetime] = None
    evidence_quality: EvidenceQuality = EvidenceQuality.LIMITED


class EvidenceProjector:
    """Projects append-only evidence events into current verified state for an offer.
    
    Adheres to evidence ordering, supersession, bidirectional stock transitions,
    and conflict detection rather than naive last-write-wins.
    """

    @staticmethod
    def project_offer_state(
        offer_id: str,
        shop_id: str,
        events: List[EvidenceEvent],
        initial_offer: Optional[Offer] = None,
    ) -> OfferStateProjection:
        # Sort events chronologically by observed_at (or ingested_at)
        sorted_events = sorted(
            events,
            key=lambda e: (e.observed_at or e.ingested_at).astimezone(timezone.utc)
            if (e.observed_at or e.ingested_at).tzinfo
            else (e.observed_at or e.ingested_at).replace(tzinfo=timezone.utc),
        )

        verified_price = initial_offer.price_toman if initial_offer else None
        price_verified_at = initial_offer.last_price_changed_at if initial_offer else None
        price_source = EvidenceSource.CATALOG_CRAWL if initial_offer else None

        stock_state = StockState.UNKNOWN
        stock_verified_at: Optional[datetime] = None
        quantity_bucket = "unknown"

        shop_open_verified: Optional[bool] = None
        shop_open_verified_at: Optional[datetime] = None

        is_conflicted = False
        conflict_reasons: List[str] = []
        last_event_at: Optional[datetime] = None

        last_seller_price_time: Optional[datetime] = None
        last_customer_price_complaint_time: Optional[datetime] = None

        for ev in sorted_events:
            ev_time = (ev.observed_at or ev.ingested_at)
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)
            last_event_at = ev_time

            # 1. Price confirmations & updates
            if ev.event_type in ("seller_price_confirmation", "seller_price_correction", "pos_price_sync"):
                p = ev.payload.get("confirmed_price") or ev.payload.get("price")
                if p is not None:
                    verified_price = float(p)
                    price_verified_at = ev_time
                    price_source = ev.source_code
                    last_seller_price_time = ev_time
                    # If this confirmation happened after a prior customer complaint, resolve conflict
                    if last_customer_price_complaint_time and ev_time > last_customer_price_complaint_time:
                        is_conflicted = False
                        conflict_reasons = [r for r in conflict_reasons if "مغایرت قیمت" not in r]

            # 2. Customer discrepancy report
            elif ev.event_type == "customer_discrepancy_reported":
                issue = ev.payload.get("issue_type")
                if issue == "price_mismatch":
                    last_customer_price_complaint_time = ev_time
                    # If complaint is newer than seller verification, flag conflict!
                    if not last_seller_price_time or ev_time > last_seller_price_time:
                        is_conflicted = True
                        msg = f"گزارش مغایرت قیمت توسط خریدار در {ev_time.strftime('%Y-%m-%d %H:%M')} ثبت شده است"
                        if msg not in conflict_reasons:
                            conflict_reasons.append(msg)
                elif issue == "shop_closed":
                    shop_open_verified = False
                    shop_open_verified_at = ev_time
                elif issue == "stock_unavailable":
                    stock_state = StockState.OUT_OF_STOCK
                    stock_verified_at = ev_time

            # 3. Stock confirmations (Supports bidirectional transitions: OUT_OF_STOCK -> RESTOCKED)
            elif ev.event_type in ("seller_stock_confirmation", "stock_restocked"):
                st_str = ev.payload.get("stock_state")
                if st_str:
                    try:
                        stock_state = StockState(st_str)
                    except ValueError:
                        stock_state = StockState.UNKNOWN
                else:
                    stock_state = StockState.IN_STORE_SELLABLE
                stock_verified_at = ev_time
                quantity_bucket = ev.payload.get("quantity_bucket", quantity_bucket)

            # 4. Branch open confirmation
            elif ev.event_type == "seller_branch_open_confirmation":
                is_open = ev.payload.get("is_open")
                if is_open is not None:
                    shop_open_verified = bool(is_open)
                    shop_open_verified_at = ev_time

        # Assess evidence quality based on independent sources
        unique_sources = set(e.source_code for e in sorted_events)
        if len(sorted_events) >= 5 and len(unique_sources) >= 2:
            quality = EvidenceQuality.HIGH
        elif len(sorted_events) >= 2:
            quality = EvidenceQuality.MODERATE
        elif len(sorted_events) == 1:
            quality = EvidenceQuality.LIMITED
        else:
            quality = EvidenceQuality.UNKNOWN

        return OfferStateProjection(
            offer_id=offer_id,
            shop_id=shop_id,
            verified_price=verified_price,
            price_verified_at=price_verified_at,
            price_verification_source=price_source,
            stock_state=stock_state,
            stock_verified_at=stock_verified_at,
            quantity_bucket=quantity_bucket,
            shop_open_verified=shop_open_verified,
            shop_open_verified_at=shop_open_verified_at,
            is_conflicted=is_conflicted,
            conflict_reasons=conflict_reasons,
            evidence_count=len(sorted_events),
            last_event_at=last_event_at,
            evidence_quality=quality,
        )
