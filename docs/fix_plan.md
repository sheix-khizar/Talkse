# Talkse — Implementation Plan to Close the Audit Findings

Branch: `fullstakcintegration`. This plan is sequenced deliberately —
**do not skip ahead**. Sprint 1 unblocks everything else: nothing in the
frontend can be verified as actually working until the WebSocket contract
and missing endpoints are fixed, so fixing TTS or auth before Sprint 1
means testing them against a UI that's silently showing fake data anyway.

**Ground rule for every sprint below:** before editing any file, `cat` it
fresh and confirm the `old_str` snippets below still match exactly — this
plan is based on a specific snapshot of the repo and may drift if other
work lands first. If a snippet doesn't match, stop and re-read the file
rather than guessing.

---

## Sprint 1 — Fix the frontend/backend contract (highest priority)

### Problem recap
- Backend WebSocket sends `{transcript, reply_text, terminal}`. Frontend
  expects `{type, data}` with `type` values like `transcript.final`. They
  never match, so the dashboard never updates from a real call.
- Frontend calls `GET /api/v1/calls`, `GET /api/v1/tenants/{id}/patients`,
  `POST /api/v1/tenants/{id}/appointments`, `POST /api/v1/calls/{id}/handoff`,
  `POST /api/v1/calls/{id}/transfer`, `POST /api/v1/calls/{id}/end` — **none
  of these exist on the backend.** Every one of these frontend functions
  silently falls back to hardcoded fake data on failure, so the dashboard
  always looks like it's working even when nothing is connected.

### Decision: standardize on the frontend's `{type, data}` shape
The frontend and the README's own "WebSocket Events" table already agree
on this shape — it's the backend that's the outlier. Changing the backend
is less total work than changing the frontend + the README.

### Step 1.1 — Backend: emit typed WebSocket events

File: `Talkse-backend/Talkse-backend/app/ws/voice_gateway.py`

Replace the entire file with:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session

router = APIRouter()


async def _emit(websocket: WebSocket, event_type: str, data: dict):
    """Sends a typed event matching the frontend's expected {type, data}
    shape (see frontend/src/hooks/useLiveCall.js handleSocketEvent and the
    README's WebSocket Events table)."""
    await websocket.send_json({"type": event_type, "data": data})


@router.websocket("/ws/calls/{call_id}")
async def voice_ws(websocket: WebSocket, call_id: str):
    await websocket.accept()
    state = get_session(call_id)
    if not state:
        await websocket.close(code=4404)
        return

    await _emit(websocket, "call.started", {
        "callId": call_id,
        "callerPhone": state.get("caller_phone"),
    })

    transcriber = StreamingTranscriber(sample_rate=16000)
    transcriber.start()
    transcriber.begin_turn()
    try:
        while True:
            data = await websocket.receive_bytes()   # raw PCM chunk from browser
            transcript = transcriber.feed(data)
            if transcript:
                await _emit(websocket, "transcript.final", {
                    "role": "customer",
                    "text": transcript,
                })

                result = handle_turn(transcript, state)
                save_session(call_id, state)

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": True,
                })

                if result.get("reply_text"):
                    await _emit(websocket, "transcript.final", {
                        "role": "ai",
                        "text": result["reply_text"],
                    })

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": False,
                })

                if result["terminal"]:
                    await _emit(websocket, "call.ended", {
                        "callId": call_id,
                        "outcome": state.get("status"),
                    })
                    break
    except WebSocketDisconnect:
        pass
    finally:
        transcriber.close()
```

**Note for Sprint 2:** this version still doesn't synthesize audio — that's
deliberate, Sprint 2 adds it on top of this fixed contract. Don't add TTS
here; keep this sprint scoped to the contract fix only.

### Step 1.2 — Backend: add the missing `GET /api/v1/calls` endpoint

File: `Talkse-backend/Talkse-backend/app/api/v1/calls.py`

Find the top of the file:
```python
from fastapi import APIRouter, UploadFile, HTTPException
import time, uuid
from app.session.store import new_session, get_session, save_session
from app.services.conversation_loop import prompt_for_field, handle_turn
from app.services import db
from app.services.poc import transcribe

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])
```

Add a new route directly after the `router = APIRouter(...)` line (before
`@router.post("/")`):

```python
@router.get("/")
def list_active_calls():
    """Returns currently active/waiting calls from Redis session state.
    NOTE: this is a placeholder scan — Redis KEYS is O(n) and not safe at
    production scale. Sprint 6 (multi-tenancy) should replace this with an
    indexed 'active calls' set maintained by new_session()/save_session(),
    not a KEYS scan. Flagged here rather than silently left as a footgun."""
    from app.session.store import list_active_sessions
    sessions = list_active_sessions()
    return [
        {
            "id": call_id,
            "status": "ACTIVE" if state.get("status") == "collecting" else state.get("status", "ACTIVE").upper(),
            "callerName": state.get("caller_name") or "Unknown Caller",
            "service": state.get("service") or "General Inquiry",
            "duration": "--:--",  # no started_at timestamp tracked yet — see Sprint 6
        }
        for call_id, state in sessions
    ]
```

### Step 1.3 — Backend: add `list_active_sessions` to the session store

File: `Talkse-backend/Talkse-backend/app/session/store.py`

Find:
```python
import json
import redis
from app.core.config import settings

_r = redis.from_url(settings.redis_url, decode_responses=True)

def new_session(call_id: str, initial_state: dict):
    _r.setex(f"call:{call_id}", 3600, json.dumps(initial_state))
```

Replace with:
```python
import json
import redis
from app.core.config import settings

_r = redis.from_url(settings.redis_url, decode_responses=True)

def new_session(call_id: str, initial_state: dict):
    _r.setex(f"call:{call_id}", 3600, json.dumps(initial_state))

def list_active_sessions() -> list[tuple[str, dict]]:
    """Scans for active call: keys and returns (call_id, state) pairs.
    See the NOTE in calls.py's list_active_calls() — this is a stopgap,
    not the production-scale answer."""
    results = []
    for key in _r.scan_iter(match="call:*"):
        raw = _r.get(key)
        if raw:
            call_id = key.split("call:", 1)[1]
            results.append((call_id, json.loads(raw)))
    return results
```

(`scan_iter` instead of `keys()` — non-blocking cursor-based scan rather
than a single blocking `KEYS *` call. Still O(n) overall, but doesn't
freeze Redis for other callers while scanning.)

### Step 1.4 — Frontend: point `getActiveCalls` at the real endpoint

File: `frontend/src/api/calls.js`

Find:
```javascript
    const res = await fetch(`/api/v1/calls?tenantId=${tenantId}&status=active,waiting`);
```
Replace with:
```javascript
    const res = await fetch(`/api/v1/calls`);
```
(Tenant filtering doesn't exist yet — see Sprint 6 — so drop the query
params rather than silently ignoring them server-side.)

### Step 1.5 — Verify before moving on
```bash
cd Talkse-backend/Talkse-backend
uvicorn app.main:app --reload --port 8000 &
curl -s http://localhost:8000/api/v1/calls | python3 -m json.tool
# Expected: [] (empty array, no active calls yet — not a 404)

curl -s -X POST http://localhost:8000/api/v1/calls/ | python3 -m json.tool
# Expected: {"call_id": "conv_web_...", "reply_text": "Hi! Are you looking to..."}

curl -s http://localhost:8000/api/v1/calls | python3 -m json.tool
# Expected: now shows one entry for the call_id just created
```
Both must return real JSON, not 404s, before continuing to Step 1.6.

### Step 1.6 — Manual integration check (can't be scripted — do this by hand)
1. Start the backend (`uvicorn app.main:app --reload`), Redis, and Postgres.
2. Start the frontend (`npm run dev`).
3. Open the dashboard, open browser devtools → Network → WS tab.
4. Trigger a call via `POST /api/v1/calls/`, then open a WebSocket to
   `/ws/calls/{call_id}` (you can do this from devtools console:
   `new WebSocket('ws://localhost:8000/ws/calls/CALL_ID')`) and send a
   raw PCM frame.
5. Confirm the frontend's `LiveTranscript` component actually updates —
   this is the real proof the contract fix works, not just that both
   sides compile.

**Do not proceed to Sprint 2 until step 1.6 is visually confirmed working.**

---

## Sprint 2 — Wire TTS into the live call path

### Problem recap
`synthesize()` (Deepgram TTS) exists and works, but only `poc.py`'s CLI
`main()` calls it. Neither `calls.py` nor `voice_gateway.py` ever
synthesizes audio for a real call.

### Step 2.1 — Backend: add a streamed TTS event to the WebSocket handler

File: `Talkse-backend/Talkse-backend/app/ws/voice_gateway.py`

This builds on Sprint 1's version. Find:
```python
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session
```
Replace with:
```python
import base64
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session
from app.services.poc import synthesize
```

Find:
```python
                if result.get("reply_text"):
                    await _emit(websocket, "transcript.final", {
                        "role": "ai",
                        "text": result["reply_text"],
                    })
```
Replace with:
```python
                if result.get("reply_text"):
                    await _emit(websocket, "transcript.final", {
                        "role": "ai",
                        "text": result["reply_text"],
                    })
                    await _synthesize_and_emit(websocket, call_id, result["reply_text"])
```

Add this new helper function above `voice_ws` (after the `_emit` function):
```python
async def _synthesize_and_emit(websocket: WebSocket, call_id: str, text: str):
    """Synthesizes reply_text to audio and sends it as a base64-encoded
    audio.chunk event. Runs synthesize() in a thread since it's a blocking
    network call (Deepgram SDK is sync) and this handler is async — without
    this, one slow TTS call would stall every other concurrent call on the
    same event loop."""
    import asyncio
    import os

    out_path = f"app/services/tts_cache/{call_id}_{abs(hash(text))}.wav"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    try:
        await asyncio.to_thread(synthesize, text, out_path)
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
        await websocket.send_json({
            "type": "audio.chunk",
            "data": {"audio_base64": base64.b64encode(audio_bytes).decode("ascii")},
        })
    except Exception as e:
        print(f"[TTS Warning] Failed to synthesize/send audio for call {call_id}: {e}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)  # don't accumulate WAV files — see Sprint 4 for the STT temp-file equivalent
```

**Known limitation, intentionally deferred:** this synthesizes the whole
reply and sends it as one chunk rather than true streaming TTS. Deepgram's
Aura API supports streaming synthesis; upgrading to chunk-by-chunk delivery
is a real latency win but is a separate, larger change — don't fold it into
this sprint. File it as a follow-up once base64-whole-clip is proven working
end-to-end.

### Step 2.2 — Frontend: play the received audio

File: `frontend/src/hooks/useLiveCall.js`

Find:
```javascript
      case 'call.ended':
        setStatus('ENDED');
        setIsAiSpeaking(false);
        break;

      default:
        break;
    }
  };
```
Replace with:
```javascript
      case 'audio.chunk':
        playAudioChunk(data.audio_base64);
        break;

      case 'call.ended':
        setStatus('ENDED');
        setIsAiSpeaking(false);
        break;

      default:
        break;
    }
  };

  const playAudioChunk = (base64Audio) => {
    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play().catch((err) => console.warn('Audio playback blocked:', err));
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to play audio chunk:', err);
    }
  };
```

### Step 2.3 — Verify
```bash
# Backend: confirm synthesize() is reachable from the websocket path
grep -n "from app.services.poc import synthesize" app/ws/voice_gateway.py
grep -n "asyncio.to_thread(synthesize" app/ws/voice_gateway.py
```
Then repeat the manual check from Sprint 1 Step 1.6 — this time confirm
you actually **hear** the AI's reply through the browser, not just see
the text.

---

## Sprint 3 — Real authentication

### Step 3.1 — Backend: minimal JWT issuing + verification

Create a new file: `Talkse-backend/Talkse-backend/app/core/security.py`
```python
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()


def create_access_token(user_id: str, role: str = "ADMIN") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        return {"user_id": payload["sub"], "role": payload.get("role", "ADMIN")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
```

Add `pyjwt` to `requirements.txt`:
```
pyjwt
```

### Step 3.2 — Backend: add JWT settings + a login endpoint

File: `Talkse-backend/Talkse-backend/app/core/config.py`

Find:
```python
class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str
    deepgram_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]  # React dev server

    class Config:
        env_file = ".env"
```
Replace with:
```python
class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str
    deepgram_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]  # React dev server
    jwt_secret: str
    jwt_expiry_minutes: int = 60

    class Config:
        env_file = ".env"
```

Add to `.env.example`:
```
JWT_SECRET=change-me-in-vault
JWT_EXPIRY_MINUTES=60
```

**Manual step for you, not the agent:** generate a real secret locally
(`python3 -c "import secrets; print(secrets.token_hex(32))"`) and put it
in your actual `.env` — never commit a real secret to `.env.example`.

Create `Talkse-backend/Talkse-backend/app/api/v1/auth.py`:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Placeholder credential check — replace with a real users table + hashed
# passwords before this touches anything beyond local dev. Flagged
# explicitly rather than silently shipped as if it were real auth.
_DEMO_USERS = {"admin": "changeme"}


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    if _DEMO_USERS.get(payload.username) != payload.password:
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token(user_id=payload.username, role="ADMIN")
    return {"access_token": token, "token_type": "bearer"}
```

Wire it into `main.py`. Find:
```python
from app.api.v1 import calls, appointments, rag, clinic
```
Replace with:
```python
from app.api.v1 import calls, appointments, rag, clinic, auth
```
Find:
```python
app.include_router(calls.router)
app.include_router(appointments.router)
app.include_router(rag.router)
app.include_router(clinic.router)
```
Replace with:
```python
app.include_router(auth.router)
app.include_router(calls.router)
app.include_router(appointments.router)
app.include_router(rag.router)
app.include_router(clinic.router)
```

### Step 3.3 — Protect the appointments list route (the one the audit flagged as wide open)

File: `Talkse-backend/Talkse-backend/app/api/v1/appointments.py`

Find:
```python
from fastapi import APIRouter
from psycopg2.extras import RealDictCursor
from app.services import db

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

@router.get("/")
def list_appointments():
```
Replace with:
```python
from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor
from app.services import db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

@router.get("/")
def list_appointments(user: dict = Depends(get_current_user)):
```

**Scope note:** don't protect every other route in this same sprint — do
`appointments.py` first as the proof this works, verify it, then apply the
identical `Depends(get_current_user)` pattern to `calls.py` and `clinic.py`
routes as a fast-follow once this one is confirmed. Rolling out auth to
every route at once makes it hard to isolate which route broke if
something goes wrong.

### Step 3.4 — Frontend: real login instead of the fake one

File: `frontend/src/auth/AuthContext.jsx`

Replace the entire file with:
```javascript
import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('talkse_token');
    if (token) {
      // Trust the stored token optimistically; a 401 on first real API
      // call will clear it (see api client interceptor pattern — Sprint 4).
      setUser({ name: 'Admin', role: 'ADMIN', isAuthenticated: true });
    }
    setIsLoading(false);
  }, []);

  const login = async (credentials) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!res.ok) {
      throw new Error('Invalid credentials');
    }
    const { access_token } = await res.json();
    localStorage.setItem('talkse_token', access_token);
    setUser({ name: credentials.username, role: 'ADMIN', isAuthenticated: true });
  };

  const logout = () => {
    localStorage.removeItem('talkse_token');
    setUser(null);
  };

  if (isLoading) return null;

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**You'll also need to update `LoginPage.jsx`** to actually call `login()`
and handle the thrown error (show an inline "Invalid credentials" message)
instead of whatever it currently does — read that file first (it wasn't
in the audit's reviewed set) before editing it, since I haven't verified
its current contents.

### Step 3.5 — Frontend: attach the token to authenticated requests
File: `frontend/src/api/patients.js` (and repeat the same pattern in
`bookings.js`, `calls.js`, `callActions.js` once this one is verified)

Find:
```javascript
    const response = await fetch(`/api/v1/tenants/${tenantId}/patients?phone=${encodeURIComponent(phone)}`);
```
Replace with:
```javascript
    const response = await fetch(`/api/v1/tenants/${tenantId}/patients?phone=${encodeURIComponent(phone)}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('talkse_token')}` },
    });
```

### Step 3.6 — Verify
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme"}'
# Expected: {"access_token": "eyJ...", "token_type": "bearer"}

curl -s http://localhost:8000/api/v1/appointments/
# Expected: 401/403, NOT the full appointments list

curl -s http://localhost:8000/api/v1/appointments/ \
  -H "Authorization: Bearer <token from login above>"
# Expected: the appointments list
```

---

## Sprint 4 — Code hygiene / migration debt

### Step 4.1 — Fix the import inconsistency properly (no more sys.path hacks)

The real fix is a proper installable package instead of path manipulation.

Create `Talkse-backend/Talkse-backend/pyproject.toml`:
```toml
[project]
name = "talkse-backend"
version = "0.1.0"

[tool.setuptools]
packages = ["app"]
```

Then, in `app/services/conversation_loop.py`, `app/services/poc.py`,
`app/services/booking_engine.py`, `app/services/db.py`,
`app/services/clinic_config.py`, and `app/services/conversation_router.py`
— find every bare import of a sibling module (e.g. `import booking_engine as be`,
`import db`, `from poc import ...`, `import clinic_config as config`,
`from conversation_router import ...`) and replace with the fully-qualified
form matching how `calls.py`/`appointments.py` already do it:

```python
# before (in conversation_loop.py)
from poc import transcribe, extract_intent, synthesize, merge_state
import booking_engine as be
import db
from conversation_router import try_rule_based_route
from rag.rag_chat import answer_question_streaming

# after
from app.services.poc import transcribe, extract_intent, synthesize, merge_state
from app.services import booking_engine as be
from app.services import db
from app.services.conversation_router import try_rule_based_route
from app.services.rag.rag_chat import answer_question_streaming
```

Apply the equivalent fix in `booking_engine.py` (`import clinic_config as config`
→ `from app.services import clinic_config as config`, `import db` →
`from app.services import db`) and in `db.py`'s own internal imports if any exist.

Then, in `app/main.py`, remove the path hack entirely:
```python
# DELETE these two lines:
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services"))
```
And remove the now-unused `import os, sys` at the top if nothing else in
that file needs them.

Install in editable mode so the package resolves without any path tricks:
```bash
cd Talkse-backend/Talkse-backend
pip install -e .
```

**Verify:** `uvicorn app.main:app --reload` starts cleanly, and
`pytest tests/` still passes — the test files also do their own
`sys.path.insert` hacks (see `tests/test_conversation.py`); once the
package is properly installable those can be deleted too, but that's a
nice-to-have, not required for this sprint to be "done."

### Step 4.2 — Rename `poc.py` out of the AI pipeline's real import path

Don't just rename the file — the whole point is the name should stop
implying "not real code." Rename to `app/services/ai_clients.py` and
update every import found in Step 4.1 accordingly
(`from app.services.poc import ...` → `from app.services.ai_clients import ...`).
Keep the CLI `main()` function at the bottom for manual latency testing —
it's genuinely useful, it's the name and the implication that it's
throwaway code that was the problem.

### Step 4.3 — Fix the temp-file storage location and cleanup

File: `Talkse-backend/Talkse-backend/app/api/v1/calls.py`

Find:
```python
    tmp_path = f"app/services/turns/tmp_{call_id}_{uuid.uuid4().hex}.wav"
    import os
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
        
    transcript, _ = transcribe(tmp_path)
    if not transcript:
        raise HTTPException(422, "no speech detected")
        
    result = handle_turn(transcript, state)
    save_session(call_id, state)
    return {"transcript": transcript, "reply_text": result["reply_text"], "state": state}
```
Replace with:
```python
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())

    try:
        transcript, _ = transcribe(tmp_path)
    finally:
        os.remove(tmp_path)  # patient call audio — don't leave it on disk

    if not transcript:
        raise HTTPException(422, "no speech detected")

    result = handle_turn(transcript, state)
    save_session(call_id, state)
    return {"transcript": transcript, "reply_text": result["reply_text"], "state": state}
```
This uses the OS temp directory (outside the source tree) and guarantees
cleanup via `finally`, even if transcription throws.

### Step 4.4 — Replace `print()` with real logging (scoped to the hottest path first)

Don't do all ~54 call sites in one pass — start with the files on the live
call path (`app/services/ai_clients.py` [renamed from poc.py],
`app/services/conversation_loop.py`, `app/ws/voice_gateway.py`), since
those are what you'd actually need logs from in production.

Add to the top of each of those files:
```python
import logging
logger = logging.getLogger("talkse")
```
Then replace each `print(f"...")` with `logger.info(f"...")` (or
`logger.warning` / `logger.error` for the ones currently prefixed
`[... Warning]` / `[... Error]`). Configure the logger once in `main.py`:
```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
```
This is intentionally not the full structured-JSON-with-call_id-correlation
setup the README describes — that's real work for Sprint 6's observability
phase. This step just stops the bleeding on the hottest files.

---

## Sprint 5 — Rewrite the README to reflect reality

Don't edit the existing README in place — the gap between claimed and
actual is large enough that a full rewrite is clearer than a patch. Split
it into two explicit sections:

1. **"Current State (as of this branch)"** — describe only what's true
   after Sprints 1–4 land: single-tenant, JWT-protected admin routes,
   FastAPI + React, real STT→LLM→booking→TTS round trip over WebSocket,
   Groq/Gemini/Deepgram fallback chains, no Docker/CI/Alembic yet.
2. **"Target Architecture (roadmap, not yet built)"** — keep the existing
   multi-tenant/RLS/Docker/CI/observability content, but explicitly labeled
   as aspirational, matching the "Sprint 6" scope below.

This is a documentation-only task — don't let it block or get blocked by
the code sprints above. Can be done in parallel by someone else.

---

## Sprint 6 — Roadmap only (do not start until Sprints 1–5 are verified done)

These are correctly large, multi-week efforts — sketched here just enough
to plan against, not detailed line-by-line like the sprints above:

1. **Multi-tenancy.** Add `tenant_id` to `appointments`, `documents`,
   `document_chunks`; a tenant-scoping dependency (mirrors
   `get_current_user`, but resolves `tenant_id` from the JWT or a header)
   applied to every route; replace `clinic_config.py`'s single
   `clinic_data.json` load with a per-tenant config lookup (DB-backed, not
   file-backed, once there's more than a demo handful of tenants).
2. **Docker + CI.** `Dockerfile` for backend and frontend, `docker-compose.yml`
   wiring Postgres/Redis/backend/frontend together, a GitHub Actions
   workflow running `pytest` + a frontend build on every PR.
3. **Alembic migrations**, replacing the raw `CREATE TABLE IF NOT EXISTS`
   calls in `db.py::init_db()`.
4. **Real observability** — structured JSON logs with `call_id`/`tenant_id`
   correlation (Sprint 4 only did plain text logging on the hot path),
   Prometheus metrics, per-stage latency tracking wired into the actual
   live call path (not just `poc.py`'s standalone CLI timing).
5. **Telnyx integration** — the actual phone-call bridge; everything built
   in Sprints 1–2 is browser-microphone-based, not real telephony yet.

---

## Summary checklist

- [ ] Sprint 1 — WebSocket contract + missing endpoints (do this first, verify manually)
- [ ] Sprint 2 — TTS wired into the live call, audio actually plays in-browser
- [ ] Sprint 3 — JWT auth, `/api/v1/appointments/` genuinely requires a token
- [ ] Sprint 4 — imports fixed, `poc.py` renamed, temp files cleaned up, hot-path logging
- [ ] Sprint 5 — README split into Current State vs. Target Architecture
- [ ] Sprint 6 — roadmap only, not started