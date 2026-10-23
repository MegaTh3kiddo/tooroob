import sqlite3
import os
import json
import csv
from datetime import datetime
from config import settings

def get_db():
    """Get SQLite connection with WAL mode and row factory."""
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Initialize SQLite database tables and migrations."""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Sellers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        seller_id TEXT PRIMARY KEY,
        phone_number TEXT UNIQUE NOT NULL,
        shop_id TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 2. Seller Devices & Push Tokens
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seller_devices (
        device_id TEXT PRIMARY KEY,
        seller_id TEXT NOT NULL,
        fcm_token TEXT UNIQUE NOT NULL,
        device_model TEXT,
        os_version TEXT,
        app_version TEXT,
        notifications_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
    )
    """)

    # 3. Inquiries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inquiries (
        inquiry_id TEXT PRIMARY KEY,
        tracking_code TEXT UNIQUE NOT NULL,
        shop_id TEXT NOT NULL,
        product_id TEXT,
        product_title TEXT NOT NULL,
        product_image_url TEXT,
        category_name TEXT,
        recorded_price_toman INTEGER DEFAULT 0,
        customer_name TEXT NOT NULL,
        customer_phone TEXT,
        inquiry_type TEXT NOT NULL, -- 'price_and_stock', 'specs', 'installment'
        user_note TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'ANSWERED', 'EXPIRED', 'TRANSFERRED'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    )
    """)

    # 4. Inquiry Responses (with client_response_id for offline idempotency)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inquiry_responses (
        response_id TEXT PRIMARY KEY,
        client_response_id TEXT UNIQUE NOT NULL,
        inquiry_id TEXT NOT NULL,
        seller_id TEXT NOT NULL,
        shop_id TEXT NOT NULL,
        offered_price_toman INTEGER NOT NULL,
        is_in_stock INTEGER NOT NULL, -- 1 = in stock, 0 = out of stock
        stock_count INTEGER DEFAULT 1,
        notes TEXT,
        submitted_at TIMESTAMP NOT NULL, -- timestamp on device
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- timestamp on server
        FOREIGN KEY (inquiry_id) REFERENCES inquiries(inquiry_id),
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
    )
    """)

    # Safe migration for existing DB
    try:
        cursor.execute("ALTER TABLE inquiry_responses ADD COLUMN stock_count INTEGER DEFAULT 1")
    except Exception:
        pass

    # 5. Push Notification Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS push_audit_logs (
        log_id TEXT PRIMARY KEY,
        inquiry_id TEXT,
        shop_id TEXT,
        fcm_token TEXT,
        notification_type TEXT NOT NULL, -- 'INITIAL_INQUIRY', 'REMINDER_5MIN', 'EXPIRATION_ALERT', 'TEST_PING'
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        payload_json TEXT,
        status TEXT NOT NULL, -- 'DELIVERED', 'FAILED', 'SIMULATED'
        error_detail TEXT,
        dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 6. Inquiry Timing & SLA Timelines
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inquiry_timelines (
        inquiry_id TEXT PRIMARY KEY,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        initial_push_at TIMESTAMP,
        reminder_push_at TIMESTAMP,
        seller_viewed_at TIMESTAMP,
        seller_responded_at TIMESTAMP,
        response_time_seconds INTEGER,
        expired_at TIMESTAMP,
        alternative_shop_id TEXT,
        FOREIGN KEY (inquiry_id) REFERENCES inquiries(inquiry_id)
    )
    """)

    # 7. Shop Operating Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_settings (
        shop_id TEXT PRIMARY KEY,
        shop_name TEXT,
        address TEXT,
        phone TEXT,
        is_open INTEGER DEFAULT 1,
        open_time TEXT DEFAULT '09:00',
        close_time TEXT DEFAULT '21:00',
        accept_inquiries INTEGER DEFAULT 1,
        holiday_mode INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 8. Dynamic Scheduler Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduler_configs (
        config_key TEXT PRIMARY KEY,
        config_value TEXT NOT NULL,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 9. Shop Change Requests Table (Support Approval Workflow)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_change_requests (
        request_id TEXT PRIMARY KEY,
        shop_id TEXT NOT NULL,
        seller_id TEXT NOT NULL,
        requested_shop_name TEXT,
        requested_phone TEXT,
        requested_address TEXT,
        requested_open_time TEXT,
        requested_close_time TEXT,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        review_notes TEXT,
        FOREIGN KEY (shop_id) REFERENCES shop_settings(shop_id),
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
    )
    """)

    # 10. Outbound Call Audit Logs (Poshteyar & Voice Notifications)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outbound_call_logs (
        call_id TEXT PRIMARY KEY,
        scenario_type TEXT NOT NULL, -- 'LANDLINE_OTP', 'UNANSWERED_INQUIRY_REMINDER'
        destination_number TEXT NOT NULL, -- clean / masked destination number (NEVER stores plaintext OTP)
        provider TEXT NOT NULL, -- 'poshteyar', 'mock', etc.
        provider_call_id TEXT,
        status TEXT NOT NULL, -- 'PENDING', 'CALL_REQUESTED', 'CALLING', 'ANSWERED', 'BUSY', 'NO_ANSWER', 'FAILED', 'COMPLETED'
        shop_id TEXT,
        error_code TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Safe migration for shop_settings extra columns
    for col, col_type in [
        ("category_names", "TEXT"),
        ("lat", "REAL"),
        ("lon", "REAL"),
        ("website_url", "TEXT"),
        ("voice_reminders_enabled", "INTEGER DEFAULT 1")
    ]:
        try:
            cursor.execute(f"ALTER TABLE shop_settings ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Safe migrations for inquiries extra columns
    for col, col_type in [
        ("decline_reason", "TEXT"),
        ("offered_price_toman", "INTEGER"),
        ("is_in_stock", "INTEGER"),
        ("response_notes", "TEXT")
    ]:
        try:
            cursor.execute(f"ALTER TABLE inquiries ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Safe migration for inquiry_responses decline_reason and status
    try:
        cursor.execute("ALTER TABLE inquiry_responses ADD COLUMN decline_reason TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE inquiry_responses ADD COLUMN status TEXT")
    except Exception:
        pass

    # Safe migration for inquiry_timelines urgent_call_push_at
    try:
        cursor.execute("ALTER TABLE inquiry_timelines ADD COLUMN urgent_call_push_at TIMESTAMP")
    except Exception:
        pass

    # Seed default scheduler configs
    cursor.execute("""
    INSERT OR IGNORE INTO scheduler_configs (config_key, config_value, description)
    VALUES
        ('reminder_timeout_seconds', '300', 'Time in seconds after creation to send reminder push'),
        ('expiration_timeout_seconds', '600', 'Time in seconds after creation to expire inquiry'),
        ('voice_reminder_eval_window_minutes', '1440', 'Evaluation window in minutes for unanswered inquiries'),
        ('voice_reminder_min_eligible', '10', 'Minimum inquiries in window to qualify for voice reminder'),
        ('voice_reminder_min_unanswered', '6', 'Minimum unanswered inquiries in window to trigger reminder'),
        ('voice_reminder_min_unanswered_rate', '0.6', 'Minimum ratio of unanswered inquiries (0.6 = 60%)'),
        ('voice_reminder_cooldown_minutes', '1440', 'Minimum minutes between reminder calls to the same store')
    """)

    # Seed shops from dataset if table has fewer than 10 rows
    cursor.execute("SELECT COUNT(*) FROM shop_settings")
    shop_count = cursor.fetchone()[0]
    if shop_count < 10:
        csv_path = os.path.join(os.path.dirname(__file__), "data", "shops.csv")
        if os.path.exists(csv_path):
            shops_to_insert = []
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = row.get('shop_id')
                    name = row.get('name')
                    if not sid or not name:
                        continue
                    addr = row.get('address') or ''
                    phone = ''
                    contacts_raw = row.get('contacts')
                    if contacts_raw:
                        try:
                            c_list = json.loads(contacts_raw)
                            if isinstance(c_list, list) and len(c_list) > 0:
                                phone = c_list[0].get('display_number') or c_list[0].get('phone') or ''
                        except Exception:
                            pass
                    
                    shops_to_insert.append((
                        sid, name, addr, phone, 1, '09:00', '21:00', 1, 0,
                        row.get('category_names'),
                        float(row['lat']) if row.get('lat') else None,
                        float(row['lon']) if row.get('lon') else None,
                        row.get('website_url')
                    ))

            cursor.executemany("""
            INSERT OR REPLACE INTO shop_settings 
            (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, category_names, lat, lon, website_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, shops_to_insert)

    # Seed default sample seller (Ali Rezaei - Mob Takht Jamshid)
    cursor.execute("""
    INSERT OR IGNORE INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
    VALUES ('seller_test_001', '09123456789', 'shop_51d0c1a6edf81ba759726bab', 'علی رضایی', 1)
    """)

    # Seed new development seller & shop (Ali Fazelniya - Computer Store)
    fazel_shop_id = "shop_fazel_computer"
    fazel_phone = "09134257815"
    fazel_seller_id = "seller_ali_fazelnya"
    fazel_name = "علی فاضل نیا"

    cursor.execute("""
    INSERT OR REPLACE INTO shop_settings 
    (shop_id, shop_name, address, phone, is_open, open_time, close_time, accept_inquiries, holiday_mode, category_names, website_url)
    VALUES (?, ?, ?, ?, 1, '09:00', '22:00', 1, 0, ?, ?)
    """, (
        fazel_shop_id,
        "فروشگاه کامپیوتر و سخت‌افزار فاضل‌نیا",
        "اصفهان، خیابان طالقانی، مجتمع کامپیوتر طالقانی، طبقه اول، واحد ۱۲",
        "۰۳۱۳۲۲۲۴۴۵۵",
        '["قطعات کامپیوتر","لپ‌تاپ و تجهیزات اداری","لوازم جانبی کامپیوتر","تجهیزات شبکه"]',
        "https://fazel-computer.ir"
    ))

    cursor.execute("""
    INSERT OR REPLACE INTO sellers (seller_id, phone_number, shop_id, full_name, is_active)
    VALUES (?, ?, ?, ?, 1)
    """, (fazel_seller_id, fazel_phone, fazel_shop_id, fazel_name))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
