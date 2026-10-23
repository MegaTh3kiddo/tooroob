# Torob Intelligence Engine — Comprehensive Traceability & Requirement Audit Matrix

This document provides a complete, requirement-level traceability mapping from the reference design documents (`llm-inspection-for-algo/price_stock_reference/`) to the implementation codebase.

---

## 1. System & Functional Requirement Traceability

| Ref Document | Specific Requirement / Invariant | Implemented In Module | Implementation Status | Test Suite & Verification | Operational Boundary / External Dependency |
|:---|:---|:---|:---:|:---|:---|
| **01_PRD** | Separate physical branch from online shop; distinguish local stock | `src/torob/domain/entities.py`, `src/torob/storage/repository_catalog.py` | ✅ Implemented | `tests/unit/test_storage.py` | Requires physical merchant branch registration. |
| **01_PRD** | User intent differentiation (`BROWSE`, `BUY`, `VISIT`) with loss weights | `src/torob/domain/enums.py`, `src/torob/intelligence/inquiry_policy.py` | ✅ Implemented | `tests/unit/test_voi_and_bayesian_correctness.py` | Clickstream / user session classification. |
| **02_Journeys** | On-route purchasing with detour minutes and dwell time | `src/torob/routing/on_route.py`, `src/torob/routing/distance.py` | ✅ Implemented | `tests/unit/test_on_route.py` | Uses graph routing with fallback to Manhattan/Euclidean. |
| **02_Journeys** | Multi-store basket coverage optimization with shop clustering | `src/torob/intelligence/basket_optimizer.py`, `src/torob/routing/clustering.py` | ✅ Implemented | `tests/unit/test_basket_optimizer.py` | Greedy/branch-and-bound optimization. |
| **03_ALGO_01** | Sentinel price handling (`price == 1`) and 10x currency error (Rial/Toman) | `src/torob/intelligence/pricing.py`, `src/torob/intelligence/market_monitor.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario H) | Deterministic ratio anomaly detection. |
| **03_ALGO_01** | Leave-One-Shop-Out peer price median comparison | `src/torob/intelligence/pricing.py` | ✅ Implemented | `tests/unit/test_intelligence.py` | Requires $\ge 3$ independent peers. |
| **03_ALGO_01** | Single-seller listing protection (no fake competitor medians) | `src/torob/intelligence/market_dynamics.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario F) | Emits `single_seller` warning. |
| **03_ALGO_02** | Multi-state inventory tracking (`in_store`, `reserved`, `preorder`, `unknown`) | `src/torob/domain/enums.py`, `src/torob/intelligence/inventory.py` | ✅ Implemented | `tests/unit/test_intelligence.py` | Time-decay hazard rate. |
| **03_ALGO_02** | Out-of-stock reporting honesty credit (no negative punishment) | `src/torob/intelligence/shop_reliability.py` | ✅ Implemented | `tests/unit/test_deep_engineering.py` | Merchant honesty credit. |
| **03_ALGO_03** | Multi-scale volatility: path log-movement vs net return | `src/torob/intelligence/market_dynamics.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario A) | $\sum \|\ln(P_t / P_{t-1})\|$. |
| **03_ALGO_03** | 7 Product Lifecycle Regimes with 3 distinct novelty timestamps | `src/torob/intelligence/market_dynamics.py`, `src/torob/domain/enums.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario B) | `global_release`, `local_seen`, `system_seen`. |
| **03_ALGO_04** | Multi-dimensional Bayesian shop reliability with Beta-Binomial shrinkage | `src/torob/intelligence/shop_reliability.py` | ✅ Implemented | `tests/unit/test_voi_and_bayesian_correctness.py` | Uses exact Beta quantiles and Kish $N_{\text{eff}}$. |
| **03_ALGO_04** | Continuous temporal evidence decay (60-day half-life) | `src/torob/intelligence/shop_reliability.py` | ✅ Implemented | `tests/unit/test_voi_and_bayesian_correctness.py` | Exponential decay weight $w_i = \exp(-\lambda \Delta t)$. |
| **03_ALGO_05** | Decision-theoretic Value of Information (VoI) in Standard Loss Points | `src/torob/intelligence/inquiry_policy.py` | ✅ Implemented | `tests/unit/test_voi_and_bayesian_correctness.py` | $1 \text{ SLP} \equiv 10,000 \text{ Toman}$; no saturation. |
| **03_ALGO_05** | Controlled audit exploration (5% sampling) with propensity logging | `src/torob/intelligence/inquiry_policy.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario E) | Logs `selection_probability` for IPW debiasing. |
| **03_ALGO_05** | Merchant fatigue protection: quiet hours & daily quotas ($\le 15$/day) | `src/torob/intelligence/inquiry_policy.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario E) | Configurable operational safeguards. |
| **03_ALGO_06** | Strict output isolation: heuristic score vs calibrated probability | `src/torob/domain/assessment.py`, `src/torob/intelligence/calibration.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario A) | `calibrated_probability` is `None` without empirical labels. |
| **03_ALGO_06** | Offline calibration evaluation suite (Brier, Log Loss, ECE) | `src/torob/intelligence/calibration.py` | ✅ Implemented | `tests/unit/test_deep_engineering.py` | Operational evaluation on labeled historical sets. |
| **04_WORK_01** | Inquiry state machine (`created`, `sent`, `delivered`, `answered`, `expired`) | `src/torob/inquiries/service.py`, `src/torob/storage/db.py` | ✅ Implemented | `tests/unit/test_workflows.py` | Transport delivery simulator. |
| **04_WORK_02** | Customer feedback attribution taxonomy & merchant fairness | `src/torob/feedback/service.py` | ✅ Implemented | `tests/unit/test_voi_and_bayesian_correctness.py` | No direct penalty on unverified complaints. |
| **04_WORK_02** | Real-time plan invalidation & adaptive recovery on verified discrepancy | `src/torob/feedback/service.py`, `src/torob/intelligence/plan_lifecycle.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario C) | Degrades plan and triggers candidate replanning. |
| **05_ARCH_01** | Idempotent snapshot ingestion with SHA256 checksums | `src/torob/ingestion/snapshot.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario H) | Handles 300 export limit gracefully. |
| **05_ARCH_02** | Event-driven market monitoring & structured quality alerts | `src/torob/intelligence/market_monitor.py` | ✅ Implemented | `tests/acceptance/test_flywheel_scenarios.py` (Scenario H) | Persists to SQLite `quality_alerts`. |
| **07_DELIV** | Operations Admin CLI toolkit & REST inspection endpoints | `src/torob/cli/admin_toolkit.py`, `src/torob/api/v1/endpoints_admin.py` | ✅ Implemented | `tests/unit/test_deep_engineering.py` | Bearer token protected. |

---

## 2. Edge Case Register Coverage (EC-001 to EC-180 Sampling)

| Edge Case ID | Domain | Specification | Code Implementation | Verification Mechanism |
|:---|:---|:---|:---|:---|
| **EC-001** | `PRICE_FORMAT` | Price = 1 Toman treated as sentinel | `pricing.py:detect_price_anomalies` | Marked as sentinel error; not included in median. |
| **EC-003** | `PRICE_FORMAT` | 10x Rial/Toman denomination error | `market_monitor.py:check_offer_price_anomalies` | Emits `currency_denomination_10x_error` quality alert. |
| **EC-010** | `PRODUCT_MATCH`| Exact variant isolation (128GB vs 256GB) | `normalizer.py:normalize_product` | Variant key hashing enforces strict SKU boundaries. |
| **EC-019** | `PRICE_SERIES` | High path movement with identical net change | `market_dynamics.py:compute_historical_features` | $\sum \|\ln(P_t/P_{t-1})\| > 0.8$ flags price instability. |
| **EC-028** | `LIFECYCLE`    | Day-1 product cold start | `market_dynamics.py:classify_product_lifecycle` | Assigned to `ProductRegime.COLD_START`. |
| **EC-030** | `LIFECYCLE`    | Global release vs local market first seen | `market_dynamics.py` | Uses separate `global_release_at` vs `local_market_first_seen_at`. |
| **EC-037** | `MARKET`       | Single seller listing with no peers | `market_dynamics.py:aggregate_market_reference` | Prohibits inventing fake competitor medians. |
| **EC-046** | `STOCK`        | Low-stock arrival survival | `inventory.py:estimate_survival_probability` | Hazard rate $\lambda$ estimates survival probability at ETA. |
| **EC-080** | `SHOP_TRUST`   | Decayed evidence with fractional weights | `shop_reliability.py:assess_shop_reliability` | Kish effective sample size $N_{\text{eff}} = (\sum w)^2 / \sum w^2$. |
| **EC-095** | `SHOP_TRUST`   | Small sample exact posterior uncertainty | `shop_reliability.py:_update_beta_binomial` | Exact Beta quantiles via `scipy.stats.beta.ppf`. |
| **EC-101** | `INQUIRY`      | Shop quiet hours enforcement (22:00 - 09:00) | `inquiry_policy.py:evaluate_inquiry_decision` | Automatically defers inquiries with `quiet_hours_active`. |
| **EC-105** | `INQUIRY`      | Merchant fatigue daily quota ($\le 15$/day) | `inquiry_policy.py:evaluate_inquiry_decision` | Action becomes `decline_or_defer` on budget exhaustion. |
| **EC-111** | `FEEDBACK`     | Negative complaint without operator audit | `feedback/service.py:submit_customer_feedback` | Prohibits direct penalty; status remains `TRIAGED`. |
| **EC-115** | `FEEDBACK`     | Plan discrepancy propagation | `plan_lifecycle.py:invalidate_plans_for_discrepancy` | Marks active plan `discrepancy_invalidated_replan_required`. |

---

## 3. Real Learning Boundaries & Production Dependencies

1. **Adaptive Bayesian Evidence Projections vs Supervised ML**:
   - The current engine provides **adaptive Bayesian conjugate updating** on structured evidence streams.
   - It updates conjugate Beta posteriors as verified physical observations, operator audits, and seller responses arrive.
   - It is **NOT** a pre-trained offline machine learning model (e.g. XGBoost, Random Forest, or Deep Neural Network) fitted to historical user purchase logs.
   - Calibrated output probabilities remain strictly `None` until empirical outcome labels are observed and verified.

2. **Off-Policy Evaluation via Controlled Exploration**:
   - The 5% exploration audit sampling tags decisions with `selection_trigger="audit_sample"` and logs `selection_probability = 0.05`.
   - This prevents self-reinforcing selection bias and establishes the logging foundation for future Inverse Propensity Weighting (IPW).
   - However, until a real stratified sample of ground-truth audit outcomes is collected by human auditors, policy simulations are evaluated on synthetic benchmarks.

3. **External Integration Dependencies**:
   - Push delivery tracking: Currently simulated via `inquiries/transport_simulator.py`. Production deployment requires integration with FCM / APNS delivery callback webhooks.
   - Street-level road routing: In-memory network and Manhattan/Euclidean fallback available; live production deployment integrates with OSRM or Valhalla routing engines.
   - Merchant dispute resolution: Customer cases are managed via `feedback/service.py`; production requires Torob merchant portal review workflows.
