# ۰۳ — ماتریس پوشش کامل ایده‌های گفت‌وگو و نیازمندی‌ها

این ماتریس تضمین می‌کند موردهای اصلی مطرح‌شده در کل گفتگو، مسیر مشخص برای طراحی و تست داشته باشند. طرح‌های تکمیلی هم مشخص شده‌اند؛ **پوشش مستندسازی** با **پیاده‌سازی** فرق دارد.

| # | موضوع مطرح‌شده | فایل مرجع | وضعیت |
|---|---|---|---|
| 01 | هدف: قیمت درست یا آپدیت هست؟ | `03_ALGORITHMS/01_Price_Validity.md` | طراحی |
| 02 | موجودی فعلی طبیعی/منطقی است؟ | `03_ALGORITHMS/02_Stock_and_Arrival.md` | طراحی |
| 03 | اپ نصب‌شدهٔ فروشنده و کاهش تماس دستی | `04_WORKFLOWS/03_Seller_App_Experience.md` | UX |
| 04 | استعلام قیمت، موجودی و بازبودن یکجا | `04_WORKFLOWS/01_Inquiry_State_Machine.md` | طراحی |
| 05 | نوتیف و یادآوری پس از ۵/۱۰ دقیقه | `11_CODE/sample_policy.yaml` | فرض آزمایشی |
| 06 | زنگ/تمام‌صفحه و محدودیت سیستم‌عامل | `08_REFERENCES/01_Source_Provenance.md` | منبع رسمی |
| 07 | قطع اینترنت/نرسیدن push | `04_WORKFLOWS/01_Inquiry_State_Machine.md` | طراحی |
| 08 | استفادهٔ دوباره از پاسخ «مغازه باز است» | `01_PRODUCT/03_Verification_Scope_and_Fulfillment.md` | قاعده |
| 09 | تفکیک حضور فروشنده از بازبودن | `04_WORKFLOWS/01_Inquiry_State_Machine.md` | قاعده |
| 10 | دسته کالا و TTL مخصوص گوشی/کامپیوتر | `03_ALGORITHMS/05_Inquiry_Policy.md` | پویا |
| 11 | جنس کالای سریع‌فروش/کم‌گردش | `03_ALGORITHMS/02_Stock_and_Arrival.md` | مدل |
| 12 | کمبود هم‌زمان کالا در بازار | `03_ALGORITHMS/02_Stock_and_Arrival.md` | bias-aware |
| 13 | امتیاز وب‌سایت/فروشگاه از ۱۰ | `03_ALGORITHMS/04_Shop_Trust.md` | تفکیک ابعاد |
| 14 | آخرین تغییر قیمت محصول/فروشگاه | `02_DATA/01_Audit.md` | ممیزی |
| 15 | آخرین مشاهده/تأیید جدا از تغییر | `02_DATA/02_Data_Dictionary.md` | قرارداد |
| 16 | قیمت نسبت به رقبا | `03_ALGORITHMS/01_Price_Validity.md` | leave-one-out |
| 17 | نرخ دلار و شدت افزایش | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | ویژگی کمکی |
| 18 | احتمال صحیح‌بودن قیمت و موجودی | `03_ALGORITHMS/06_ML_Evaluation.md` | فقط پس از calibration |
| 19 | فیدبک بسته بودن مغازه | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | کیس |
| 20 | فیدبک ناموجودی، رنگ یا مدل اشتباه | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | کیس |
| 21 | فیدبک قیمت متفاوت | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | کیس |
| 22 | فیدبک آدرس/پاساژ/واحد اشتباه | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | کیس |
| 23 | گزارش مثبت و تجربهٔ موفق | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | کیس |
| 24 | امکان پیگیری و اعتراض فروشنده | `04_WORKFLOWS/02_Customer_Feedback_and_Cases.md` | جریان |
| 25 | اعتبار کلی فروشگاه و نشان بیرونی | `03_ALGORITHMS/04_Shop_Trust.md` | prior |
| 26 | «مدام آپدیت می‌کند» در برابر «واقعاً دقیق است» | `03_ALGORITHMS/04_Shop_Trust.md` | تفکیک |
| 27 | تغییر خالص کم اما نوسان مسیر زیاد | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | حل شده |
| 28 | پنجره‌های ۲۴ساعته/۷/۳۰/۹۰ روز | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | طرح |
| 29 | محصول تازه معرفی و قیمت تثبیت نشده | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | cold start |
| 30 | معرفی جهانی ≠ ورود ایران ≠ ورود دیتاست | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | تفکیک |
| 31 | پایان عمر و کمیابی کالا | `03_ALGORITHMS/03_Lifecycle_Regime_FX.md` | طرح |
| 32 | پیشنهاد قابل سفارش ≠ موجودی مغازه | `01_PRODUCT/03_Verification_Scope_and_Fulfillment.md` | scope |
| 33 | مشتری قبل از رسیدن کالای تک‌عدد فروخته شود | `03_ALGORITHMS/02_Stock_and_Arrival.md` | ETA model |
| 34 | رزرو اختیاری | `03_ALGORITHMS/02_Stock_and_Arrival.md` | آینده |
| 35 | چند پیشنهاد یک کالا، واریانت و گارانتی | `01_PRODUCT/03_Verification_Scope_and_Fulfillment.md` | entity |
| 36 | SKU اشتباه و قیمت عمده/متری | `06_QUALITY/01_Edge_Case_Register.md` | QA |
| 37 | هم‌منبع بودن قیمت رقبا | `03_ALGORITHMS/01_Price_Validity.md` | وابستگی |
| 38 | اختلاف شواهد و دو کارمند | `04_WORKFLOWS/01_Inquiry_State_Machine.md` | conflict |
| 39 | پیام دیررس، نسخهٔ قدیمی قیمت | `04_WORKFLOWS/01_Inquiry_State_Machine.md` | event time |
| 40 | گزارش جعلی رقبا و بازی با امتیاز | `05_ARCHITECTURE/03_Security_Privacy_Abuse.md` | سوءاستفاده |
| 41 | بایاس به علت انتخاب استعلام‌های مشکوک | `03_ALGORITHMS/06_ML_Evaluation.md` | آزمایش |
| 42 | هزینهٔ خطا با هدف خرید یا مراجعه | `03_ALGORITHMS/05_Inquiry_Policy.md` | تصمیم |
| 43 | سیاست کم‌مزاحمت/گروه‌بندی استعلام | `04_WORKFLOWS/03_Seller_App_Experience.md` | UX |
| 44 | شرایط پرداخت و قیمت قابل تحقق | `01_PRODUCT/03_Verification_Scope_and_Fulfillment.md` | قرارداد |
| 45 | کد، قرارداد پایگاه داده و API | `05_ARCHITECTURE/02_API_and_Events.md` | نمونه |
| 46 | تست، سناریو، شکست و پذیرش | `06_QUALITY/02_Test_Strategy.md` | چک لیست |
| 47 | اولویت فازها و قابلیت‌های آینده | `07_DELIVERY/01_Roadmap.md` | اجرا |
| 48 | ارزش تجاری و KPI | `07_DELIVERY/02_Metrics_and_Experiments.md` | ارزیابی |
| 49 | محدودیت دادهٔ snapshot و cap300 | `02_DATA/01_Audit.md` | قابل اندازه‌گیری |
| 50 | احتمال خرید موفق/تحویل کالا | `01_PRODUCT/03_Verification_Scope_and_Fulfillment.md` | هدف محصول |
| 51 | شارژ مجدد موجودی بعد از ناموجودی و مدل دوطرفه | `03_ALGORITHMS/02_Stock_and_Arrival.md` | گذار وضعیت |

## چیزهای افزوده‌شده در مستند، فراتر از موارد صریح گفت‌وگو
- اسکیما رویداد با version/correlation، جداسازی `case_status` و `case_outcome`، ارزیابی leakage و propensity، نگهداری محرمانگی مدارک، برنامهٔ ADR، پایش drift و سلامت پایپلاین.
- رجیستر ۱۸۰ سناریوی مرزی؛ کد نمونهٔ غیرآموزش‌دیده و policy قابل آزمایش؛ HTML یکپارچهٔ قابل مرور و manifest شفاف.

## هشدار پوشش
این ماتریس معنای نیاز را ردیابی می‌کند؛ **نه** ادعای اینکه همهٔ امکانات پیاده‌سازی شده‌اند. وضعیت مدل‌ها عمدتاً «پیشنهادی» است و با نمونه‌گیری مستقل باید ارزیابی شود.
