# ۱۴ — ماشین حالت استعلام و تحویل اعلان

## موجودیت‌ها
`inquiry` (یک نیاز منطقی)، `inquiry_subscriber` (متقاضیانی که به پاسخ مشترک متصل‌اند)، `delivery_attempt` (تلاش ارسال مستقل در هر دستگاه/کانال)، `response` (شاهد دربارهٔ یک scope و زمان)، `inquiry_job` (زمان‌بند یادآوری/انقضا).

## حالت‌های درخواست
`created -> queued -> active -> answered | expired | cancelled | superseded`؛ تأخیر/ارسال ناموفق حالت inquiry نهایی نیست، بلکه حالت delivery است. یک درخواست می‌تواند چند بار تلاش ارسال داشته باشد، اما `answered` باید idempotent و حاوی چند پاسخ قابل تعارض باشد.

## حالت‌های delivery
`scheduled`, `sent_to_provider`, `provider_accepted`, `device_received`, `opened`, `failed`, `unknown`, `expired`. پذیرفته‌شدن push توسط ارائه‌دهنده تضمین delivery در گوشی نیست. «نمایش روی گوشی» و «بازکردن توسط فروشنده» ممکن است telemetry دقیقی نداشته باشند؛ unknown به دروغ delivered نشود.

## استانداردهای زمان
- `requested_at`, `deadline_at` در بک‌اند UTC؛
- `delivered_at`, `opened_at`, `responded_at`, `observed_at` جدا؛
- `observed_at` ادعایی کاربر ممکن است نیازمند ارزیابی clock skew باشد؛
- پاسخ دیررس بعد از `deadline_at` برای audit حفظ، نه overwrite خودکار وضعیت فعلی.

## dedupe
کلید اشتراک درخواست بر اساس `(branch, sku_variant, offer_version or tolerated_revision, channel, question_scope, deadline_bucket)`؛ سفارش‌های دو مشتری با همان scope می‌توانند مشترک شوند. درخواست برای قیمت ≠ درخواست موجودی؛ می‌توان آن‌ها را در یک پیام گروه کرد اما نتیجه باید مستقل باشد.

## ترتیب ارسال و یادآوری
حد اولیه (قابل تنظیم): T0 پیام معمولی؛ T+5m بررسی وضعیت و یادآوری نرم؛ T+10m یادآوری تنها با اجازه و budget؛ T+15m انقضای درخواست. اگر پاسخ رسید، تمام jobهای مانده لغو شوند؛ اگر مغازه بسته/در quiet hours بود، defer/skip و به خریدار توضیح داده شود. retryهای شبکه backoff و سقف مشخص دارند.

## پاسخ‌دهندهٔ متعدد
کارمندان چندگوشی می‌توانند پاسخ متعارض بدهند؛ `role`, `actor_id`, `device_id`, `response_source` ثبت و مسئله حل شود. در رخداد هم‌زمان، پاسخ‌های idempotent متمایز بمانند؛ event consumerها حداقل یک‌بار اجراشدن را تحمل کنند.

## offline
اپ پاسخ محلی می‌گیرد، ولی پاسخ همراه با ساعت محلی و زمان دریافت سرور ذخیره می‌شود؛ اگر deadline گذشته، به عنوان وضعیت اکنون بدون تأیید مجدد استفاده نکنید. اتصال مجدد: fetch requests فعال، suppress نمایش pushهای منقضی، clear queued local answers با آگاهی کاربر.

## تفاوت حضور/بازبودن/پاسخ
«فروشنده پاسخ می‌دهد» با «در مغازه حاضر است» و «در آن ساعت مغازه باز است» جدا. تأیید بازبودن فقط در شعبه/شیفت مرتبط قابل reuse است. `weekly_hours` برای برنامهٔ اعلامی است، نه اثبات بازبودن لحظه‌ای.

## محافظ‌های حیاتی
عدم پاسخ ↛ stock false؛ push accepted ↛ device received؛ پیام دیررس ↛ پاسخ معتبر کنونی؛ استعلام duplicate ↛ نوتیف duplicate؛ پاسخ مثبت ↛ تمام کانفیگ‌ها موجود؛ نشان بیرونی ↛ ضمانت حضوری.

## شبه‌الگوریتم
```text
on_new_intent(intent):
  scope = canonicalize_exact_offer(intent)
  if cached_evidence_is_sufficient(scope, intent.arrival_eta): show_evidence(); return
  if existing_active_inquiry(scope): subscribe(intent.user); return
  if quiet_hours or seller_budget_exhausted: show_uncertainty(); defer_if_allowed(); return
  inquiry = create_with_idempotency_key(scope, deadline, policy_version)
  enqueue_push(inquiry)
  register_reminders_and_expiry(inquiry)

on_response(response):
  verify_actor_and_scope(response)
  persist_immutable_event(response)
  if after_deadline or stale_offer_version: mark_historical_only()
  else update_projection_if_consistent(); resolve_related_jobs()
  if conflicting: create_conflict_case()
```
