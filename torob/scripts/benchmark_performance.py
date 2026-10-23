#!/usr/bin/env python3
"""Benchmark performance of Torob Intelligence Engine.

Measures:
1. Ingestion / startup time
2. Point lookups (products, shops, offers)
3. Normalized Persian text search
4. LOSO competitor price analysis
5. Complex route and feasibility calculation
6. P50, P90, P99 latency percentiles and QPS

Outputs results to data/performance_benchmark.json.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List

import numpy as np

# Ensure src is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from torob.domain.enums import SortMode
from torob.ingestion.loader import ingest_catalog
from torob.intelligence.pricing import PriceIntelligenceEngine
from torob.routing.distance import DistanceRouter
from torob.routing.feasibility import VisitFeasibilityEngine
from torob.routing.itinerary import ItineraryPlanner
from torob.storage.db import db_manager
from torob.storage.repository_catalog import CatalogRepository
from torob.storage.repository_ledger import LedgerRepository


def measure_latencies(fn: Callable[[], None], iterations: int = 100) -> Dict[str, float]:
    """Execute fn multiple times and calculate latency percentiles in milliseconds."""
    # Warmup
    for _ in range(min(5, iterations)):
        fn()

    times: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)  # ms

    arr = np.array(times)
    total_time_s = sum(times) / 1000.0
    qps = iterations / total_time_s if total_time_s > 0 else 0

    return {
        "iterations": iterations,
        "mean_ms": round(float(np.mean(arr)), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p90_ms": round(float(np.percentile(arr, 90)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "p99_ms": round(float(np.percentile(arr, 99)), 3),
        "min_ms": round(float(np.min(arr)), 3),
        "max_ms": round(float(np.max(arr)), 3),
        "qps": round(float(qps), 1),
    }


def main():
    print("=" * 60)
    print(" Torob Intelligence Engine Performance Benchmark")
    print("=" * 60)

    data_dir = BASE_DIR / "data"
    output_path = data_dir / "performance_benchmark.json"

    # Step 1: Measure Catalog Ingestion
    print("\n1. Measuring Catalog CSV Ingestion...")
    con = db_manager.get_duckdb()
    t0 = time.perf_counter()
    ingest_catalog(con=con, csv_dir=data_dir, force_reload=True)
    ingest_time_s = time.perf_counter() - t0

    counts = {
        "shops": con.execute("SELECT COUNT(*) FROM shops").fetchone()[0],
        "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "offers": con.execute("SELECT COUNT(*) FROM offers").fetchone()[0],
    }
    print(f"   Loaded: {counts['shops']:,} shops, {counts['products']:,} products, {counts['offers']:,} offers")
    print(f"   Total ingestion time: {ingest_time_s:.3f} s")

    catalog_repo = CatalogRepository(con=con)
    ledger_repo = LedgerRepository()
    pricing_engine = PriceIntelligenceEngine()
    feasibility_engine = VisitFeasibilityEngine()
    planner = ItineraryPlanner()

    # Step 2: Sample entities for testing
    print("\n2. Sampling test targets from live dataset...")
    # Fetch top 10 products that have multiple offers
    sample_prod_rows = con.execute("""
        SELECT product_id, COUNT(*) as cnt 
        FROM offers 
        GROUP BY product_id 
        HAVING cnt >= 3 
        ORDER BY cnt DESC 
        LIMIT 10
    """).fetchall()
    sample_product_ids = [r[0] for r in sample_prod_rows]
    sample_product_id = sample_product_ids[0] if sample_product_ids else "p1"
    print(f"   Sample multi-seller product: {sample_product_id}")

    sample_offer_row = con.execute("SELECT offer_id FROM offers LIMIT 1").fetchone()
    sample_offer_id = sample_offer_row[0] if sample_offer_row else "off1"

    sample_shop_row = con.execute("SELECT shop_id FROM shops WHERE lat IS NOT NULL LIMIT 1").fetchone()
    sample_shop_id = sample_shop_row[0] if sample_shop_row else "s1"

    # Step 3: Run Microbenchmarks
    benchmarks: Dict[str, Any] = {
        "ingestion": {
            "time_seconds": round(ingest_time_s, 3),
            "counts": counts,
        },
        "query_latencies": {},
    }

    # Benchmark A: Product Primary Key Lookup
    print("\n   Benchmarking Product PK Lookup...")
    benchmarks["query_latencies"]["product_pk_lookup"] = measure_latencies(
        lambda: catalog_repo.get_product(sample_product_id), iterations=200
    )

    # Benchmark B: Offer PK Lookup
    print("   Benchmarking Offer PK Lookup...")
    benchmarks["query_latencies"]["offer_pk_lookup"] = measure_latencies(
        lambda: catalog_repo.get_offer(sample_offer_id), iterations=200
    )

    # Benchmark C: Shop PK Lookup
    print("   Benchmarking Shop PK Lookup...")
    benchmarks["query_latencies"]["shop_pk_lookup"] = measure_latencies(
        lambda: catalog_repo.get_shop(sample_shop_id), iterations=200
    )

    # Benchmark D: Normalized Persian Search (Multi-token)
    print("   Benchmarking Persian Product Search ('سامسونگ گلکسی')...")
    benchmarks["query_latencies"]["persian_search_multitoken"] = measure_latencies(
        lambda: catalog_repo.search_products(q="سامسونگ گلکسی", limit=20), iterations=100
    )

    # Benchmark E: LOSO Competitor Offer Fetch
    print("   Benchmarking LOSO Competitor Retrieval...")
    benchmarks["query_latencies"]["loso_peer_offers_fetch"] = measure_latencies(
        lambda: catalog_repo.get_peer_offers_loso(sample_product_id, sample_shop_id), iterations=100
    )

    # Benchmark F: Price Assessment Engine (Median, LOSO, IQR, Staleness)
    print("   Benchmarking Price Anomaly Engine Assessment...")
    sample_offer = catalog_repo.get_offer(sample_offer_id)
    peer_offers = catalog_repo.get_peer_offers_loso(sample_offer.product_id, sample_offer.shop_id)
    benchmarks["query_latencies"]["price_anomaly_assessment"] = measure_latencies(
        lambda: pricing_engine.assess_offer_price(sample_offer, peer_offers), iterations=200
    )

    # Benchmark G: Route Feasibility Computation
    print("   Benchmarking Route Feasibility Evaluation...")
    sample_shop = catalog_repo.get_shop(sample_shop_id)
    benchmarks["query_latencies"]["visit_feasibility"] = measure_latencies(
        lambda: feasibility_engine.assess_visit_feasibility(
            origin_lat=35.7000,
            origin_lon=51.4000,
            shop=sample_shop,
            offer=sample_offer,
        ),
        iterations=100,
    )

    # Output results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(benchmarks, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f" Benchmark Complete! Results written to {output_path}")
    print(" Summary:")
    for name, stats in benchmarks["query_latencies"].items():
        print(f"   - {name:<30}: Mean {stats['mean_ms']}ms | P95 {stats['p95_ms']}ms | QPS {stats['qps']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
