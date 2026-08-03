import json
import redis
from app.core.config import settings

try:
    _r = redis.from_url(settings.redis_url, decode_responses=True, protocol=2)
    _r.ping()
except Exception:
    import fakeredis
    _r = fakeredis.FakeStrictRedis(decode_responses=True)

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


def get_session(call_id: str) -> dict | None:
    raw = _r.get(f"call:{call_id}")
    return json.loads(raw) if raw else None

def save_session(call_id: str, state: dict):
    _r.setex(f"call:{call_id}", 3600, json.dumps(state, default=str))
