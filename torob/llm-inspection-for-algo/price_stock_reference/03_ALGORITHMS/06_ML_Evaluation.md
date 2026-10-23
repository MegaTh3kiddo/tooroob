# ۱۳ — معماری یادگیری، کالیبراسیون و آزمون علمی

## نردبان بلوغ
**سطح ۰: قواعد کنترل کیفیت و استعلام** — بدون ادعای احتمال.  
**سطح ۱: نرخ‌های تجربی** — confidence intervals با prior خانواده و دادهٔ تصادفی.  
**سطح ۲: مدل‌های داده‌محور** — Logistic/GBDT و calibration برای قیمت/موجودی، survival/hazard برای زمان.  
**سطح ۳: تصمیم‌گیری علّی/آزمایش‌محور** — contextual bandit یا value of information با محافظ‌های ایمنی/عدالت.

## برچسب‌ها و حقیقت مستقل
`price_valid_exact_scope`, `stock_sellable_at_observation`, `shop_open_at_visit`, `fulfillment_possible_at_arrival`, `address_correct_at_visit`؛ هر برچسب شامل زمان مشاهده، نسخهٔ پیشنهاد، میزان شواهد و منبع است. گزارش فروشنده source است نه gold label خودکار؛ بازخورد مشتری هم نیازمند کیفیت/راستی‌آزمایی است. موفقیت خرید ≠ فقط وقوع تراکنش؛ ممکن است مشتری منصرف شده باشد.

## شیوهٔ تقسیم داده
برای پیش‌بینی آینده از temporal holdout با purge/embargo در رویدادهای مرتبط، جلوگیری از leakage میان snapshotهای یک offer؛ ارزیابی جدا برای محصولات جدید و فروشگاه‌های جدید و ریسک‌های نادر. `as_of` مدل باید strict باشد؛ دادهٔ بعد از زمان تصمیم حق ورود به ویژگی ندارد. اگر فروشگاه مشترک در train/test می‌ماند، گزارش انحراف قابل انتقال به فروشگاه جدید جدا ارائه شود.

## معیارها
- Binary calibration: Brier Score، log-loss، reliability diagram، ECE با احتیاط و گروه‌بندی;
- رتبه‌بندی استعلام: precision@budget, useful inquiries per 100, avoided expected loss;
- رخداد زمانی: time-dependent Brier, concordance، کیفیت interval-censor handling؛
- عملیاتی: زمان پاسخ، delivered/opened/answered rates، اعلان به ازای فروشگاه/روز، SLA, هزینه؛
- تجربه: false-positive stock, price mismatch, successful visit availability, geographic address error، نوع خطا/دلیل؛
- انصاف: مقایسهٔ گروه‌های کوچک/بزرگ، فروشگاه تازه‌وارد، مناطق/کانال‌ها، فروشگاه معتبر و نامعتبر.

## بایاس انتخاب و نمونه‌برداری
سیستم موارد پرریسک را بیشتر استعلام می‌کند: نرخ مغایرت در این نمونه تخمین کل بازار نیست. ثبت propensity و یک stratified random audit ضروری است. گزارش‌های پس از مراجعه self-selected هستند؛ برای مدل prevalence باید وزن‌دهی/نمونه‌برداری یا طراحی پژوهش مستقل کرد.

## چگونگی آزمایش سیاست
A/B امن (پیش/پس کنترل با احتیاط؛ cohort فروشگاهی برای مزاحمت)، guardrails برای کاهش شدید پاسخ‌گویی، شکایات، latency، عدالت و ریزش نصب. هدف «اعلان کمتر و مراجعهٔ موفق بیشتر» است؛ نه بیشینه‌کردن صرف تعامل با اپ.

## Drift و بازآموزی
مانیتور تغییر رژیم ارز، عرضهٔ نسل جدید، سن ورودی سیستم، تغییر مالکیت شعبه، تغییر رفتار فروشگاه، فصل خرید؛ در صورت افت کالیبراسیون fallback به قواعد محافظه‌کار و افزایش unknown/verification، نه ساخت درصد جعلی.

## اولویت مدل‌ها
اول قیمت عددی و entity matching؛ سپس نسخهٔ رویداد، cold-start و استعلام؛ بعد stock transition و shop trust؛ سپس market regime و decision policy. مدل complex بدون ثبت صحیح شواهد سود محدودی دارد.
