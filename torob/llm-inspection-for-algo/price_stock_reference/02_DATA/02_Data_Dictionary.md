# ۰۷ — فرهنگ دادهٔ موجود و شکاف‌های داده

## فایل `shops.csv` (۱۳ ستون)
| ستون | معنا | توجه |
|---|---|---|
| `shop_id` | شناسهٔ فروشگاه در خروجی | معادل branch_id تأیید نشده |
| `name` | نام فروشگاه | برای identity resolution ناکافی |
| `address` | آدرس متن | طبقه/واحد/شماره ممکن است قدیمی باشد |
| `lat`, `lon` | مختصات | وجود ≠ صحت مکانی |
| `location_label` | برچسب محله/موقعیت | اطلاعات کمکی |
| `contacts` | کانال‌های تماس، JSON رشته‌ای | شماره/راه ارتباط شخصی محسوب نشود بدون بررسی |
| `instagram` | حساب اجتماعی | ممکن است null |
| `website_url` | دامنه ثبت‌شده | پوشش اندک؛ نبود ≠ نبود سایت |
| `weekly_hours` | ساعت هفتگی، JSON رشته‌ای | تعطیلی استثنایی/بازبودن فعلی ندارد |
| `category_names` | مجموعه دسته‌ها | هم‌پوشانی و طبقه‌بندی فروشگاه |
| `payment_options` | روش‌های پرداخت | صرفاً اظهار/منبع |
| `supports_fast_delivery` | ارسال سریع | null/اعلامی |

## `products.csv` (۷ ستون)
`product_id`, `persian_title`, `brand_name`, `model`, `category_name`, `specs`, `image_urls`. بخش `specs`، JSON ساختاریافته اما متنوع است؛ `model` عمدتاً خالی است. مشخصات باید با OCR یا تصویر حدسی تکمیل نشوند مگر فرایند اعتبارسنجی جدا؛ عنوان/متن ممکن است ناقص یا مبهم باشد.

## `offers.csv` (۸ ستون)
`offer_id`, `product_id`, `shop_id`, `seller_title`, `description`, `warranty`, `price_toman`, `last_price_changed_at`. این داده نوع قیمت، قیمت واقعی معامله، نوع کانال، وضعیت حضوری، موجودی و تعداد ندارد. `last_price_changed_at` را به زمان تأیید rename نکنید.

## مقادیر مفقود و JSON
صادرکننده `null` را به‌صورت رشته می‌نویسد و آرایه‌ها/آبجکت‌ها را JSON فشرده در CSV ذخیره می‌کند. در ETL ابتدا nullها normalize شوند و سپس JSON با schema validation و ثبت خطای parse باز شوند.

## موجودیت‌های پیشنهادی جدید
- `shop_legal_entity`, `shop_branch`, `shop_channel`, `shop_identity_evidence`؛
- `sku_variant`, `offer_terms`, `offer_versions`؛
- `offer_observation`, `market_price_observation`, `stock_observation`, `shop_presence_observation`؛
- `inquiry`, `inquiry_delivery_attempt`, `inquiry_response`, `inquiry_subscriber`؛
- `feedback_report`, `feedback_case`, `case_action`, `case_evidence`, `case_appeal`؛
- `external_trust_evidence`, `shop_reliability_dimension`, `model_prediction`, `decision_log`؛
- `market_fx_snapshot`, `market_regime_event`, `product_lifecycle_signal`؛
- `outlet_business_hours_exception`, `seller_device`, `notification_preferences`.

## زمان‌های استاندارد
`event_time/observed_at` (واقعاً چه وقت مشاهده شد)، `ingested_at` (سرور چه وقت دریافت کرد)، `last_changed_at` (آخرین تغییر شناخته‌شده)، `verified_at` (زمان تأیید)، `valid_until` (انقضای حقوقی/عملیاتی)، `decision_at` (زمان پیش‌بینی). همه timestampها UTC ذخیره و با منطقهٔ زمانی شعبه نمایش داده شوند؛ زمان مشاهدهٔ ادعایی منبع می‌تواند نیازمند تأیید باشد.

## شناسه و ارتباطات
هویت فروشگاه و شعبه با `shop_id` صرفاً پوشش داده نمی‌شود؛ دامنهٔ اینترنتی، تلفن، نشانی، حساب اپ و مالک حقوقی ممکن است یک‌به‌چند باشند. تغییر مالکیت شعبه و انتقال آدرس باید versioned و قابل بازگشت باشد.
