# Torob Merchant Platform (`torob_merchant_app`)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Android](https://img.shields.io/badge/Android-Jetpack%20Compose%20%7C%20Kotlin-3DDC84.svg?style=flat-square&logo=android)](https://developer.android.com/jetpack/compose)
[![Database](https://img.shields.io/badge/Database-SQLite%20WAL%20Mode-003B57.svg?style=flat-square&logo=sqlite)](https://sqlite.org)
[![Telephony](https://img.shields.io/badge/Telephony-Poshteyar%20%2B%20Persian%20TTS-FF6F00.svg?style=flat-square)](https://poshtyar.com)
[![Tests](https://img.shields.io/badge/Pytest-100%25%20Passing-brightgreen.svg?style=flat-square)](tests/)

The **Torob Merchant Platform** is an enterprise-grade seller communication and real-time inquiry management ecosystem designed for the **Torob (ترب)** marketplace. It enables in-person and online merchants to receive instant price and inventory inquiries from buyers, review product specifications, submit live quotes, or report out-of-stock items within strict time limits.

---

## 🚀 Key Highlights & Features

### 1. Instant Inquiry & Time-Zero Notification Flow
- **Real-Time Push Dispatch**: When a customer submits an inquiry, the backend immediately triggers an FCM high-priority push notification.
- **Enforced Business Hours**: Inquiries are only routed to merchants during working hours, accounting for store schedules and holiday mode.

### 2. 2-Minute Emergency Ringing Window (`URGENT_CALL`)
- **Dual Detection (Push + Local)**: If an inquiry remains unanswered with $\le 120$ seconds left, the backend pushes an urgent call alert, and the Android client's internal countdown independently triggers the alarm even if offline.
- **Continuous Ringtone & Vibration**: `InquiryAlertService` runs as a high-priority foreground service playing looped ringtones and rhythmic vibrations.
- **Full-Screen Call UI**: `IncomingInquiryActivity` launches over the lock screen with immediate action options: *Submit Quote*, *Confirm Previous Price*, *Out of Stock*, or *Decline*.

### 3. Automated Expiration & Clean History Transition
- **Automatic Server & Client Expiry**: At 0:00 remaining seconds, the backend immediately updates the record to `EXPIRED`.
- **Seamless State Hand-off**: The Android app instantly silences the ringtone, stops the foreground alert, and moves the inquiry from the "استعلام‌های فعال" (Active Inquiries) tab to the "تاریخچه" (History) tab.
- **Clean UI**: Synced inquiries display no redundant "ثبت نهایی در سرور" badges.

### 4. Persian Outbound Voice Calls & Poshteyar Integration
- **Landline Voice OTP**: Landline store numbers (e.g. Tehran `021...`) are automatically detected and verified via outbound Persian voice calls reciting spoken security digits with rhythmic pauses.
- **Automated Delinquent Store Reminders**: A background cron evaluator monitors store response rates across 24 hours. When unanswered rates exceed thresholds (e.g., $\ge 6$ unanswered inquiries and $\ge 60\%$ unanswered rate), an automated voice reminder is placed via Poshteyar.
- **Persian Text-to-Speech (TTS)**: Supports Poshteyar Announcement API and Google Cloud Persian TTS engines.

### 5. Offline-First Resilience & Idempotent Sync
- **Local Room Database**: Complete client-side caching of inquiries and merchant profile.
- **Idempotent Queue**: Offline responses are tagged with a client-generated UUID (`client_response_id`). Retries or duplicate dispatches never produce duplicate records on the server.
- **Batch Synchronization**: When internet connectivity is restored, queued items sync via `POST /api/seller/sync/batch-responses`.

### 6. Authentic Dataset & Web Admin Dashboard
- **41,563 Authentic Torob Stores**: Loaded directly from `torob-dataset/shops.csv` into SQLite with indexed searching.
- **Persian RTL Admin Panel**: Single-page dashboard accessible at `http://localhost:8080/admin` for monitoring live inquiries, push audit logs, outbound voice calls, and adjusting scheduler parameters.

---

## 🛠️ Architecture & Tech Stack

```text
torob_merchant_app/
├── admin/                         # Persian RTL Single-Page Web Admin Panel
│   ├── index.html
│   ├── style.css
│   └── app.js
├── android/                       # Native Android Merchant App (Jetpack Compose)
│   ├── app/src/main/java/ir/torob/seller/
│   │   ├── data/                  # Room DB, Retrofit API Client, Repositories
│   │   ├── service/               # InquiryAlertService (Foreground Service)
│   │   ├── ui/                    # Screens (Inquiries, Detail, History, Store, Metrics)
│   │   └── util/                  # RingtoneManager, NotificationHelper, PersianFormatters
│   └── build.gradle.kts
├── backend/                       # FastAPI REST Server & Background Scheduler
│   ├── main.py                    # App entrypoint and route mounting
│   ├── database.py                # SQLite schema setup & CSV shop importer
│   ├── config.py                  # Pydantic environment configuration
│   ├── routers/                   # Auth, Shop, Inquiries, Push, Metrics, Admin
│   └── services/                  # Scheduler, Push, Working Hours, Poshteyar/Voice
├── docs/                          # Detailed Technical Specifications (English)
│   ├── BUILD_AND_TEST_REPORT.md   # Build status and test results
│   ├── EXTERNAL_SERVICES.md       # Poshteyar, TTS, FCM, and SMS provider details
│   ├── PUSH_SERVICE_GUIDE.md      # Emergency ringing and push architecture
│   └── RUNNING_GUIDE.md           # Step-by-step setup and simulation guide
├── tests/                         # Automated Backend Test Suite (Pytest)
├── torob-dataset/                 # Authentic Torob Dataset (shops.csv)
├── API_DOCUMENTATION.md           # Complete REST API Specification
└── README.md                      # Primary Project Documentation
```

### Technologies:
- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLite 3 (WAL Mode), HTTPX, Pydantic v2
- **Android**: Kotlin, Jetpack Compose, Material 3, Coroutines & StateFlow, Room Database, Retrofit 2, OkHttp 3, AndroidX Media
- **Telephony & Notifications**: Poshteyar REST API, Firebase Cloud Messaging (FCM HTTP v1), Persian TTS Engines

---

## 🚦 Quick Start Guide

### 1. Start the Backend Server
```bash
# Install Python requirements
pip install -r backend/requirements.txt

# Start FastAPI server on port 8080
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Once started:
- **Admin Dashboard:** [http://localhost:8080/admin](http://localhost:8080/admin)
- **Interactive Swagger Docs:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **Health Check:** [http://localhost:8080/api/health](http://localhost:8080/api/health)

### 2. Run Backend Automated Tests
```bash
python3 -m pytest tests/ -v
```

### 3. Build & Run the Android Merchant App
```bash
# 1. Connect physical device or start emulator
adb devices

# 2. Reverse port forwarding so app communicates with localhost:8080
adb reverse tcp:8080 tcp:8080

# 3. Assemble and install debug APK
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 4. Launch App
adb shell am start -n ir.torob.seller.debug/ir.torob.seller.MainActivity
```

---

## ⚙️ Environment Variables Reference

Configure environment settings in `backend/.env` (based on `.env.example`):

```env
# Application
APP_NAME="Torob Seller API"
DEBUG=true
PORT=8080

# Telephony & Poshteyar
OUTBOUND_CALL_PROVIDER=poshtyar
POSHTYAR_ENABLED=true
POSHTYAR_API_URL=https://api.poshtyar.com/api/v1/external/calls/originate
POSHTYAR_API_KEY=your_poshtyar_api_key_here
POSHTYAR_OPERATOR_ID=your_poshtyar_operator_id_here

# Persian Text-to-Speech (TTS)
TTS_PROVIDER=poshtyar_announcement
TTS_DEFAULT_LANGUAGE=fa-IR
TTS_DEFAULT_SPEAKING_RATE=0.9

# Voice Inquiry Reminder Policy (for delinquent stores)
VOICE_REMINDERS_ENABLED=true
VOICE_REMINDER_MIN_ELIGIBLE_INQUIRIES=10
VOICE_REMINDER_MIN_UNANSWERED_INQUIRIES=6
VOICE_REMINDER_MIN_UNANSWERED_RATE=0.6
VOICE_REMINDER_MIN_INTERVAL_MINUTES=1440
VOICE_REMINDER_MAX_CALLS_PER_DAY=1

# Firebase Cloud Messaging (FCM)
FCM_ENABLED=false
FCM_PROJECT_ID=your-project-id
FCM_SERVICE_ACCOUNT_FILE=backend/service-account.json

# SMS Gateway
SMS_PROVIDER=mock
SMS_API_KEY=""

# Database & Dataset
DATABASE_URL=sqlite:///backend/chatapp_seller.db
SHOPS_DATASET_PATH=torob-dataset/shops.csv
```

---

## 📡 REST API Summary

Full documentation is available in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

| Category | Method | Endpoint | Description |
| :--- | :---: | :--- | :--- |
| **Auth** | `POST` | `/api/seller/auth/request-otp` | Request OTP via SMS or Voice Call (Landlines) |
| **Auth** | `POST` | `/api/seller/auth/verify-otp` | Verify OTP and obtain Bearer token |
| **Auth** | `GET` | `/api/seller/auth/me` | Get authenticated merchant profile |
| **Shop** | `GET` | `/api/seller/shop` | Get store profile and live operating status |
| **Shop** | `PUT` | `/api/seller/shop` | Update working hours, holiday mode, preferences |
| **Shop** | `POST` | `/api/seller/shop/toggle-status` | Toggle open/closed manually |
| **Inquiries** | `GET` | `/api/seller/inquiries` | List store inquiries (with auto-expiry) |
| **Inquiries** | `GET` | `/api/seller/inquiries/{id}` | Get inquiry details |
| **Inquiries** | `POST` | `/api/seller/inquiries/{id}/respond` | Submit live quote, out of stock, or decline |
| **Inquiries** | `POST` | `/api/seller/sync/batch-responses` | Batch synchronize offline queued responses |
| **Push** | `POST` | `/api/seller/push/register-token` | Register or update device FCM push token |
| **Metrics** | `GET` | `/api/seller/metrics` | Retrieve store performance statistics |
| **Admin** | `GET` | `/api/admin/inquiries` | View all system inquiries |
| **Admin** | `POST` | `/api/admin/inquiries/create-test` | Inject simulated customer inquiry |
| **Admin** | `GET` | `/api/admin/outbound-calls` | Outbound voice call audit logs |
| **Admin** | `POST` | `/api/admin/voice-reminders/evaluate`| Evaluate and execute delinquent store voice reminders |

---

## 📚 Technical Documentation Index

For in-depth guides, refer to the `docs/` directory:
- [API Documentation (`API_DOCUMENTATION.md`)](API_DOCUMENTATION.md) — Complete endpoint reference, schemas, and sequence diagrams.
- [Running & Setup Guide (`docs/RUNNING_GUIDE.md`)](docs/RUNNING_GUIDE.md) — Detailed environment setup, execution steps, and test simulations.
- [Push & Emergency Alerting Guide (`docs/PUSH_SERVICE_GUIDE.md`)](docs/PUSH_SERVICE_GUIDE.md) — Foreground service, wake locks, ringtone loop, and full-screen calling mechanics.
- [External Services Guide (`docs/EXTERNAL_SERVICES.md`)](docs/EXTERNAL_SERVICES.md) — Poshteyar telephony, Persian TTS engines, and fallback configurations.
- [Build and Test Report (`docs/BUILD_AND_TEST_REPORT.md`)](docs/BUILD_AND_TEST_REPORT.md) — Verification results, test coverage, and physical device test evidence.

---

## 📄 License & Maintainers
Developed for the **Torob Marketplace Ecosystem**. All rights reserved.
