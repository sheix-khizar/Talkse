# Talkse — AI Voice Receptionist Platform

Multi-tenant Voice AI receptionist for US aesthetic clinics (medspas, botox/laser/skin clinics). Answers inbound calls, understands natural speech, books/reschedules/cancels appointments, answers FAQs from a clinic's knowledge base, and hands off to a human when confidence is low.

> **This README reflects the actual code on the `merge` branch.** The previous version of this doc described a Telnyx/self-hosted-model architecture that no longer matches the codebase — see [Architecture](#architecture) below for what's actually running.

> **Primary product: the Voice AI.** The Admin Dashboard exists only to support it. If a change doesn't improve the Voice AI's reliability or the caller experience, question whether it belongs in this release.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Two Ways a Call Reaches the AI](#two-ways-a-call-reaches-the-ai)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Managed AI & Telephony Providers Setup](#managed-ai--telephony-providers-setup)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [API Structure](#api-structure)
- [WebSocket Events](#websocket-events)
- [Testing Without Placing a Real Phone Call](#testing-without-placing-a-real-phone-call)
- [Testing](#testing)
- [Known Gaps / Open Items](#known-gaps--open-items)
- [Contribution Guide](#contribution-guide)

---

## Features

- Real-time inbound call handling over a WebSocket-based telephony bridge (SignalWire)
- A parallel **browser-based test-call path** (mic → WebSocket) that exercises the entire AI pipeline with no telephony involved
- Streaming speech-to-text via Deepgram's live WebSocket API (one persistent connection per call, kept alive across turns), with a Groq Whisper batch fallback on the browser path
- Deterministic conversation state machine (not implicit LLM memory) — see `app/services/conversation_loop.py` / `conversation_router.py`
- RAG-backed FAQ answering over a clinic's own content (`app/services/rag/`)
- Two-tier TTS: Deepgram Aura-1 by default, ElevenLabs layered in first for tenants on the "paid" plan (falls back to Deepgram on failure)
- Idempotent appointment booking (`booking_engine.py`) keyed by call ID
- Multi-tenant: tenant resolved per call/request, with row-level security enabled in Postgres
- Full call logging and transcript storage
- Clerk-based auth for the dashboard, with a local-dev fallback identity so the API is usable without a Clerk account while developing
- Admin dashboard (React) — live call view, call history, appointments, calendar, per-tenant settings, TTS usage tracking

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python, async) |
| Frontend | React 18 + Vite, React Router, Recharts |
| Database | PostgreSQL (via `psycopg2`) |
| Session / Call State | Redis, with automatic `fakeredis` in-memory fallback if no Redis is reachable |
| Speech-to-Text | Deepgram streaming (`nova-2`), Groq Whisper as a batch fallback on the browser path |
| LLM / NLU | Gemini (`google-genai`) |
| Text-to-Speech | Deepgram Aura-1 (default), ElevenLabs (paid-plan tenants only, optional) |
| Telephony | SignalWire (SWML + bidirectional media WebSocket, Twilio-compatible) |
| Realtime Transport | WebSockets (both the telephony bridge and the browser test-call path) |
| Auth | Clerk (`clerk-backend-api`) |
| Package management | `uv` (`uv.lock` present) / `pip` |
| Testing | Pytest (`pytest-asyncio`) |

> There is no Docker/Compose setup in this branch yet, despite earlier docs referencing one — see [Known Gaps](#known-gaps--open-items).

## Architecture

```mermaid
flowchart TD
    A[Caller - PSTN] --> B[SignalWire]
    B -->|SWML webhook| C[FastAPI: signalwire_webhook.py]
    C -->|answer + connect stream| D[WS: signalwire_gateway.py]
    B2[Browser mic - Dashboard test call] -->|raw PCM| D2[WS: voice_gateway.py]
    D --> E[Deepgram Streaming STT]
    D2 --> E
    E --> F[Conversation Loop / State Machine]
    F --> G[Gemini LLM - intent/entity extraction]
    G --> H[Business Logic + Booking Engine]
    H --> I[(PostgreSQL)]
    F --> J[RAG FAQ Retriever]
    H --> K[TTS Router: Deepgram Aura-1 / ElevenLabs]
    D2 --> L[Redis session store - call: prefix, 1h TTL]
    D --> L
```

Two independent WebSocket entry points both funnel into the same conversation engine:

- **`/ws/signalwire/{call_sid}`** — driven by a real (or SignalWire-simulated) phone call, mu-law 8kHz audio
- **`/ws/calls/{call_id}`** — driven by the dashboard's browser mic, linear16 PCM audio, used for the in-app "test call" flow and for QA without touching the phone network

## Folder Structure

```
Talkse/                            (repo root, branch: merge)
├── Talkse-backend/
│   └── Talkse-backend/
│       ├── app/
│       │   ├── api/v1/
│       │   │   ├── calls.py             # REST call lifecycle (start/turn/end/history)
│       │   │   ├── appointments.py
│       │   │   ├── tenants.py           # per-tenant config, plan, phone number, patients
│       │   │   ├── clinic.py            # services / providers lookup
│       │   │   ├── rag.py               # FAQ query endpoint
│       │   │   └── signalwire_webhook.py
│       │   ├── ws/
│       │   │   ├── voice_gateway.py     # browser mic test-call path
│       │   │   └── signalwire_gateway.py
│       │   ├── core/
│       │   │   ├── config.py            # pydantic-settings Settings
│       │   │   └── security.py          # Clerk auth + tenant resolution
│       │   ├── services/
│       │   │   ├── ai_clients.py
│       │   │   ├── conversation_loop.py
│       │   │   ├── conversation_router.py
│       │   │   ├── booking_engine.py
│       │   │   ├── clinic_config.py
│       │   │   ├── db.py
│       │   │   ├── streaming_stt.py
│       │   │   ├── telephony/audio_convert.py   # mu-law ⇄ PCM16 conversion
│       │   │   ├── tts/                 # base.py, router.py, deepgram_tts.py, elevenlabs_tts.py
│       │   │   └── rag/                 # ingest, chunk, clean, embeddings, retriever, scrape
│       │   ├── session/store.py         # Redis-backed session store
│       │   └── main.py
│       ├── tests/
│       ├── requirements.txt / pyproject.toml / uv.lock
│       └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/        # DashboardPage, CallsPage, LiveCallView, AppointmentsPage, CalendarPage, SettingsPage, OverviewPage
│   │   ├── components/   # CallControls, LiveTranscript, NluBookingPanel, WaveformCenterpiece, PatientCard, NavBar, ...
│   │   ├── hooks/        # useLiveCall.js — owns the /ws/calls/{call_id} connection
│   │   ├── api/          # calls.js, callActions.js, patients.js, client.js
│   │   ├── auth/
│   │   └── context/
│   ├── package.json
│   └── vite.config.js
└── docs/
    └── fix_plan.md        # sprint-by-sprint plan closing out a prior frontend/backend contract audit
```

## Two Ways a Call Reaches the AI

**1. Real (or SignalWire-simulated) phone call**
`SignalWire → POST /api/v1/signalwire/voice → SWML response instructing SignalWire to open a bidirectional media stream → WS /ws/signalwire/{call_sid}`. Audio arrives as base64 mu-law @ 8kHz; converted to PCM16 for STT and back to mu-law for TTS playback (`app/services/telephony/audio_convert.py`).

**2. Dashboard test call (browser mic)**
`POST /api/v1/calls/ → {call_id} → WS /ws/calls/{call_id}`. The frontend's `useLiveCall.js` opens this socket and streams raw mic audio; the server emits typed `{type, data}` events (`transcript.final`, `state.changed`, `audio.chunk`, `call.ended`, …) that the dashboard renders live. This path never touches SignalWire and costs nothing beyond your AI providers' usage — see [Testing Without Placing a Real Phone Call](#testing-without-placing-a-real-phone-call).

## Installation

### Prerequisites

- Python 3.11+ (backend uses `uv` or `pip`)
- Node.js 18+
- A reachable PostgreSQL instance (`DATABASE_URL`)
- Redis is optional for local dev — the session store falls back to in-memory `fakeredis` automatically if it can't connect
- API keys for Groq, Gemini, Deepgram, and Clerk are required to boot; ElevenLabs and SignalWire keys are optional unless you're testing paid-plan TTS or real telephony (see below)

```bash
git clone https://github.com/sheix-khizar/Talkse.git
cd Talkse
git checkout merge
cp Talkse-backend/Talkse-backend/.env.example Talkse-backend/Talkse-backend/.env
cp frontend/.env.example frontend/.env
```

## Environment Variables

**Backend** (`Talkse-backend/Talkse-backend/.env`):

```bash
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
LLM_TIMEOUT_SECONDS=4.0

# ElevenLabs — only required if a tenant is on the "paid" plan
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL_ID=eleven_turbo_v2_5

CLERK_SECRET_KEY=sk_test_your_key_here
CLERK_AUTHORIZED_PARTY=http://localhost:5173

# Only required for real inbound telephony via SignalWire — not needed
# for the browser test-call path
SIGNALWIRE_SPACE=
SIGNALWIRE_PROJECT=
SIGNALWIRE_TOKEN=
SIGNALWIRE_SIGNING_KEY=
PUBLIC_HOST=            # your public hostname, e.g. from ngrok, used to build the wss:// stream URL SignalWire connects back to

REDIS_URL=redis://localhost:6379/0    # optional, see above
```

**Frontend** (`frontend/.env`):

```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
VITE_WS_URL=   # optional; defaults to same-origin ws(s):// if unset
```

## Managed AI & Telephony Providers Setup

All AI components are hosted APIs — no local model hosting required.

- **Groq:** [console.groq.com](https://console.groq.com) — free tier, no card required. Used for the browser-path batch STT fallback.
- **Gemini:** [Google AI Studio](https://aistudio.google.com) — free tier, no card required. Powers intent/entity extraction.
- **Deepgram:** [deepgram.com](https://deepgram.com) — signup credit, used for streaming STT and default TTS.
- **ElevenLabs:** only needed for tenants on the "paid" TTS plan; the TTS router falls back to Deepgram automatically if it's unset or fails.
- **Clerk:** [clerk.com](https://clerk.com) — dashboard auth. If unreachable or the token is missing/invalid, `get_current_user()` falls back to a `dev_user` / tenant `042` identity so local development isn't blocked.
- **SignalWire:** [signalwire.com](https://signalwire.com) — only needed to receive real inbound PSTN calls. Free trial credit is available and trial accounts let you verify and call numbers you own without a card. **You do not need this to test the AI pipeline itself** — see below.

## Backend Setup

```bash
cd Talkse-backend/Talkse-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On startup (`app/main.py` lifespan), the app initializes/migrates its own Postgres tables (tenants, RAG, TTS usage, call logs) and enables row-level security — no separate Alembic step is required in this branch.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## API Structure

```
GET    /health

POST   /api/v1/calls/                          # start a call session (browser test-call path)
POST   /api/v1/calls/{call_id}/turn             # typed-text turn (no audio)
POST   /api/v1/calls/{call_id}/turn/audio        # browser-recorded audio blob turn
POST   /api/v1/calls/{call_id}/end
GET    /api/v1/calls/                            # active calls for the current tenant
GET    /api/v1/calls/history
GET    /api/v1/calls/{call_id}

GET    /api/v1/appointments/

GET    /api/v1/tenants/{tenant_id}/tts-usage
GET    /api/v1/tenants/{tenant_id}/stats
GET    /api/v1/tenants/{tenant_id}/config
PUT    /api/v1/tenants/{tenant_id}/plan
PUT    /api/v1/tenants/{tenant_id}/phone-number
GET    /api/v1/tenants/{tenant_id}/patients
POST   /api/v1/tenants/{tenant_id}/appointments

GET    /api/v1/clinic/services
GET    /api/v1/clinic/providers

POST   /api/v1/rag/query

POST   /api/v1/signalwire/voice                  # SignalWire webhook, returns SWML

WS     /ws/calls/{call_id}                       # browser mic test-call
WS     /ws/signalwire/{call_sid}                 # real telephony media stream
```

## WebSocket Events

Events on `/ws/calls/{call_id}` (browser path), sent as `{"type": ..., "data": ...}`:

| Event | Direction | Payload |
|---|---|---|
| `call.started` | Server → Client | `{callId, callerPhone, plan}` |
| `transcript.final` | Server → Client | `{role, text}` |
| `state.changed` | Server → Client | `{status, isAiSpeaking, nlu?}` |
| `audio.chunk` | Server → Client | `{audio_base64}` |
| `call.ended` | Server → Client | `{callId, outcome}` |

`/ws/signalwire/{call_sid}` speaks SignalWire's own Media Streams protocol directly (`start` / `media` / `stop` events with base64 mu-law payloads), not this typed shape.

## Testing Without Placing a Real Phone Call

You don't need a SignalWire number, a US carrier, or any real telephony to test the AI pipeline end to end:

1. Start the backend and frontend as above.
2. In the dashboard, start a call — this hits `POST /api/v1/calls/` and opens `ws://.../ws/calls/{call_id}`.
3. Speak into your mic. Audio streams to Deepgram STT → the conversation engine → Gemini → the TTS router, and the AI's spoken reply streams back and plays in-browser.

This costs only your AI providers' usage (all have no-card free tiers). To validate the SignalWire webhook layer specifically without dialing internationally, run `pytest tests/test_signalwire.py` (posts a fake `CallSid` and checks the returned SWML) — or, if you want to test a real inbound leg, use SignalWire's browser-based test dialer or a free SIP softphone registered to your SignalWire project so the call routes over IP instead of your local carrier.

## Testing

```bash
cd Talkse-backend/Talkse-backend
pytest                          # full suite
pytest tests/test_conversation.py
pytest tests/test_signalwire.py
pytest tests/test_tts_router.py tests/test_tts_providers.py
pytest tests/test_sprint1_contract.py tests/test_sprint2_tts.py
pytest tests/test_call_plan_resolution.py
```

## Known Gaps / Open Items

- No Dockerfile/`docker-compose.yml` exists in this branch yet — local setup is native (venv + npm), not containerized.
- `GET /api/v1/calls/` (active calls) does a Redis `KEYS`-style scan (`list_active_sessions`); noted in-code as a stopgap, not safe at production scale.
- Call duration isn't tracked from a real start timestamp yet (`started_at` is passed as `None` when logging calls).
- See `docs/fix_plan.md` for a fuller sprint-by-sprint account of frontend/backend contract issues that were found and fixed on this branch — worth a read before assuming any given endpoint is wired all the way through.

## Contribution Guide

1. Branch from `develop` (or the current integration branch).
2. Write/update tests for any behavior change, especially conversation flows.
3. Run `pytest` locally before opening a PR.
4. Describe the tenant/business-rule impact of your change in the PR description.
5. Get one review approval; CI must pass.