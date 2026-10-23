# Torob AI Shopping Agent & Intelligent Recommendation Backend

## 1. Executive Summary & Architecture

The **Torob AI Shopping Agent** is an evidence-grounded, constraint-aware conversational shopping advisor built directly on top of the Torob Intelligence Engine backend. It translates customer intents, requirements, and budgets into actionable purchase recommendations grounded in real catalog data and multi-dimensional trust evaluations.

### Architectural Philosophy
1. **Strictly Backend-First**: Operates autonomously as a headless API service with zero UI/frontend dependencies.
2. **Evidence-Grounded (Zero Hallucination)**: Never invents products, shops, prices, or artificial certainty. 100% of recommended candidate entities exist in DuckDB catalog storage.
3. **Multi-Turn Context Preservation**: Retains constraints (brand, device type, budget ceiling, variant specs) across turns while allowing dynamic adjustments.
4. **Intelligent Clarification**: Non-rigid question policy bounded by a strict question budget (default max 2) that only interrupts when clarification materially impacts recommendation space.
5. **Deterministic Offline Fallback**: Fully functional without external network access or LLM API keys via `DeterministicFallbackParser`, while supporting optional external OpenAI/Gemini providers when configured.

---

## 2. Agent Component Topology

```
User Query (Persian / English)
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│               ShoppingAgentOrchestrator                     │
│  - Session Retrieval & Isolation (SQLite with TTL)          │
│  - Constraint Extraction & Merging                          │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│  DeterministicFallbackParser │ │     ClarificationPolicy     │
│  - Persian numerals/scales   │ │  - Question budget check    │
│  - Tehran landmark mapping   │ │  - Material impact check    │
│  - Intent classification     │ │  - Skip on exact search     │
└───────────────┬──────────────┘ └─────────────┬───────────────┘
                │                             │
                └──────────────┬──────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     ShoppingRecommender                     │
│  1. Candidate Retrieval (DuckDB Catalog with Synonyms)      │
│  2. Strict Hard-Constraint Enforcement (Budget, Condition)  │
│  3. Multi-Engine Intelligence Evaluation:                   │
│     • Price LOSO Anomaly & Volatility (PricingEngine)       │
│     • Stock Depletion Hazard at Arrival (InventoryEngine)   │
│     • Bayesian Multi-Dimensional Trust (ReliabilityEngine)  │
│     • Travel ETA & Business Hours (Routing / Feasibility)   │
│  4. Deterministic Scoring & Trade-Off Assignment:           │
│     • best_overall | budget_pick | verified_confidence      │
│  5. Grounded Persian Summary & Inquiry Recommendation       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Supported Shopping Intents

| Intent | Code Enum | Trigger & Behavior | Example Query |
| :--- | :--- | :--- | :--- |
| **Exact Product Search** | `exact_search` | Specific flagship/model named. Zero unnecessary clarification; direct ranking. | `گوشی سامسونگ S23 Ultra` |
| **Needs-Based Shopping** | `needs_based` | Requirements stated without budget or specific model. Clarifies budget/workload. | `لپ‌تاپ برای برنامه‌نویسی و هوش مصنوعی` |
| **Budget-Constrained** | `budget_search` | Hard budget ceiling. Strict enforcement; all candidates $\le$ budget. | `گوشی گیمینگ زیر ۳۰ میلیون تومان` |
| **Local Physical Visit** | `local_physical` | Urgent / in-person purchase. Checks Tehran landmark, travel ETA, and store hours. | `کارت گرافیک فوری برای امروز حضوری سمت میدان انقلاب` |
| **Product Comparison** | `product_comparison` | Compares two brands or models. Pools candidates and outputs side-by-side trade-offs. | `مقایسه لپ تاپ ایسوس و لنوو` |
| **Conversational Refinement**| `refinement` | Adjusts previous constraint (e.g., higher budget, preferred RAM/color). Context preserved. | `بودجه رو تا ۸۵ میلیون افزایش بده` |

---

## 4. API Specification (`/api/v1/assistant/*`)

### 4.1 Create Session
- **Endpoint**: `POST /api/v1/assistant/sessions`
- **Request Body**:
  ```json
  {
    "user_id": "buyer_123",
    "initial_message": "سلام، دنبال لپ تاپ برای برنامه نویسی هستم"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "sess_9e86139d273e",
    "user_id": "buyer_123",
    "created_at": "2026-10-23T11:50:00Z",
    "expires_at": "2026-10-25T11:50:00Z",
    "initial_reply": "برای انتخاب بهترین گزینه‌ها، سقف بودجهٔ مد نظرتان چقدر است؟"
  }
  ```

### 4.2 Send Message
- **Endpoint**: `POST /api/v1/assistant/sessions/{session_id}/messages`
- **Headers**: `X-User-Id`, `X-User-Role` (Enforces session isolation; cross-user access returns 403)
- **Request Body**:
  ```json
  {
    "message": "سقف بودجه من حدود ۷۰ میلیون تومان هست"
  }
  ```
- **Response**:
  ```json
  {
    "session_id": "sess_9e86139d273e",
    "reply_text": "نتایج جستجو و ارزیابی شواهد در ترب برای شما:\n\n1. **لپ تاپ HP EliteBook** 🌟 [بهترین انتخاب جامع]...",
    "detected_intent": "needs_based",
    "active_clarification": null,
    "constraints": {
      "budget_max_toman": 70000000.0,
      "target_category": "لپ تاپ و نوت بوک",
      "preferred_specs": {"device_type": "لپ‌تاپ"}
    },
    "recommendations": {
      "intent": "needs_based",
      "total_candidates_found": 15,
      "top_recommendations": [
        {
          "product_id": "product_7647b9de16a9c6c8b5830dcb",
          "product_title": "لپ تاپ HP مدلEliteBook 840 G1",
          "offer_id": "offer_abc123",
          "shop_id": "shop_xyz789",
          "shop_name": "فروشگاه رایانه گستر",
          "price_toman": 25500000.0,
          "reference_market_price": 26000000.0,
          "is_price_anomaly": false,
          "suitability_score": 0.85,
          "shop_reliability_score": 0.82,
          "trade_off_label": "best_overall",
          "pros": ["صرفه‌جویی عالی در بودجه", "فروشگاه دارای امتیاز اعتماد بالا"],
          "cons": [],
          "uncertainty_warnings": []
        }
      ],
      "trade_off_summary": "گزینه پیشنهادی اصلی: «لپ تاپ HP» از فروشگاه «رایانه گستر»...",
      "hard_constraints_satisfied": true
    },
    "proposed_actions": []
  }
  ```

### 4.3 Get Session History & Recommendations
- **Endpoint**: `GET /api/v1/assistant/sessions/{session_id}`
- **Endpoint**: `GET /api/v1/assistant/sessions/{session_id}/recommendations`

---

## 5. Security & Isolation Controls

1. **Session Ownership Enforcement**: Sessions tagged with `user_id` strictly deny read/write access to callers with mismatched `X-User-Id` unless role is `admin` (HTTP 403 Forbidden).
2. **Prompt Injection Sanitization**: Seller titles and free-text descriptions are sanitized via `sanitize_untrusted_text` prior to processing or feeding to external LLMs, replacing malicious instruction jailbreaks with `[REDACTED_SUSPICIOUS_PHRASE]`.
3. **Inquiry Mutation Authorization**: Seller responses to inquiries are validated via `verify_seller_ownership`, blocking unauthorized cross-shop modifications.
4. **Tool Parameter Bounding**: API limits clamped to safe bounds (e.g. maximum 25 items).

---

## 6. Deterministic Evaluation Results (40 Aspects)

The agent evaluation harness (`scripts/evaluate_agent.py`) tests all 40 aspects against real DuckDB and SQLite datasets:

| ID | Evaluation Aspect | Status | Measured Latency | Verification Outcome |
| :---: | :--- | :---: | :---: | :--- |
| **01** | Exact product search | **PASSED** | 165.1 ms | Found exact flagship S23 Ultra offers; 0 unnecessary questions |
| **02** | Needs-based laptop recommendation | **PASSED** | 206.2 ms | Triggered targeted clarification for missing budget/workload |
| **03** | Budget-constrained shopping | **PASSED** | 563.3 ms | Strict 30M budget ceiling enforced with 0 violations |
| **04** | Clarification of missing critical info | **PASSED** | 0.1 ms | Intercepted missing location for physical visit |
| **05** | Avoidance of unnecessary questions | **PASSED** | 0.0 ms | Bypassed clarification when exact model specified |
| **06** | Multi-turn constraint preservation | **PASSED** | 666.4 ms | Preserved Asus brand, laptop type, and budget across turn 2 |
| **07** | Budget updates | **PASSED** | 954.3 ms | Updated budget from 50M to 85M Toman without loss of context |
| **08** | Product comparison | **PASSED** | 376.6 ms | Generated side-by-side trade-off between Asus and Lenovo |
| **09** | No matching candidates | **PASSED** | 140.5 ms | Handled impossible budget gracefully (0 hallucinated products) |
| **10** | Single-seller products | **PASSED** | 3.5 ms | Flagged limited evidence; no artificial peer median claimed |
| **11** | Suspiciously low prices | **PASSED** | 3.6 ms | Detected 0.1x currency mismatch anomaly (RiskBand CRITICAL) |
| **12** | Unknown inventory | **PASSED** | 3.4 ms | Preserved uncertainty: `is_calibrated=False` for unverified stock |
| **13** | Trusted shop with stale stock | **PASSED** | 6.5 ms | High-trust shop penalized for 45-day stale inventory |
| **14** | High-volatility products | **PASSED** | 0.2 ms | Classified path volatility regime as `SHOCKED` with jump counts |
| **15** | Newly launched products | **PASSED** | 0.1 ms | Classified lifecycle stage as `NEWLY_LAUNCHED` / `PRICE_DISCOVERY` |
| **16** | Multi-component compatibility | **PASSED** | 0.1 ms | Variant matcher blocked comparing 128GB with 256GB |
| **17** | Urgent local purchase | **PASSED** | 247.0 ms | Mapped Enqelab landmark to lat/lon; evaluated opening hours |
| **18** | Missing location | **PASSED** | 200.1 ms | Clarification policy prompted user for Tehran neighborhood |
| **19** | Unavailable routing provider | **PASSED** | 3.5 ms | Gracefully fell back to urban distance calculator |
| **20** | Unavailable LLM provider | **PASSED** | 0.2 ms | Deterministic parser operated completely offline |
| **21** | Hallucinated product prevention | **PASSED** | 162.8 ms | 100% of candidate IDs verified in catalog (0.0% hallucination) |
| **22** | Prompt injection inside catalogue | **PASSED** | 0.2 ms | Sanitized untrusted text; stripped injection instructions |
| **23** | Unauthorized inquiry attempts | **PASSED** | 0.0 ms | Enforced shop ownership; blocked cross-shop mutation (403) |
| **24** | Tool execution limits | **PASSED** | 154.0 ms | Clamped query limits to safe bounds |
| **25** | Session isolation & unauthorized access | **PASSED** | 12.1 ms | API rejected foreign user message attempt with 403 Forbidden |
| **26** | Contradictory user preferences | **PASSED** | 148.9 ms | Detected impossible budget/model contradiction (iPhone for 5M) |
| **27** | Persian colloquial requests | **PASSED** | 0.2 ms | Parsed "کار راه‌انداز" and "زیر ۳۰ تومن" as 30M laptop request |
| **28** | Persian numerals & scales | **PASSED** | 0.3 ms | Normalized "۷۰ میلیون" and "۸۵ ملیون" accurately |
| **29** | Product variant ambiguity | **PASSED** | 145.9 ms | Explicitly distinguished storage/RAM variants |
| **30** | Retrieval under mixed Persian/English | **PASSED** | 273.4 ms | Retrieved catalog matches across bilingual queries |
| **31** | PC build basket hardware compatibility | **PASSED** | 0.1 ms | Verified LGA1700 CPU + B760 DDR5 Motherboard + DDR5 RAM |
| **32** | Urban neighborhood spatial grounding | **PASSED** | 0.1 ms | Resolved commercial hubs (Alaeddin, Charsou, Mirdamad, Isfahan) |
| **33** | Contextual budget magnitude disambiguation | **PASSED** | 0.3 ms | Disambiguated accessory 30K from device 30M Toman |
| **34** | Conversational rejection handling | **PASSED** | 1068.8 ms | Blacklisted rejected products and refreshed recommendations |
| **35** | Negative brand exclusion | **PASSED** | 139.8 ms | Extracted "به جز سامسونگ" and filtered 100% of Samsung offers |
| **36** | Technical suitability reasoning | **PASSED** | 287.9 ms | Evaluated CPU tier (i7/Ryzen 7), 16GB+ RAM, and dedicated GPU |
| **37** | Metamorphic budget sensitivity | **PASSED** | 538.1 ms | Monotonic candidate space reduction; 0 higher-priced leaks |
| **38** | Latency breakdown & compute transparency | **PASSED** | 261.1 ms | Verified local deterministic compute distinct from external LLM |
| **39** | Missing spec explicit uncertainty admission | **PASSED** | 1.0 ms | Flagged uncertain_missing_specs rather than false-positive pass |
| **40** | Tool orchestrator safety boundedness | **PASSED** | 302.1 ms | Safely bounded tool calling loop at max_steps=4 |

### Summary Statistics
- **Aspects Evaluated**: 40 / 40
- **Pass Rate**: 100.0%
- **Execution Duration**: 7.04 seconds
- **Average Latency (Deterministic Local Engine)**: 176.0 ms
- **Hallucination Rate**: 0.0%
- **Evidence Grounding Rate**: 100.0%

### Latency Breakdown & Compute Architecture
- **Local In-Memory Compute**: The measured 176.0 ms average latency represents pure local CPU processing: DuckDB analytical joins, SQLite ledger updates, regex normalization, and spatial distance calculation.
- **External LLM Latency Separation**: When external LLM providers (e.g. `gpt-4o-mini`) are enabled via `TOROB_LLM_API_KEY`, network transit and model generation add typical latency of 800 ms - 2,500 ms. The evaluation suite rigorously validates the deterministic engine in isolation to establish deterministic baseline reproducibility.
