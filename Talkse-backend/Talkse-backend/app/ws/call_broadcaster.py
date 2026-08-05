import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger("talkse")

# In-memory registry of dashboard WebSocket clients watching a given call.
# Only valid within a single backend process — fine for local dev / a
# single uvicorn worker. NOTE for Sprint 6+: once this runs behind more
# than one worker/process, this must move to a Redis pub/sub channel
# instead, or a dashboard client connected to a different worker than the
# one handling the live call will never receive events.
_subscribers: Dict[str, List[WebSocket]] = {}
_lock = asyncio.Lock()


async def subscribe(call_id: str, websocket: WebSocket) -> None:
    async with _lock:
        _subscribers.setdefault(call_id, []).append(websocket)


async def unsubscribe(call_id: str, websocket: WebSocket) -> None:
    async with _lock:
        listeners = _subscribers.get(call_id)
        if not listeners:
            return
        if websocket in listeners:
            listeners.remove(websocket)
        if not listeners:
            _subscribers.pop(call_id, None)


async def emit(call_id: str, event_type: str, data: dict) -> None:
    """Pushes a typed {type, data} event (matching the frontend's
    useLiveCall.js handleSocketEvent contract) to every dashboard
    WebSocket currently subscribed to this call_id. Silently drops
    dead/broken connections instead of letting one bad socket break
    delivery to the others."""
    async with _lock:
        listeners = list(_subscribers.get(call_id, []))
    for ws in listeners:
        try:
            await ws.send_json({"type": event_type, "data": data})
        except Exception as e:
            logger.warning(f"[CallBroadcaster] Dropping dead subscriber for {call_id}: {e}")
            await unsubscribe(call_id, ws)
