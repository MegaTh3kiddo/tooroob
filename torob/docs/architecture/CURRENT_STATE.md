# وضعیت کنونی مخزن و دارایی‌های موجود (Current State Audit)

**تاریخ تحلیل:** ۲۳ اکتبر ۲۰۲۶  
**دامنه:** مخزن [`/root/starcoach-hack/torob`](file:///root/starcoach-hack/torob)  
**چارچوب:** هکاتون هوش مصنوعی استارکوچ — بخش سامانهٔ اعتبارسنجی قیمت، موجودی و امکان خرید حضوری ترب  

---

## ۱. نمای کلی دارایی‌های موجود در مخزن

پروژه در حال حاضر از سه بخش کامپوننت تشکیل شده است:

```
torob/
├── data/                               # داده‌های خام واقعی اسنپ‌شات استارکوچ v16
│   ├── products.csv                   # ۲۲۵٬۹۰۳ محصول (~196 MB)
│   ├── offers.csv                     # ۳۳۱٬۵۰۶ پیشنهاد قیمت (~80 MB)
│   ├── shops.csv                      # ۶٬۴۷۶ فروشگاه حضوری (~9.2 MB)
│   └── README.txt                     # مشخصات سقف ۳۰۰ کالا و فرمت داده
│
├── nearest-price-ui-example/          # پروتوتایپ ایزوله فرانت‌اند (Read-Only)
│   ├── index.html                     # رابط وب فارسی راست‌چین با نقشه Leaflet
│   ├── css/style.css                  # استایل‌های تم دارک/لایت، کارت‌ها و نقشه
│   └── js/                            # منطق کلاینت با دیتای ساختگی (app, data, map, plan, art)
│
├── llm-inspection-for-algo/           # مستندات مرجع، رجیسترها و کدهای الگو
│   ├── torob.html                     # نسخهٔ یکپارچه HTML از کل اسناد
│   └── price_stock_reference/         # ۱۲ پوشه سرفصل معماری، الگوریتم، داده و کیفیت
│       ├── 00_START/                  # خلاصه مدیریتی، تعاریف و ماتریس پوشش ۵۱ ایده
│       ├── 01_PRODUCT/                # PRD، سناریوهای کاربر، دامنه تأیید
│       ├── 02_DATA/                   # آدیت بازتولیدپذیر، فرهنگ داده، verified_audit.json
│       ├── 03_ALGORITHMS/             # ۶ سند تخصصی الگوریتم‌های قیمت، موجودی، نوسان، اعتماد و استعلام
│       ├── 04_WORKFLOWS/              # ماشین حالت استعلام، فیدبک مشتری و اپ فروشنده
│       ├── 05_ARCHITECTURE/           # معماری داده، قراردادهای API و امنیت
│       ├── 06_QUALITY/                # رجیستر ۱۸۰ سناریوی مرزی (edge_case_register.csv) و استراتژی تست
│       ├── 07_DELIVERY/               # نقشه راه، شاخص‌های ارزیابی و ADRها
│       ├── 08_REFERENCES/             # منشأ اطلاعات و منابع رسمی
│       ├── 09_EXAMPLES/               # نمونه‌های تصمیم‌گیری گام‌به‌گام
│       ├── 10_SOURCE_DATA/            # راهنما و فایل‌های تکمیلی داده
│       └── 11_CODE/                   # کدهای مرجع، اسکیما SQL و تست‌های پایه‌ای
│
└── .gitignore                         # تنظیم‌شده برای جلوگیری از کامیت فایل‌های حجیم CSV
```

---

## ۲. ارزیابی دقیق داده‌های واقعی (`data/`)

ممیزی انجام‌شده روی داده‌ها حقایق زیر را اثبات می‌کند:

| مؤلفه | تعداد ردیف | حجم فایل | وضعیت و مشاهدات کلیدی |
|---|---:|---:|---|
| **فروشگاه‌ها (`shops.csv`)** | ۶٬۴۷۶ | ۹.۲ مگابایت | همه دارای مختصات جغرافیایی `lat` و `lon`؛ ۴٬۴۷۳ فروشگاه دارای ساعت کاری معتبر و ۲٬۰۰۳ فروشگاه ساعت کاری خالی یا `{}`؛ تنها ۹۰ فروشگاه دارای وب‌سایت ثبت‌شده هستند. |
| **محصولات (`products.csv`)** | ۲۲۵٬۹۰۳ | ۱۹۶ مگابایت | ۳٬۴۲۸ دسته‌بندی متمایز؛ ۱۴۴٬۵۹۹ محصول دارای ویژگی ساختاریافته (specs)؛ ۴٬۰۵۶ محصول دارای فیلد صریح `model`؛ تنوع گسترده در عناوین فارسی و انگلیسی. |
| **پیشنهادها (`offers.csv`)** | ۳۳۱٬۵۰۶ | ۸۰ مگابایت | ۳۱۱٬۱۹۱ زوج یکتای فروشگاه-محصول؛ ۳۱۶٬۴۲۳ رکورد قیمت عددی؛ ۱۵٬۰۸۳ رکورد قیمت null؛ ۶۳۵ رکورد قیمت یک تومانی (Sentinel)؛ ۱٬۶۴۵ رکورد کمتر از ۱٬۰۰۰ تومان؛ ۱۲۶ رکورد بالای ۱ تریلیون تومان. |

### محدودیت‌های بنیادین داده‌های فعلی (Data Limitations)
1. **اسنپ‌شات در برابر سری زمانی:** داده‌های موجود یک خروجی مقطعی (Snapshot) هستند؛ فیلد `last_price_changed_at` فقط زمان «آخرین تغییر قیمت» است، نه زمان مشاهده، خزش (crawl) یا تأیید توسط فروشگاه.
2. **عدم وجود تاریخچهٔ تراکنش و موجودی:** هیچ لاگ رسمی از خریدوفروش، خروج کالا از انبار، یا شارژ مجدد در این فایل‌ها موجود نیست.
3. **پدیدار شدن سقف فروشگاه (Cap-300 Censoring):** طبق مستندات، هر فروشگاه حداکثر با ۳۰۰ محصول در خروجی آمده است؛ ۴۶۱ فروشگاه دقیقاً به سقف ۳۰۰ رسیده‌اند. بنابراین نبودن کالایی از یک فروشگاه دلیلی بر عدم فروش آن کالا در آن فروشگاه نیست.
4. **تسلط کالاهای تک‌فروشنده:** ۱۹۰٬۶۴۹ محصول (۸۴.۴٪) تنها توسط یک فروشگاه عرضه شده‌اند و فقط ۳۵٬۲۵۴ محصول (۱۵.۶٪) حداقل دو فروشنده دارند. این یعنی برای اکثر کالاها نمی‌توان قیمت همتایان بازار (Peer Comparison) را مستقیماً محاسبه کرد و نیازمند رویکرد سلسله‌مراتبی دسته‌ای (Hierarchical Fallback) هستیم.

---

## ۳. ارزیابی کدهای پایتون و ابزارهای موجود (`11_CODE/`)

در پوشهٔ [`llm-inspection-for-algo/price_stock_reference/11_CODE`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE) موارد زیر بررسی شدند:

1. **[`baseline_reference.py`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/baseline_reference.py):**
   * یک پیاده‌سازی مینیمال بر پایه قواعد اکتشافی (Heuristics) با استفاده از `dataclasses` پایتون استاندارد.
   * کلاس‌های [`OfferEvidence`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/baseline_reference.py#L9-L23) و [`Decision`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/baseline_reference.py#L24-L30) را تعریف کرده و تابع [`decide()`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/baseline_reference.py#L32-L58) اقداماتی مثل `show_evidence`, `show_warning`, `enqueue_inquiry` را با امتیاز ریسک محاسبه می‌کند.
   * آزمون‌های آن در [`test_baseline.py`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/test_baseline.py) با موفقیت پاس شدند (۷ آزمون).
   * **محدودیت:** فاقد اتصال به دیتابیس، فاقد مدیریت همزمانی، فاقد وب‌سرویس و API، و متکی به متغیرهای دستی درون حافظه.

2. **[`schema.sql`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/schema.sql):**
   * ساختار DDL مفهومی پستگرس شامل ۱۲ جدول: `shop_branches`, `sku_variants`, `offers_current`, `evidence_events`, `inquiries`, `inquiry_subscribers`, `inquiry_delivery_attempts`, `inquiry_responses`, `feedback_cases`, `feedback_case_events`, `external_trust_evidence`, `predictions`, `policy_decisions`.
   * یک پایگاه مدل رویدادمحور و Ledger-based عالی برای طراحی مدل‌های دامنه‌ای.

3. **[`sample_policy.yaml`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/sample_policy.yaml):**
   * پیکربندی قوانین کسب‌وکار، حدود نوسان قیمت، بازه‌های یادآوری اعلان، فیلترهای کیفیت قیمت، و تنظیمات اکتشافی.

4. **[`evidence.schema.json`](file:///root/starcoach-hack/torob/llm-inspection-for-algo/price_stock_reference/11_CODE/evidence.schema.json):**
   * اسکیما JSON Schema برای استانداردسازی رویدادهای مشاهده، منابع، تایم‌استمپ‌ها و امضاهای اعتبارسنجی.

---

## ۴. وضعیت فرانت‌اند (`nearest-price-ui-example/`)

فرانت‌اند موجود یک پروتوتایپ کامل کلاینت با جاوااسکریپت وانیلا و CSS است که:
* دارای ۸ فروشگاه هاردکدشده (`s1` تا `s8`) در محدوده مرکزی تهران است.
* دارای ۵ دسته‌بندی با تعداد محدودی پیشنهاد قیمت فیک است.
* لاجیک مسیریابی تقریبی پیاده‌سازی شده در [`js/plan.js`](file:///root/starcoach-hack/torob/nearest-price-ui-example/js/plan.js) از ضریب ۱.۳ روی فاصله اقلیدسی استفاده می‌کند و توقف‌ها را بر اساس زمان بسته‌شدن مرتب می‌سازد.
* **مطابق دستور کاربر:** فرانت‌اند به عنوان دارایی **فقط‌خواندنی (Read-Only)** حفظ می‌شود و بک‌اند مستقل و کامل برای اتصال بعدی ساخته خواهد شد.

---

## ۵. خلاصه وضعیت محیط اجرا

* پایتون: `Python 3.12.3`
* پکیج‌های نصب‌شده در محیط ایزولهٔ پروژه ([`.venv`](file:///root/starcoach-hack/torob/.venv)): `fastapi 0.115.2`, `pydantic 2.8.2`, `duckdb 2.0.0`, `sqlite3` (built-in), `pytest 8.2.0`, `uvicorn 0.54.0`, `httpx 0.28.1`, `pyyaml 6.0.1`.
* پکیج‌های عملیاتی به طور کامل آمادهٔ اجرای سریع و تحلیل ستونی روی ۳۳۱ هزار ردیف هستند.
