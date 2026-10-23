# ۲۶ — منشأ اطلاعات، منابع خارجی و حدود اعتبار

## منبع اصلی این مجموعه
- [داده] `10_SOURCE_DATA/shops.csv` (۶٬۴۷۶ رکورد)، `products.csv` (۲۲۵٬۹۰۳)، `offers.csv` (۳۳۱٬۵۰۶)، `README_from_export.txt`؛ مرجع قابل محاسبه.
- [گفت‌وگو] کل سناریوهای کاربر: نصب اپ فروشنده، استعلام قیمت/موجودی/بازبودن، یادآوری ۵/۱۰ دقیقه، اینترنت قطع، reuse تأیید، دسته‌بندی، نوسان مسیر، دلار، سن عرضه، امتیاز فروشگاه، تأیید بیرونی، فیدبک حضوری و پرونده.
- [پیشنهاد] معماری، معیارهای تصمیم، مدل‌های hazard/CTMC، سیاست‌های زمان، case workflow، KPI و API schema؛ هنوز نیازمند اعتبارسنجی میدانی‌اند.
- [فرض آزمایشی] هر عدد TTL/مهلت/success threshold بیرون از آمار CSV. **هیچ نرخ واقعی بازار از حدس ساخته نشده است.**

## منابع رسمی برای محدودیت‌های پلتفرم
1. [Android 14 full-screen intent restrictions](https://developer.android.com/about/versions/14/behavior-changes-14) — مستند رسمی Google Android؛ تأکید بر تماس و آلارم و کاهش مجوز برای اپ‌های دیگر.
2. [Apple PushKit VoIP notifications](https://developer.apple.com/documentation/pushkit/responding-to-voip-notifications-from-pushkit) — رسمی Apple؛ PushKit برای تماس واقعی VoIP و CallKit.
3. [Firebase FCM delivery](https://firebase.google.com/docs/cloud-messaging/understand-delivery) — رسمی Firebase؛ تفکیک `MESSAGE_ACCEPTED` از `MESSAGE_DELIVERED` و موانع گزارش‌شدن تحویل.
4. [Android notification permission](https://developer.android.com/develop/ui/views/notifications/notification-permission) — منبع رسمی برای رفتار مجوز اعلان Android 13+.
5. [Torob / guarantee landing](https://torob.com/landings/guarantee/) — صفحهٔ معرفی ضمانت؛ شرایط و وضعیت باید در زمان استفاده به‌صورت مجزا راستی‌آزمایی شوند. **از نشان ترب هیچ رابطه/مجوز فنی یا تضمین موجودی حضوری نتیجه نگیرید.**

## منابع روش‌شناسی برای مطالعهٔ بیشتر (موضوع، نه نتیجهٔ اندازه‌گیری داده‌های ما)
- Survival analysis و interval censoring: رخداد تغییر بین دو مشاهده.
- Change-point detection / volatility estimation: تشخیص جهش و رژیم بازار.
- Beta-Binomial و hierarchical modeling: اعتبار فروشگاه کم‌نمونه.
- Calibration / Brier score / temporal validation: ارزیابی کیفیت احتمال‌ها.
- Contextual bandit و value of information: استعلام هدفمند زیر بودجه.

## هشدار دربارهٔ دادهٔ بیرونی
این بسته هیچ امتیاز رسمی فروشگاه از ترب، هیچ دادهٔ حقیقی نرخ ارز و هیچ نتیجهٔ خرید مشتری را از اینترنت استخراج نکرده است. هر URL صرفاً برای بررسی مستندات/سیاست یا امکان راستی‌آزمایی آینده است.

## اعتبار و بازتولید
هش SHA256 منبع‌ها در `02_DATA/verified_audit.json` ثبت شده است. اعداد بدون منبع صریح در بعضی مثال‌ها «فرضی» هستند. timestamp مبنای ممیزی ثابت و مستند است. خروجی هشدارهای قیمت فقط کاندیدای بازبینی‌اند.
