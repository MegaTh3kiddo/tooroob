# 🏛️ معماری کلان و سیستم تصمیم‌گیری ترب‌مپ (System Architecture)

<p align="center">
  <b>🌐 زبان / Language:</b>
  <a href="ARCHITECTURE.md"><b> 🇮🇷 فارسی (پیش‌فرض)</b></a> |
  <a href="ARCHITECTURE_EN.md"><b> 🇬🇧 English</b></a>
</p>

---

> این سند تشریح‌کنندهٔ معماری سیستم، جریان انتها-به-انتها داده‌ها، موتورهای استنتاج آماری، و نردبان تشدید تعهدات (SLA) در سامانه **ترب‌مپ (TorobMap)** است.

---

## ۱. نمای کلی سیستم و چرخه حیات استعلام

ترب‌مپ بر پایه این واقعیت بنا شده است که در خرید حضوری، هزینه مراجعه نادرست (ترافیک تهران، زمان هدر رفته، کالای ناموجود یا قیمت کاذب) بسیار سنگین است. بنابراین سیستم به جای نمایش قیمت‌های ایستا، از یک رویکرد **شواهد-محور (Evidence-Driven)** استفاده می‌کند:

```mermaid
flowchart TB
    subgraph Clients["کاربران و برنامه‌های کلاینت"]
        WebShopper[" خریدار حضوری<br/>(trobapp · Next.js 14)"]
        MerchantAndroid[" فروشنده موبایل<br/>(torob_merchant_app · Jetpack Compose)"]
        LandlinePhone[" تلفن ثابت مغازه<br/>(تماس صوتی Poshteyar TTS)"]
    end

    subgraph Gateway["درگاه ارتباطی و پراکسی"]
        NextProxy["Next.js API Route Proxy<br/>/api/v1/*"]
        FastAPIGw["FastAPI Gateway & Auth<br/>CORS / Rate Limiting"]
    end

    subgraph Intelligence["موتورهای هوش و تصمیم‌گیری آماری"]
        VoIEngine["سیاست ارزش اطلاعات (VoI)<br/>محاسبه سود کاهش ابهام در برابر هزینه مزاحمت"]
        PriceEngine["ارزیابی معقولیت قیمت<br/>Leave-One-Out Peer Median و تشخیص ریال/تومان"]
        StockHazard["مدل بقای موجودی کالا<br/>ETA Hazard Model با ورودی زمان رسیدن"]
        BayesTrust["اعتماد بیزی فروشگاه<br/>توزیع بتا-دوپمله‌ای با اثر زوال زمانی"]
        TorobChatRAG["ترب‌چت (TorobChat)<br/>RAG روی ۲۲۵k کالا و ۶.۴k فروشگاه فیزیکی"]
    end

    subgraph Storage["لایه پایگاه داده و ذخیره‌سازی"]
        DuckDBCatalog[("کاتالوگ کالاها و فروشگاه‌ها<br/>DuckDB Analytic Store")]
        EvidenceLedger[("دفتر کل شواهد و رویدادها<br/>SQLite WAL Mode")]
    end

    subgraph Escalation["نردبان تشدید استعلام (SLA Ladder)"]
        L1["مرحله ۱: اعلان آنی Push به اندروید (۰ تا ۳۰ ثانیه)"]
        L2["مرحله ۲: زنگ اضطراری URGENT_CALL (۳۰ تا ۱۲۰ ثانیه)"]
        L3["مرحله ۳: تماس خودکار با تلفن ثابت (دقیقه ۲ تا ۳)"]
        L4["مرحله ۴: انقضا و بازتوزیع به فروشگاه‌های جایگزین"]
    end

    WebShopper -->|۱. جستجو / گفتگو با ترب‌چت| NextProxy
    NextProxy --> FastAPIGw
    FastAPIGw --> Intelligence
    Intelligence <--> Storage

    FastAPIGw -->|ارزیابی ضرورت استعلام| VoIEngine
    VoIEngine -->|ارزش اطلاعات مثبت| Escalation

    L1 --> MerchantAndroid
    L2 --> MerchantAndroid
    L3 --> LandlinePhone

    MerchantAndroid -->|پاسخ لحظه‌ای فروشنده| FastAPIGw
    FastAPIGw -->|ثبت شواهد قطعی| EvidenceLedger
    EvidenceLedger -->|به‌روزرسانی مدل‌ها| Intelligence
    FastAPIGw -->|اعلان آنی نتیجه به خریدار| WebShopper
```

---

## ۲. موتورهای استنتاج و الگوریتم‌های هوش مصنوعی

### الف) مدل معقولیت قیمت (Price Reasonableness)
برای اینکه قیمت یک فروشگاه با قیمت‌های معتبر بازار ارزیابی شود و خود آن فروشگاه در میانه انحراف ایجاد نکند، از میانه همتایان بدون خود فروشگاه (**Leave-One-Out Peer Median**) استفاده می‌شود:

```math
\tilde{P}_{-i} = \operatorname{Median}\left(\{P_j : j \in \mathcal{S}_{\mathrm{peer}}, j \neq i\}\right)
```

- در صورتی که $|P_i - \tilde{P}\_{-i}| \approx 9 \times P_i$ یا نسبت $P_i / \tilde{P}\_{-i} \in [9.5, 10.5]$ یا $[0.095, 0.105]$ باشد، خطای واحد ریال/تومان به‌صورت خودکار تشخیص داده شده و هشدار داده می‌شود.

### ب) مدل بقای موجودی کالا (Stock Arrival Hazard Model)
احتمال اینکه کالا تا زمان رسیدن خریدار به فروشگاه همچنان در انبار موجود بماند طبق تابع بقا مدل‌سازی می‌شود:

```math
S(t_{\mathrm{ETA}}) = \exp(-\lambda \cdot t_{\mathrm{ETA}})
```

که در آن:
- $t\_{\mathrm{ETA}}$ زمان تخمینی رسیدن خریدار با توجه به فاصله و ترافیک شهری تهران است.
- $\lambda$ نرخ خروج کالا از انبار مغازه است که به محبوبیت کالا و سرعت فروش تاریخی فروشگاه بستگی دارد:

```math
\lambda = \lambda_0 \cdot \gamma_{\mathrm{popularity}} \cdot \gamma_{\mathrm{store\_velocity}}
```

### ج) مدل اعتماد بیزی فروشگاه (Bayesian Shop Trust Model)
امتیاز اعتماد هر فروشگاه بر اساس توزیع پسین بتا-دوپمله‌ای (**Beta-Binomial Conjugate**) با توزیع پیشین $\operatorname{Beta}(\alpha\_0, \beta\_0)$ و انقباض بیزی (Bayesian Shrinkage) به‌روز می‌شود:

```math
\alpha_{\mathrm{new}} = \alpha_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + k
```

```math
\beta_{\mathrm{new}} = \beta_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + (n - k)
```

```math
\hat{\theta} = \frac{\alpha_{\mathrm{new}}}{\alpha_{\mathrm{new}} + \beta_{\mathrm{new}}}
```

- فروشگاه‌های جدید با توزیع پیشین محافظه‌کارانه شروع می‌کنند.
- هر پاسخ مثبت، رد مستند با دلیل مشخص، یا پاسخ سریع وزن مثبت می‌گیرد.
- انقضای مکرر استعلام‌ها یا عدم پاسخ‌گویی به تماس‌ها امتیاز اعتماد فروشگاه را کاهش داده و اولویت ارسال استعلام‌های آینده را به فروشندگان متعهدتر می‌دهد.

### د) سیاست ارزش اطلاعات (Value of Information - VoI)
ارسال نوتیفیکیشن یا تماس صوتی با فروشنده دارای هزینهٔ مزاحمت (**Nuisance Cost**) است. سیستم تنها زمانی استعلام جدید صادر می‌کند که ارزش رفع ابهام از هزینه ایجاد مزاحمت بیشتر باشد:

```math
\mathrm{VoI} = \Delta \mathrm{Certainty} \times \mathrm{TransactionValue} - \mathrm{InterruptionCost} > 0
```

برای کالاهای ارزان‌قیمت سوپرمارکتی استعلام فرستاده نمی‌شود، اما برای کالاهای گران‌قیمت یا کالاهایی با موجودی حساس، استعلام در اولویت بالا قرار می‌گیرد.

---

## ۳. نردبان تشدید استعلام (SLA Ladder)

پاسخ‌گویی به خریدار بر پایه ۴ مرحله با زمان‌بندی دقیق طراحی شده است:

1. **۰ تا ۳۰ ثانیه (Normal Push)**: ارسال نوتیفیکیشن بی‌صدا یا کم‌صدا به گوشی فروشنده.
2. **۳۰ تا ۱۲۰ ثانیه (Urgent Call Takeover)**: فعال‌سازی سرویس پیش‌زمینه اندروید با زنگ ممتد تماس و ویبره مشابه تماس تلفنی ورودی (`androidapp-4.png`).
3. **۱۲۰ تا ۱۸۰ ثانیه (Voice Fallback)**: در صورت عدم پاسخ فروشنده به اپلیکیشن، سرویس تلفن گویای پشت‌یار (Poshteyar TTS) به‌صورت خودکار با تلفن ثابت فروشگاه تماس گرفته و پیام صوتی استعلام را قرائت می‌کند.
4. **پس از ۳ دقیقه (Timeout & Fallback)**: استعلام منقضی شده، خریدار از وضعیت مطلع گشته و فروشگاه‌های جایگزین به او پیشنهاد داده می‌شوند.

---

## ۴. لینک‌های مرتبط

- 🌐 [راهنمای وب‌اپلیکیشن خریدار](WEB_APP.md)
- 📱 [راهنمای اپلیکیشن اندروید فروشنده](MERCHANT_APP.md)
- 🧠 [راهنمای موتور هوش و بک‌اند](INTELLIGENCE_ENGINE.md)
- 📸 [کاتالوگ تصاویر و اسکرین‌شات‌ها](../screenshots/README.md)
- 🇬🇧 [English Version of Architecture Document](ARCHITECTURE_EN.md)
