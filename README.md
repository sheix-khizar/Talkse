# Talkse — AI Voice Receptionist Platform

Multi-tenant Voice AI receptionist tailored for aesthetic clinics and medical spas. Answers inbound phone calls, processes real-time natural speech, schedules and manages appointments, answers clinic FAQs via RAG, and handles live caller interaction over WebSockets.

---

## 🏗️ Architecture & Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.11+, async), Uvicorn |
| **Frontend** | React 18, Vite, React Router, Recharts |
| **Database** | PostgreSQL (Supabase / local Postgres with row-level security) |
| **State / Sessions** | Redis (with automatic `fakeredis` fallback for local dev) |
| **Speech-to-Text (STT)** | Deepgram Live Streaming (`nova-2`), Groq Whisper batch fallback |
| **LLM / NLU** | Google Gemini (`google-genai`) |
| **Text-to-Speech (TTS)** | Deepgram Aura-1 (default), ElevenLabs (paid tier) |
| **Telephony Bridge** | SignalWire (cXML / LaML + bidirectional WebSockets) |
| **Local Tunneling** | Cloudflare Tunnel (`cloudflared`) |

---

## 📁 Repository Structure

```
NewTalkse/
├── Talkse-backend/
│   └── Talkse-backend/             # FastAPI backend root
│       ├── app/                    # Application source code
│       │   ├── api/v1/             # REST & Webhook endpoints (SignalWire, Calls, Appointments)
│       │   ├── ws/                 # WebSocket handlers (voice_gateway, signalwire_gateway)
│       │   ├── services/           # AI clients, RAG, conversation loop, TTS router
│       │   └── main.py             # App entry point & DB migrations
│       ├── venv/                   # Python virtual environment
│       ├── cloudflared             # Cloudflare tunnel executable
│       ├── .env.example            # Backend env template
│       └── requirements.txt        # Python dependencies
├── frontend/                       # React + Vite frontend
│   ├── src/                        # Components, Pages, Hooks, API layer
│   ├── .env.example                # Frontend env template
│   └── package.json                # Frontend dependencies
└── README.md                       # Project documentation
```

---

## ⚙️ Environment Configuration

1. **Backend Environment Setup:**
   Copy `.env.example` to `.env` in `Talkse-backend/Talkse-backend/`:
   ```bash
   cp Talkse-backend/Talkse-backend/.env.example Talkse-backend/Talkse-backend/.env
   ```
   Fill in your API keys:
   - `GROQ_API_KEY`, `GEMINI_API_KEY`, `DEEPGRAM_API_KEY`
   - `DATABASE_URL` (PostgreSQL connection string)
   - `CLERK_SECRET_KEY`
   - `SIGNALWIRE_SPACE`, `SIGNALWIRE_PROJECT`, `SIGNALWIRE_TOKEN`, `SIGNALWIRE_SIGNING_KEY`
   - `PUBLIC_HOST` (used for SignalWire WebSocket callback URL)

2. **Frontend Environment Setup:**
   Copy `.env.example` to `.env` in `frontend/`:
   ```bash
   cp frontend/.env.example frontend/.env
   ```
   Set `VITE_CLERK_PUBLISHABLE_KEY`.

---

## 🚀 How to Run the Project

### 1. Run the Backend Server

```bash
cd "Talkse-backend/Talkse-backend"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base URL: `http://localhost:8000`
- Health Check: `http://localhost:8000/health`

### 2. Run the Frontend Development Server

Open a new terminal window:

```bash
cd frontend
npm run dev
```
- Dashboard URL: `http://localhost:3000` (or `http://localhost:5173`)

---

## 🧪 Testing the Voice AI

You can test the platform using **two different methods**:

### Option A: In-App Browser Mic Test (No Phone Call Required)

1. Ensure the Backend and Frontend servers are running.
2. Open `http://localhost:3000` in your browser.
3. Click **Start Test Call** in the dashboard.
4. Speak directly into your microphone. The AI will stream audio responses live back to your browser using Deepgram & Gemini.

---

### Option B: Real Phone Call Testing via SignalWire & Cloudflare

To test with a real inbound phone call from your mobile phone or SIP phone:

#### Step 1: Start Cloudflare Tunnel
Expose your local FastAPI server (port 8000) to the public internet:

```bash
cd "Talkse-backend/Talkse-backend"
./cloudflared tunnel --url http://localhost:8000
```
Cloudflare will print a URL in the console, e.g.:
`https://moments-thinkpad-amplifier-reserve.trycloudflare.com`

#### Step 2: Configure `PUBLIC_HOST` in Backend `.env`
Copy the domain part **without `https://`** into `Talkse-backend/Talkse-backend/.env`:
```env
PUBLIC_HOST=moments-thinkpad-amplifier-reserve.trycloudflare.com
```

#### Step 3: Restart Backend
Restart `uvicorn` in your backend terminal so it reads the updated `PUBLIC_HOST`.

#### Step 4: Configure SignalWire Webhook
1. Log into your [SignalWire Console](https://signalwire.com).
2. Go to **Phone Numbers** -> Select your phone number.
3. Under **Voice Settings**:
   - **Handling**: Select `Webhook` / `cXML Webhook`.
   - **When a call comes in**: Set to `https://<YOUR_PUBLIC_HOST>/api/v1/signalwire/voice` (Method: `POST`).
4. Save the configuration.

#### Step 5: Place a Test Call
Dial your SignalWire phone number from your phone. SignalWire will issue a webhook to `/api/v1/signalwire/voice`, establish a WebSocket audio stream (`wss://<YOUR_PUBLIC_HOST>/ws/signalwire/<call_sid>`), and connect the caller live with the AI voice pipeline.

---

## 📄 License & Notes
- Built for multi-tenant voice AI deployment.
- Ensures idempotent booking logic and persistent session state handling.
