import gzip
import csv
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from torob.core.config import settings
from torob.storage.db import db_manager

logger = logging.getLogger("merchant_import")


def seed_scheduler_configs(conn: sqlite3.Connection):
    """Seed dynamic inquiry scheduler configuration thresholds."""
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO scheduler_configs (config_key, config_value, description)
    VALUES
        ('reminder_timeout_seconds', '300', 'Time in seconds after creation to send reminder push (5 min)'),
        ('expiration_timeout_seconds', '600', 'Time in seconds after creation to expire inquiry (10 min)'),
        ('urgent_call_remaining_seconds', '120', 'Time in seconds remaining before expiration to ring urgent call (2 min)'),
        ('voice_reminder_eval_window_minutes', '1440', 'Evaluation window in minutes for unanswered inquiries'),
        ('voice_reminder_min_eligible', '10', 'Minimum inquiries in window to qualify for voice reminder'),
        ('voice_reminder_min_unanswered', '6', 'Minimum unanswered inquiries in window to trigger reminder'),
        ('voice_reminder_min_unanswered_rate', '0.6', 'Minimum ratio of unanswered inquiries (0.6 = 60%)'),
        ('voice_reminder_cooldown_minutes', '1440', 'Minimum minutes between reminder calls to the same store')
    """)
    conn.commit()


def seed_shops_settings(conn: sqlite3.Connection, csv_path: Optional[Path] = None):
    """Import shops into shop_settings from shops.csv if shop_settings has fewer than 10 rows."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM shop_settings")
    count = cursor.fetchone()[0]
    if count >= 10:
        logger.info(f"shop_settings already contains {count} records, skipping bulk CSV import.")
        return

    # Find shops.csv in project data directory or merchant app data
    candidates = [
        csv_path,
        settings.data_dir / "shops.csv",
        settings.data_dir / "shops.csv.gz",
        Path("/root/starcoach-hack/torob/data/shops.csv"),
        Path("/root/starcoach-hack/torob_merchant_app/backend/data/shops.csv"),
    ]
    actual_path = None
    for cand in candidates:
        if cand and cand.exists():
            actual_path = cand
            break

    if not actual_path:
        logger.warning("shops.csv not found for seeding shop_settings.")
        return

    logger.info(f"Importing shops into shop_settings from {actual_path}...")
    shops_to_insert = []
    opener = gzip.open if actual_path.suffix == ".gz" else open
    with opener(actual_path, mode="rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get("shop_id")
            name = row.get("name")
            if not sid or not name:
                continue
            addr = row.get("address") or ""
            phone = ""
            contacts_raw = row.get("contacts")
            if contacts_raw:
                try:
                    c_list = json.loads(contacts_raw)
                    if isinstance(c_list, list) and len(c_list) > 0:
                        first = c_list[0]
                        phone = first.get("display_number") or first.get("phone") or ""
                except Exception:
                    pass

            lat = float(row["lat"]) if row.get("lat") else None
            lon = float(row["lon"]) if row.get("lon") else None
            cat_names = row.get("category_names")
            web_url = row.get("website_url")

            shops_to_insert.append((
                sid, name, addr, phone, 1, "09:00", "21:00", 1, 0,
                cat_names, lat, lon, web_url, 1
            ))

    cursor.executemany("""
    INSERT OR REPLACE INTO shop_settings 
    (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, category_names, lat, lon, website_url, voice_reminders_enabled)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, shops_to_insert)
    conn.commit()
    logger.info(f"Imported {len(shops_to_insert)} shops into shop_settings.")


def seed_demo_sellers_and_shops(conn: sqlite3.Connection):
    """Seed baseline demo sellers and development shops."""
    cursor = conn.cursor()

    # 1. Fazel Computer Store
    fazel_shop_id = "shop_fazel_computer"
    cursor.execute("""
    INSERT OR REPLACE INTO shop_settings 
    (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, category_names, lat, lon, website_url, voice_reminders_enabled)
    VALUES (?, ?, ?, ?, 1, '09:00', '22:00', 1, 0, ?, 32.6577, 51.6692, ?, 1)
    """, (
        fazel_shop_id,
        "فروشگاه کامپیوتر و سخت‌افزار فاضل‌نیا",
        "اصفهان، خیابان طالقانی، مجتمع کامپیوتر طالقانی، طبقه اول، واحد ۱۲",
        "۰۳۱۳۲۲۲۴۴۵۵",
        '["قطعات کامپیوتر","لپ‌تاپ و تجهیزات اداری","لوازم جانبی کامپیوتر","تجهیزات شبکه"]',
        "https://fazel-computer.ir"
    ))

    # Ali Fazelniya seller
    cursor.execute("""
    INSERT OR REPLACE INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
    VALUES (?, ?, ?, ?, 1)
    """, ("seller_ali_fazelnya", "09134257815", fazel_shop_id, "علی فاضل نیا"))

    # 2. Ali Rezaei (Demo Takht Jamshid Shop)
    demo_shop_id = "shop_51d0c1a6edf81ba759726bab"
    # Ensure this shop exists in shop_settings
    cursor.execute("SELECT shop_id FROM shop_settings WHERE shop_id = ?", (demo_shop_id,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT OR REPLACE INTO shop_settings
        (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, category_names, lat, lon, voice_reminders_enabled)
        VALUES (?, 'موبایل تخت جمشید', 'تهران، خیابان جمهوری، پاساژ علاءالدین', '02166700001', 1, '09:00', '21:00', 1, 0, '["گوشی موبایل","لوازم جانبی"]', 35.6942, 51.4081, 1)
        """, (demo_shop_id,))

    cursor.execute("""
    INSERT OR REPLACE INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
    VALUES (?, ?, ?, ?, 1)
    """, ("seller_test_001", "09123456789", demo_shop_id, "علی رضایی"))

    # 3. Seed Demo Customer Profile
    cursor.execute("""
    INSERT OR REPLACE INTO customer_profiles (
        customer_id, display_name, phone, email, preferred_city, default_travel_mode, plan_tier, photo_url, preferences_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "cust_demo_01",
        "مهدی رضایی",
        "09121234567",
        "customer@torob.demo",
        "Tehran",
        "DRIVING",
        "free",
        "img/avatar.svg",
        json.dumps({"theme": "light", "max_walking_minutes": 15, "notifications_enabled": True})
    ))

    conn.commit()


def seed_all_merchant_data(conn: Optional[sqlite3.Connection] = None):
    """One-stop seeder for merchant settings, default sellers, configs, and customer demo profiles."""
    owns_conn = False
    if conn is None:
        conn = db_manager.get_sqlite()
        owns_conn = False

    try:
        seed_scheduler_configs(conn)
        seed_shops_settings(conn)
        seed_demo_sellers_and_shops(conn)
        logger.info("Successfully completed merchant & customer seed.")
    except Exception as e:
        logger.error(f"Error during merchant data seeding: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_all_merchant_data()
    print("Merchant data seeded successfully into torob_ledger.db")
