from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from torob.domain.enums import (
    EvidenceQuality,
    InquiryPriority,
    PriceAssessmentStatus,
    RiskBand,
    StockState,
)

class PriceAssessment(BaseModel):
    status: PriceAssessmentStatus
    price_toman: Optional[float] = None
    reference_peer_price: Optional[float] = None
    peer_shops_count: int = 0
    price_deviation_ratio: Optional[float] = None
    risk_score: int = Field(ge=0, le=100)
    risk_band: RiskBand
    risk_score_type: str = "heuristic"
    calibrated_probability: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    evidence_quality: EvidenceQuality = EvidenceQuality.LIMITED

class StockAssessment(BaseModel):
    status: StockState
    survival_probability_at_arrival: Optional[float] = None
    is_calibrated: bool = False
    last_verified_at: Optional[datetime] = None
    quantity_bucket: str = "unknown"  # 1_unit, 2_to_5, gt_5, unknown
    reasons: List[str] = Field(default_factory=list)
    evidence_quality: EvidenceQuality = EvidenceQuality.LIMITED

class ShopReliabilityAssessment(BaseModel):
    shop_id: str
    composite_reliability_score: float = Field(ge=0.0, le=1.0)
    dimensions: Dict[str, float] = Field(default_factory=dict)
    observation_count: int = 0
    reasons: List[str] = Field(default_factory=list)
    evidence_quality: EvidenceQuality = EvidenceQuality.LIMITED

class InquiryRecommendation(BaseModel):
    recommended: bool
    priority: InquiryPriority = InquiryPriority.MEDIUM
    reason: str
    expected_utility: float = 0.0
    suggested_scope: List[str] = Field(default_factory=list)

class VisitFeasibility(BaseModel):
    feasible: bool
    shop_open_now: bool
    shop_open_at_arrival: bool
    distance_km: float
    travel_minutes: float
    transport_mode: str  # walking or driving
    shop_closing_time: Optional[str] = None
    minutes_until_close: Optional[int] = None
    stock_survival_probability: Optional[float] = None
    risk_band: RiskBand
    warnings: List[str] = Field(default_factory=list)

class OfferAssessmentResult(BaseModel):
    offer_id: str
    product_id: str
    shop_id: str
    price_assessment: PriceAssessment
    stock_assessment: StockAssessment
    shop_reliability: ShopReliabilityAssessment
    inquiry_recommendation: InquiryRecommendation
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    policy_version: str = "1.0.0"
    data_limitations: List[str] = Field(
        default_factory=lambda: [
            "Dataset is snapshot-based without historical price series",
            "Missing stock is not confirmation of stock-out",
            "Cap-300 censoring applies per shop",
        ]
    )
