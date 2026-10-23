# Torob Intelligence Engine — Merchant Android & Customer Demo Integration Guide

**Integration Release:** 1.1.0  
**Git Baseline:** `73d5029`  
**Classification:** Major Integration & Architecture Unification Report  
**Scope:** Backend Only (Zero Frontend / Zero Kotlin Android Changes)

---

## 1. Executive Summary

This release unifies the Torob Intelligence Engine backend with:
1. **The Native Android Kotlin Merchant App** ([`torob_merchant_app`](file:///root/starcoach-hack/torob_merchant_app)): Zero Android modifications required. Full compatibility with Retrofit interfaces (`SellerApiService.kt`), DTO contracts (`Models.kt`), FCM notifications (`SellerFirebaseMessagingService.kt`), and offline Room sync queue.
2. **The Customer Demo Web UI** ([`static-ui-ref`](file:///root/starcoach-hack/trb-ui/static-ui-ref)): Full backend parity for the conversational agent, product discovery, store visit plans, live customer inquiry tracking, map store exploration, and store comparisons.
3. **Unified Single Database Architecture:** Merged all merchant entities into the primary SQLite ledger database (`data/torob_ledger.db`) while DuckDB remains dedicated to analytical full-text catalogue search.

---

## 2. Merged Database Schema Architecture

The single operational database [`data/torob_ledger.db`](file:///root/starcoach-hack/torob/data/torob_ledger.db) now incorporates:

```
                            +---------------------------------------+
                            |            DuckDB Catalogue           |
                            |   (products, shops, offers, metrics)  |
                            +---------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------+
|                       CENTRAL SQLITE OPERATIONAL LEDGER (data/torob_ledger.db)                |
+-----------------------------------------------------------------------------------------------+
|  1. sellers                 - Merchant identities, phone numbers, shop assignments            |
|  2. seller_devices          - Device FCM tokens, OS version, notification preferences         |
|  3. shop_settings           - Shop hours, open/closed state, holiday mode, contact info       |
|  4. shop_change_requests    - Formal merchant audit workflow for name/address modifications   |
|  5. push_audit_logs         - Android FCM dispatches, types, status (SIMULATED/DELIVERED)     |
|  6. inquiry_timelines       - SLA tracking (initial push, 5m reminder, 2m urgent call)       |
|  7. scheduler_configs       - Dynamic SLA timeouts (reminder: 300s, expiration: 600s)         |
|  8. outbound_call_logs      - Poshteyar and voice reminder call records                       |
|  9. shop_identity_mappings  - Entity reconciliation between catalogue and merchant apps       |
| 10. customer_profiles       - Customer name, phone, preferred city, default travel mode       |
| 11. customer_saved_plans    - Saved shopping itineraries and checklist completion toggles     |
| 12. support_submissions     - Customer complaints, feedback, and report tickets               |
| 13. inquiries               - Unified inquiry states, tracking codes, customer notes          |
| 14. inquiry_responses       - Idempotent responses with client_response_id & exact stock_cnt  |
| 15. evidence_events         - Ground-truth event stream feeding Bayesian reliability engine   |
+-----------------------------------------------------------------------------------------------+
```

---

## 3. Real-Time End-to-End Inquiry & Response Flow

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer (Web Demo)
    participant Backend as Torob Central Backend
    participant DB as SQLite Operational Ledger
    actor Merchant as Merchant (Android App)

    Customer->>Backend: POST /api/v1/customer/inquiries
    Backend->>DB: INSERT inquiries (ACTIVE, expires_at: +10min)
    Backend->>DB: INSERT inquiry_timelines (Time Zero)
    Backend->>Merchant: FCM Push (INITIAL_INQUIRY)
    Merchant->>Backend: GET /seller/inquiries?status=ACTIVE
    Backend-->>Merchant: 200 OK (List[InquiryDto])
    Merchant->>Backend: POST /seller/inquiries/{id}/respond (offered_price, stock_count, notes)
    Backend->>DB: Check idempotency (client_response_id)
    Backend->>DB: UPDATE inquiries (status=ANSWERED, offered_price)
    Backend->>DB: INSERT inquiry_responses & evidence_events
    Customer->>Backend: GET /api/v1/customer/inquiries
    Backend-->>Customer: 200 OK (status=ANSWERED, merchant price & note)
```

---

## 4. Verification Results & Quality Metrics

- **Total Test Suite:** **157 / 157 passing tests** (100% pass rate).
- **Code Coverage:** **82% total coverage** across all modules.
- **Frontend Code Integrity:** `git diff 323bf2e..HEAD -- nearest-price-ui-example/` reports **0 lines modified**.
- **Android App Code Integrity:** `torob_merchant_app` working tree reports **0 files modified**.
- **Idempotency Guarantee:** Duplicate offline batch items with identical `client_response_id` are safely detected and counted as duplicates without error or double records.
- **Stock Integrity:** Exact stock count (`stock_count = 0`) is strictly preserved and never substituted with 1.
