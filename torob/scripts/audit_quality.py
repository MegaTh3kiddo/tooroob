import json
from pathlib import Path
import time
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

def run_quality_audit():
    print(f"Starting reproducible quality audit on datasets in {DATA_DIR}...")
    t0 = time.time()
    con = duckdb.connect()

    # Load shops
    con.execute(f"""
    CREATE TABLE shops AS 
    SELECT 
        shop_id, name, address, 
        TRY_CAST(lat AS DOUBLE) as lat, 
        TRY_CAST(lon AS DOUBLE) as lon,
        category_names, weekly_hours, website_url, supports_fast_delivery
    FROM read_csv('{DATA_DIR / "shops.csv"}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    # Load products
    con.execute(f"""
    CREATE TABLE products AS 
    SELECT 
        product_id, persian_title, brand_name, category_name, model, specs
    FROM read_csv('{DATA_DIR / "products.csv"}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    # Load offers
    con.execute(f"""
    CREATE TABLE offers AS 
    SELECT 
        offer_id, product_id, shop_id,
        TRY_CAST(price_toman AS DOUBLE) as price_toman,
        TRY_CAST(last_price_changed_at AS TIMESTAMPTZ) as last_price_changed_at,
        seller_title, warranty
    FROM read_csv('{DATA_DIR / "offers.csv"}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    total_shops = con.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
    total_products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_offers = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

    # Price stats
    price_stats = con.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(price_toman) as numeric_count,
        COUNT(*) - COUNT(price_toman) as null_count,
        SUM(CASE WHEN price_toman = 1 THEN 1 ELSE 0 END) as sentinel_1_toman,
        SUM(CASE WHEN price_toman > 1 AND price_toman < 1000 THEN 1 ELSE 0 END) as below_1000,
        SUM(CASE WHEN price_toman > 1000000000000 THEN 1 ELSE 0 END) as above_1_trillion,
        MEDIAN(price_toman) as median_price,
        MIN(CASE WHEN price_toman > 1 THEN price_toman END) as min_valid_price,
        MAX(CASE WHEN price_toman < 1000000000000 THEN price_toman END) as max_valid_price
    FROM offers;
    """).fetchone()

    # Competitor coverage
    single_seller_products = con.execute("""
    SELECT COUNT(*) FROM (
        SELECT product_id FROM offers GROUP BY product_id HAVING COUNT(DISTINCT shop_id) = 1
    )
    """).fetchone()[0]

    multi_seller_products = con.execute("""
    SELECT COUNT(*) FROM (
        SELECT product_id FROM offers GROUP BY product_id HAVING COUNT(DISTINCT shop_id) >= 2
    )
    """).fetchone()[0]

    # Age stats
    age_stats = con.execute("""
    SELECT 
        COUNT(last_price_changed_at) as with_timestamp,
        COUNT(*) - COUNT(last_price_changed_at) as missing_timestamp,
        MIN(last_price_changed_at) as oldest_change,
        MAX(last_price_changed_at) as newest_change
    FROM offers;
    """).fetchone()

    audit_result = {
        "audit_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution_seconds": round(time.time() - t0, 3),
        "dataset_counts": {
            "shops": total_shops,
            "products": total_products,
            "offers": total_offers,
        },
        "price_quality": {
            "total_offers": price_stats[0],
            "numeric_prices": price_stats[1],
            "null_prices": price_stats[2],
            "sentinel_1_toman": price_stats[3],
            "below_1000_toman": price_stats[4],
            "above_1_trillion_toman": price_stats[5],
            "median_price_toman": price_stats[6],
            "min_valid_price": price_stats[7],
            "max_valid_price": price_stats[8],
        },
        "market_structure": {
            "products_single_seller": single_seller_products,
            "products_multi_seller": multi_seller_products,
            "single_seller_ratio": round(single_seller_products / total_products, 4) if total_products else 0,
        },
        "timestamps": {
            "valid_timestamps": age_stats[0],
            "missing_timestamps": age_stats[1],
            "oldest_timestamp": str(age_stats[2]),
            "newest_timestamp": str(age_stats[3]),
        }
    }

    report_path = DATA_DIR / "data_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2, ensure_ascii=False)

    print(f"Audit completed in {audit_result['execution_seconds']}s.")
    print(f"Report saved to {report_path}")
    print(json.dumps(audit_result, indent=2))
    return audit_result

if __name__ == "__main__":
    run_quality_audit()
