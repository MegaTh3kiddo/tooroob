# Merchant Android app screenshots — what to use in the presentation

Originals are kept untouched; renamed copies are in `named/`.

## Use these (in this order)
| # | File | Why it matters / what to say |
|---|------|------------------------------|
| 1 | `12-URGENT-CALL-incoming` ⭐ **hero shot** | The "phone rings" screen. A full-screen, call-style takeover (dark, red accent) fires when a customer inquiry arrives: product, customer's question, last recorded price, and a **live countdown «فرصت فوری ۱:۵۷»**. Three one-tap actions: *اعلام قیمت و موجودی*, *تأیید سریع قیمت قبلی*, *اعلام عدم موجودی* / *رد استعلام*. Say: "the merchant never has to open an app or type — a ring, one tap, and the customer has a verified answer in seconds." Show it right after the inquiry is sent from the web app. |
| 2 | `13-URGENT-decline-reason` | Declining requires a **reason** (shop closed / not sold here / can't check price / wrong request / other). Say: "every refusal becomes structured evidence for the reliability model — not a silent ignore." |
| 3 | `11-respond-form` | The answer form: *in stock in the warehouse* vs *not currently available*, **exact quantity** (0 is kept as 0, never turned into 1), ±50k/±100k quick price nudges, suggested price + toman equivalent. Feeds the stock-survival model. |
| 4 | `03-metrics` | Merchant scorecard: response rate (20%), avg response time (1m 9s), received/answered counts, status distribution, "how to raise your rank". Say: "responsiveness is measured and feeds shop trust — a feedback loop that rewards merchants who answer." |
| 5 | `02-history` | Inquiry history with tracking codes (TRB-…), statuses (answered / expired / out-of-stock / rejected), and the customer's question. Shows the lifecycle + audit trail. |
| 6 | `06-settings-alerts` | *Instant inquiry notifications*, **urgent call-style playback**, **vibration**, ringtone choice, "play sample", full-screen permission granted. Supports the "ring" story. |
| 7 | `01-login-otp` | OTP login by phone / landline (landlines get a voice-call code). Optional for a "how merchants onboard" slide. |
| 8 | `05-shop-info-locked` | Shop identity fields are **locked**; changes only via support request (data integrity). Optional. |

## Skip / use only if there is room
- `04-shop-status` — status options, good for a "merchant controls availability" line, but it is a long form; this capture shows the shop as **closed/inactive** which looks odd in a demo.
- `07`, `08` — theme picker and "about" page. Filler.
- `09`, `10` — answered / expired detail states. Useful only as a small inset next to the history screen.

## Before you present (fix these in the shots)
1. **Privacy:** `05`, `07`, `08` show a real-looking owner name/phone/shop ("فاضل‌نیا", 0313…). Blur them, or re-shoot logged in as **فروشگاه جیمبو** (`09120000000`, code `123456`).
2. `12`/`13` show "Galaxy S24 Ultra" — fine, but ideally re-shoot the ring screen with a Jimbo catalogue product so it matches the web demo (e.g. send the inquiry from the web app and screenshot the real ring).
3. `04`/`09`/`10`/`11` contain test strings like «کالای تست اعلان» — keep them out of the main slides.
4. The ring screen (`12`) is the single most persuasive image; if you can, screen-record it (phone → web answer appearing) instead of using a still.
