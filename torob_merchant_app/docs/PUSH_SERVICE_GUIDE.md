# Push Notifications & Emergency Calling Architecture Guide

This guide describes the configuration, delivery mechanics, foreground services, full-screen intents, continuous ringtones, and offline countdown monitoring for the Torob Merchant Platform.

---

## 1. Notification Architecture & Dispatch Pipeline

```text
┌─────────────────────────────────┐
│     Customer Submits Inquiry    │
└────────────────┬────────────────┘
                 │ (Time Zero: 0:00)
┌────────────────▼────────────────┐
│   FastAPI Backend Scheduler     │
│ - Registers inquiry timeline    │
│ - push_service.send_to_seller() │
└────────────────┬────────────────┘
                 │
                 ▼ FCM HTTP v1 API
┌─────────────────────────────────┐
│ Firebase Cloud Messaging (Google)│
└────────────────┬────────────────┘
                 │ (High-Priority Data Payload)
┌────────────────▼────────────────────────────────────────┐
│ Merchant Android Phone (Screen Off / Doze Mode)        │
│ 1. SellerFirebaseMessagingService receives payload      │
│ 2. TorobNotificationHelper displays heads-up alert     │
│ 3. Deep link "torob://inquiry/{id}" ready for tap      │
└─────────────────────────────────────────────────────────┘
                 │
                 │ After 8 minutes without response (T - 2 min)
┌────────────────▼────────────────────────────────────────┐
│ Emergency Ringing Window (Urgent Call):                │
│ 1. FCM delivers URGENT_CALL push OR                     │
│    Local InquiryViewModel detects remaining <= 120s    │
│ 2. InquiryAlertService starts as Foreground Service    │
│ 3. InquiryRingtoneManager triggers looped ringtone &   │
│    continuous vibration pattern                        │
│ 4. Full-Screen IncomingInquiryActivity launches        │
│ 5. Merchant can quote, declare out of stock, or decline │
└─────────────────────────────────────────────────────────┘
                 │
                 │ At 10:00 (Expiration)
┌────────────────▼────────────────────────────────────────┐
│ Automatic Expiry Handling:                              │
│ 1. ACTION_STOP_ALERT silences ringtone immediately     │
│ 2. Inquiry status transitions to EXPIRED in Room DB     │
│ 3. Card removed from Active list and moved to History  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Setting Up Firebase Cloud Messaging (FCM HTTP v1)

### Step 1: Client `google-services.json`
1. Access the [Firebase Console](https://console.firebase.google.com/).
2. Create or open your project and register an Android app with package name `ir.torob.seller`.
3. Download the generated `google-services.json` and place it at:
   ```
   android/app/google-services.json
   ```

### Step 2: Backend Service Account JSON
1. In the Firebase Console, navigate to **Project Settings** > **Service accounts**.
2. Click **Generate new private key** to download the Service Account credentials file.
3. Save the file on the server (e.g., `backend/service-account.json`).
4. Configure the environment variables in `backend/.env`:
   ```env
   FCM_ENABLED=true
   FCM_PROJECT_ID="your-firebase-project-id"
   FCM_SERVICE_ACCOUNT_FILE="service-account.json"
   ```

---

## 3. High-Priority Payload Specification

The backend dispatches pure data messages with `priority: "high"` to ensure instant wake-up even during Android Doze mode:

```json
{
  "message": {
    "token": "device_fcm_token_here",
    "data": {
      "notification_type": "URGENT_CALL",
      "inquiry_id": "inq_80717080cc",
      "tracking_code": "TRB-38698A",
      "product_title": "لپ‌تاپ ایسوس ROG Strix",
      "customer_name": "رضا محمدی",
      "title": "تماس فوری استعلام ترب",
      "body": "فقط ۲ دقیقه تا پایان مهلت پاسخ به استعلام لپ‌تاپ ایسوس ROG Strix باقی مانده است!",
      "duration_seconds": "120"
    },
    "android": {
      "priority": "HIGH"
    }
  }
}
```

---

## 4. Android Client Alert Components

### 4.1. `InquiryAlertService` (Foreground Service)
- Manages wake locks (`PowerManager.PARTIAL_WAKE_LOCK` with `ACQUIRE_CAUSES_WAKEUP`).
- Runs as a foreground service with type `FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK` on Android 10+ (API 29+).
- Handles actions:
  - `ACTION_START_ALERT`: Initiates continuous ringing, vibration, and full-screen intent.
  - `ACTION_STOP_ALERT`: Silences audio, terminates vibration, releases wake locks, and stops the service.

### 4.2. `InquiryRingtoneManager`
- Uses `RingtoneManager.TYPE_RINGTONE` (fallback to `TYPE_ALARM` or `TYPE_NOTIFICATION`).
- Configures `AudioAttributes.USAGE_NOTIFICATION_RINGTONE` and `USAGE_ALARM`.
- Plays on a continuous loop until explicitly stopped or until maximum timeout (120 seconds).
- Executes rhythmic vibration pattern: `[0ms delay, 1000ms vibrate, 1000ms pause]`.

### 4.3. `IncomingInquiryActivity` (Full-Screen Intent)
- Declared with:
  ```xml
  android:showWhenLocked="true"
  android:turnScreenOn="true"
  ```
- Renders full-screen incoming call UI showing product title, customer question, reference price, and remaining countdown.
- Provides immediate actions:
  - **Submit Response (اعلام قیمت و موجودی)**: Opens response form.
  - **Quick Confirm Previous Price (تأیید سریع قیمت قبلی)**: Instantly confirms catalog price.
  - **Out of Stock (اعلام عدم موجودی)**: Sends immediate out-of-stock response.
  - **Decline Inquiry (رد استعلام)**: Prompts for decline reason.

### 4.4. Offline & Local Countdown Fail-Safe
To safeguard merchants in environments without Google Play Services or when internet connectivity drops:
- `InquiryViewModel` runs a periodic 3-second evaluation loop (`startPeriodicSyncAndUrgentCheck`).
- Calculates live remaining seconds using the UTC expiration timestamp (`getLiveRemainingSeconds()`).
- If remaining time is $\le 120$ seconds, it locally initiates `ACTION_START_ALERT` regardless of push delivery.
- If remaining time reaches 0 seconds, it automatically marks the inquiry as `EXPIRED`, cancels all alarms, and updates the local Room database.
