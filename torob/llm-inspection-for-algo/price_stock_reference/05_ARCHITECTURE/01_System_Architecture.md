# ۱۷ — معماری سامانه، ذخیره‌سازی و قراردادهای زمانی

## ماژول‌های مفهومی (نه الزاماً مایکروسرویس)
`Catalog Ingestion` → `Entity/SKU Resolution` → `Snapshot/Event Ledger` → `Feature Store` → `Scoring` → `Decision Policy` → `Inquiry Orchestrator` → `Seller App` → `Feedback Case Manager` → بازگشت به Ledger/Training.

## زیرساخت شروع پیشنهادی
PostgreSQL برای entity/state/eventهای نسخه‌دار؛ Redis اختیاری برای TTL cache و dedupe کم‌ریسک با پایگاه داده به عنوان مرجع؛ صف وظایف برای اعلان/expire/backoff؛ Object Storage برای تصاویر مدرک با عمر محدود؛ پردازش batch برای features/ممیزی؛ سرویس API با auth و RBAC؛ گزارش‌دهی آفلاین و داشبورد مانیتورینگ.

## معماری رویدادمحور
Append-only evidence log → materialized current view. «وضعیت فعلی» نمای مشتق‌شده است؛ تغییر شواهد تاریخی را حذف نکنید. درج رویداد با `idempotency_key`، `source_event_id`, `observed_at`, `ingested_at`, `offer_version`, `scope_hash`. رویدادهای قدیمی می‌توانند دیر برسند و نباید last-write-wins کور رخ دهد.

## نسخه‌ها و consistency
`offer_versions` با hash محتوا/شرایط؛ پاسخ به نسخهٔ ثبت‌شده هنگام سؤال؛ تغییر قیمت هم‌زمان با استعلام → current projection جدید و پاسخ قبلی تاریخی. identity merges نباید به آرامی شواهد مربوط به فروشگاه دیگری را منتقل کنند. تغییر مالکیت/دامنه/شعبه/version جدا ثبت شود.

## مقیاس و هزینه
۳۳۱٬۵۰۶ پیشنهاد فعلی کوچک‌تر از مقیاس روزانهٔ بالقوهٔ رویدادهاست؛ هر مشاهدهٔ بدون تغییر را فشرده/partition کنید و materialized summaries داشته باشید. ایندکس روی `branch_id,sku_id,observed_at`, `offer_id,version`, `case_id` و pending inquiries. محدودیت نرخ api، صف تکراری و latency؛ ابتدا بار واقعی را اندازه بگیرید.

## وابستگی و lineage
هر score/recommendation باید `model_version`, `policy_version`, `feature_as_of`, `source_events_hash`, `reason_codes` داشته باشد. اگر منبع خطا کشف شد بتوان اثر آن را روی scoreها بازپخش/replay کرد.

## سیستم ساعت
UTC در ذخیره‌سازی، منطقهٔ زمانی شعبه برای ساعت کاری و تعطیلی؛ `observed_at` فروشنده می‌تواند دستکاری/clock drift داشته باشد؛ `server_received_at` هم ذخیره شود. تجارت در تعطیلات خاص باید `hours_exception` داشته باشد.

## حالت‌های degraded
- DB/queue down: عدم تأیید جعلی، request idempotency و UI «موقتاً امکان استعلام نیست»؛
- Push down: صف و expiry، fallback اختیاری، عدم جریمهٔ فروشنده؛
- Market FX down: حذف/کاهش وزن feature، افزایش uncertainty؛
- Geocoder down: نمایش آدرس اعلامی و هشدار؛
- Model unavailable: قواعد محافظه‌کار و evidence UI؛
- Dataset stale: عدم اعلام درصد تازه، flag وضعیت منبع.
