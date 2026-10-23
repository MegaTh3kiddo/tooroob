# Complete Running & Setup Guide

This guide provides end-to-end instructions for running the backend API, the Persian Web Admin Dashboard, automated test suites, and the Android merchant mobile application.

---

## 1. System Requirements

- **Operating System:** Linux (Ubuntu 20.04+), macOS, or Windows 10/11 (WSL2 recommended)
- **Python:** Python 3.10+ (tested on Python 3.12)
- **Java / Android:** OpenJDK 17 or 21 and Android SDK 34 (Android Studio Hedgehog or newer)
- **Physical Device or Emulator:** Android 7.0+ (API Level 24 to 34), with USB Debugging enabled

---

## 2. Setting Up the Backend & Admin Web Dashboard

### Step 1: Install Python Dependencies
From the repository root:
```bash
pip install -r backend/requirements.txt
```

### Step 2: Configure Environment Variables
Copy the example environment template:
```bash
cp .env.example backend/.env
```
*(All defaults are pre-configured for local offline development with simulated telephony and SMS providers).*

Key settings in `backend/.env`:
```env
# Telephony & Poshteyar
OUTBOUND_CALL_PROVIDER=poshtyar
POSHTYAR_ENABLED=true
POSHTYAR_API_URL=https://api.poshtyar.com/api/v1/external/calls/originate
POSHTYAR_API_KEY=your_poshtyar_api_key_here
POSHTYAR_OPERATOR_ID=your_poshtyar_operator_id_here

# Persian TTS
TTS_PROVIDER=poshtyar_announcement
TTS_DEFAULT_LANGUAGE=fa-IR
TTS_DEFAULT_SPEAKING_RATE=0.9

# Voice Reminders for Delinquent Stores
VOICE_REMINDERS_ENABLED=true
VOICE_REMINDER_MIN_ELIGIBLE_INQUIRIES=10
VOICE_REMINDER_MIN_UNANSWERED_INQUIRIES=6
VOICE_REMINDER_MIN_UNANSWERED_RATE=0.6

# Database & Dataset
DATABASE_URL=sqlite:///backend/chatapp_seller.db
SHOPS_DATASET_PATH=torob-dataset/shops.csv
```

### Step 3: Start the Backend Service
Run Uvicorn inside the `backend/` directory:
```bash
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Step 4: Verify Endpoints
Once running:
- **Admin Web Dashboard (Persian RTL):** [http://localhost:8080/admin](http://localhost:8080/admin)
- **Interactive Swagger Documentation:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **API Health Check:** [http://localhost:8080/api/health](http://localhost:8080/api/health)

---

## 3. Running Automated Tests

Run the full pytest suite from the project root:
```bash
python3 -m pytest tests/ -v
```

All 7 core test modules will execute and report 100% pass rates.

---

## 4. Building & Running the Android App

### Method A: Via Command-Line & ADB

1. **Connect your physical Android device via USB** (or start an Android Emulator):
   ```bash
   adb devices
   ```

2. **Forward Backend Port to Connected Device**:
   ```bash
   adb reverse tcp:8080 tcp:8080
   ```
   *(This ensures `http://127.0.0.1:8080` calls from inside the Android app reach the host machine backend).*

3. **Compile the Debug APK**:
   ```bash
   cd android
   ./gradlew assembleDebug
   ```

4. **Install on Device**:
   ```bash
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```

5. **Launch the Application**:
   ```bash
   adb shell am start -n ir.torob.seller.debug/ir.torob.seller.MainActivity
   ```

### Method B: Via Android Studio

1. Open Android Studio and select **Open**, pointing to the `android/` directory.
2. Wait for Gradle Sync to complete.
3. Select your connected device or emulator in the device dropdown.
4. Click **Run** (`Shift + F10`).

---

## 5. Simulating Test Workflows

### 5.1. Injecting a Test Buyer Inquiry
Send a request to the admin endpoint:
```bash
curl -X POST http://localhost:8080/api/admin/inquiries/create-test \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "shop_51d0c1a6edf81ba759726bab",
    "product_id": "p_test_laptop",
    "product_title": "لپ‌تاپ ایسوس ROG Strix",
    "category_name": "لپ‌تاپ",
    "recorded_price_toman": 85000000,
    "customer_name": "رضا محمدی",
    "customer_phone": "09129876543",
    "inquiry_type": "price_and_stock",
    "user_note": "آیا گارانتی اصلی سازگار دارد؟"
  }'
```

### 5.2. Testing the 2-Minute Emergency Ringing Call
Update the inquiry's `expires_at` to be within 110 seconds:
```bash
python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('backend/chatapp_seller.db')
c = conn.cursor()
new_exp = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=110)).strftime('%Y-%m-%d %H:%M:%S')
c.execute('UPDATE inquiries SET expires_at = ? WHERE status = \"ACTIVE\"', (new_exp,))
conn.commit()
print('Inquiry updated to 110s remaining')
"
```
Within 3 seconds, the phone will begin ringing and vibrating, displaying `IncomingInquiryActivity`. Upon reaching 0:00, it automatically stops ringing and moves the card to the History tab.

### 5.3. Testing Persian Voice OTP on Landlines
Request an OTP with a landline number (e.g. Tehran `021...`):
```bash
curl -X POST http://localhost:8080/api/seller/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "02176557624"}'
```
Response will return `delivery_method: "voice_call"` and the spoken verification code.
