# ۱۸ — قرارداد API و پیام رویداد (نمونهٔ پیشنهادی)

این‌ها قراردادهای طراحی‌اند و endpointهای واقعی موجود را ادعا نمی‌کنند. JSON Schema در `11_CODE/evidence.schema.json` و DDL در `11_CODE/schema.sql` آمده‌اند.

## endpointهای اصلی
| Endpoint پیشنهادی | عملیات | نکته |
|---|---|---|
| `GET /v1/offers/{id}/confidence?arrival_at=...` | نمایش score و شواهد | scope/زمان/نسخه دقیق |
| `POST /v1/inquiries` | ایجاد یا join درخواست | idempotency key الزامی |
| `GET /v1/inquiries/{id}` | وضعیت پاسخ | تفکیک inquiry/delivery |
| `POST /v1/inquiries/{id}/responses` | ثبت پاسخ فروشنده | actor authorization، offer_version |
| `GET /v1/seller/inbox` | صندوق درخواست‌ها | شعبه، فیلتر نقش و انقضا |
| `POST /v1/feedback` | گزارش مراجعه | positive/negative، evidence optional |
| `GET /v1/feedback/cases/{id}` | مرحلهٔ رسیدگی | کنترل دسترسی |
| `POST /v1/feedback/cases/{id}/shop-response` | توضیح فروشنده | append-only |
| `POST /v1/feedback/cases/{id}/appeal` | اعتراض | مهار سوءاستفاده |
| `POST /v1/shops/{id}/presence` | اعلام حضور/باز بودن | scope شعبه؛ مستقل از پاسخ آنلاین |

## نمونهٔ درخواست استعلام
```json
{
  "branch_id": "branch_example",
  "offer_id": "offer_example",
  "offer_version": 7,
  "sku_variant_id": "sku_black_256_registered",
  "channel": "in_store",
  "questions": ["price", "sellable_stock", "branch_open"],
  "user_intent": "visit",
  "arrival_at": "2026-10-23T10:30:00Z",
  "request_deadline_at": "2026-10-23T10:10:00Z",
  "idempotency_key": "example-unique-token"
}
```

## نمونهٔ پاسخ درست
```json
{
  "response_id": "resp_example",
  "inquiry_id": "inq_example",
  "offer_version": 7,
  "observed_at": "2026-10-23T10:04:00Z",
  "price": {"status":"confirmed","amount_toman":70000000,"price_type":"fixed_purchase_price"},
  "stock": {"state":"in_store_sellable","quantity_bucket":"one"},
  "presence": {"branch_open":true,"seller_physically_present":null},
  "source":"shop_employee_app"
}
```

## رویدادهای اصلی
`OfferObserved`, `OfferPriceChanged`, `PriceVerified`, `StockObserved`, `PresenceVerified`, `InquiryRequested`, `PushProviderAccepted`, `PushReceived`, `InquiryAnswered`, `InquiryExpired`, `CustomerFeedbackReported`, `CaseResolved`, `ExternalTrustSignalVerified`, `ScoreCalculated`, `PolicyDecisionLogged`.

## اسکیما و قوانین جهانی
هر رویداد `event_id`, `event_type`, `event_version`, `aggregate_id`, `observed_at`, `ingested_at`, `source`, `actor_id`, `scope`, `payload`, `consent`, `correlation_id` دارد. ورودی‌های تکراری idempotent؛ `observed_at` الزاماً زمان receipt نیست؛ actor دسترسی باید به شعبه/offer مرتبط باشد؛ حذف فیزیکی evidence فقط تحت سیاست حقوقی مخصوص انجام شود و رد ممیزی مناسب باقی بماند.

## خطاهای API
`400 invalid_scope`, `401/403 unauthorized`, `409 stale_offer_version`, `409 conflicting_response`, `410 inquiry_expired`, `422 mismatched_variant`, `429 budget_exceeded`, `503 delivery_unavailable`؛ نه اینکه بعد از خطا status موجودی تغییر کند.
