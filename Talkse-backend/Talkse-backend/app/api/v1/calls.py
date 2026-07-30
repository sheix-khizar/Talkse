from fastapi import APIRouter, UploadFile, HTTPException
import time, uuid
import logging

logger = logging.getLogger("talkse")
from app.session.store import new_session, get_session, save_session
from app.services.conversation_loop import prompt_for_field, handle_turn
from app.services import db
from app.services.ai_clients import transcribe

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

@router.get("")
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
        if state.get("status") not in ("ended", "done", "rejected", "emergency_transferred", "flagged_human_review")
    ]

@router.post("")
@router.post("/")
def start_call(tenant_id: str = "042", plan: str | None = None):
    from app.services import clinic_config as config

    resolved_plan = plan if plan in ("free", "paid") else config.get_plan_for_tenant(tenant_id)

    call_id = f"conv_web_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    state = {
        "intent": None, "service": None, "preferred_time": None,
        "caller_name": None, "existing_appointment_ref": None,
        "turn_count": 0, "status": "collecting",
        "idempotency_key": call_id, "booking_result": None,
        "tenant_id": tenant_id,
        "plan": resolved_plan,
    }
    new_session(call_id, state)
    opening = prompt_for_field("intent")
    return {"call_id": call_id, "reply_text": opening}

@router.post("/{call_id}/turn")
def turn(call_id: str, payload: dict):
    """payload: {"text": "..."} for typed/already-transcribed input"""
    state = get_session(call_id)
    if not state:
        raise HTTPException(404, "call not found or expired")

    state["turn_count"] += 1
    result = handle_turn(payload["text"], state)
    save_session(call_id, state)

    reply_text = result.get("reply_text", "")
    audio_base64 = None
    if reply_text:
        import os, tempfile, base64
        from app.services.tts.router import synthesize_for_plan
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            elapsed, provider_used = synthesize_for_plan(state.get("plan", "free"), reply_text, tmp_path)
            with open(tmp_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode("ascii")
            
            try:
                db.log_tts_usage(
                    call_id,
                    state.get("tenant_id") if state else None,
                    provider_used,
                    len(reply_text),
                    elapsed
                )
            except Exception as e:
                logger.warning(f"[TTS] Failed to log usage: {e}")

        except Exception as e:
            logger.error(f"[TTS] synthesis failed for call {call_id}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return {
        "reply_text": reply_text,
        "audio_base64": audio_base64,
        "state": state,
        "terminal": result.get("terminal", False)
    }

@router.post("/{call_id}/turn/audio")
async def turn_audio(call_id: str, file: UploadFile):
    """Browser-recorded audio blob path (equivalent of Tab1's audio_input)."""
    state = get_session(call_id)
    if not state:
        raise HTTPException(404, "call not found or expired")
    
    import os, tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())
        
    try:
        transcript, _ = transcribe(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    if not transcript:
        raise HTTPException(422, "no speech detected")
        
    result = handle_turn(transcript, state)
    save_session(call_id, state)
    return {"transcript": transcript, "reply_text": result["reply_text"], "state": state}

@router.post("/{call_id}/end")
def end_call(call_id: str):
    """Marks the session ended. The Redis key still expires naturally via
    its existing 3600s TTL — we don't delete it early so the dashboard can
    still show the final transcript/state after end."""
    state = get_session(call_id)
    if not state:
        raise HTTPException(404, "call not found or expired")
    state["status"] = "ended"
    save_session(call_id, state)
    return {"status": "success", "message": "Call ended."}
