import json
import sqlite3
from pathlib import Path
from typing import Optional
import duckdb

from torob.core.config import settings

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    observed_at TEXT,
    ingested_at TEXT NOT NULL,
    source_code TEXT NOT NULL,
    actor_id TEXT,
    payload_json TEXT NOT NULL,
    external_event_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_event_type ON evidence_events(event_type);
CREATE INDEX IF NOT EXISTS idx_evidence_observed ON evidence_events(observed_at);

CREATE TABLE IF NOT EXISTS inquiries (
    inquiry_id TEXT PRIMARY KEY,
    shop_id TEXT NOT NULL,
    offer_id TEXT,
    product_id TEXT,
    question_scope_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'created',
    priority TEXT NOT NULL DEFAULT 'medium',
    dedupe_key TEXT NOT NULL DEFAULT '',
    requested_at TEXT NOT NULL DEFAULT '',
    deadline_at TEXT NOT NULL DEFAULT '',
    policy_version TEXT NOT NULL DEFAULT 'v1',
    delivery_attempts INTEGER NOT NULL DEFAULT 0,
    cancellation_reason TEXT,
    tracking_code TEXT UNIQUE,
    product_title TEXT,
    product_image_url TEXT,
    category_name TEXT,
    recorded_price_toman INTEGER DEFAULT 0,
    customer_name TEXT,
    customer_phone TEXT,
    inquiry_type TEXT DEFAULT 'price_and_stock',
    user_note TEXT,
    decline_reason TEXT,
    offered_price_toman INTEGER,
    is_in_stock INTEGER,
    response_notes TEXT,
    created_at TEXT,
    expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_inquiries_shop_status ON inquiries(shop_id, status);
CREATE INDEX IF NOT EXISTS idx_inquiries_dedupe ON inquiries(dedupe_key, status);

CREATE TABLE IF NOT EXISTS inquiry_delivery_attempts (
    attempt_id TEXT PRIMARY KEY,
    inquiry_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    provider_accepted_at TEXT,
    device_received_at TEXT,
    failure_reason TEXT,
    FOREIGN KEY(inquiry_id) REFERENCES inquiries(inquiry_id)
);

CREATE TABLE IF NOT EXISTS inquiry_responses (
    response_id TEXT PRIMARY KEY,
    inquiry_id TEXT NOT NULL,
    actor_id TEXT NOT NULL DEFAULT '',
    observed_at TEXT,
    ingested_at TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    scope_json TEXT NOT NULL DEFAULT '{}',
    answer_json TEXT NOT NULL DEFAULT '{}',
    client_response_id TEXT UNIQUE,
    seller_id TEXT,
    shop_id TEXT,
    offered_price_toman INTEGER,
    is_in_stock INTEGER,
    stock_count INTEGER DEFAULT 1,
    notes TEXT,
    submitted_at TEXT,
    received_at TEXT,
    decline_reason TEXT,
    FOREIGN KEY(inquiry_id) REFERENCES inquiries(inquiry_id)
);
CREATE INDEX IF NOT EXISTS idx_inquiry_resp_inquiry ON inquiry_responses(inquiry_id);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    shop_id TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_sellers_shop ON sellers(shop_id);

CREATE TABLE IF NOT EXISTS seller_devices (
    device_id TEXT PRIMARY KEY,
    seller_id TEXT NOT NULL,
    fcm_token TEXT UNIQUE NOT NULL,
    device_model TEXT,
    os_version TEXT,
    app_version TEXT,
    notifications_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
);
CREATE INDEX IF NOT EXISTS idx_seller_devices_seller ON seller_devices(seller_id);

CREATE TABLE IF NOT EXISTS shop_settings (
    shop_id TEXT PRIMARY KEY,
    shop_name TEXT,
    address TEXT,
    phone TEXT,
    is_open INTEGER DEFAULT 1,
    open_time TEXT DEFAULT '09:00',
    close_time TEXT DEFAULT '21:00',
    accept_inquiries INTEGER DEFAULT 1,
    holiday_mode INTEGER DEFAULT 0,
    category_names TEXT,
    lat REAL,
    lon REAL,
    website_url TEXT,
    voice_reminders_enabled INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shop_settings_open ON shop_settings(is_open, accept_inquiries);

CREATE TABLE IF NOT EXISTS shop_change_requests (
    request_id TEXT PRIMARY KEY,
    shop_id TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    requested_shop_name TEXT,
    requested_phone TEXT,
    requested_address TEXT,
    requested_open_time TEXT,
    requested_close_time TEXT,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    FOREIGN KEY (shop_id) REFERENCES shop_settings(shop_id),
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
);
CREATE INDEX IF NOT EXISTS idx_shop_change_requests_shop ON shop_change_requests(shop_id, status);

CREATE TABLE IF NOT EXISTS push_audit_logs (
    log_id TEXT PRIMARY KEY,
    inquiry_id TEXT,
    shop_id TEXT,
    fcm_token TEXT,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    payload_json TEXT,
    status TEXT NOT NULL,
    error_detail TEXT,
    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_push_audit_shop ON push_audit_logs(shop_id, dispatched_at);

CREATE TABLE IF NOT EXISTS inquiry_timelines (
    inquiry_id TEXT PRIMARY KEY,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    initial_push_at TIMESTAMP,
    reminder_push_at TIMESTAMP,
    urgent_call_push_at TIMESTAMP,
    seller_viewed_at TIMESTAMP,
    seller_responded_at TIMESTAMP,
    response_time_seconds INTEGER,
    expired_at TIMESTAMP,
    alternative_shop_id TEXT,
    FOREIGN KEY (inquiry_id) REFERENCES inquiries(inquiry_id)
);

CREATE TABLE IF NOT EXISTS scheduler_configs (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outbound_call_logs (
    call_id TEXT PRIMARY KEY,
    scenario_type TEXT NOT NULL,
    destination_number TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_call_id TEXT,
    status TEXT NOT NULL,
    shop_id TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_identity_mappings (
    central_shop_id TEXT PRIMARY KEY,
    external_merchant_shop_id TEXT NOT NULL,
    match_status TEXT NOT NULL DEFAULT 'verified',
    match_evidence TEXT,
    merchant_account_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_profiles (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    preferred_city TEXT DEFAULT 'Tehran',
    default_travel_mode TEXT DEFAULT 'DRIVING',
    plan_tier TEXT DEFAULT 'free',
    photo_url TEXT,
    preferences_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_saved_plans (
    saved_plan_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    plan_id TEXT,
    title TEXT NOT NULL,
    mode TEXT DEFAULT 'smart',
    depart_time TEXT,
    stops_json TEXT NOT NULL DEFAULT '[]',
    plan_data_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customer_saved_plans_cust ON customer_saved_plans(customer_id);

CREATE TABLE IF NOT EXISTS support_submissions (
    submission_id TEXT PRIMARY KEY,
    customer_id TEXT,
    ticket_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    contact_info TEXT,
    status TEXT NOT NULL DEFAULT 'received',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_cases (
    case_id TEXT PRIMARY KEY,
    shop_id TEXT NOT NULL,
    offer_id TEXT,
    product_id TEXT,
    visit_at TEXT,
    opened_at TEXT NOT NULL,
    case_status TEXT NOT NULL DEFAULT 'received',
    outcome TEXT NOT NULL DEFAULT 'not_yet_determined',
    issue_type TEXT NOT NULL,
    reporter_token TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_shop_status ON feedback_cases(shop_id, case_status);

CREATE TABLE IF NOT EXISTS feedback_case_events (
    case_event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    observed_at TEXT,
    recorded_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES feedback_cases(case_id)
);

CREATE TABLE IF NOT EXISTS shop_reliability_state (
    shop_id TEXT PRIMARY KEY,
    commercial_trust_score REAL NOT NULL DEFAULT 0.5,
    price_fidelity_score REAL NOT NULL DEFAULT 0.5,
    stock_accuracy_score REAL NOT NULL DEFAULT 0.5,
    physical_presence_score REAL NOT NULL DEFAULT 0.5,
    inquiry_responsiveness_score REAL NOT NULL DEFAULT 0.5,
    address_accuracy_score REAL NOT NULL DEFAULT 0.5,
    composite_reliability_score REAL NOT NULL DEFAULT 0.5,
    observation_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot_manifests (
    snapshot_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    checksum TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS offer_observations (
    observation_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    shop_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    price_toman REAL,
    availability_status TEXT NOT NULL DEFAULT 'unknown',
    observed_at TEXT NOT NULL,
    is_price_changed INTEGER NOT NULL DEFAULT 0,
    previous_price_toman REAL,
    observation_interval_hours REAL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshot_manifests(snapshot_id)
);
CREATE INDEX IF NOT EXISTS idx_observations_offer ON offer_observations(offer_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_observations_shop ON offer_observations(shop_id, observed_at);

CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    action_code TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    selection_probability REAL,
    selection_trigger TEXT NOT NULL DEFAULT 'heuristic_risk',
    expected_benefit REAL,
    expected_cost REAL,
    risk_features_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_policy_decisions_created ON policy_decisions(created_at);

CREATE TABLE IF NOT EXISTS quality_alerts (
    alert_id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    is_resolved INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_quality_alerts_resolved ON quality_alerts(is_resolved, severity);

CREATE TABLE IF NOT EXISTS external_trust_evidence (
    trust_evidence_id TEXT PRIMARY KEY,
    shop_id TEXT NOT NULL,
    branch_id TEXT,
    source_name TEXT NOT NULL,
    scope TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    expires_at TEXT,
    verification_method TEXT,
    raw_evidence_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_trust_evidence_shop ON external_trust_evidence(shop_id);

CREATE TABLE IF NOT EXISTS recommendation_decisions (
    decision_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    objective TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    candidate_product_ids_json TEXT NOT NULL,
    selected_product_ids_json TEXT NOT NULL,
    ranking_policy_version TEXT NOT NULL,
    warnings_json TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_rec_decisions_session ON recommendation_decisions(session_id);

CREATE TABLE IF NOT EXISTS recommendation_outcomes (
    outcome_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    outcome_type TEXT NOT NULL,
    product_id TEXT,
    recorded_at TEXT NOT NULL,
    payload_json TEXT DEFAULT '{}',
    FOREIGN KEY(decision_id) REFERENCES recommendation_decisions(decision_id)
);
CREATE INDEX IF NOT EXISTS idx_rec_outcomes_decision ON recommendation_outcomes(decision_id);

CREATE TABLE IF NOT EXISTS shopping_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    detected_intent TEXT,
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON shopping_sessions(updated_at);
"""

MIGRATION_COLUMNS = [
    # Table, Column, Type
    ("inquiries", "tracking_code", "TEXT"),
    ("inquiries", "product_title", "TEXT"),
    ("inquiries", "product_image_url", "TEXT"),
    ("inquiries", "category_name", "TEXT"),
    ("inquiries", "recorded_price_toman", "INTEGER DEFAULT 0"),
    ("inquiries", "customer_name", "TEXT"),
    ("inquiries", "customer_phone", "TEXT"),
    ("inquiries", "inquiry_type", "TEXT DEFAULT 'price_and_stock'"),
    ("inquiries", "user_note", "TEXT"),
    ("inquiries", "decline_reason", "TEXT"),
    ("inquiries", "offered_price_toman", "INTEGER"),
    ("inquiries", "is_in_stock", "INTEGER"),
    ("inquiries", "response_notes", "TEXT"),
    ("inquiries", "created_at", "TEXT"),
    ("inquiries", "expires_at", "TEXT"),
    ("inquiry_responses", "client_response_id", "TEXT"),
    ("inquiry_responses", "seller_id", "TEXT"),
    ("inquiry_responses", "shop_id", "TEXT"),
    ("inquiry_responses", "offered_price_toman", "INTEGER"),
    ("inquiry_responses", "is_in_stock", "INTEGER"),
    ("inquiry_responses", "stock_count", "INTEGER DEFAULT 1"),
    ("inquiry_responses", "notes", "TEXT"),
    ("inquiry_responses", "submitted_at", "TEXT"),
    ("inquiry_responses", "received_at", "TEXT"),
    ("inquiry_responses", "decline_reason", "TEXT"),
    ("shop_settings", "category_names", "TEXT"),
    ("shop_settings", "lat", "REAL"),
    ("shop_settings", "lon", "REAL"),
    ("shop_settings", "website_url", "TEXT"),
    ("shop_settings", "voice_reminders_enabled", "INTEGER DEFAULT 1"),
    ("inquiry_timelines", "urgent_call_push_at", "TIMESTAMP"),
]


def _apply_migrations(conn: sqlite3.Connection):
    """Safely apply column additions and indices to any pre-existing SQLite database."""
    cursor = conn.cursor()
    for table_name, column_name, col_type in MIGRATION_COLUMNS:
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type};")
        except Exception:
            # Column already exists or table created fresh with column
            pass

    # Ensure unique and lookup indexes
    indexes = [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_inquiry_resp_client_id ON inquiry_responses(client_response_id);",
        "CREATE INDEX IF NOT EXISTS idx_inquiries_tracking_code ON inquiries(tracking_code);",
        "CREATE INDEX IF NOT EXISTS idx_sellers_shop ON sellers(shop_id);",
        "CREATE INDEX IF NOT EXISTS idx_seller_devices_seller ON seller_devices(seller_id);",
        "CREATE INDEX IF NOT EXISTS idx_shop_settings_open ON shop_settings(is_open, accept_inquiries);",
        "CREATE INDEX IF NOT EXISTS idx_customer_saved_plans_cust ON customer_saved_plans(customer_id);",
    ]
    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass
    conn.commit()


import threading


class DatabaseManager:
    def __init__(self, duckdb_path: Optional[str] = None, sqlite_path: Optional[Path] = None):
        self.duckdb_path = duckdb_path or settings.duckdb_path
        self.sqlite_path = sqlite_path or settings.sqlite_path
        self._duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._init_lock = threading.Lock()

    def get_duckdb(self) -> duckdb.DuckDBPyConnection:
        if self._duckdb_conn is None:
            self._duckdb_conn = duckdb.connect(self.duckdb_path)
        return self._duckdb_conn.cursor()

    def get_sqlite(self) -> sqlite3.Connection:
        if str(self.sqlite_path) == ":memory:":
            with self._init_lock:
                if self._sqlite_conn is None:
                    self._sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
                    self._sqlite_conn.row_factory = sqlite3.Row
                    self._sqlite_conn.executescript(SQLITE_SCHEMA)
                    _apply_migrations(self._sqlite_conn)
                    self._sqlite_conn.commit()
                return self._sqlite_conn

        conn = getattr(self._local, "conn", None)
        if conn is None:
            if self.sqlite_path != ":memory:":
                self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            with self._init_lock:
                conn.executescript(SQLITE_SCHEMA)
                _apply_migrations(conn)
                conn.commit()
            self._local.conn = conn
        return conn

    def close(self):
        if self._duckdb_conn:
            self._duckdb_conn.close()
            self._duckdb_conn = None
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None


db_manager = DatabaseManager()
