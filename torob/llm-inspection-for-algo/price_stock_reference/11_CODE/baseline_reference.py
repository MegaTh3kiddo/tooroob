"""Educational evidence-based rule baseline. NOT a calibrated probability engine.
Standalone standard-library demo. No production traffic, SMS or push implementation.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
import math

@dataclass(frozen=True)
class OfferEvidence:
    offer_id: str
    price_toman: Optional[float]
    price_type: str = "fixed_purchase_price"
    exact_sku_match: bool = True
    observed_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    reference_peer_price: Optional[float] = None
    independent_peer_shops: int = 0
    market_shock: bool = False
    user_intent: str = "browse"  # browse | buy | visit
    stock_status: str = "unknown"
    store_open_status: str = "unknown"

@dataclass(frozen=True)
class Decision:
    action: str   # show_evidence | show_warning | enqueue_inquiry
    reasons: Tuple[str, ...]
    priority_band: str
    risk_points_heuristic: int


def decide(x: OfferEvidence, now: datetime) -> Decision:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    issues=[]
    if not x.exact_sku_match:issues.append("sku_match_uncertain")
    if x.price_toman is None:issues.append("missing_price")
    elif not math.isfinite(x.price_toman) or x.price_toman <= 1:issues.append("price_sentinel_or_invalid")
    elif x.price_toman > 1e12:issues.append("extreme_absolute_price")
    if x.price_type != "fixed_purchase_price":issues.append("non_fixed_price_type")
    if x.reference_peer_price is not None and x.reference_peer_price > 0 and x.independent_peer_shops >= 3 and x.price_toman is not None and x.price_toman > 0:
        r=x.price_toman/x.reference_peer_price
        if r>3 or r<(1/3):issues.append("peer_deviation_gt_3x")
    if x.last_verified_at is None:issues.append("no_direct_price_verification")
    else:
        hours=max(0,(now-x.last_verified_at).total_seconds()/3600)
        if hours>72:issues.append("verification_older_than_example_72h")  # EXAMPLE only
    if x.market_shock:issues.append("market_shock")
    if x.user_intent in ("buy","visit") and x.stock_status == "unknown":issues.append("stock_not_verified_for_purchase")
    if x.user_intent == "visit" and x.store_open_status == "unknown":issues.append("shop_open_not_verified")
    high=any(c in issues for c in ["sku_match_uncertain","price_sentinel_or_invalid","extreme_absolute_price","missing_price","market_shock","peer_deviation_gt_3x"])
    points=min(100,20*len(issues))
    if x.user_intent in ("buy","visit") and issues:
        return Decision("enqueue_inquiry",tuple(issues),"high" if high else "medium",points)
    if issues:
        return Decision("show_warning",tuple(issues),"high" if high else "medium",points)
    return Decision("show_evidence",("sufficient_heuristic_evidence_for_browse",),"low",0)

if __name__=="__main__":
    x=OfferEvidence(offer_id="demo",price_toman=1,user_intent="visit")
    print(decide(x,datetime.now(timezone.utc)))
