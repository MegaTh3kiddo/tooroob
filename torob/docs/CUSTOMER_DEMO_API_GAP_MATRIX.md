# Customer Demo & Merchant Android Backend API Gap Matrix

**Document Classification:** Architecture & API Gap Analysis Matrix  
**System:** Torob Intelligence Engine (Unified Multi-App Platform)  
**Target Clients:**  
1. **Customer Static Demo UI:** [`static-ui-ref/`](file:///root/starcoach-hack/trb-ui/static-ui-ref/) (`index.html`, `js/app.js`, `js/agent.js`, `js/plan.js`, `js/account.js`, `js/map.js`)
2. **Merchant Native Android App:** Kotlin Retrofit Client ([`SellerApiService.kt`](file:///root/starcoach-hack/torob_merchant_app/android/app/src/main/java/ir/torob/seller/data/remote/SellerApiService.kt), [`Models.kt`](file:///root/starcoach-hack/torob_merchant_app/android/app/src/main/java/ir/torob/seller/data/model/Models.kt), [`SellerFirebaseMessagingService.kt`](file:///root/starcoach-hack/torob_merchant_app/android/app/src/main/java/ir/torob/seller/service/SellerFirebaseMessagingService.kt))

---

## 1. Executive Overview

This matrix maps every client capability across the Customer Frontend Demo and the Merchant Native Android Application to the unified Torob Intelligence Engine backend. It verifies that zero client code changes are required: the backend conforms exactly to existing client contracts, Retrofit interfaces, DTO fields, and UI expectations.

---

## 2. Customer Demo Frontend (`static-ui-ref`) API Gap Analysis Matrix

| UI Component / View | Client Action / Trigger | Frontend Script Reference | Backend Target Route | HTTP Method | Implementation Status | Request / Response Payload Specification | Persian / Business Logic Guarantee |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent View (`#agent`)** | Send message to TorobChat assistant | `js/agent.js: sendMessage()` | `/api/v1/assistant/chat` | `POST` | Existing (Verified) | Request: `{session_id, user_message}`<br>Response: `{assistant_response, intent, recommendations, clarification}` | Full Persian text understanding, intent extraction, and recommendation explanation. |
| **Agent View (`#agent`)** | List historical chat sessions | `js/account.js: clearHistory()` | `/api/v1/assistant/sessions` | `GET` | **NEW** (Customer Demo Parity) | Query: `?customer_id=...`<br>Response: `List[{session_id, created_at, last_message, intent}]` | Enables chat history persistence and resumption across sessions. |
| **List View (`#list`)** | Search products with Persian text & filters | `js/app.js: renderList()` | `/api/v1/products` | `GET` | Existing (Verified) | Query: `?query=...&page=...&page_size=...`<br>Response: `ProductSearchResult` with `items` and pagination | DuckDB full-text search with Persian character normalization. |
| **List View (`#list`)** | View offers & seller prices for product | `js/app.js: renderOffers()` | `/api/v1/products/{product_id}/offers` | `GET` | Existing (Verified) | Path: `product_id`<br>Response: `List[OfferDetail]` with shop metadata and warranty | Returns real-time catalogue listings sorted by total cost or distance. |
| **Map View (`#map`)** | Bounding-box / radius store discovery | `js/map.js: updateBounds()`, `js/app.js: searchStores()` | `/api/v1/map/stores` | `GET` | **NEW** (Customer Demo Parity) | Query: `?min_lat=...&max_lat=...&min_lon=...&max_lon=...` or `?center_lat=...&center_lon=...&radius_km=...`<br>Response: `List[{shop_id, shop_name, address, phone, lat, lon, is_open, rating, active_offers_count}]` | Provides geo-coordinates and open/close status for Leaflet map pins. |
| **Inquiries Inbox (`#inq`)** | View customer inquiry inbox & status | `js/app.js: renderInqs()`, `inqBadge()` | `/api/v1/customer/inquiries` | `GET` | **NEW** (Customer Demo Parity) | Query: `?customer_id=...&status=...`<br>Response: `List[{inquiry_id, shop_id, shop_name, product_title, recorded_price_toman, offered_price_toman, is_in_stock, status, created_at, expires_at, remaining_seconds, response_notes}]` | Shows live countdown and merchant responses (`ACTIVE`, `ANSWERED`, `OUT_OF_STOCK`, `EXPIRED`, `DECLINED`). |
| **Inquiries Inbox (`#inq`)** | Dispatch new customer price/stock inquiry | `js/app.js: openCallDlg()`, `js/agent.js` | `/api/v1/inquiries` | `POST` | Existing & Merged | Request: `{shop_id, product_id, inquiry_type, user_note, customer_name, customer_phone}`<br>Response: `{inquiry_id, tracking_code, status, expires_at}` | Emits real-time push to merchant Android device and registers SLA timeline. |
| **Saved Plan Tab (`#tabPlan`)** | Retrieve saved shopping plan & checklist | `js/plan.js: load()`, `js/app.js: renderPlan()` | `/api/v1/customer/saved-plans` | `GET` | **NEW** (Customer Demo Parity) | Query: `?customer_id=...`<br>Response: `List[{saved_plan_id, plan_id, title, stops, mode, depart_time, created_at}]` | Persists stops: `{shop_id, categories, done}` for customer offline checklists. |
| **Saved Plan Tab (`#tabPlan`)** | Save / update shopping plan itinerary | `js/plan.js: save()` | `/api/v1/customer/saved-plans` | `POST` | **NEW** (Customer Demo Parity) | Request: `{customer_id, plan_id, title, stops, mode, depart_time}`<br>Response: `{saved_plan_id, status: 'saved'}` | Full plan persistence with scheduling mode (`smart`, `near`, `closing`). |
| **Saved Plan Tab (`#tabPlan`)** | Toggle stop completion status (`done`) | `js/plan.js: find().done = true` | `/api/v1/customer/saved-plans/{id}/stops/{stop_id}/status` | `PATCH` | **NEW** (Customer Demo Parity) | Request: `{done: boolean}`<br>Response: `{stop_id, done: boolean, updated_at}` | Allows customer to check off stores visited during shopping trip. |
| **On-Route Route Tab (`#tabResults`)** | Calculate detour shopping along travel route | `js/app.js: calcOnRoute()` | `/api/v1/shopping-plans/on-route` | `POST` | Existing (Verified) | Request: `{origin, destination, product_ids, max_detour_minutes, travel_mode}`<br>Response: `OnRouteShoppingPlan` | Exact polyline detour calculations with independent stop timing. |
| **Multi-Store Basket (`#tabResults`)** | Optimize basket across multiple stores | `js/app.js: optimizeBasket()` | `/api/v1/shopping-plans/basket` | `POST` | Existing (Verified) | Request: `{product_ids, origin, max_stops, strategy}`<br>Response: `BasketOptimizationPlan` | Finds minimum-cost store combination with verified in-stock certainty. |
| **Store Comparison Dialog (`#cmpDlg`)** | Side-by-side store multi-attribute compare | `js/app.js: openCompare()`, `offerCmpData()` | `/api/v1/catalog/compare-stores` | `POST` | **NEW** (Customer Demo Parity) | Request: `{shop_ids: [...], product_id: ...}`<br>Response: `List[{shop_id, shop_name, price_toman, stock_confidence, travel_minutes, reliability_score, badges}]` | Multi-criteria evaluation comparing price, distance, stock, and reputation. |
| **Account Dialog (`#acctDlg`)** | Fetch customer profile & preferences | `js/account.js: loadProfile()` | `/api/v1/customer/profile` | `GET` | **NEW** (Customer Demo Parity) | Query: `?customer_id=...`<br>Response: `{customer_id, display_name, phone, email, preferred_city, default_travel_mode, plan_tier}` | Defaults to demo customer profile with persistent server-side preferences. |
| **Account Dialog (`#acctDlg`)** | Update customer profile & preferences | `js/account.js: saveProfile()` | `/api/v1/customer/profile` | `PUT` | **NEW** (Customer Demo Parity) | Request: `{display_name, phone, email, preferred_city, default_travel_mode}`<br>Response: `CustomerProfileDto` | Persists user preferred city and travel mode across device sessions. |
| **Account Dialog (`#acctDlg`)** | Submit customer feedback / support ticket | `js/account.js: afSupport` | `/api/v1/customer/support` | `POST` | **NEW** (Customer Demo Parity) | Request: `{customer_id, ticket_type, subject, description, contact_info}`<br>Response: `{ticket_id, status: 'received', message}` | Direct channel for user complaints, bug reports, and seller reviews. |
| **Report Dialog (`#reportDlg`)** | Report price discrepancy or merchant fault | `js/app.js: submitReport()` | `/api/v1/feedback/cases` | `POST` | Existing (Verified) | Request: `{shop_id, offer_id, issue_type, notes}`<br>Response: `{case_id, case_status, outcome}` | Creates formal feedback case in central ledger for dispute evaluation. |

---

## 3. Merchant Native Android App (`torob_merchant_app`) API Contract Matrix

The Native Android App interacts via Retrofit 2 (`ir.torob.seller.data.remote.SellerApiService`). Base URL configured in Android is `http://127.0.0.1:8080/api/` with endpoints prefixed by `seller/...`. The central backend mounts these routes at both `/api/seller/...` and `/seller/...` for compatibility.

| Retrofit Method | HTTP Path | Parameters / Body DTO | Response DTO | Implemented Handler in Central Backend | Backend Operational Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `requestOtp` | `POST seller/auth/request-otp` | `RequestOtpRequest(phone_number)` | `RequestOtpResponse(success, message, demo_otp)` | `endpoints_seller.py: request_otp` | Validates Iranian mobile/landline. Generates 5-min OTP. Returns demo OTP `123456` in mock mode. |
| `verifyOtp` | `POST seller/auth/verify-otp` | `VerifyOtpRequest(phone_number, otp_code)` | `TokenResponse(access_token, token_type, seller)` | `endpoints_seller.py: verify_otp` | Checks OTP code. Auto-resolves/provisions seller record. Issues bearer token `token_{seller_id}`. |
| `getMe` | `GET seller/auth/me` | Header: `Authorization: Bearer ...` | `SellerDto(seller_id, phone, shop_id, full_name, is_active)` | `endpoints_seller.py: get_me` | Resolves seller from header. Returns identity and shop association. |
| `getShopProfile` | `GET seller/shop` | Header: `Authorization: Bearer ...` | `ShopDto(shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, ...)` | `endpoints_seller.py: get_shop_profile` | Computes dynamic open/close state based on Asia/Tehran clock and holiday setting. |
| `updateShopProfile` | `PUT seller/shop` | `ShopUpdateDto(is_open, accept_inquiries, holiday_mode, voice_reminders_enabled)` | `ShopDto(...)` | `endpoints_seller.py: update_shop_profile` | Direct toggle for operational flags (`is_open`, `holiday_mode`). Rejects direct edits to general info. |
| `toggleShopStatus` | `POST seller/shop/toggle-status` | Header: `Authorization: Bearer ...` | `ShopDto(...)` | `endpoints_seller.py: toggle_shop_status` | One-touch toggle for store open/closed state. |
| `submitChangeRequest` | `POST seller/shop/change-requests` | `ShopChangeRequestCreateDto(requested_shop_name, requested_phone, requested_address, ...)` | `ShopChangeRequestDto(request_id, status: 'PENDING', ...)` | `endpoints_seller.py: submit_change_request` | Records profile change request into `shop_change_requests` for operator audit. |
| `getLatestChangeRequest` | `GET seller/shop/change-requests/latest` | Header: `Authorization: Bearer ...` | `ShopChangeRequestDto(...)` | `endpoints_seller.py: get_latest_change_request` | Returns newest submitted change request and review status (`PENDING`, `APPROVED`, `REJECTED`). |
| `getInquiries` | `GET seller/inquiries` | Query: `status: Optional[str]` | `List[InquiryDto]` | `endpoints_seller.py: list_inquiries` | Filters inquiries by status (`ACTIVE`, `ANSWERED`, `OUT_OF_STOCK`, `EXPIRED`, `HISTORY`). Auto-expires overdue items. |
| `getInquiryDetail` | `GET seller/inquiries/{id}` | Path: `id` | `InquiryDto` | `endpoints_seller.py: get_inquiry_detail` | Returns complete inquiry details, customer name, notes, and remaining response seconds. |
| `submitResponse` | `POST seller/inquiries/{id}/respond` | `InquiryResponseRequest(client_response_id, offered_price_toman, is_in_stock, stock_count, notes, ...)` | `InquiryResponseDto(...)` | `endpoints_seller.py: respond_to_inquiry` | **Idempotent.** Records merchant answer. Updates `inquiries`, `inquiry_responses`, and appends evidence event into ledger. Accurately preserves `stock_count = 0`. |
| `batchSyncResponses` | `POST seller/inquiries/batch-sync`<br>`POST seller/sync/batch-responses` | `BatchSyncRequest(items: List[BatchSyncItem])` | `BatchSyncResponse(total_processed, synced_count, duplicate_count, results)` | `endpoints_seller.py: batch_sync_responses` | Processes offline queue from Android Room DB. Safely deduplicates using `client_response_id`. |
| `registerPushToken` | `POST seller/push/register-token` | `PushTokenRegisterRequest(fcm_token, device_model, os_version, app_version)` | `Map[String, Any]` (`success: True`) | `endpoints_seller.py: register_push_token` | Saves device FCM token into `seller_devices` for push delivery. |
| `updatePushPreferences` | `PUT seller/push/preferences` | `PushPreferenceRequest(notifications_enabled)` | `Map[String, Any]` (`success: True`) | `endpoints_seller.py: update_push_preferences` | Updates device notification toggle in database. |
| `getStoreMetrics` | `GET seller/metrics` | Header: `Authorization: Bearer ...` | `MetricsDto(shop_id, total, answered, expired, active, response_rate_percent, avg_response_time_seconds, ...)` | `endpoints_seller.py: get_store_metrics` | Aggregates real response rate and average response latency formatted in Persian digits. |

---

## 4. FCM Push Notification Payload Contract

The Android FCM receiver (`SellerFirebaseMessagingService.kt`) requires the following payload fields:

```json
{
  "message": {
    "token": "<FCM_DEVICE_TOKEN>",
    "notification": {
      "title": "استعلام جدید در ترب",
      "body": "یک مشتری منتظر استعلام قیمت و موجودی است."
    },
    "data": {
      "inquiry_id": "inq_99a8b12f",
      "notification_type": "URGENT_CALL",
      "title": "تماس فوری استعلام ترب",
      "body": "فقط ۲ دقیقه تا پایان مهلت پاسخ باقی مانده است!",
      "duration_seconds": "120",
      "product_title": "گوشی سامسونگ گلکسی S24"
    },
    "android": {
      "priority": "HIGH"
    }
  }
}
```

### Action Mappings in Android:
- `notification_type == "INITIAL_INQUIRY"`: Displays high-priority heads-up notification with sound and vibration.
- `notification_type == "REMINDER_5MIN"`: Displays 5-minute reminder alert notification.
- `notification_type == "URGENT_CALL"`: Starts foreground ringing alarm (`InquiryAlertService.ACTION_START_ALERT`) with full-screen calling UI.
- `notification_type == "EXPIRATION_ALERT"`: Stops ringing alarm (`InquiryAlertService.ACTION_STOP_ALERT`) and marks inquiry expired.
