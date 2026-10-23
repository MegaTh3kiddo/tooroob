# ترب مپ · سامانه هوشمند خرید حضوری (TorobMap)
### Starcoach AI Hackathon — Unified Monorepo

> **English Summary**: Traditional price-comparison platforms answer *"who sells cheapest online?"*. But a buyer preparing to navigate city traffic needs a much harder question answered:  
> **"If I travel to this store right now, will the product still be in stock, at the stated price, and can this merchant be trusted?"**  
> 
> **TorobMap (ترب مپ)** solves this using an evidence-driven, probabilistic intelligence engine combined with real-time merchant inquiry routing, an offline-resilient Android merchant app, an interactive customer web experience, and an AI shopping assistant.

---

## 🗂️ اجزای ریپازیتوری (What Are Those?)

این ریپازیتوری شامل چهار مؤلفهٔ اصلی پروژه به‌همراه دارایی‌های طراحی و دمو است:

| پوشه (Folder) | مؤلفه | فناوری‌ها | نقش و وظیفه |
|---|---|---|---|
| [`torob/`](torob/) | **موتور هوش و بک‌اند مرکزی**<br/>*(Intelligence Backend)* | FastAPI · Python 3.11+ · DuckDB · SQLite WAL · Pydantic | هستهٔ محاسباتی و تصمیم‌گیری: ارزیابی معقولیت قیمت، تخمین بقای موجودی تا رسیدن خریدار، اعتماد چندبعدی فروشگاه با مدل بیزی، الگوریتم ارزش اطلاعات (VoI) برای ارسال استعلام، دستیار هوشمند تربچت (RAG روی کاتالوگ ۲۲۵ هزار کالا و ۶۴۰۰ فروشگاه)، و برنامه‌ریزی بهینهٔ مسیر خرید حضوری. |
| [`trobapp/`](trobapp/) | **وب‌اپلیکیشن مشتری**<br/>*(Customer Web App)* | Next.js 14 · React · TypeScript · Tailwind CSS · Leaflet | رابط کاربری خریدار: نمایش نقشهٔ زندهٔ تهران با خوشه‌بندی قیمت‌ها، فیلتر و مقایسهٔ فروشگاه‌ها، چرخهٔ زندهٔ استعلام قیمت/موجودی از فروشنده با شمارش معکوس SLA، گفتگوی هوشمند تربچت با فیلترهای تعاملی، و بهینه‌سازی مسیر مراجعه. |
| [`torob_merchant_app/`](torob_merchant_app/) | **پلتفرم و اپلیکیشن اندروید فروشنده**<br/>*(Merchant Platform & Android App)* | Kotlin · Jetpack Compose · Room DB · Retrofit · Poshteyar TTS | اپلیکیشن موبایل بومی فروشندگان: دریافت آنی استعلام‌ها با Push Notification، پنجرهٔ هشدار اضطراری ۲ دقیقه‌ای (`URGENT_CALL` با سرویس پیش‌زمینه و رابط شبیه تماس تلفنی)، صف آفلاین با شناسهٔ یکتا (Idempotent Sync)، پشتیبان صوتی خودکار با تماس تلفنی به خطوط ثابت مغازه‌ها، و داشبورد مدیریت وب. |
| [`presentation/`](presentation/) | **ارائهٔ تعاملی و ضبط دمو**<br/>*(Interactive Pitch Deck)* | HTML5 · CSS3 / Tailwind · JavaScript · MP4 Assets | دک ارائهٔ ۱۷ اسلایدی تعاملی و خودکفا (بدون نیاز به اینترنت): ویدیوی هم‌زمان خریدار و زنگ‌خوردن گوشی فروشنده، متن گفتار ارائه (`SCRIPT.md`)، و ابزارهای خودکار ضبط اسلایدها و ویدیوها. |
| [`trb-ui/`](trb-ui/) | **نمونه اولیه رابط کاربری**<br/>*(Design Prototype)* | HTML / CSS / Vanilla JS | مرجع و منبع حقیقت طراحی ظاهر و استایل‌های رابط کاربری. |
| [`merchentappimages/`](merchentappimages/) | **اسکرین‌شات‌های اپ فروشنده**<br/>*(Merchant Screenshots)* | PNG Images · Markdown Notes | اسکرین‌شات‌های کامل مراحل اپلیکیشن فروشنده (ورود، استعلام فعال، زنگ اضطراری، دلایل رد و تاریخچه). |

---

## 🏛️ معماری کلان و جریان داده (Architecture & Data Flow)

```mermaid
flowchart TB
    subgraph Users["کاربران (Clients)"]
        Shopper["خریدار حضوری<br/>(Next.js · trobapp)"]
        MerchantApp["فروشنده در مغازه<br/>(Android · Jetpack Compose)"]
        MerchantPhone["فروشگاه ثابت / تلفن گویا<br/>(Poshteyar Persian Voice TTS)"]
    end

    subgraph Backend["هسته مرکزی (FastAPI · torob)"]
        API["درگاه API و روتینگ<br/>/api/v1 + /api/seller"]
        
        subgraph Intel["موتورهای هوش و شواهد"]
            PriceEngine["هوش قیمت<br/>Peer Median · ریال/تومان"]
            StockHazard["مدل بقای موجودی<br/>ETA Hazard Model"]
            TrustBayes["اعتماد بیزی فروشگاه<br/>Beta-Binomial Shrinkage"]
            VoIPolicy["سیاست ارزش اطلاعات (VoI)<br/>هزینه مزاحمت vs رفع ابهام"]
            TorobChat["تربچت<br/>RAG روی کاتالوگ و ارزیابی"]
        end

        subgraph CoreData["پایگاه داده و شواهد"]
            Ledger[(دفتر کل شواهد<br/>Evidence Ledger DB)]
            Catalog[(کاتالوگ ترب<br/>225k کالا · 6.4k فروشگاه)]
        end

        InquiryLadder["نردبان SLA استعلام<br/>Push → زنگ اضطراری → تماس صوتی → انقضا"]
    end

    Shopper -->|۱. جستجو، بررسی یا گفتگو| API
    API --> Intel
    Intel <--> CoreData

    Intel -->|عدم قطعیت بالا و ارزش اطلاعات مثبت| VoIPolicy
    VoIPolicy --> InquiryLadder

    InquiryLadder -->|Push Notification| MerchantApp
    InquiryLadder -->|تماس صوتی پشتیبان به خط ثابت| MerchantPhone
    
    MerchantApp -->|پاسخ به استعلام (موجودی/قیمت)| API
    API -->|ثبت شواهد جدید| Ledger
    Ledger -->|به‌روزرسانی امتیاز اعتماد و بقا| Intel
    API -->|اعلان زنده پاسخ به خریدار| Shopper
```

---

## 🔍 جزئیات مؤلفه‌ها (Component Breakdown)

### ۱. موتور بک‌اند ترب (`torob/`)
- **هوش قیمت**: تشخیص خطاهای واحد (۱۰ برابر شدن به دلیل ریال/تومان)، میانهٔ همتا بدون خود فروشگاه (Leave-One-Out Peer Median)، و تشخیص نوسان مشکوک.
- **احتمال بقای موجودی**: مدل مخاطره زمانی $S(t) = \exp(-\lambda \cdot t)$ که زمان رسیدن خریدار (ETA) بر اساس فاصله جغرافیایی و سرعت حرکت را در نظر می‌گیرد.
- **اعتماد چندبعدی فروشگاه**: به‌روزرسانی بیزی توزیع بتا-دوپمله‌ای با اثر زوال زمانی برای تفکیک فروشندگان متعهد از فروشگاه‌های دارای ادعای کاذب.
- **استعلام هوشمند با سیاست ارزش اطلاعات (VoI)**: عدم ارسال استعلام برای کالاهای ارزان با هزینهٔ مزاحمت بالا؛ اعمال سقف روزانه و رعایت ساعات کاری فروشگاه.
- **تربچت (TorobChat)**: دستیار هوشمند با توانایی تفسیر مقصود کاربر، فیلتر بودجه، برند، فروشگاه‌های نزدیک و پیشنهاد کالاهای جایگزین.
- **استقرار ابری**: مستقر در لیارا به آدرس `https://torobmap-api.liara.run` (مستندات Swagger در `/docs`).

### ۲. وب‌اپلیکیشن مشتری (`trobapp/`)
- پیاده‌سازی شده با **Next.js 14 App Router**.
- رندر کامل و دقیق پروتوتایپ طراحی بدون افت کیفیت یا نقص در چیدمان RTL.
- نقشه تعاملی با کتابخانه Leaflet، پین‌های هوشمند قیمت و تفکیک موجودی قطعی از نامشخص.
- فرم مودال و کارت‌های زنده برای ارسال استعلام، با قابلیت Polling هوشمند و دریافت پاسخ فوری فروشنده.
- پراکسی خودکار درخواست‌ها به بک‌اند از طریق `next.config.mjs` جهت رفع محدودیت‌های CORS.
- استقرار ابری: مستقر در لیارا به آدرس `https://torobmap.liara.run`.

### ۳. اپلیکیشن موبایل فروشنده (`torob_merchant_app/`)
- توسعه‌یافته با **Kotlin** و معماری مدرن **Jetpack Compose**.
- ذخیره‌سازی محلی با **Room Database** جهت عملکرد پایدار در قطعی اینترنت.
- **پنجره ۲ دقیقه‌ای هشدار اضطراری (`URGENT_CALL`)**: اجرای Foreground Service اختصاصی با صدای زنگ مداوم و ویبره حتی در صورت قفل بودن صفحه.
- پاسخ‌دهی سریع با گزینه‌های پیش‌فرض: تایید موجودی و قیمت قبلی، اعلام قیمت جدید، اتمام موجودی، یا عدم امکان پاسخ‌گویی با ذکر دلیل.
- **پشتیبان صوتی اختصاصی**: ادغام با سرویس پشت‌یار (Poshteyar) برای برقراری تماس خودکار صوتی و بازخوانی کد یا یادآوری استعلام‌های معوق فروشگاه‌های پرتأخیر.

### ۴. اسلایدهای ارائه هکاتون (`presentation/`)
- ارائهٔ تعاملی مبتنی بر وب (HTML5/Tailwind) بدون وابستگی خارجی.
- دربرگیرنده ۱۷ اسلاید جامع شامل بخش اول (آنچه ساخته‌ایم و دموی واقعی) و بخش دوم (معماری، فرمول‌ها و طراحی سیستم).
- دموی ضبط‌شدهٔ هماهنگ دو گوشی خریدار و فروشنده در لحظهٔ ارسال و پاسخ استعلام.
- سناریوی کامل سخنرانی ارائه در فایل `SCRIPT.md`.

---

## 🚀 راهنمای اجرا و توسعه (Getting Started)

### ۱. اجرای بک‌اند (`torob`)
```bash
cd torob
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn torob.api.main:app --host 0.0.0.0 --port 8080 --reload
```
دسترسی به API: `http://localhost:8080`  
مستندات سواگر: `http://localhost:8080/docs`

### ۲. اجرای فرانت‌اند مشتری (`trobapp`)
```bash
cd trobapp
npm install
npm run dev
```
دسترسی به وب‌اپلیکیشن: `http://localhost:3000`

### ۳. ساخت و اجرای اپلیکیشن اندروید (`torob_merchant_app`)
پروژه را در Android Studio باز کرده یا از خط فرمان با Gradle بیلد کنید:
```bash
cd torob_merchant_app/android
./gradlew assembleDebug
```
فایل APK تولیدی در مسیر `app/build/outputs/apk/debug/` قرار می‌گیرد.

### ۴. مشاهده ارائه هکاتون (`presentation`)
کافی است فایل `presentation/index.html` را در مرورگر کروم یا اج باز کنید:
```bash
# از طریق مرورگر یا وب‌سرور سبک:
cd presentation && python3 -m http.server 8000
```
آدرس: `http://localhost:8000`

---

## 🌐 لینک‌های استقرار آنلاین (Live Deployments)

- 📱 **وب‌اپلیکیشن مشتری (TrobApp)**: [https://torobmap.liara.run](https://torobmap.liara.run)
- ⚙️ **سرویس بک‌اند و هوش (Torob Intelligence API)**: [https://torobmap-api.liara.run](https://torobmap-api.liara.run)
- 📖 **مستندات تعاملی Swagger API**: [https://torobmap-api.liara.run/docs](https://torobmap-api.liara.run/docs)
- 🩺 **بررسی سلامت سامانه (Health Check)**: [https://torobmap-api.liara.run/api/v1/health](https://torobmap-api.liara.run/api/v1/health)
