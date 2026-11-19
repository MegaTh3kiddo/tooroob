# 🚀 Local Development & Liara Cloud Deployment Guide

<p align="center">
  <b>🌐 Language / زبان:</b>
  <a href="DEPLOYMENT_GUIDE.md"><b> 🇮🇷 فارسی</b></a> |
  <a href="DEPLOYMENT_GUIDE_EN.md"><b> 🇬🇧 English (Current)</b></a>
</p>

---

> Step-by-step instructions for running the full TorobMap ecosystem locally and deploying containerized services to Liara Cloud.

---

## 1. System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows WSL2
- **Node.js**: v18+ (Recommended: Node 20+)
- **Python**: v3.11+
- **Java / Android Studio**: JDK 17 for building the Android APK
- **Package Managers**: `npm`, `pip`

---

## 2. Local Full-Stack Setup

### Step 1: Customer Web App (`trobapp`)
```bash
cd trobapp
npm install
npm run build
npm start
# or development mode:
npm run dev
```
- Web Application URL: [http://localhost:3000](http://localhost:3000)

### Step 2: Intelligence Backend API (`torob`)
```bash
cd torob
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn torob.api.main:app --host 0.0.0.0 --port 8080 --reload
```
- API Gateway: [http://localhost:8080](http://localhost:8080)
- Interactive Swagger Documentation: [http://localhost:8080/docs](http://localhost:8080/docs)

### Step 3: Merchant Android App (`torob_merchant_app`)
```bash
cd torob_merchant_app/android
./gradlew assembleDebug
```
Output APK: `app/build/outputs/apk/debug/app-debug.apk`

### Step 4: Interactive Pitch Deck (`presentation`)
```bash
cd presentation
python3 -m http.server 8000
```
Open [http://localhost:8000](http://localhost:8000).

---

## 3. Environment Variables

### Frontend (`trobapp/.env.production` or `.env.local`):
```ini
BACKEND_API_URL=http://localhost:8080
```

### Backend (`torob/.env`):
```ini
TOROB_LLM_PROVIDER=openai_compatible
TOROB_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
TOROB_LLM_API_KEY=YOUR_GEMINI_API_KEY
TOROB_LLM_MODEL=gemini-3.1-flash-lite
TOROB_LLM_TIMEOUT_SECONDS=10
TOROB_LLM_POLISH_REPLIES=true
```

---

## 4. Liara Cloud Deployment

Both `torob` and `trobapp` include ready-to-use `liara.json` configurations:

### Backend Deployment:
```bash
cd torob
liara deploy --app torobmap-api --port 8080
```

### Frontend Deployment:
```bash
cd trobapp
liara deploy --app torobmap --port 3000
```
