# AI Voice Receptionist Platform (Talkse)

Multi-tenant Voice AI receptionist for US aesthetic clinics (medspas, botox/laser/skin clinics), built on managed AI APIs (Gemini, Groq, Deepgram, Telnyx). Answers calls, understands natural speech, books/reschedules/cancels appointments, answers FAQs, and hands off to a human when needed.

> **Architecture note:** This platform previously targeted self-hosted Ollama/Whisper/Piper on CPU. As of this revision it runs on managed AI APIs instead — see `Docs/ARCHITECTURE_DECISIONS.md` for the full reasoning and the cost-based trigger for revisiting self-hosting at higher call volume.

> **Primary Product: the Voice AI.** The Admin Dashboard exists only to support it. If a change doesn't improve the Voice AI's reliability or the caller experience, question whether it belongs in this release.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Voice AI Pipeline](#voice-ai-pipeline)
- [Development Roadmap](#development-roadmap)
- [Installation](#installation)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [PostgreSQL Setup](#postgresql-setup)
- [Redis Setup](#redis-setup)
- [Managed AI Providers Setup](#managed-ai-providers-setup)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [API Structure](#api-structure)
- [WebSocket Events](#websocket-events)
- [Folder Naming & Coding Standards](#folder-naming--coding-standards)
- [Branch Strategy & Git Workflow](#branch-strategy--git-workflow)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contribution Guide](#contribution-guide)
- [Future Roadmap](#future-roadmap)

---

## Features

- Real-time inbound call handling over WebSocket-based telephony bridge (Telnyx)
- Streaming speech-to-text via Groq (`whisper-large-v3-turbo`) — hosted, no local GPU/CPU inference required
- LLM-based intent/entity understanding via Gemini (`gemini-flash-lite-latest`) — **LLM never touches the database**
- Deterministic conversation state machine (not implicit LLM memory)
- Rule-based yes/no and digit-only routing in `conversation/` to cut unnecessary LLM calls and API cost
- Idempotent, race-safe appointment booking/reschedule/cancel
- Human call transfer with context handoff on low confidence or explicit request
- Multi-tenant: one deployment serves many clinics with isolated data and per-clinic configuration
- Full call logging, transcription, and audit trail
- Admin dashboard for staff (calendar, transcripts, escalations, config)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python, async) |
| Frontend | React |
| Database | PostgreSQL |
| Cache / Session Store | Redis |
| Speech-to-Text | Groq (`whisper-large-v3-turbo`), hosted |
| LLM | Gemini API (`gemini-flash-lite-latest`), hosted |
| Text-to-Speech | Deepgram Aura-1 (`aura-asteria-en`), hosted, with response audio caching |
| Telephony | Telnyx (SIP trunking + WebSocket audio bridge) |
| Realtime Transport | WebSockets |
| Auth | JWT |
| Containerization | Docker / Docker Compose |
| Reverse Proxy | Nginx |

> See `Docs/ARCHITECTURE_DECISIONS.md` for the cost model and the call-volume threshold at which self-hosting STT/LLM/TTS becomes cheaper than this managed stack.

## Architecture

```mermaid
flowchart TD
    A[Caller] --> B[Telephony Provider]
    B --> C[FastAPI Voice Gateway]
    C --> D[Call Session Manager - Redis]
    D --> E[Groq Whisper - STT, hosted]
    E --> F[Conversation Manager - State Machine]
    F --> G[Gemini LLM, hosted]
    G --> H[Intent/Entity Extraction]
    H --> I[Business Logic Layer]
    I --> J[Booking Engine]
    J --> K[(PostgreSQL)]
    I --> L[Response Generator]
    L --> M[Deepgram Aura-1 TTS, hosted]
    M --> B
    I -.low confidence.-> N[Human Transfer]
```

**Non-negotiable rule:** the LLM only ever sees a transcript + conversation context and returns structured JSON (intent, entities, confidence). It never queries or writes the database. The Business Logic Layer owns every rule, availability check, and write.

## Folder Structure

```
voice-receptionist-platform/
├── backend/
│   ├── app/
│   │   ├── api/                  # REST routers (dashboard, admin, tenant config)
│   │   ├── ws/                   # WebSocket handlers (voice gateway)
│   │   ├── core/                 # config, security, logging, settings
│   │   ├── session/              # Call Session Manager (Redis-backed)
│   │   ├── conversation/         # Conversation Manager / state machine
│   │   ├── stt/                  # Groq Whisper client wrapper
│   │   ├── llm/                  # Gemini orchestrator, prompt templates, timeout/circuit breaker
│   │   ├── nlu/                  # Intent/entity extraction + validation schemas
│   │   ├── business/             # Business Logic Layer (per-tenant rules)
│   │   ├── booking/              # Booking Engine (transactional, idempotent)
│   │   ├── tts/                  # Deepgram Aura client wrapper & audio cache
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── db/                   # session, migrations (Alembic)
│   │   └── observability/        # logging, metrics, tracing
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conversation_flows/   # scripted conversation regression tests
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── hooks/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── docker-compose.yml        # backend, frontend, postgres, redis, nginx (no local AI services)
│   ├── nginx/
│   └── deploy/                   # environment-specific configs
├── Docs/
│   ├── ARCHITECTURE_DECISIONS.md
│   ├── KPI_PLAN (1) (1).md
│   └── README (3).md
└── .github/workflows/            # CI/CD pipelines
```

## Voice AI Pipeline

```mermaid
sequenceDiagram
    participant Caller
    participant GW as Voice Gateway
    participant STT as Groq Whisper (hosted)
    participant CM as Conversation Manager
    participant LLM as Gemini (hosted)
    participant BL as Business Logic
    participant DB as PostgreSQL
    participant TTS as Deepgram Aura-1 (hosted)

    Caller->>GW: Audio stream
    GW->>STT: Chunked audio
    STT-->>CM: Transcript (partial/final)
    CM->>LLM: Transcript + state + tenant context
    LLM-->>CM: {intent, entities, confidence}
    CM->>BL: Validated request
    BL->>DB: Availability / write
    DB-->>BL: Result
    BL-->>CM: Next state + response text
    CM->>TTS: Response text
    TTS-->>GW: Synthesized audio
    GW-->>Caller: Audio stream
```

## Development Roadmap

- **Phase 1:** Core pipeline on managed APIs (STT → LLM → NLU → Business Logic → Booking → TTS), single-tenant, real latency baseline measurement against managed-provider targets
- **Phase 2:** Multi-tenant data model, tenant-scoped prompts/config, dashboard MVP
- **Phase 3:** Observability stack, circuit breakers, rate limiting, CI/CD
- **Phase 4:** Load testing, horizontal scaling, human handoff refinement
- **Phase 5:** Production rollout to pilot clinics, then general availability

## Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- No GPU/CPU model hosting required — all AI components are managed APIs; you need API keys for Gemini, Groq, Deepgram, and Telnyx before running the full pipeline (see [Managed AI Providers Setup](#managed-ai-providers-setup))

```bash
git clone https://github.com/your-org/voice-receptionist-platform.git
cd voice-receptionist-platform
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

## Docker Setup

`infra/docker-compose.yml` defines: `backend`, `frontend`, `postgres`, `redis`, `nginx`. No local AI service containers (no Ollama, no self-hosted STT/TTS) — Gemini, Groq, and Deepgram are called over the network via their respective API keys in `.env`. Each service has its own healthcheck; `backend` waits on `postgres` and `redis` healthchecks before starting.

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml logs -f backend
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/voice_platform

# Redis
REDIS_URL=redis://redis:6379/0

# Gemini (LLM)
GEMINI_API_KEY=change-me-in-vault
GEMINI_MODEL=gemini-flash-lite-latest

# Groq (STT)
GROQ_API_KEY=change-me-in-vault
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

# Deepgram (TTS)
DEEPGRAM_API_KEY=change-me-in-vault
DEEPGRAM_VOICE=aura-asteria-en

# Telnyx (Telephony)
TELNYX_API_KEY=change-me-in-vault
TELNYX_PUBLIC_KEY=change-me-in-vault
TELNYX_PHONE_NUMBER=+1XXXXXXXXXX

# Auth
JWT_SECRET=change-me-in-vault
JWT_EXPIRY_MINUTES=60

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
LLM_TIMEOUT_SECONDS=4.0
```

> In production, secrets come from a vault/secret manager — never committed `.env` files.

## PostgreSQL Setup

```bash
docker exec -it voice-platform-postgres psql -U user -d voice_platform
alembic upgrade head
```

Row-level security is enabled per tenant table; every query must run with the tenant context set (`SET app.current_tenant = '<tenant_id>'`) via a session middleware.

## Redis Setup

Redis stores ephemeral state only: active call sessions, conversation turn history, and rate-limit counters. Nothing durable lives in Redis — PostgreSQL is the source of truth for anything that must survive a restart.

```bash
docker exec -it voice-platform-redis redis-cli PING
```

## Managed AI Providers Setup

No local model downloads or GPU/CPU provisioning required — all three AI components are hosted APIs. Sign up for each provider and add the resulting keys to `.env` (never `.env.example`):

- **Gemini (LLM):** [Google AI Studio](https://aistudio.google.com) — free tier available, no card required. Use the `gemini-flash-lite-latest` alias so the config auto-tracks Google's current model without manual updates as older versions get deprecated.
- **Groq (STT):** [console.groq.com](https://console.groq.com) — free tier available, no card required (2,000 requests/day).
- **Deepgram (TTS):** [deepgram.com](https://deepgram.com) — $200 signup credit, no recurring free tier after that.
- **Telnyx (Telephony):** [telnyx.com](https://telnyx.com) — free trial credit, no card required to start. Consider applying to Telnyx's AI Accelerator program for additional startup credit.

The LLM Orchestrator wraps all Gemini calls with a timeout (`LLM_TIMEOUT_SECONDS`, default 4s for hosted API) and circuit breaker; on failure it returns a fallback canned response, never hanging the call.

Pre-synthesize and cache common TTS phrases (greetings, confirmations) per tenant to cut both latency and character-based Deepgram cost.

**Free tiers are for development only, not a production cost plan.** They are rate-limited (~15-30 requests/minute) and, for Deepgram, a one-time credit rather than a recurring allowance. See `Docs/ARCHITECTURE_DECISIONS.md` for production cost modeling and the volume threshold for revisiting self-hosting.

## Backend Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## API Structure

```
POST   /api/v1/tenants/{tenant_id}/appointments
GET    /api/v1/tenants/{tenant_id}/appointments/{id}
PATCH  /api/v1/tenants/{tenant_id}/appointments/{id}
DELETE /api/v1/tenants/{tenant_id}/appointments/{id}
GET    /api/v1/tenants/{tenant_id}/calls
GET    /api/v1/tenants/{tenant_id}/calls/{call_id}/transcript
GET    /api/v1/tenants/{tenant_id}/escalations
POST   /api/v1/auth/login
```

Example booking request:

```json
POST /api/v1/tenants/clinic_042/appointments
{
  "caller_phone": "+15551234567",
  "service_id": "svc_botox_touchup",
  "provider_id": "prov_dr_smith",
  "requested_time": "2026-07-25T15:30:00-05:00",
  "idempotency_key": "call_88f2e1-book-1"
}
```

Example response:

```json
{
  "appointment_id": "appt_9a31c",
  "status": "confirmed",
  "scheduled_time": "2026-07-25T15:30:00-05:00",
  "provider": "Dr. Smith",
  "service": "Botox Touch-Up"
}
```

## WebSocket Events

| Event | Direction | Payload |
|---|---|---|
| `call.started` | Gateway → Client | `{call_id, tenant_id, caller_number}` |
| `audio.chunk` | Client ↔ Gateway | binary audio frame |
| `transcript.partial` | Gateway → Client (internal) | `{call_id, text}` |
| `transcript.final` | Gateway → Client (internal) | `{call_id, text}` |
| `state.changed` | Internal | `{call_id, from_state, to_state}` |
| `call.transferred` | Gateway → Telephony | `{call_id, reason, target}` |
| `call.ended` | Gateway → Client | `{call_id, outcome}` |

## Folder Naming & Coding Standards

- `snake_case` for Python modules/files, `PascalCase` for classes, `camelCase` for React components/files.
- One responsibility per module — e.g., `booking/engine.py` never imports `llm/` directly; it only receives validated data from `business/`.
- All Pydantic schemas for LLM output live in `nlu/schemas.py` — the LLM's JSON is validated against these before anything downstream trusts it.
- Type hints required on all backend function signatures.

## Branch Strategy & Git Workflow

- `main` — production-ready, protected, deploy-on-merge to prod
- `develop` — integration branch, deploy-on-merge to staging
- `feature/<ticket-id>-short-desc` — feature branches off `develop`
- `hotfix/<ticket-id>` — off `main`, merged back to both `main` and `develop`

All PRs require: passing CI (lint, unit tests, conversation-flow regression tests), one reviewer approval, and no direct commits to `main`/`develop`.

## Testing

- **Unit tests** — business logic, booking engine, NLU schema validation
- **Integration tests** — API + DB + Redis, using test containers
- **Conversation-flow regression tests** — scripted multi-turn transcripts run against the Conversation Manager + LLM to catch prompt/model-swap regressions before deploy
- **Load tests** — concurrent call simulation to validate latency SLAs under load

```bash
pytest backend/tests/unit
pytest backend/tests/integration
pytest backend/tests/conversation_flows
```

## Deployment

- Staged environments: `dev → staging → production`
- CI/CD via GitHub Actions: lint → test → build image → push → deploy
- Blue/green or canary deploy for the Voice Gateway to avoid dropping active calls
- Database migrations run as a pre-deploy step, backward-compatible for at least one release

## Monitoring

- Structured JSON logs with `call_id`/`tenant_id` correlation, shipped to a log aggregator
- Prometheus metrics: latency per pipeline stage, STT/LLM/TTS error rates, active call count, escalation rate
- Grafana dashboards per tenant and platform-wide
- Alerting on: latency SLA breach, error rate spike, Gemini/Groq/Deepgram API failure or rate-limit (429) errors

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Long silence mid-call | LLM or STT timeout without fallback | Check circuit breaker logs; verify Gemini/Groq API status and rate-limit headers |
| Double-booked slot | Missing row lock / idempotency key | Check Booking Engine transaction logs |
| Cross-tenant data appearing | Missing tenant_id filter or RLS misconfig | Verify `SET app.current_tenant` middleware is active |
| High latency | Network latency to a provider, or hitting a free-tier rate limit | Check provider status pages; confirm you're on a paid/Developer tier if traffic exceeds free-tier RPM limits |

## Contribution Guide

1. Fork/branch from `develop`.
2. Write/update tests for any behavior change, especially conversation flows.
3. Run `pytest` and lint locally before opening a PR.
4. Describe the tenant/business-rule impact of your change in the PR description.
5. Get one review approval; CI must pass.

## Future Roadmap

Multi-language support, SMS/email confirmations, outbound reminder calls, calendar integrations, sentiment-based QA scoring, self-serve clinic onboarding.
