# External Services, Telephony Providers & Fallbacks

This document details all third-party integrations, external service providers, telephony gateways, API configurations, and implemented fallback mechanisms within the Torob Merchant Platform.

---

## 1. Outbound Telephony & Persian Text-to-Speech (Poshteyar)

| Attribute | Specification |
| :--- | :--- |
| **Purpose** | 1) Telephone-based login verification for merchant landline store numbers.<br/>2) Automated voice reminders for delinquent stores with excessive unanswered inquiries. |
| **Provider** | **Poshteyar** (`poshtyar`) |
| **Endpoint** | `https://api.poshtyar.com/api/v1/external/calls/originate` |
| **Authentication** | API Key header (`X-API-KEY` or Bearer token) |
| **Persian TTS Engines** | `poshtyar_announcement` (Poshteyar native audio announcement endpoint), `google` (Google Cloud Text-to-Speech `fa-IR`), or `mock` (development simulation). |
| **Audio Format** | WAV / MP3 8kHz/16kHz Mono compliant with Iranian telecom codecs. |
| **Config Keys** | `OUTBOUND_CALL_PROVIDER`, `POSHTYAR_ENABLED`, `POSHTYAR_API_URL`, `POSHTYAR_API_KEY`, `POSHTYAR_OPERATOR_ID`, `TTS_PROVIDER`, `TTS_DEFAULT_LANGUAGE`, `TTS_DEFAULT_SPEAKING_RATE`. |
| **Fallback / Dev Mode** | If `POSHTYAR_API_KEY` is not provided or `OUTBOUND_CALL_PROVIDER="mock"`, outbound calls are simulated immediately without network latency. Full call metadata is recorded in `outbound_call_logs`, and for landline OTP requests, the generated security code is returned in the API response under `demo_otp`. |

---

## 2. Firebase Cloud Messaging (FCM HTTP v1)

| Attribute | Specification |
| :--- | :--- |
| **Purpose** | Immediate push notification delivery to Android devices for Time-Zero inquiries, 2-minute urgent alerts, and expiration events even when the device is locked or in Doze Mode. |
| **Authentication** | Google OAuth2 via Service Account JSON (`https://www.googleapis.com/auth/firebase.messaging`). |
| **Required Keys** | `FCM_PROJECT_ID` and `FCM_SERVICE_ACCOUNT_FILE` on the backend, and `google-services.json` in `android/app/`. |
| **Config Keys** | `FCM_ENABLED`, `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_FILE`. |
| **Fallback / Dev Mode** | When FCM credentials are not configured, the backend logs notifications to `push_audit_logs` in SQLite and skips external network delivery (`SKIPPED_NO_DEVICES` or simulated dispatch). The Android client also maintains a 3-second local polling loop and live countdown calculation, guaranteeing that urgent ringing and expiration occur accurately even without Google Play Services or FCM connectivity. |

---

## 3. SMS OTP Gateway

| Attribute | Specification |
| :--- | :--- |
| **Purpose** | Delivers 5-digit verification codes to merchant mobile numbers. |
| **Supported Gateways** | Kavenegar, Sms.ir, and built-in mock generator. |
| **Config Keys** | `SMS_PROVIDER` (`kavenegar`, `sms_ir`, or `mock`), `SMS_API_KEY`. |
| **Fallback / Dev Mode** | Defaults to `mock` mode. The generated OTP is returned directly in the response field `demo_otp`. In test environments, the master test OTP `12345` is also accepted, allowing full end-to-end testing without external SMS billing. |

---

## 4. Map & Navigation Schemes (Zero-Key Navigation)

| Attribute | Specification |
| :--- | :--- |
| **Purpose** | Navigates buyers directly to the merchant's physical store address in Tehran. |
| **Supported Applications** | Neshan (`nshn:`), Balad (`balad:`), and Google Maps (`geo:`, `https://maps.google.com`). |
| **API Keys** | **Zero API Keys Required**. Handled entirely through standard Android intent URI schemes and geo-coordinates. |

---

## 5. Embedded Database Engine (SQLite WAL)

| Attribute | Specification |
| :--- | :--- |
| **Technology** | SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), Foreign Keys enabled, and Synchronous NORMAL. |
| **Dataset** | Automatically provisions tables and imports 41,563 authentic Torob shops from `torob-dataset/shops.csv` during `init_db()`. |
| **Maintenance** | Auto-purging of stale sync queues and historical audit records via background scheduler routines. |
