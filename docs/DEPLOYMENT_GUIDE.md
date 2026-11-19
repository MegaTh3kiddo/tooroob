# 🚀 راهنمای جامع راه‌اندازی و استقرار محلی و ابری (Deployment Guide)

<p align="center">
  <b>🌐 زبان / Language:</b>
  <a href="DEPLOYMENT_GUIDE.md"><b> 🇮🇷 فارسی (پیش‌فرض)</b></a> |
  <a href="DEPLOYMENT_GUIDE_EN.md"><b> 🇬🇧 English</b></a>
</p>

---

---

## ۱. پیش‌نیازهای سیستمی

- **سیستم‌عامل**: Linux (Ubuntu 20.04+) یا macOS یا Windows با WSL2
- **Node.js**: نسخه 18 یا بالاتر (پیشنهادی: Node 20+)
- **Python**: نسخه 3.11 یا بالاتر
- **Java / Android Studio**: JDK 17 جهت بیلد پروژه اندروید
- **مدیر بسته‌ها**: `npm` یا `pnpm` و `pip`

---

## ۲. راه‌اندازی محلی (Local Full-Stack Setup)

### مرحله ۱: اجرای وب‌اپلیکیشن مشتری (`trobapp`)
```bash
cd trobapp
npm install
npm run build
npm start
# یا برای حالت توسعه:
npm run dev
```
- **آدرس دسترسی وب‌اپلیکیشن**: [http://localhost:3000](http://localhost:3000)

### مرحله ۲: اجرای بک‌اند هوش و API (`torob`)
```bash
cd torob
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn torob.api.main:app --host 0.0.0.0 --port 8080 --reload
```
- **درگاه API محلی**: [http://localhost:8080](http://localhost:8080)
- **مستندات تعاملی Swagger**: [http://localhost:8080/docs](http://localhost:8080/docs)

### مرحله ۳: بیلد اپلیکیشن موبایل فروشنده (`torob_merchant_app`)
```bash
cd torob_merchant_app/android
./gradlew assembleDebug
```
فایل APK در مسیر زیر ساخته می‌شود:
`app/build/outputs/apk/debug/app-debug.apk`

### مرحله ۴: مشاهده اسلایدهای ارائه (`presentation`)
```bash
cd presentation
python3 -m http.server 8000
```
- **آدرس اسلایدها**: [http://localhost:8000](http://localhost:8000)

---

## ۳. تنظیمات متغیرهای محیطی (Environment Variables)

### فرانت‌اند مشتری (`trobapp/.env.production` یا `.env.local`):
```ini
# آدرس بک‌اند جهت پراکسی درخواست‌های /api/v1/*
BACKEND_API_URL=http://localhost:8080
```

### بک‌اند مرکزی (`torob/.env`):
```ini
# تنظیمات دستیار ترب‌چت با مدل Gemini یا OpenAI
TOROB_LLM_PROVIDER=openai_compatible
TOROB_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
TOROB_LLM_API_KEY=YOUR_GEMINI_API_KEY
TOROB_LLM_MODEL=gemini-3.1-flash-lite
TOROB_LLM_TIMEOUT_SECONDS=10
TOROB_LLM_POLISH_REPLIES=true
```

---

## ۴. استقرار ابری روی لیارا (Liara Cloud Deployment)

هر دو مؤلفه `torob` و `trobapp` دارای فایل‌های پیکربندی آماده `liara.json` هستند:

### استقرار بک‌اند:
```bash
cd torob
liara deploy --app torobmap-api --port 8080
```

### استقرار فرانت‌اند:
```bash
cd trobapp
liara deploy --app torobmap --port 3000
```

---

## ۵. مستندات تکمیلی

- 🏛️ [معماری کلان سیستم](ARCHITECTURE.md)
- 🌐 [راهنمای وب‌اپلیکیشن مشتری](WEB_APP.md)
- 📱 [راهنمای اپلیکیشن اندروید فروشنده](MERCHANT_APP.md)
- 📸 [کاتالوگ تصاویر و اسکرین‌شات‌ها](../screenshots/README.md)
