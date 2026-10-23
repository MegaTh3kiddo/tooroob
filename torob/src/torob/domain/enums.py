from enum import Enum

class PriceAssessmentStatus(str, Enum):
    VALID_ESTIMATE = "valid_estimate"
    SENTINEL_ANOMALY = "sentinel_anomaly"
    MISSING_PRICE = "missing_price"
    EXTREME_VALUE = "extreme_value"
    PEER_DEVIATION_HIGH = "peer_deviation_high"
    PEER_DEVIATION_LOW = "peer_deviation_low"
    CURRENCY_MISMATCH_SUSPECT = "currency_mismatch_suspect"
    STALE = "stale"
    UNKNOWN = "unknown"

class StockState(str, Enum):
    IN_STORE_SELLABLE = "in_store_sellable"
    IN_OTHER_WAREHOUSE = "in_other_warehouse"
    SUPPLIER_AVAILABLE = "supplier_available"
    PREORDER = "preorder"
    RESERVED = "reserved"
    DISPLAY_ONLY = "display_only"
    DEFECTIVE = "defective"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"

class InquiryStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    DELIVERED = "delivered"
    ANSWERED = "answered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class InquiryPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class CaseStatus(str, Enum):
    RECEIVED = "received"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    SELLER_RESPONDED = "seller_responded"
    CLOSED = "closed"

class CaseOutcome(str, Enum):
    NOT_YET_DETERMINED = "not_yet_determined"
    RESOLVED_CORRECT = "resolved_correct"
    RESOLVED_PRICE_UPDATED = "resolved_price_updated"
    RESOLVED_STOCK_UPDATED = "resolved_stock_updated"
    DISPUTED = "disputed"
    UNSUBSTANTIATED = "unsubstantiated"

class FeedbackIssueType(str, Enum):
    SHOP_CLOSED = "shop_closed"
    STOCK_UNAVAILABLE = "stock_unavailable"
    PRICE_MISMATCH = "price_mismatch"
    VARIANT_MISMATCH = "variant_mismatch"
    COLOR_MISMATCH = "color_mismatch"
    WARRANTY_MISMATCH = "warranty_mismatch"
    ADDRESS_INCORRECT = "address_incorrect"
    ORDER_ONLY = "order_only"
    SUCCESSFUL_PURCHASE = "successful_purchase"
    OTHER = "other"

class EvidenceSource(str, Enum):
    SELLER_CONFIRMATION = "seller_confirmation"
    CUSTOMER_REPORT = "customer_report"
    OPERATOR_AUDIT = "operator_audit"
    CATALOG_CRAWL = "catalog_crawl"
    POS_INTEGRATION = "pos_integration"
    SYSTEM_RULE = "system_rule"
    PEER_CONSENSUS = "peer_consensus"
    MARKET_INFERENCE = "market_inference"
    SYNTHETIC_FIXTURE = "synthetic_fixture"

class EvidenceQuality(str, Enum):
    UNKNOWN = "unknown"
    LIMITED = "limited"
    MODERATE = "moderate"
    HIGH = "high"

class UserIntent(str, Enum):
    BROWSE = "browse"
    BUY = "buy"
    VISIT = "visit"

class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SortMode(str, Enum):
    PRICE = "price"
    NEAR = "near"
    CLOSING = "closing"
    SMART = "smart"

class ProductRegime(str, Enum):
    COLD_START = "cold_start"
    PRICE_DISCOVERY = "price_discovery"
    STABILIZING = "stabilizing"
    ESTABLISHED = "established"
    SHOCK_REGIME = "shock_regime"
    END_OF_LIFE_OR_SCARCITY = "end_of_life_or_scarcity"
    INTERMITTENT_SUPPLY = "intermittent_supply"
