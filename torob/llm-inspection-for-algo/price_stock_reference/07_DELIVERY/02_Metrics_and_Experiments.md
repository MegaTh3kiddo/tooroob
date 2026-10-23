# ۲۴ — شاخص‌های ارزیابی، آزمایش و پایش

## North Star
**نرخ امکان خرید موفقِ واقعی پس از مشاهده/استعلام، با هزینهٔ قابل‌قبول برای فروشگاه و کاربر**. «خرید انجام شد» به‌تنهایی هدف مناسب نیست؛ مشتری ممکن است انصراف دهد با اینکه پیشنهاد قابل تحقق بوده است.

## شاخص‌های محصول
- `verified_price_mismatch_rate`: نسبت مغایرت‌های تأییدشده به فرصت‌های مشاهدهٔ مستقل واجد شرایط؛
- `false_in_store_availability_rate`: نرخ تأیید موجودی نادرست در زمان مراجعه؛
- `successful_visit_opportunity_rate`: مراجعه‌هایی که کالا با شرایط اعلامی قابل خرید بوده؛
- `wrong_address_report_rate`: گزارش‌های معتبر مکان/شعبه؛
- `case_resolution_time`, `appeal_reversal_rate`, `system_fault_fraction`؛
- پوشش unknown/contradictory/stale در هر دسته، نه صرفاً متوسط کل.

## شاخص‌های استعلام
`requests_per_shop_per_day`, `duplicates_avoided`, `batch_size`, `provider_accept_rate`, `device_receive_observed_rate`, `answer_rate_when_delivered`, `median_time_to_answer`, `useful_inquiries/100`, `seller_opt_out`, `notification_disable_rate`, `seller_churn`.

## شاخص‌های ML
Brier Score و calibration plot برای probability؛ log loss؛ prediction interval coverage؛ false negative/positive بر مبنای هزینه؛ lift over baseline TTL/age؛ valid temporal evaluation؛ تفاوت دسته، شعبه، تازه‌وارد/قدیمی، معتبر/کم‌سابقه، شوک/آرام.

## A/B / شبه‌آزمایش
A: قاعدهٔ ثابت برای دسته در برابر مدل هوشمند با همان budget.  
B: batch inquiry در برابر push جدا با سقف مساوی.  
C: نمایش شواهد زمان‌مند در برابر فقط نمرهٔ کلی.  
D: prior چندبعدی فروشگاه در برابر prior کلی.  
E: نمونه‌گیری تصادفی کنترل‌شده برای calibration و نمونهٔ گزینشی برای کاربرد عملی.

## تهدید به استنباط
نرخ شکایت به تعداد بازدید/تعداد خرید/حجم استعلام وابسته است؛ مقایسهٔ تعداد شکایت خام ناعادلانه است. تغییرات قیمت/موجودی در بازار پرنوسان با سیستم هم‌زمان‌اند؛ اثر محصول را از اثر مدل جدا کنید. برای گروه‌های با دادهٔ کم بازهٔ اطمینان اعلام کنید.

## داشبورد پایش
نرخ خطا/نامشخص به دسته و شعبه، تأخیر از آخرین مشاهده و تأیید، تعداد پرونده‌های باز، delivered unknown، احتمال و اعتبار فروشنده، distribution shift، هزینهٔ هر استعلام مفید، سهم پاسخ منفی در گروه‌ها با اصلاح بایاس.
