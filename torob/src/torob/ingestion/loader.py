import logging
from pathlib import Path
from typing import Optional
import duckdb

from torob.core.config import settings
from torob.storage.db import db_manager

logger = logging.getLogger("torob.ingestion.loader")


def get_default_catalog_path() -> Path:
    return settings.data_dir / "torob_catalog.duckdb"


def ingest_catalog(
    con: Optional[duckdb.DuckDBPyConnection] = None,
    csv_dir: Optional[Path] = None,
    force_reload: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Load and normalize raw CSV datasets (shops, products, offers) into DuckDB.
    
    If DuckDB database is persistent and tables already exist with rows, it skips re-ingestion
    unless force_reload is True.
    """
    directory = csv_dir or settings.data_dir
    def _csv(name: str) -> Path:
        # Deployments ship gzip-compressed CSVs; DuckDB reads .csv.gz transparently.
        plain = directory / name
        gz = directory / (name + ".gz")
        return plain if plain.exists() or not gz.exists() else gz

    shops_csv = _csv("shops.csv")
    products_csv = _csv("products.csv")
    offers_csv = _csv("offers.csv")

    if not (shops_csv.exists() and products_csv.exists() and offers_csv.exists()):
        raise FileNotFoundError(
            f"Missing required CSV files in {directory}. Expected shops.csv, products.csv, offers.csv."
        )

    con = con or db_manager.get_duckdb()

    # Check if tables already exist and are populated
    try:
        tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        if not force_reload and set(["shops", "products", "offers"]).issubset(set(tables)):
            shop_cnt = con.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
            if shop_cnt > 0:
                logger.info(f"Catalog tables already loaded ({shop_cnt} shops). Skipping re-ingestion.")
                return con
    except Exception:
        pass

    logger.info("Ingesting and normalizing catalog from CSV files into DuckDB...")

    # Load shops
    con.execute(f"""
    CREATE OR REPLACE TABLE shops AS 
    SELECT 
        shop_id,
        name,
        address,
        TRY_CAST(lat AS DOUBLE) AS lat,
        TRY_CAST(lon AS DOUBLE) AS lon,
        location_label,
        category_names,
        payment_options,
        CASE WHEN LOWER(supports_fast_delivery) IN ('true', '1', 't') THEN true ELSE false END AS supports_fast_delivery,
        website_url,
        weekly_hours,
        contacts,
        instagram
    FROM read_csv('{shops_csv.as_posix()}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    # Load products
    con.execute(f"""
    CREATE OR REPLACE TABLE products AS 
    SELECT 
        product_id,
        persian_title,
        brand_name,
        category_name,
        model,
        image_urls,
        specs
    FROM read_csv('{products_csv.as_posix()}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    # Load offers with normalized numeric prices and timestamps
    con.execute(f"""
    CREATE OR REPLACE TABLE offers AS 
    SELECT 
        offer_id,
        product_id,
        shop_id,
        TRY_CAST(price_toman AS DOUBLE) AS price_toman,
        TRY_CAST(last_price_changed_at AS TIMESTAMPTZ) AS last_price_changed_at,
        seller_title,
        warranty,
        description
    FROM read_csv('{offers_csv.as_posix()}', nullstr=['null', 'NULL', ''], all_varchar=true);
    """)

    # Pre-build analytical views for fast peer comparison & product aggregations
    con.execute("""
    CREATE OR REPLACE VIEW v_product_peer_stats AS 
    SELECT 
        product_id,
        COUNT(*) as total_offers,
        COUNT(DISTINCT shop_id) as independent_shops_count,
        MEDIAN(price_toman) as peer_median_price,
        MIN(price_toman) as peer_min_price,
        MAX(price_toman) as peer_max_price,
        AVG(price_toman) as peer_avg_price
    FROM offers
    WHERE price_toman IS NOT NULL AND price_toman > 1 AND price_toman < 1000000000000
    GROUP BY product_id;
    """)

    logger.info("Catalog ingestion completed successfully.")
    return con


def initialize_storage():
    """Initialize both DuckDB catalog and SQLite operational ledger."""
    db_manager.get_sqlite()  # Initializes tables if needed
    ingest_catalog()
