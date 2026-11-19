# 🧠 موتور هوش، تصمیم‌گیری آماری و بک‌اند مرکزی (Torob Intelligence Backend)

<p align="center">
  <b>🌐 زبان / Language:</b>
  <a href="INTELLIGENCE_ENGINE.md"><b> 🇮🇷 فارسی (پیش‌فرض)</b></a> |
  <a href="INTELLIGENCE_ENGINE_EN.md"><b> 🇬🇧 English</b></a>
</p>

---

> این سند مشخصات فنی، معماری سرویس‌های هوش مصنوعی، مدل‌های احتمالاتی و APIهای موجود در ماژول [`torob/`](../torob/) را تبیین می‌کند.

---

## ۱. نقش و مسئولیت هسته مرکزی

ماژول بک‌اند قلب تپندهٔ محاسباتی سیستم ترب‌مپ است. برخلاف سامانه‌های سنتی که صرفاً داده‌های ایستا را واکشی می‌کنند، این ماژول چهار مدل تصمیم‌گیری فعال را به‌صورت بلادرنگ پردازش می‌کند:

1. **ارزیابی معقولیت و خطای قیمت (Price Reasonableness & Outliers)**
2. **پیش‌بینی بقای موجودی تا رسیدن خریدار (Stock Arrival Survival Hazard Model)**
3. **محاسبه اعتماد چندبعدی فروشگاه (Bayesian Trust Shrinkage)**
4. **سیاست بهینه ارسال استعلام بر مبنای ارزش اطلاعات (Value of Information - VoI)**
5. **دستیار هوشمند ترب‌چت (TorobChat RAG)**

---

## ۲. فرمولاسیون و مبانی ریاضی مدل‌ها

### الف) مدل میانه همتایان بدون خود فروشگاه (Leave-One-Out Peer Median)
برای اینکه قیمت یک فروشگاه با قیمت‌های معتبر بازار ارزیابی شود و خود آن فروشگاه در میانه انحراف ایجاد نکند:

```math
\tilde{P}_{-i} = \operatorname{Median}\left(\{P_j : j \in \mathcal{S}_{\mathrm{peer}}, j \neq i\}\right)
```

- چنانچه $|P_i - \tilde{P}\_{-i}| \approx 9 \times P_i$ یا نسبت $P_i / \tilde{P}\_{-i} \in [9.5, 10.5]$ یا $[0.095, 0.105]$ باشد، خطای سیستماتیک ۱۰ برابری واحد پولی (ریال به جای تومان) شناسایی می‌شود.

### ب) مدل مخاطره بقای موجودی کالا (Stock Survival Hazard Model)
خریدار برای خرید حضوری در سفر شهری است. بقای کالای موجود در انبار طبق توزیع نمایی برآورد می‌شود:

```math
S(t_{\mathrm{ETA}}) = P(T > t_{\mathrm{ETA}}) = \exp(-\lambda \cdot t_{\mathrm{ETA}})
```

که در آن:
- $t\_{\mathrm{ETA}}$ زمان رسیدن خریدار به دقیقه است.
- نرخ خروج کالا $\lambda$ با ترکیب ویژگی‌های کالا و فروشگاه محاسبه می‌شود:

```math
\lambda = \lambda_0 \cdot \gamma_{\mathrm{popularity}} \cdot \gamma_{\mathrm{store\_velocity}}
```

### ج) به‌روزرسانی بیزی اعتماد فروشگاه (Bayesian Beta-Binomial Trust)
اعتماد به فروشگاه $\theta$ با توزیع پیشین $\operatorname{Beta}(\alpha\_0, \beta\_0)$ مدل می‌شود. پس از دریافت $n$ شواهد جدید با $k$ پاسخ موفق:

```math
\alpha_{\mathrm{new}} = \alpha_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + k
```

```math
\beta_{\mathrm{new}} = \beta_{\mathrm{old}} \cdot e^{-\Delta t / \tau} + (n - k)
```

```math
\hat{\theta} = \frac{\alpha_{\mathrm{new}}}{\alpha_{\mathrm{new}} + \beta_{\mathrm{new}}}
```

ضریب $e^{-\Delta t / \tau}$ اثر زوال زمانی (Time Decay) است که باعث می‌شود رفتارهای اخیر فروشگاه تاثیر پررنگ‌تری در مقایسه با گذشته داشته باشند.

### د) سیاست ارزش اطلاعات (Value of Information - VoI)
ارسال نوتیفیکیشن یا تماس صوتی با فروشنده دارای هزینهٔ مزاحمت است. سیستم تنها زمانی استعلام جدید صادر می‌کند که:

```math
\mathrm{VoI} = \Delta \mathrm{Certainty} \times \mathrm{TransactionValue} - \mathrm{InterruptionCost} > 0
```

---

## ۳. استک فنی بک‌اند

- **زبان و فریم‌ورک**: Python 3.11+ · [FastAPI](https://fastapi.tiangolo.com/) · Uvicorn
- **موتور تحلیلی کاتالوگ**: [DuckDB](https://duckdb.org/) جهت کوئری‌های فوق‌سریع روی فایل‌های CSV بزرگ کاتالوگ (۲۲۵k کالا و ۶.۴k فروشگاه) در کسری از میلی‌ثانیه
- **دفتر کل شواهد (Evidence Ledger)**: پایگاه داده SQLite در حالت WAL Mode جهت اطمینان از صحت ثبت تراکنش‌های همزمان
- **صحت‌سنجی داده‌ها**: Pydantic v2 با پشتیبانی کامل از OpenAPI v3
- **دستیار هوشمند کاتالوگ**: ادغام با رابط سازگار با OpenAI و Google Gemini جهت پردازش پرامپت‌های ترب‌چت

---

## ۴. ساختار کدهای ماژول `torob/`

```
torob/
├── src/
│   └── torob/
│       ├── api/            # روت‌های FastAPI (/customer, /seller, /inquiries)
│       ├── core/           # تنظیمات محیطی و لاگرها
│       ├── intelligence/   # پیاده‌سازی مدل‌های قیمت، بقا، اعتماد بیزی و VoI
│       ├── catalog/        # کوئری‌های DuckDB روی داده‌های کاتالوگ
│       └── chat/           # ماژول RAG ترب‌چت
├── data/                   # فایل‌های کاتالوگ (products.csv, shops.csv, offers.csv)
├── tests/                  # آزمون‌های واحد و یکپارچگی الگوریتم‌ها
├── requirements.txt
└── pyproject.toml
```

---

## ۵. راهنمای اجرا و آزمایش محلی

```bash
cd torob
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# اجرای سرور با Reload خودکار:
uvicorn torob.api.main:app --host 0.0.0.0 --port 8080 --reload
```
- مستندات تعاملی Swagger API: `http://localhost:8080/docs`
- مستندات Redoc: `http://localhost:8080/redoc`

---

## ۶. مستندات مرتبط

- 🏛️ [معماری سیستم و جریان استعلام](ARCHITECTURE.md)
- 🌐 [راهنمای وب‌اپلیکیشن مشتری](WEB_APP.md)
- 📱 [راهنمای اپلیکیشن اندروید فروشنده](MERCHANT_APP.md)
- 🇬🇧 [English Version of Intelligence Backend Document](INTELLIGENCE_ENGINE_EN.md)
