import json
import redis
from app.core.config import settings

_r = redis.from_url(settings.redis_url, decode_responses=True)

def new_session(call_id: str, initial_state: dict):
    _r.setex(f"call:{call_id}", 3600, json.dumps(initial_state))

def get_session(call_id: str) -> dict | None:
    raw = _r.get(f"call:{call_id}")
    return json.loads(raw) if raw else None

def save_session(call_id: str, state: dict):
    _r.setex(f"call:{call_id}", 3600, json.dumps(state))
