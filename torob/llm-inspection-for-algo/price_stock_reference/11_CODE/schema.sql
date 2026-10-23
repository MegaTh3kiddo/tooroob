-- PostgreSQL concept DDL, intentionally minimal: adjust types, indexes, partitioning & FK constraints before production.
-- Never treat this as a drop-in production migration.
CREATE TABLE shop_branches (
 branch_id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, address TEXT, latitude DOUBLE PRECISION,
 longitude DOUBLE PRECISION, timezone TEXT NOT NULL DEFAULT 'Asia/Tehran',
 identity_version BIGINT NOT NULL DEFAULT 1, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE sku_variants (
 sku_id TEXT PRIMARY KEY, product_id TEXT NOT NULL, attributes JSONB NOT NULL DEFAULT '{}',
 condition_code TEXT NOT NULL DEFAULT 'unknown', canonical_hash TEXT NOT NULL
);
CREATE TABLE offers_current (
 offer_id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, branch_id TEXT REFERENCES shop_branches(branch_id),
 sku_id TEXT REFERENCES sku_variants(sku_id), channel TEXT NOT NULL DEFAULT 'unknown',
 price_type TEXT NOT NULL DEFAULT 'unknown', price_toman NUMERIC(20,2),
 price_terms JSONB NOT NULL DEFAULT '{}', offer_version BIGINT NOT NULL,
 last_observed_at TIMESTAMPTZ, last_price_changed_at TIMESTAMPTZ,
 last_price_verified_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE evidence_events (
 event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, event_version INTEGER NOT NULL DEFAULT 1,
 scope JSONB NOT NULL, observed_at TIMESTAMPTZ, ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 source_code TEXT NOT NULL, actor_id TEXT, payload JSONB NOT NULL,
 external_event_id TEXT, correlation_id TEXT, consent JSONB,
 UNIQUE(source_code,external_event_id)
);
CREATE INDEX idx_evidence_scope_gin ON evidence_events USING GIN (scope);
CREATE INDEX idx_evidence_observed ON evidence_events(observed_at DESC);
CREATE TABLE inquiries (
 inquiry_id TEXT PRIMARY KEY, branch_id TEXT NOT NULL REFERENCES shop_branches(branch_id),
 offer_id TEXT NOT NULL, offer_version BIGINT, sku_id TEXT NOT NULL, channel TEXT NOT NULL,
 question_scope JSONB NOT NULL, status TEXT NOT NULL DEFAULT 'created',
 dedupe_key TEXT NOT NULL UNIQUE, requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 deadline_at TIMESTAMPTZ NOT NULL, policy_version TEXT NOT NULL, selection_probability DOUBLE PRECISION
);
CREATE TABLE inquiry_subscribers (
 inquiry_id TEXT NOT NULL REFERENCES inquiries(inquiry_id), subscriber_token TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(inquiry_id, subscriber_token)
);
CREATE TABLE inquiry_delivery_attempts (
 attempt_id TEXT PRIMARY KEY, inquiry_id TEXT NOT NULL REFERENCES inquiries(inquiry_id),
 device_id TEXT, provider TEXT NOT NULL, status TEXT NOT NULL,
 queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), provider_accepted_at TIMESTAMPTZ,
 device_received_at TIMESTAMPTZ, opened_at TIMESTAMPTZ, failure_reason TEXT
);
CREATE TABLE inquiry_responses (
 response_id TEXT PRIMARY KEY, inquiry_id TEXT NOT NULL REFERENCES inquiries(inquiry_id),
 actor_id TEXT NOT NULL, offer_version BIGINT, observed_at TIMESTAMPTZ,
 ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), status TEXT NOT NULL,
 scope JSONB NOT NULL, answer JSONB NOT NULL
);
CREATE TABLE feedback_cases (
 case_id TEXT PRIMARY KEY, branch_id TEXT, offer_id TEXT, offer_version BIGINT,
 sku_id TEXT, visit_at TIMESTAMPTZ, opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 case_status TEXT NOT NULL DEFAULT 'received', outcome TEXT NOT NULL DEFAULT 'not_yet_determined',
 issue_type TEXT NOT NULL, reporter_token TEXT, privacy_flags JSONB DEFAULT '{}'
);
CREATE TABLE feedback_case_events (
 case_event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES feedback_cases(case_id),
 event_type TEXT NOT NULL, actor_role TEXT NOT NULL, observed_at TIMESTAMPTZ,
 recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), payload JSONB NOT NULL
);
CREATE TABLE external_trust_evidence (
 trust_evidence_id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, branch_id TEXT,
 source_name TEXT NOT NULL, scope TEXT NOT NULL, verified_at TIMESTAMPTZ,
 expires_at TIMESTAMPTZ, verification_method TEXT, raw_evidence JSONB
);
CREATE TABLE predictions (
 prediction_id TEXT PRIMARY KEY, offer_id TEXT NOT NULL, offer_version BIGINT,
 branch_id TEXT, sku_id TEXT, prediction_at TIMESTAMPTZ NOT NULL,
 target_event TEXT NOT NULL, target_time TIMESTAMPTZ, probability DOUBLE PRECISION,
 uncertainty JSONB, model_version TEXT NOT NULL, evidence_quality TEXT NOT NULL,
 reason_codes JSONB NOT NULL, CONSTRAINT prob_in_range CHECK (probability IS NULL OR (probability >= 0 AND probability <= 1))
);
CREATE TABLE policy_decisions (
 decision_id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 scope JSONB NOT NULL, action_code TEXT NOT NULL, reason_codes JSONB NOT NULL,
 policy_version TEXT NOT NULL, selection_probability DOUBLE PRECISION,
 expected_benefit NUMERIC, expected_cost NUMERIC
);
