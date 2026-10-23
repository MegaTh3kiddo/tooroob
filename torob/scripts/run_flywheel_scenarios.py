#!/usr/bin/env python3
"""Standalone Runner for Torob Flywheel Acceptance Scenarios (Scenarios A through H).

Executes Scenarios A through H end-to-end, measuring execution latency,
verifying constraints, printing inspectable outputs, and generating a machine-readable
report at data/flywheel_scenarios_report.json.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

# Ensure source directory is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from fastapi.testclient import TestClient
from torob.api.main import app
from torob.domain.assessment import PriceAssessment, ShopReliabilityAssessment, StockAssessment
from torob.domain.entities import Shop
from torob.domain.enums import (
    CaseOutcome,
    CaseStatus,
    FeedbackIssueType,
    InquiryPriority,
    PriceAssessmentStatus,
    ProductRegime,
    RiskBand,
    StockState,
    UserIntent,
)
from torob.domain.plans import BasketItemMatch, MultiStoreBasketPlan, ShopBasketCoverage
from torob.feedback.service import FeedbackService
from torob.ingestion.loader import ingest_catalog
from torob.ingestion.snapshot import SnapshotIngestionEngine
from torob.intelligence.inquiry_policy import AdaptiveInquiryPolicyEngine
from torob.intelligence.market_dynamics import MarketDynamicsEngine
from torob.intelligence.market_monitor import MarketMonitoringEngine
from torob.intelligence.plan_lifecycle import ShoppingPlanLifecycleManager
from torob.intelligence.plan_recovery import AdaptivePlanRecoveryEngine
from torob.intelligence.policy_simulator import VerificationPolicySimulator
from torob.intelligence.shop_reliability import BayesianShopReliabilityEngine
from torob.storage.db import db_manager
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository


def print_banner():
    print("\n" + "=" * 80)
    print("  TOROB CONTINUOUS INTELLIGENCE FLYWHEEL — ACCEPTANCE RUNNER")
    print("  Scenarios A through H: Observe -> Assess -> Verify -> Evaluate -> Learn")
    print("=" * 80)


def run_all_scenarios():
    print_banner()
    print("🔧 Initializing Catalog Ingestion & Storage Repositories...")
    t_setup_start = time.perf_counter()
    ingest_catalog()
    client = TestClient(app)
    ledger_repo = LedgerRepository(conn=db_manager.get_sqlite())
    catalog_repo = CatalogRepository(con=db_manager.get_duckdb())
    setup_latency_ms = (time.perf_counter() - t_setup_start) * 1000.0
    print(f"✅ Storage & Catalog Ingestion Initialized in {setup_latency_ms:.1f} ms\n")

    results = []
    scenarios = [
        ("Scenario A: Price Instability & Path Volatility VoI", run_scenario_a),
        ("Scenario B: Trusted Seller Prior During Market Shock", run_scenario_b),
        ("Scenario C: Customer Feedback & Plan Propagation", run_scenario_c),
        ("Scenario D: Stock Depletion & Restock Restoration", run_scenario_d),
        ("Scenario E: Daily Interruption Fatigue Budget", run_scenario_e),
        ("Scenario F: Single-Seller Peer Reference Protection", run_scenario_f),
        ("Scenario G: Recommendation Negative Preference Learning", lambda: run_scenario_g(client)),
        ("Scenario H: Snapshot Idempotency & 10x Currency Anomaly", run_scenario_h),
    ]

    print("=" * 95)
    print(f"{'#':<3} | {'Status':<6} | {'Scenario':<48} | {'Latency':<9} | {'Details'}")
    print("-" * 95)

    for idx, (title, func) in enumerate(scenarios, 1):
        t0 = time.perf_counter()
        try:
            detail, preview = func()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            status = "PASS"
            print(f"{idx:<3} | {status:<6} | {title:<48} | {latency_ms:>7.1f}ms | {detail[:40]}")
            print(f"    👤 Inspectable Output: {preview}")
            print("-" * 95)
            results.append({
                "index": idx,
                "title": title,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "detail": detail,
                "preview": preview,
            })
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            status = "FAIL"
            print(f"{idx:<3} | {status:<6} | {title:<48} | {latency_ms:>7.1f}ms | Error: {e}")
            print("-" * 95)
            results.append({
                "index": idx,
                "title": title,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            })

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    
    # Disaggregated latency accounting:
    # Deterministic intelligence engines (Scenarios A-F, H) vs Conversational multi-turn HTTP agent (Scenario G)
    sum_scenario_latencies = sum(r["latency_ms"] for r in results)
    det_scenarios = [r for r in results if r["index"] != 7]
    conv_scenarios = [r for r in results if r["index"] == 7]
    
    avg_det_latency = sum(r["latency_ms"] for r in det_scenarios) / len(det_scenarios) if det_scenarios else 0.0
    conv_latency = conv_scenarios[0]["latency_ms"] if conv_scenarios else 0.0
    overall_mean_latency = sum_scenario_latencies / total if total else 0.0

    print(f"\n🎯 Total Scenarios: {total} | Passed: {passed} | Failed: {total - passed} | Pass Rate: {(passed / total * 100.0):.1f}%")
    print(f"⏱️ Timing Breakdown & Latency Reconciliation:")
    print(f"   • Database & Catalog Init Overhead : {setup_latency_ms:>7.1f} ms")
    print(f"   • Deterministic Engines (A-F, H)  : {avg_det_latency:>7.1f} ms avg (sum: {sum(r['latency_ms'] for r in det_scenarios):.1f} ms)")
    print(f"   • Multi-Turn Agent HTTP Client (G): {conv_latency:>7.1f} ms (2 round-trips)")
    print(f"   • Sum of Pure Scenario Latencies   : {sum_scenario_latencies:>7.1f} ms")
    print(f"   • Grand Total Execution Time       : {(setup_latency_ms + sum_scenario_latencies):>7.1f} ms\n")

    report_path = REPO_ROOT / "data" / "flywheel_scenarios_report.json"
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(passed / total * 100.0, 1),
        "timing_breakdown": {
            "catalog_and_db_setup_ms": round(setup_latency_ms, 2),
            "deterministic_scenarios_avg_ms": round(avg_det_latency, 2),
            "conversational_agent_scenario_ms": round(conv_latency, 2),
            "sum_scenario_latencies_ms": round(sum_scenario_latencies, 2),
            "overall_mean_scenario_latency_ms": round(overall_mean_latency, 2),
            "grand_total_wall_clock_ms": round(setup_latency_ms + sum_scenario_latencies, 2),
        },
        "scenarios": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"📄 Report written to: {report_path}\n")
    return passed == total


def run_scenario_a():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    engine = MarketDynamicsEngine(ledger_repo=repo)
    now = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
    obs = [
        {"observed_at": (now - timedelta(days=5)).isoformat(), "price_toman": 100.0},
        {"observed_at": (now - timedelta(days=4)).isoformat(), "price_toman": 125.0},
        {"observed_at": (now - timedelta(days=3)).isoformat(), "price_toman": 95.0},
        {"observed_at": (now - timedelta(days=2)).isoformat(), "price_toman": 135.0},
        {"observed_at": (now - timedelta(days=1)).isoformat(), "price_toman": 90.0},
        {"observed_at": now.isoformat(), "price_toman": 102.0},
    ]
    feat = engine.compute_historical_features("off_a", obs, as_of=now)
    assert feat.total_abs_log_movement > 0.8
    detail = f"Net change: +{feat.net_change_pct}%, Path movement: {feat.total_abs_log_movement:.2f}, Freq: {feat.price_change_frequency}"
    preview = f"Realized Path Log Movement: {feat.total_abs_log_movement:.4f} | Sparsity: {feat.observation_sparsity_score}"
    return detail, preview


def run_scenario_b():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    shop = Shop(shop_id="sh_b", name="فروشگاه ممتاز", address="تهران")
    rel_eng = BayesianShopReliabilityEngine()
    outcomes = [{"dimension": "price_fidelity", "is_success": True} for _ in range(20)]
    asmt = rel_eng.assess_shop_reliability(shop, verified_outcomes=outcomes)
    policy_eng = AdaptiveInquiryPolicyEngine(ledger_repo=repo)
    dec = policy_eng.evaluate_inquiry_decision(
        offer_id="off_b",
        shop_id="sh_b",
        product_id="prd_b",
        price_assessment=PriceAssessment(
            status=PriceAssessmentStatus.VALID_ESTIMATE,
            risk_score=35,
            risk_band=RiskBand.LOW,
        ),
        stock_assessment=StockAssessment(status=StockState.UNKNOWN),
        shop_assessment=asmt,
        user_intent=UserIntent.BUY,
        product_regime=ProductRegime.SHOCK_REGIME,
    )
    assert dec.action_code == "enqueue_inquiry"
    detail = f"Shop trust: {asmt.composite_reliability_score:.2f}, Action under shock: {dec.action_code}"
    preview = f"Trigger: {dec.selection_trigger} | VoI Benefit: {dec.expected_benefit:.1f} | Priority: {dec.priority.value}"
    return detail, preview


def run_scenario_c():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    cat_repo = CatalogRepository(con=db_manager.get_duckdb())
    rec_eng = AdaptivePlanRecoveryEngine(catalog_repo=cat_repo, ledger_repo=repo)
    life_mgr = ShoppingPlanLifecycleManager(ledger_repo=repo, catalog_repo=cat_repo, recovery_engine=rec_eng)
    fb_svc = FeedbackService(ledger_repo=repo, plan_lifecycle_manager=life_mgr)
    coverage = ShopBasketCoverage(
        shop_id="sh_c_target",
        shop_name="فروشگاه سی",
        shop_address="تهران",
        items_covered_count=1,
        total_items_requested=1,
        covers_entire_basket=True,
        matched_items=[
            BasketItemMatch(
                query="کیبورد",
                matched_product_id="p1",
                matched_product_title="کیبورد",
                offer_id="o1",
                price_toman=500_000.0,
            )
        ],
        total_listed_price_toman=500_000.0,
        shop_reliability_score=0.90,
    )
    plan = MultiStoreBasketPlan(
        plan_id="plan_run_c",
        strategy="single_store",
        stores=[coverage],
        total_product_cost_toman=500_000.0,
        total_stops=1,
        all_items_covered=True,
        composite_score=0.90,
    )
    life_mgr.register_plan(plan)
    # 1. Customer submits complaint: Complaint alone does NOT degrade plan or penalize merchant
    case = fb_svc.submit_customer_feedback(shop_id="sh_c_target", issue_type=FeedbackIssueType.SHOP_CLOSED)
    plan_under_review = life_mgr.get_plan("plan_run_c")
    assert plan_under_review.guarantee_status != "discrepancy_invalidated_replan_required"

    # 2. Operator verifies and attributes to seller misstatement -> Degrades plan and updates reliability
    fb_svc.resolve_case(case.case_id, CaseOutcome.RESOLVED_STOCK_UPDATED, "Confirmed shop closed", attribution_cause="seller_misstatement")
    deg_plan = life_mgr.get_plan("plan_run_c")
    assert deg_plan.guarantee_status == "discrepancy_invalidated_replan_required"
    detail = f"Plan degraded: {deg_plan.guarantee_status}, Score: {deg_plan.composite_score}"
    preview = f"Warning: {deg_plan.warnings[-1]}"
    return detail, preview


def run_scenario_d():
    cat_repo = CatalogRepository(con=db_manager.get_duckdb())
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    rec_eng = AdaptivePlanRecoveryEngine(catalog_repo=cat_repo, ledger_repo=repo)
    life_mgr = ShoppingPlanLifecycleManager(ledger_repo=repo, catalog_repo=cat_repo, recovery_engine=rec_eng)
    coverage = ShopBasketCoverage(
        shop_id="sh_s3",
        shop_name="روورا نوینا",
        shop_address="تهران",
        items_covered_count=1,
        total_items_requested=1,
        covers_entire_basket=True,
        matched_items=[
            BasketItemMatch(
                query="ریموت کنترل ایرماوس مدل M",
                matched_product_id="pr_s3_1",
                matched_product_title="ریموت کنترل ایرماوس مدل M",
                offer_id="of_s3_1",
                price_toman=1_000_000.0,
                seller_confirmed=True,
                stock_state=StockState.IN_STORE_SELLABLE,
            )
        ],
        total_listed_price_toman=1_000_000.0,
        shop_reliability_score=0.95,
    )
    plan = MultiStoreBasketPlan(
        plan_id="plan_run_d",
        strategy="single_store",
        stores=[coverage],
        total_product_cost_toman=1_000_000.0,
        total_stops=1,
        all_items_covered=True,
        composite_score=0.95,
        guarantee_status="seller_confirmed_in_store",
    )
    life_mgr.register_plan(plan)
    adapt_res = life_mgr.adaptive_replan_after_stock_rejection("plan_run_d", "ریموت کنترل ایرماوس مدل M", "sh_s3")
    assert adapt_res.is_recovered
    restock_res = life_mgr.adaptive_replan_after_restock("plan_run_d", "pr_s3_1", "sh_s3")
    assert restock_res.is_recovered
    detail = f"Rejection replaced; Restock restored: {restock_res.revised_plan.guarantee_status}"
    preview = f"Restocked Guarantee: {restock_res.revised_plan.guarantee_status} | Coverage: {restock_res.revised_plan.stores[0].items_covered_count}/1"
    return detail, preview


def run_scenario_e():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    policy_eng = AdaptiveInquiryPolicyEngine(ledger_repo=repo)
    asmt = ShopReliabilityAssessment(shop_id="sh_e", composite_reliability_score=0.75, dimensions={"inquiry_responsiveness": 0.8})
    dec_under = policy_eng.evaluate_inquiry_decision(
        offer_id="o1", shop_id="sh_e", product_id="p1",
        price_assessment=PriceAssessment(status=PriceAssessmentStatus.VALID_ESTIMATE, risk_score=70, risk_band=RiskBand.HIGH),
        stock_assessment=StockAssessment(status=StockState.UNKNOWN),
        shop_assessment=asmt, active_inquiries_count_today=5
    )
    dec_over = policy_eng.evaluate_inquiry_decision(
        offer_id="o2", shop_id="sh_e", product_id="p2",
        price_assessment=PriceAssessment(status=PriceAssessmentStatus.VALID_ESTIMATE, risk_score=70, risk_band=RiskBand.HIGH),
        stock_assessment=StockAssessment(status=StockState.UNKNOWN),
        shop_assessment=asmt, active_inquiries_count_today=15
    )
    assert dec_under.action_code == "enqueue_inquiry"
    assert dec_over.action_code == "decline_or_defer"
    detail = f"Load=5: {dec_under.action_code} | Load=15: {dec_over.action_code}"
    preview = f"Fatigue Capped: {dec_over.action_code} (Reason: {dec_over.reason_codes[0]})"
    return detail, preview


def run_scenario_f():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    eng = MarketDynamicsEngine(ledger_repo=repo)
    ref = eng.aggregate_market_reference("prd_f", [{"offer_id": "o_f", "shop_id": "s_f", "price_toman": 10_000_000.0}], "o_f")
    assert ref.is_single_seller
    assert ref.peer_median_price_toman is None
    detail = f"Single seller: is_single={ref.is_single_seller}, peer_median={ref.peer_median_price_toman}"
    preview = f"Warning: {ref.warning}"
    return detail, preview


def run_scenario_g(client):
    r1 = client.post("/api/v1/assistant/sessions", json={"user_id": "usr_test_run"})
    sid = r1.json()["session_id"]
    client.post(f"/api/v1/assistant/sessions/{sid}/messages", json={"message": "لپ تاپ تا ۵۰ میلیون تومان"})
    r3 = client.post(f"/api/v1/assistant/sessions/{sid}/messages", json={"message": "اون اولی رو نمیخوام، یه مدل دیگه بده"})
    d3 = r3.json()
    assert len(d3["constraints"]["rejected_product_ids"]) > 0
    rej_id = d3["constraints"]["rejected_product_ids"][0]
    detail = f"Session {sid[:10]}: Rejected {rej_id} preserved in constraints"
    preview = f"Rejected Product IDs: {d3['constraints']['rejected_product_ids']}"
    return detail, preview


def run_scenario_h():
    repo = LedgerRepository(conn=db_manager.get_sqlite())
    monitor = MarketMonitoringEngine(ledger_repo=repo)
    alert = monitor.check_offer_price_anomalies("off_h", "sh_h", "pr_h", 150_000_000.0, 15_000_000.0)
    assert alert is not None
    assert alert.alert_type == "currency_denomination_10x_error"
    ingestion = SnapshotIngestionEngine(ledger_repo=repo)
    r1 = ingestion.ingest_snapshot([{"offer_id": "off_h_snap", "shop_id": "sh_h", "product_id": "pr_h", "price_toman": 500_000.0}], snapshot_id="snap_h")
    r2 = ingestion.ingest_snapshot([{"offer_id": "off_h_snap", "shop_id": "sh_h", "product_id": "pr_h", "price_toman": 500_000.0}], snapshot_id="snap_h")
    assert r2.new_offers_count == 0
    detail = f"10x Alert: {alert.alert_type}, Idempotent replay: {r2.new_offers_count} new"
    preview = f"Alert Suspected Correct: {alert.payload['suspected_correct_price']:,.0f} Toman"
    return detail, preview


if __name__ == "__main__":
    success = run_all_scenarios()
    sys.exit(0 if success else 1)
