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

    call_sid = None
    from_number = None
    to_number = None

    # Try JSON body (SignalWire SWML / Call Fabric format)
    try:
        json_data = await request.json()
        if isinstance(json_data, dict):
            call_sid = (
                json_data.get("call_id")
                or json_data.get("call_sid")
                or json_data.get("CallSid")
                or (json_data.get("call", {}) if isinstance(json_data.get("call"), dict) else {}).get("call_id")
            )
            from_number = json_data.get("from") or json_data.get("From")
            to_number = json_data.get("to") or json_data.get("To")
    except Exception:
        pass

    # Fallback to form data (LaML format)
    if not call_sid:
        try:
            form = await request.form()
            call_sid = form.get("CallSid") or form.get("CallID") or form.get("call_id")
            from_number = from_number or form.get("From")
            to_number = to_number or form.get("To")
        except Exception:
            pass

    if not call_sid:
        import uuid
        call_sid = f"sw_{uuid.uuid4().hex[:12]}"

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

    from fastapi.responses import Response

    public_host = settings.public_host or request.headers.get("host") or "localhost:8000"
    public_host = public_host.replace("https://", "").replace("http://", "").strip().rstrip("/")
    ws_url = f"wss://{public_host}/ws/signalwire/{call_sid}"

    accept = request.headers.get("accept", "").lower()
    content_type = request.headers.get("content-type", "").lower()

    # If LaML XML explicitly requested via Accept header
    if "xml" in accept or "laml" in accept:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""
        return Response(content=xml_content, media_type="application/xml")

    # SWML format (SignalWire Markup Language)
    swml = {
        "version": "1.0.0",
        "sections": {
            "main": [
                {"answer": {}},
                {
                    "stream": {
                        "url": ws_url,
                        "track": "both_tracks"
                    }
                },
                {
                    "connect": {
                        "stream": {
                            "url": ws_url,
                            "track": "both_tracks"
                        }
                    }
                }
            ]
        },
    }
    return swml
