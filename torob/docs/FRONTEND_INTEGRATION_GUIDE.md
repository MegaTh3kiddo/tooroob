# Torob Intelligence Engine — Frontend Integration Guide (API Contract V1)

**Contract Status:** Frozen (Backend V1)  
**API Prefix:** `/api/v1`  
**OpenAPI Specification:** [`/openapi.json`](file:///root/starcoach-hack/torob/data/openapi.json)  
**Swagger UI:** `http://localhost:8001/docs`  
**Target Clients:** Web App, Mobile Frontend, Mini-Apps  

---

## 1. Quickstart & Client Configuration

### Base URLs:
- **Local Development:** `http://localhost:8001` (or `http://127.0.0.1:8001`)
- **Health Check:** `GET /api/v1/health`
- **Documentation:** `GET /docs` (Interactive Swagger UI)

### Global Request Headers:
All frontend HTTP requests should include standard content headers and optional tracing/auth headers:

```http
Content-Type: application/json
Accept: application/json
X-Correlation-ID: req_abc123xyz   # Optional: Client-generated UUID for distributed request tracing
X-User-Role: customer            # Role: customer | seller | operator | admin (default: public)
X-User-ID: cust_987654           # Optional: User identifier or anonymized customer session ID
X-Shop-Id: shp_d9a17ad60b0f      # Required ONLY for authenticated seller actions
```

### CORS Behavior:
The backend explicitly permits cross-origin requests from the following development origins with full cookie/credential support:
- `http://localhost:3000` (Next.js / React)
- `http://localhost:5173` (Vite)
- `http://localhost:8080` (Vue / Webpack)
- Custom origins configured via `TOROB_CORS_ORIGINS` in `.env`.

---

## 2. Authentication & Role-Based Access Control (RBAC)

The Torob Intelligence backend uses lightweight, header-based RBAC suitable for API Gateways and micro-frontends:

| Role (`X-User-Role`) | Permissions | Typical Caller |
| :--- | :--- | :--- |
| `public` *(default)* | Read-only catalogue search, price assessment, public reliability, visit feasibility | Anonymous shoppers, guest web traffic |
| `customer` | Create assistant chat sessions, plan routes, submit visit feedback & reports | Logged-in buyers, mobile app users |
| `seller` | View shop-specific inquiry inbox, submit stock/price confirmations | Shop merchants, seller dashboard |
| `operator` / `admin` | Resolve disputes, inspect audit ledger, adjust priors, run policy simulations | Torob internal back-office & operations |

> [!NOTE]
> If `X-User-Role` is omitted, the request defaults to `public`. Any endpoint requiring elevated permissions will return `403 Forbidden` if the role is insufficient. Supplying an unrecognized role returns `400 Bad Request`.

---

## 3. Core API Endpoints & Request/Response Contracts

### 3.1. Catalogue Search & Details

#### `GET /api/v1/products`
Search catalogue items with Persian full-text and brand filters.

- **Query Parameters:**
  - `q`: Search query string (e.g., `کابل`, `سامسونگ`, `لپ‌تاپ`)
  - `category`: Category filter (optional)
  - `brand`: Brand name filter (optional)
  - `page`: Page index (default: `1`)
  - `limit`: Items per page (default: `20`, max: `100`)

```json
// Response: 200 OK
{
  "items": [
    {
      "product_id": "product_af3172caa21dd9a3e40e6349",
      "persian_title": "کوپلر برنجی - اتصال دهنده میله ارت - آچارخور سایز 16",
      "brand_name": "نامشخص",
      "category_name": "اتصالات صنعتی",
      "model": "16",
      "image_urls": [],
      "specs": {"size": "16"}
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

#### `GET /api/v1/products/{product_id}/offers`
Retrieve all current shop listings for a given product.

```json
// Response: 200 OK
[
  {
    "offer_id": "offer_98512b2127469a2d20a64b3b",
    "product_id": "product_af3172caa21dd9a3e40e6349",
    "shop_id": "shop_d9a17ad60b0fd5c15bbe2f0a",
    "price_toman": 610000.0,
    "last_price_changed_at": "2026-10-15T10:00:00Z",
    "seller_title": "کوپلر برنجی سایز ۱۶ اصلی",
    "warranty": "اصالت کالا",
    "description": "موجود در انبار لاله زار"
  }
]
```

---

### 3.2. Price Assessment & Shop Reliability

#### `GET /api/v1/offers/{offer_id}/assessment`
Runs real-time anomaly detection, Leave-One-Shop-Out peer comparisons, and stock survival heuristics.

```json
// Response: 200 OK
{
  "offer_id": "offer_98512b2127469a2d20a64b3b",
  "product_id": "product_af3172caa21dd9a3e40e6349",
  "shop_id": "shop_d9a17ad60b0fd5c15bbe2f0a",
  "price_assessment": {
    "status": "valid_estimate",
    "price_toman": 610000.0,
    "reference_peer_price": 630000.0,
    "peer_shops_count": 4,
    "price_deviation_ratio": 0.968,
    "risk_score": 10,
    "risk_band": "low",
    "risk_score_type": "heuristic",
    "calibrated_probability": null,
    "reasons": ["قیمت با رقبای هم‌تراز در بازار همخوانی دارد"],
    "evidence_quality": "moderate"
  },
  "stock_assessment": {
    "status": "in_store_sellable",
    "survival_probability_at_arrival": 0.92,
    "is_calibrated": false,
    "last_verified_at": "2026-10-23T08:30:00Z",
    "quantity_bucket": "gt_5",
    "reasons": ["موجودی فیزیکی در فروشگاه تایید شده است"],
    "evidence_quality": "high"
  },
  "shop_reliability": {
    "shop_id": "shop_d9a17ad60b0fd5c15bbe2f0a",
    "composite_reliability_score": 0.88,
    "dimensions": {
      "price_fidelity": 0.92,
      "stock_accuracy": 0.86,
      "business_hours": 0.95
    },
    "observation_count": 18,
    "reasons": ["فروشگاه دارای سابقه پایدار تایید قیمت است"],
    "evidence_quality": "moderate"
  },
  "recommended_inquiry": null
}
```

#### `GET /api/v1/shops/{shop_id}/reliability`
Detailed Bayesian shrinkage reliability breakdown across all trust dimensions.

```json
// Response: 200 OK
{
  "shop_id": "shop_d9a17ad60b0fd5c15bbe2f0a",
  "composite_reliability_score": 0.88,
  "confidence_tier": "moderate",
  "dimensions": {
    "price_fidelity": 0.92,
    "stock_accuracy": 0.86,
    "business_hours": 0.95,
    "fulfillment_quality": 0.84
  },
  "credible_intervals": {
    "composite": [0.78, 0.94],
    "price_fidelity": [0.82, 0.97]
  },
  "observation_count": 18,
  "effective_sample_size": 14.2,
  "risk_factors": []
}
```

---

### 3.3. AI Shopping Assistant (Conversational Advisor)

The AI Shopping Assistant maintains persistent multi-turn conversations, extracts implicit customer preferences, detects shopping intents, and returns structured purchase recommendations.

#### `POST /api/v1/assistant/sessions`
Initializes a new shopping session.

```json
// Request Body
{
  "user_id": "cust_12345",
  "initial_message": "یه لپ‌تاپ اداری میخوام تا ۳۰ میلیون تومان"
}

// Response: 200 OK
{
  "session_id": "sess_8c7f91a2b0e4",
  "user_id": "cust_12345",
  "created_at": "2026-10-23T18:00:00Z",
  "expires_at": "2026-10-23T19:00:00Z",
  "initial_reply": "چندین گزینه مناسب اداری در این بازه قیمتی در کاتالوگ موجود است..."
}
```

#### `POST /api/v1/assistant/sessions/{session_id}/messages`
Sends user message, performs preference revision, and returns structured recommendations.

```json
// Request Body
{
  "message": "بودجه رو تا ۵۰ میلیون افزایش بده، برند ایسوس ترجیحمه"
}

// Response: 200 OK
{
  "session_id": "sess_8c7f91a2b0e4",
  "reply_text": "بودجه شما تا سقف ۵۰ میلیون تومان به‌روزرسانی شد و گزینه‌های منتخب برند ایسوس فیلتر شدند.",
  "detected_intent": "preference_refinement",
  "active_clarification": null,
  "constraints": {
    "budget_min_toman": null,
    "budget_max_toman": 50000000.0,
    "budget_is_strict": true,
    "target_brand": "Asus",
    "target_product_title": "لپ‌تاپ",
    "color": null,
    "storage": null,
    "condition": "new",
    "preferred_shopping_mode": "any"
  },
  "recommendations": {
    "total_candidates_found": 8,
    "top_recommendations": [
      {
        "product_id": "product_asus_vivobook_15",
        "product_title": "لپ تاپ ۱۵.۶ اینچی ایسوس مدل Vivobook 15",
        "price_toman": 44500000.0,
        "shop_id": "shop_3f93a30a9e66c6dece07cdff",
        "shop_name": "فرورا رویس",
        "composite_score": 0.89,
        "recommendation_reasons": ["تطابق کامل با بودجه ۵۰ میلیون", "کیفیت ساخت و پردازنده مناسب کارهای اداری"]
      }
    ],
    "trade_off_explanation": "مدل Vivobook 15 بالاترین ارزش خرید را نسبت به قیمت در بازه اداری دارد."
  },
  "proposed_actions": [
    {
      "action_type": "view_product",
      "label": "مشاهده مشخصات Vivobook 15",
      "target_id": "product_asus_vivobook_15"
    }
  ]
}
```

---

### 3.4. Contextual Shopping Plans

#### `POST /api/v1/shopping-plans/on-route`
Calculates optimal stop along travel path, separating driving detour from dwell time.

```json
// Request Body
{
  "origin_lat": 35.7200,
  "origin_lon": 51.3350,
  "dest_lat": 35.8050,
  "dest_lon": 51.4270,
  "product_query": "SSD",
  "corridor_width_km": 8.0,
  "max_detour_minutes": 20.0
}

// Response: 200 OK
{
  "is_feasible": true,
  "baseline_distance_km": 14.2,
  "baseline_duration_minutes": 28.5,
  "recommended_stops": [
    {
      "shop_id": "shop_51d0c1a6edf81ba759726bab",
      "shop_name": "موبایل تخت جمشید",
      "lat": 35.6953,
      "lon": 51.4107,
      "detour_minutes": 4.5,
      "dwell_minutes": 10.0,
      "total_additional_journey_minutes": 14.5,
      "offered_price_toman": 4850000.0,
      "is_open_at_arrival": true,
      "routing_quality": "synthetic_road_graph",
      "is_detour_verified": false
    }
  ],
  "warnings": ["زمان‌های سفر بر اساس تخمین ترافیک شریانی شهر تهران محاسبه شده‌اند."]
}
```

#### `POST /api/v1/shopping-plans/basket`
Optimizes multi-item baskets across 1 or more shops with honest partial coverage.

```json
// Request Body
{
  "basket_queries": ["مانیتور", "کیبورد", "ماوس"],
  "max_stops": 2,
  "require_single_store": false
}

// Response: 200 OK
[
  {
    "plan_id": "plan_9f8e7d6c5b4a",
    "strategy": "lowest_total_cost",
    "strategy_label_persian": "کمترین هزینه کل سبد",
    "stores": [
      {
        "shop_id": "shop_3f93a30a9e66c6dece07cdff",
        "shop_name": "فرورا رویس",
        "items_covered_count": 2,
        "total_items_requested": 3,
        "matched_items": [
          {"query": "مانیتور", "matched_product_title": "مانیتور ۲۴ اینچ", "price_toman": 8500000.0},
          {"query": "کیبورد", "matched_product_title": "کیبورد لاجیتک K120", "price_toman": 850000.0}
        ],
        "missing_items": ["ماوس"],
        "is_total_price_complete": true
      },
      {
        "shop_id": "shop_51d0c1a6edf81ba759726bab",
        "shop_name": "موبایل تخت جمشید",
        "items_covered_count": 1,
        "total_items_requested": 3,
        "matched_items": [
          {"query": "ماوس", "matched_product_title": "ماوس گیمینگ", "price_toman": 650000.0}
        ],
        "missing_items": ["مانیتور", "کیبورد"],
        "is_total_price_complete": true
      }
    ],
    "total_product_cost_toman": 10000000.0,
    "is_total_price_complete": true,
    "total_stops": 2,
    "all_items_covered": true,
    "missing_items": [],
    "guarantee_status": "complete_catalog_coverage_unverified_stock",
    "composite_score": 0.88,
    "trade_off_explanation": "تامین کامل سبد با دو توقف در خیابان انقلاب. مجموع قیمت ۱۰,۰۰۰,۰۰۰ تومان."
  }
]
```

---

### 3.5. Customer Feedback & Dispute Review

#### `POST /api/v1/feedback`
Submits report of price discrepancy, store closed, or successful purchase.

```json
// Request Body
{
  "shop_id": "shop_3f93a30a9e66c6dece07cdff",
  "issue_type": "price_mismatch",
  "offer_id": "offer_98512b2127469a2d20a64b3b",
  "notes": "قیمت ثبت‌شده ۶۱۰ هزار تومان بود ولی در فروشگاه ۶۹۰ هزار تومان اعلام شد."
}

// Response: 201 Created
{
  "case_id": "case_1b2c3d4e5f6a",
  "shop_id": "shop_3f93a30a9e66c6dece07cdff",
  "issue_type": "price_mismatch",
  "case_status": "triaged",
  "outcome": "not_yet_determined",
  "opened_at": "2026-10-23T18:10:00Z",
  "notes": "قیمت ثبت‌شده ۶۱۰ هزار تومان بود ولی در فروشگاه ۶۹۰ هزار تومان اعلام شد."
}
```

---

## 4. Key Enums & Value Standards

### Price Assessment Statuses:
- `valid_estimate`: Reliable price estimate matching market peers.
- `currency_mismatch_suspect`: 10x or 100x discrepancy indicating Rial/Toman input error.
- `peer_deviation_high`: Price significantly higher than peers ($> 3\times$ median).
- `peer_deviation_low`: Price significantly lower than peers ($< 0.33\times$ median).
- `sentinel_anomaly`: Dummy placeholder price ($0$ or $1$ Toman).
- `missing_price`: Null, empty, or unparseable price value.

### Stock States:
- `in_store_sellable`: Confirmed physical stock ready for purchase.
- `in_other_warehouse`: Available in central warehouse (same-day or next-day transfer).
- `supplier_available`: Available through distributor; requires ordering.
- `out_of_stock`: Sold out.
- `unknown`: Stock status unverified.

### Risk Bands:
- `critical`: Risk score $80\text{–}100$ (High likelihood of customer disappointment).
- `high`: Risk score $60\text{–}79$.
- `medium`: Risk score $30\text{–}59$.
- `low`: Risk score $0\text{–}29$ (Safe to visit/purchase).

---

## 5. Standard Error Responses

All non-2xx responses conform to standard FastAPI error structures:

```json
// 400 Bad Request
{
  "detail": "Invalid X-User-Role: 'superman'. Allowed: public, customer, seller, operator, admin"
}

// 403 Forbidden
{
  "detail": "Forbidden: Administrative or Operator role required for this action"
}

// 404 Not Found
{
  "detail": "Product product_invalid_xyz not found"
}

// 422 Unprocessable Entity (Validation Error)
{
  "detail": [
    {
      "loc": ["body", "basket_queries"],
      "msg": "List should have at least 1 item after validation, not 0",
      "type": "too_short"
    }
  ]
}
```
