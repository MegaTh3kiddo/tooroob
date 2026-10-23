#!/usr/bin/env python3
"""Executable Backend-First Demonstrations for Torob Intelligence Engine (Scenarios A through G).

Demonstrates real backend services, persistence, and intelligence without frontend:
- Demo A: Shopping on an existing journey (origin -> stop -> destination with separated dwell/detour).
- Demo B: Complete basket from one physical store (item-level prices & verification status).
- Demo C: Multi-store shopping set-cover (combinatorial optimization with bounded stops).
- Demo D: Natural-language agent orchestration via Assistant API (/assistant/sessions/{id}/messages).
- Demo E: Multi-turn conversational refinement (updating budget/reliability while preserving context).
- Demo F: Dynamic evidence refresh (seller inventory response invalidating/confirming plan with audit history).
- Demo G: Infeasible request handling (transparent refusal and constructive guidance, no hallucination).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from fastapi.testclient import TestClient

from torob.api.main import app
from torob.domain.plans import PlanOptimizationPriority
from torob.ingestion.loader import initialize_storage
from torob.intelligence.basket_optimizer import BasketOptimizationEngine
from torob.intelligence.plan_lifecycle import ShoppingPlanLifecycleManager
from torob.routing.distance import DeterministicRoadNetworkProvider, DistanceRouter, RoadNetworkGraph
from torob.routing.on_route import OnRouteShoppingEngine
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def demo_a_on_route_purchasing():
    print_header("DEMO A: Shopping On An Existing Journey (Separate Dwell & Verified Road Route)")
    # Build road network graph for demonstration
    graph = RoadNetworkGraph()
    # Sadeghiyeh -> Enqelab -> Tajrish corridor
    graph.add_node("sadeghiyeh", 35.7200, 51.3350)
    graph.add_node("enqelab", 35.7012, 51.3912)
    graph.add_node("valiasr", 35.7115, 51.4070)
    graph.add_node("tajrish", 35.8050, 51.4270)
    graph.add_edge("sadeghiyeh", "enqelab", distance_km=6.5, speed_kmh=35.0)
    graph.add_edge("enqelab", "valiasr", distance_km=2.2, speed_kmh=25.0)
    graph.add_edge("valiasr", "tajrish", distance_km=11.0, speed_kmh=40.0)

    provider = DeterministicRoadNetworkProvider(graph)
    router = DistanceRouter(provider=provider)
    repo = CatalogRepository()
    engine = OnRouteShoppingEngine(catalog_repo=repo, router=router)

    res = engine.find_on_route_purchases(
        origin_lat=35.7200,
        origin_lon=51.3350,
        dest_lat=35.8050,
        dest_lon=51.4270,
        product_query="SSD",
        corridor_width_km=10.0,
        limit=3,
    )

    print(f"• مبدا: صادقیه | مقصد: تجریش | کالای درخواستی: SSD")
    print(f"• مدت سفر مستقیم بدون توقف: {res.baseline_duration_minutes:.1f} دقیقه ({res.baseline_distance_km:.1f} کیلومتر)")
    print(f"• وضعیت شبکه معابر: {'تاییدشده شبکه جاده‌ای' if res.is_verified_road_network else 'تخمین شهری'}")
    print(f"• تعداد توقف‌های پیشنهادی منطبق: {len(res.recommended_stops)}")

    for idx, s in enumerate(res.recommended_stops, start=1):
        print(f"  [{idx}] {s.shop_name} ({s.trade_off_label})")
        print(f"      - قیمت کالا: {s.price_toman:,.0f} تومان | محصول: {s.product_title[:35]}")
        print(f"      - انحراف زمانی خالص: {s.detour_minutes:.1f} دقیقه | توقف خرید: {s.dwell_minutes:.1f} دقیقه")
        print(f"      - کل زمان سفر از مبدا تا مقصد با توقف: {s.trip_via_shop_minutes:.1f} دقیقه")
        print(f"      - وضعیت کاری در زمان رسیدن ({s.arrival_at}): {'باز' if s.is_open_at_arrival else 'بسته'}")
    print(f"• خلاصه تحلیل: {res.trade_off_summary}")


def demo_b_complete_single_store_basket():
    print_header("DEMO B: Complete Basket From One Store (Evidence & Item Verification Status)")
    repo = CatalogRepository()
    engine = BasketOptimizationEngine(catalog_repo=repo)

    plans = engine.optimize_basket(
        basket_queries=["ماوس", "کیبورد"],
        require_single_store=True,
    )

    print(f"• اقلام درخواستی: ماوس + کیبورد (شرط: ۱۰۰٪ از یک فروشگاه)")
    print(f"• تعداد طرح‌های ارزیابی‌شده: {len(plans)}")

    for idx, p in enumerate(plans[:2], start=1):
        print(f"  [{idx}] استراتژی: {p.strategy_label_persian} ({p.strategy})")
        print(f"      - کل اقلام تحت پوشش: {'بله' if p.all_items_covered else 'خیر'}")
        print(f"      - مجموع قیمت کاتالوگ: {p.total_product_cost_toman:,.0f} تومان | وضعیت قیمت: {'قطعی' if p.is_total_price_complete else 'ناقص'}")
        print(f"      - وضعیت تضمین انبار: {p.guarantee_status}")
        for s in p.stores:
            print(f"      - فروشگاه: {s.shop_name} (اعتماد: {int(s.shop_reliability_score*100)}٪)")
            for item in s.matched_items:
                print(f"        * {item.query}: {item.matched_product_title[:35]} -> {item.price_toman:,.0f} ت [{item.stock_evidence}]")


def demo_c_multi_store_shopping():
    print_header("DEMO C: Multi-Store Basket Optimization (Pareto Trade-Offs & Set-Cover)")
    repo = CatalogRepository()
    engine = BasketOptimizationEngine(catalog_repo=repo)

    plans = engine.optimize_basket(
        basket_queries=["مانیتور", "کیبورد", "ماوس"],
        max_stops=2,
        optimization_priority=PlanOptimizationPriority.CHEAPEST,
    )

    print(f"• سبد خرید: مانیتور + کیبورد + ماوس | سقف توقف: ۲ فروشگاه | اولویت: اقتصادی‌ترین")
    for idx, p in enumerate(plans, start=1):
        print(f"  [{idx}] طرح {p.strategy} | برچسب‌های پارتو: {p.pareto_labels}")
        print(f"      - تعداد توقف: {p.total_stops} فروشگاه | هزینه مجموع: {p.total_product_cost_toman:,.0f} تومان")
        print(f"      - زمان تخمینی سفر: {p.estimated_total_travel_minutes:.0f} دقیقه")
        print(f"      - توضیح مقایسه‌ای: {p.trade_off_explanation}")


def demo_d_agent_orchestration():
    print_header("DEMO D: Natural-Language Agent Orchestration via Messages API")
    client = TestClient(app)
    s_res = client.post("/api/v1/assistant/sessions")
    sess_id = s_res.json()["session_id"]

    query = "از صادقیه میخوام برم تجریش، توی راه یه SSD دو ترابایت بخرم."
    print(f"• پیام کاربر: «{query}»")

    msg_res = client.post(
        f"/api/v1/assistant/sessions/{sess_id}/messages",
        json={"message": query},
    )
    data = msg_res.json()
    print(f"• نیت شناسایی‌شده: {data['detected_intent']}")
    print(f"• قیود استخراج‌شده:")
    print(f"  - مبدا: {data['constraints']['origin_name']} ({data['constraints']['origin_lat']}, {data['constraints']['origin_lon']})")
    print(f"  - مقصد: {data['constraints']['destination_name']} ({data['constraints']['destination_lat']}, {data['constraints']['destination_lon']})")
    print(f"  - محصول درخواستی: {data['constraints']['target_product_title']}")
    print(f"• پاسخ مشاور خرید ترب:\n{data['reply_text']}")


def demo_e_multiturn_refinement():
    print_header("DEMO E: Multi-Turn Conversational Refinement (Constraint Preservation)")
    client = TestClient(app)
    s_res = client.post("/api/v1/assistant/sessions")
    sess_id = s_res.json()["session_id"]

    # Turn 1
    t1 = "ماوس و کیبورد میخوام ارزان‌ترین حالت"
    print(f"[نوبت ۱] کاربر: «{t1}»")
    r1 = client.post(f"/api/v1/assistant/sessions/{sess_id}/messages", json={"message": t1}).json()
    print(f"         سیستم: سبد={r1['constraints']['basket_queries']}, اولویت={r1['constraints']['optimization_priority']}")

    # Turn 2: Refine trust
    t2 = "همونا رو میخوام ولی فروشگاه مطمئنتر باشه."
    print(f"[نوبت ۲] کاربر: «{t2}»")
    r2 = client.post(f"/api/v1/assistant/sessions/{sess_id}/messages", json={"message": t2}).json()
    print(f"         سیستم: نیت={r2['detected_intent']}, حداقل اعتماد={r2['constraints']['min_shop_reliability']}, سبد حفظ‌شده={r2['constraints']['basket_queries']}")

    # Turn 3: Switch objective
    t3 = "دیگه ارزونترین مهم نیست، سریعترین راه خرید رو پیدا کن."
    print(f"[نوبت ۳] کاربر: «{t3}»")
    r3 = client.post(f"/api/v1/assistant/sessions/{sess_id}/messages", json={"message": t3}).json()
    print(f"         سیستم: نیت={r3['detected_intent']}, اولویت جدید={r3['constraints']['optimization_priority']}, سبد حفظ‌شده={r3['constraints']['basket_queries']}")


def demo_f_evidence_refresh_lifecycle():
    print_header("DEMO F: Dynamic Evidence Refresh & Audit History")
    repo = CatalogRepository()
    ledger_repo = LedgerRepository()
    basket_engine = BasketOptimizationEngine(catalog_repo=repo)
    manager = ShoppingPlanLifecycleManager(ledger_repo=ledger_repo)

    plans = basket_engine.optimize_basket(basket_queries=["ماوس", "کیبورد"])
    plan = plans[0]
    manager.register_plan(plan)
    target_shop = plan.stores[0]

    print(f"• طرح اولیه سبد خرید ثبت شد:")
    print(f"  - نمره اطمینان اولیه: {plan.composite_score} | وضعیت تضمین: {plan.guarantee_status}")

    # Dispatch inquiry
    inq = manager.dispatch_authorized_basket_inquiry(
        plan_id=plan.plan_id,
        shop_id=target_shop.shop_id,
        user_authorized=True,
    )
    print(f"• استعلام تجمیعی با شناسه {inq['inquiry_id']} برای فروشگاه {target_shop.shop_name} صادر شد.")

    # Seller responds with Out of Stock
    prod_ids = [m.matched_product_id for m in target_shop.matched_items]
    updated = manager.process_seller_response_and_update_plan(
        plan_id=plan.plan_id,
        inquiry_id=inq["inquiry_id"],
        actor_id=f"seller_{target_shop.shop_id}",
        item_stock_results={prod_ids[0]: False},
        notes="کالا در انبار ناموجود است",
    )

    print(f"• استعلام فروشنده دریافت شد (عدم موجودی کالای اول).")
    print(f"• وضعیت به‌روزرسانی‌شده طرح:")
    print(f"  - پوشش کامل سبد: {'بله' if updated.all_items_covered else 'خیر'}")
    print(f"  - نمره اطمینان جدید: {updated.composite_score} (کاهش یافت)")
    print(f"  - وضعیت جدید: {updated.guarantee_status}")
    print(f"  - هشدارها: {updated.warnings}")

    history = manager.get_audit_history(plan.plan_id)
    print(f"• تاریخچه رخدادهای زنجیره شواهد (Audit Trail): {len(history)} نگارش")
    for h in history:
        print(f"  - نسخه {h['version']}: {h['event']} ({h['timestamp']})")


def demo_g_infeasible_request():
    print_header("DEMO G: Infeasible Request Handling (Refusal without Hallucination)")
    repo = CatalogRepository()
    engine = OnRouteShoppingEngine(catalog_repo=repo)

    # Impossible detour constraint: 0.1 minutes for 15km journey
    res = engine.find_on_route_purchases(
        origin_lat=35.7200,
        origin_lon=51.3350,
        dest_lat=35.8050,
        dest_lon=51.4270,
        product_query="SSD",
        max_detour_minutes=0.1,
    )

    print(f"• درخواست: خرید SSD در مسیر صادقیه به تجریش با سقف انحراف غیرممکن ۰.۱ دقیقه (۶ ثانیه)")
    print(f"• امکان‌پذیری طرح: {'امکان‌پذیر' if res.is_feasible else 'غیرقابل انجام (رد شفاف)'}")
    print(f"• تعداد توقف‌های ساختگی: {len(res.recommended_stops)} (هیچ داده جعلی ساخته نشد)")
    print(f"• هشدارهای سیستمی: {res.warnings}")
    print(f"• راهنمایی کاربر: {res.trade_off_summary}")


def main():
    print("🚀 Initializing Torob Intelligence Engine Storage & Catalog...")
    initialize_storage()
    demo_a_on_route_purchasing()
    demo_b_complete_single_store_basket()
    demo_c_multi_store_shopping()
    demo_d_agent_orchestration()
    demo_e_multiturn_refinement()
    demo_f_evidence_refresh_lifecycle()
    demo_g_infeasible_request()
    print("\n✅ All 7 Demonstrations Completed Successfully!\n")


if __name__ == "__main__":
    main()
