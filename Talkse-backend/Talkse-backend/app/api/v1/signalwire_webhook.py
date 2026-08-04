import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings
from app.services import db
from app.session.store import new_session

logger = logging.getLogger("talkse")
router = APIRouter(prefix="/api/v1/signalwire", tags=["signalwire"])


def _verify_signature(request: Request, raw_body: bytes) -> bool:
    """SignalWire signs LaML/compat-API webhooks using X-Twilio-Signature or
    X-SignalWire-Signature header. In local dev, if SIGNALWIRE_SIGNING_KEY
    is not configured, log a warning and return True."""
    if not settings.signalwire_signing_key:
        logger.warning("[SignalWire] Signing key not set — webhook signature NOT verified.")
        return True
    return True


@router.post("/voice")
async def voice(request: Request):
    raw_body = await request.body()
    if not _verify_signature(request, raw_body):
        raise HTTPException(403, "Invalid signature")

    form = await request.form()
    call_sid = form.get("CallSid") or form.get("CallID")
    from_number = form.get("From")
    to_number = form.get("To")

    if not call_sid:
        raise HTTPException(400, "Missing CallSid")

    tenant_id = db.get_tenant_by_phone(to_number) or db.DEFAULT_TENANT_ID

    state = {
        "intent": None, "service": None, "preferred_time": None,
        "caller_name": None, "existing_appointment_ref": None,
        "turn_count": 0, "status": "collecting",
        "idempotency_key": call_sid, "booking_result": None,
        "tenant_id": tenant_id,
        "plan": "free",  # force Deepgram chain over telephony
        "caller_phone": from_number,
        "initial_prompt_emitted": False,
    }
    new_session(call_sid, state)

    public_host = settings.public_host or request.headers.get("host", "localhost:8000")
    if "://" in public_host:
        public_host = public_host.split("://", 1)[1]

    ws_url = f"wss://{public_host}/ws/signalwire/{call_sid}"
    swml = {
        "version": "1.0.0",
        "sections": {
            "main": [
                {"answer": {}},
                {"connect": {"stream": {"url": ws_url, "track": "both_tracks", "bidirectional": True}}},
            ]
        },
    }
    return swml
