# ۲۳ — نقشهٔ راه پیشنهادی، وابستگی‌ها و ترتیب ساخت

**اصل:** تاریخ/هفته‌های زیر تعهد زمانی نیستند؛ ترتیب پیشنهادی بر اساس وابستگی فنی و داده‌ای است. زمان‌بندی پروژه بدون اطلاع از تیم، بودجه و وضعیت اپ فعلی قابل برآورد معتبر نیست.

## فاز ۰ — آماده‌سازی داده و مفاهیم
- قرارداد Offer/SKU/Variant/Branch/Channel/PriceType/StockState و `verification_scope`؛
- ممیزی داده، برچسب اختلال و کاهش false anomaly؛
- timestampهای `seen/changed/verified/observed/ingested`؛
- event ledger، versioning، traceability، سیاست retention؛
- تعریف outcome های قیمت، موجودی، مراجعه، آدرس و فیدبک.
**Definition of Done:** هر مشاهده و اقدام قابل بازپخش تا SKU دقیق، branch و source باشد؛ وضعیت unknown با false تفاوت داشته باشد.

## فاز ۱ — MVP قابل‌استفاده
- baseline data quality و ریسک توضیح‌پذیر در خانواده‌های منتخب؛
- seller onboarding و notification inbox/quiet hours/batching؛
- پاسخ قیمت، موجودی و بازبودن جدا؛
- dedupe, retries, expiry, offline sync و عدم جریمهٔ پاسخ ندادن؛
- UI مشتری با آخرین تأیید و مدت اعتبار، درخواست قبل از مراجعه؛
- فیدبک مثبت/منفی و پیگیری اولیه؛
- داشبورد کیفیت، لاگ تصمیم‌ها، sample audit.
**گروه‌های پایلوت:** گوشی، قطعات کامپیوتر، یک دستهٔ صنعتی/کابل. اندازهٔ نمونه باید با پوشش واقعی CSV و مشارکت فروشندگان تعیین شود.

## فاز ۲ — قابلیت اعتماد داده و مدل‌های ساده
- history واقعی snapshots و فروش/شارژ اختیاری؛
- معتبرسازی بیرونی نشان‌ها همراه تاریخ و دامنه؛
- محاسبهٔ ابعاد اعتبار فروشگاه با prior و shrinkage؛
- فیدبک case management کامل، حق اعتراض و منشأ خطا؛
- قیمت مرجع leave-one-shop-out، volatility و lifecycle اولیه؛
- احتمال‌های آموزش‌دیده فقط در گروه‌های دارای دادهٔ کافی منتشر شوند.
**Definition of Done:** ارزیابی out-of-time، calibration و گزارش تفکیکی + کاهش بار اعلان.

## فاز ۳ — هوشمندسازی عمیق
- survival/hazard قیمت، CTMC/stock replenishment، احتمال در ETA؛
- regime detector، بازار FX و supplier clusters؛
- ارزش اطلاعات و policy adaptation/experimentation؛
- اتصال اختیاری POS و رزرو، بهبود اقدام خودکار کم‌مزاحمت؛
- مانیتورینگ drift، fairness و incident review.

## تحویل‌های پیشنهادی Epic
E1 Entity matching; E2 Evidence and snapshots; E3 Merchant app; E4 Inquiry orchestrator; E5 Buyer trust UI; E6 Feedback case workflow; E7 Data audit dashboard; E8 Scoring; E9 Experimentation; E10 Governance/Security. هر epic باید مالک، هزینه، Definition of Done و تست P0 داشته باشد.

## الزامات قبل از انتشار عمومی
بررسی سیاست پلتفرم نوتیفیکیشن، مجوز مصرف نشان/منبع، فرآیند رسیدگی و شکایت، نگهداری شواهد، وضعیت‌های عدم‌قطعیت، چند شعبه، SLA عملیاتی و امکان opt-out.
