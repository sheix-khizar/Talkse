"""
Session store — Redis-backed (production) with in-memory fallback (local dev).

If Redis is unavailable (e.g. no local Redis install), the module automatically
falls back to a plain dict. Sessions survive for the process lifetime only, which
is fine for local development. Production should always have Redis available.
"""

import json
import threading
import time
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attempt to connect to Redis; fall back to in-memory if unavailable.
# ---------------------------------------------------------------------------
_redis_client = None
_SESSION_TTL_SECONDS = 3600  # 1 hour, matches the original setex TTL

try:
    from app.core.config import settings
    import redis as redis_lib

    _r = redis_lib.from_url(
        settings.redis_url,
        decode_responses=True,
        protocol=2,
        socket_connect_timeout=2,   # fail fast instead of blocking forever
        socket_timeout=2,
    )
    _r.ping()  # verify connection is actually alive
    _redis_client = _r
    logger.info("[Session Store] Redis connection established at %s", settings.redis_url)
except Exception as exc:
    logger.warning(
        "[Session Store] Redis unavailable (%s). Falling back to in-memory store. "
        "Sessions will not persist across server restarts.",
        exc,
    )
    _redis_client = None


# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------
_memory_store: dict[str, tuple[dict, float]] = {}  # call_id -> (state, expires_at)
_store_lock = threading.Lock()


def _mem_set(call_id: str, state: dict) -> None:
    with _store_lock:
        _memory_store[call_id] = (state, time.time() + _SESSION_TTL_SECONDS)


def _mem_get(call_id: str) -> dict | None:
    with _store_lock:
        entry = _memory_store.get(call_id)
        if entry is None:
            return None
        state, expires_at = entry
        if time.time() > expires_at:
            del _memory_store[call_id]
            return None
        return state


def _mem_list() -> list[tuple[str, dict]]:
    now = time.time()
    with _store_lock:
        expired = [k for k, (_, exp) in _memory_store.items() if now > exp]
        for k in expired:
            del _memory_store[k]
        return [(k, state) for k, (state, _) in _memory_store.items()]


# ---------------------------------------------------------------------------
# Public API — same interface as before, transparent Redis/memory dispatch
# ---------------------------------------------------------------------------

def new_session(call_id: str, initial_state: dict) -> None:
    if _redis_client:
        _redis_client.setex(f"call:{call_id}", _SESSION_TTL_SECONDS, json.dumps(initial_state))
    else:
        _mem_set(call_id, initial_state)


def get_session(call_id: str) -> dict | None:
    if _redis_client:
        raw = _redis_client.get(f"call:{call_id}")
        return json.loads(raw) if raw else None
    return _mem_get(call_id)


def save_session(call_id: str, state: dict) -> None:
    if _redis_client:
        _redis_client.setex(f"call:{call_id}", _SESSION_TTL_SECONDS, json.dumps(state, default=str))
    else:
        _mem_set(call_id, state)

def list_active_sessions() -> list[tuple[str, dict]]:
    """Returns (call_id, state) pairs for all live sessions.

    Redis path: scans for call:* keys — O(n) stopgap (see Sprint 6 note in calls.py).
    Memory path: iterates the in-process dict, evicting expired entries first.
    """
    if _redis_client:
        results = []
        for key in _redis_client.scan_iter(match="call:*"):
            raw = _redis_client.get(key)
            if raw:
                call_id = key.split("call:", 1)[1]
                results.append((call_id, json.loads(raw)))
        return results
    return _mem_list()

