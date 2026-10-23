from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from torob.domain.enums import (
    CaseOutcome,
    CaseStatus,
    EvidenceQuality,
    EvidenceSource,
    FeedbackIssueType,
    InquiryPriority,
    InquiryStatus,
    RiskBand,
    StockState,
)

class Shop(BaseModel):
    shop_id: str
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_label: Optional[str] = None
    category_names: List[str] = Field(default_factory=list)
    payment_options: Optional[str] = None
    supports_fast_delivery: bool = False
    website_url: Optional[str] = None
    weekly_hours: Optional[Dict[str, Any]] = None
    contacts: Optional[str] = None
    instagram: Optional[str] = None

class Product(BaseModel):
    product_id: str
    persian_title: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    model: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    specs: Dict[str, Any] = Field(default_factory=dict)

class Offer(BaseModel):
    offer_id: str
    product_id: str
    shop_id: str
    price_toman: Optional[float] = None
    last_price_changed_at: Optional[datetime] = None
    seller_title: Optional[str] = None
    warranty: Optional[str] = None
    description: Optional[str] = None

class Variant(BaseModel):
    sku_id: str
    product_id: str
    color: Optional[str] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    condition: str = "new"  # new, used, refurbished
    warranty: Optional[str] = None
    specs: Dict[str, Any] = Field(default_factory=dict)

class EvidenceEvent(BaseModel):
    event_id: str
    event_type: str
    scope: Dict[str, Any]
    observed_at: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None
    source_code: EvidenceSource
    source_identity: Optional[str] = None
    actor_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    commercial_terms: Dict[str, Any] = Field(default_factory=dict)
    evidence_quality: EvidenceQuality = EvidenceQuality.LIMITED
    is_synthetic: bool = False
    superseded_by: Optional[str] = None
    external_event_id: Optional[str] = None

class Inquiry(BaseModel):
    inquiry_id: str
    shop_id: str
    offer_id: Optional[str] = None
    product_id: Optional[str] = None
    question_scope: Dict[str, Any] = Field(default_factory=dict)
    status: InquiryStatus = InquiryStatus.CREATED
    priority: InquiryPriority = InquiryPriority.MEDIUM
    dedupe_key: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deadline_at: datetime
    policy_version: str = "1.0.0"
    delivery_attempts: int = 0
    cancellation_reason: Optional[str] = None

class InquiryResponse(BaseModel):
    response_id: str
    inquiry_id: str
    actor_id: str
    observed_at: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    answer: Dict[str, Any] = Field(default_factory=dict)

class FeedbackCase(BaseModel):
    case_id: str
    shop_id: str
    offer_id: Optional[str] = None
    product_id: Optional[str] = None
    visit_at: Optional[datetime] = None
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    case_status: CaseStatus = CaseStatus.RECEIVED
    outcome: CaseOutcome = CaseOutcome.NOT_YET_DETERMINED
    issue_type: FeedbackIssueType
    reporter_token: Optional[str] = None
    notes: Optional[str] = None

class FeedbackCaseEvent(BaseModel):
    case_event_id: str
    case_id: str
    event_type: str
    actor_role: str  # customer, seller, operator, system
    observed_at: Optional[datetime] = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)

class ShopReliability(BaseModel):
    shop_id: str
    commercial_trust_score: float = 0.5
    price_fidelity_score: float = 0.5
    stock_accuracy_score: float = 0.5
    physical_presence_score: float = 0.5
    inquiry_responsiveness_score: float = 0.5
    address_accuracy_score: float = 0.5
    composite_reliability_score: float = 0.5
    observation_count: int = 0
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
