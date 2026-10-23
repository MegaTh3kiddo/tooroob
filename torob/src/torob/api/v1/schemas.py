from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

from torob.domain.assessment import (
    OfferAssessmentResult,
    ShopReliabilityAssessment,
    VisitFeasibility,
)
from torob.domain.entities import FeedbackCase, Inquiry, Offer, Product, Shop
from torob.domain.enums import (
    CaseOutcome,
    CaseStatus,
    FeedbackIssueType,
    InquiryPriority,
    InquiryStatus,
    SortMode,
    StockState,
    UserIntent,
)

T = TypeVar("T")

class HealthResponse(BaseModel):
    status: str
    version: str
    catalog_counts: Dict[str, int]
    timestamp: datetime

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int

# Inquiries
class CreateInquiryRequest(BaseModel):
    shop_id: str
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    question_scope: Dict[str, Any] = Field(default_factory=lambda: {"type": "price_and_stock"})
    priority: InquiryPriority = InquiryPriority.MEDIUM

class CreateInquiryResponse(BaseModel):
    inquiry: Inquiry
    is_new: bool
    message: str

class SubmitSellerResponseRequest(BaseModel):
    actor_id: str = "seller_portal"
    confirmed_price: Optional[float] = None
    confirmed_stock_state: Optional[StockState] = None
    shop_is_open: Optional[bool] = None
    notes: Optional[str] = None

# Feedback
class SubmitFeedbackRequest(BaseModel):
    shop_id: str
    issue_type: FeedbackIssueType
    offer_id: Optional[str] = None
    product_id: Optional[str] = None
    reporter_token: Optional[str] = None
    notes: Optional[str] = None

class SubmitSellerCaseResponseRequest(BaseModel):
    actor_id: str = "seller_portal"
    response_text: str
    proof_details: Optional[Dict[str, Any]] = None

class ResolveCaseRequest(BaseModel):
    outcome: CaseOutcome
    resolution_notes: str

# Visits & Routing
class VisitAssessRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    shop_id: str
    offer_id: Optional[str] = None
    stock_status: StockState = StockState.UNKNOWN
    quantity_bucket: str = "unknown"

class CandidateStopInput(BaseModel):
    shop_id: str
    product_ids: List[str] = Field(default_factory=list)

class RoutePlanRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    stops: List[CandidateStopInput]
    departure_time: Optional[datetime] = None
    sort_mode: SortMode = SortMode.SMART
    dwell_minutes_per_stop: int = 10
