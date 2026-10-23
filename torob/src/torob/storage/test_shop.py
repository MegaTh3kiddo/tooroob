"""Seed the «فروشگاه جیمبو» test shop for end-to-end demos.

The shop is clearly a TEST fixture: it lives in the real catalogue (so search, the
assistant, price assessment and the merchant Android app all see it), but its offers
are generated from the live peer-median of well-covered products and are labelled
as test data in their description.
"""
import json
import logging
from datetime import datetime, timezone

from torob.storage.db import db_manager

logger = logging.getLogger("torob.storage.test_shop")

JIMBO_SHOP_ID = "shop_jimbo_test"
JIMBO_SHOP_NAME = "فروشگاه جیمبو"
JIMBO_SELLER_ID = "seller_jimbo"
JIMBO_SELLER_PHONE = "09120000000"
JIMBO_ADDRESS = "تهران، خیابان جمهوری، پاساژ علاءالدین، طبقهٔ سوم، واحد ۳۱۲"
JIMBO_LAT, JIMBO_LON = 35.69555, 51.40760
JIMBO_PHONE = "۰۲۱۶۶۷۰۰۰۹۹"
JIMBO_CATEGORIES = ["گوشی موبایل", "هدفون، هدست و هندزفری", "شارژر و آداپتور", "پاوربانک", "ساعت و مچ‌بند هوشمند", "لوازم جانبی موبایل"]

# (category, optional title keyword, how many products) — matched against the real catalogue
PRODUCT_QUERIES = [
    ("گوشی موبایل", "سامسونگ", 3),
    ("گوشی موبایل", "اپل", 2),
    ("گوشی موبایل", "شیائومی", 2),
    ("هدفون، هدست و هندزفری", "", 4),
    ("شارژر گوشی", "", 2),
    ("پاوربانک و شارژر همراه", "", 2),
    ("ساعت و مچ بند هوشمند", "", 2),
]
PRICE_FACTOR = 0.98  # slightly under the peer median, rounded to 1,000 toman


def _seed_catalogue(con) -> int:
    con.execute("DELETE FROM offers WHERE shop_id = ?", [JIMBO_SHOP_ID])
    con.execute("DELETE FROM shops WHERE shop_id = ?", [JIMBO_SHOP_ID])
    hours = {d: {"shifts": [{"start_time": "09:00:00", "end_time": "21:00:00"}], "status": "declared"}
             for d in ["sat", "sun", "mon", "tue", "wed", "thu"]}
    hours["fri"] = {"shifts": [{"start_time": "10:00:00", "end_time": "14:00:00"}], "status": "declared"}
    con.execute(
        """INSERT INTO shops (shop_id, name, address, lat, lon, location_label, category_names, payment_options,
                              supports_fast_delivery, website_url, weekly_hours, contacts, instagram)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [JIMBO_SHOP_ID, JIMBO_SHOP_NAME, JIMBO_ADDRESS, JIMBO_LAT, JIMBO_LON, "جمهوری",
         json.dumps(JIMBO_CATEGORIES, ensure_ascii=False), json.dumps(["torobpay"]), True, None,
         json.dumps(hours), json.dumps([{"channel": "phone", "display_number": JIMBO_PHONE}], ensure_ascii=False), None],
    )

    now = datetime.now(timezone.utc)
    picked = []
    for category, keyword, n in PRODUCT_QUERIES:
        rows = con.execute(
            """SELECT p.product_id, p.persian_title, s.peer_median_price
               FROM products p JOIN v_product_peer_stats s USING (product_id)
               WHERE p.category_name = ? AND p.persian_title LIKE ?
                 AND s.independent_shops_count >= 2 AND s.peer_median_price > 100000
               ORDER BY s.independent_shops_count DESC, p.product_id
               LIMIT ?""",
            [category, f"%{keyword}%", n + 6],
        ).fetchall()
        taken = 0
        for pid, title, median in rows:
            if taken >= n or pid in {x[0] for x in picked} or title in {x[1] for x in picked}:
                continue
            picked.append((pid, title, round(median * PRICE_FACTOR / 1000) * 1000))
            taken += 1

    for i, (pid, title, price) in enumerate(picked, 1):
        con.execute(
            """INSERT INTO offers (offer_id, product_id, shop_id, price_toman, last_price_changed_at,
                                   seller_title, warranty, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [f"offer_jimbo_{i:03d}", pid, JIMBO_SHOP_ID, float(price), now, title,
             "گارانتی ۱۸ ماهه", "فروشگاه تستی جیمبو — قیمت آزمایشی برای دمو"],
        )
    return len(picked)


def _seed_ledger(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO shop_settings
           (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode,
            category_names, lat, lon, website_url, voice_reminders_enabled)
           VALUES (?, ?, ?, ?, 1, '09:00', '21:00', 1, 0, ?, ?, ?, NULL, 1)""",
        (JIMBO_SHOP_ID, JIMBO_SHOP_NAME, JIMBO_ADDRESS, JIMBO_PHONE,
         json.dumps(JIMBO_CATEGORIES, ensure_ascii=False), JIMBO_LAT, JIMBO_LON),
    )
    cur.execute(
        """INSERT OR REPLACE INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
           VALUES (?, ?, ?, ?, 1)""",
        (JIMBO_SELLER_ID, JIMBO_SELLER_PHONE, JIMBO_SHOP_ID, "مدیر فروشگاه جیمبو"),
    )
    conn.commit()


def seed_jimbo_test_shop() -> int:
    """Idempotently (re)create the Jimbo test shop. Returns the number of seeded offers."""
    n = _seed_catalogue(db_manager.get_duckdb())
    _seed_ledger(db_manager.get_sqlite())
    logger.info(f"Seeded test shop «{JIMBO_SHOP_NAME}» with {n} offers.")
    return n
