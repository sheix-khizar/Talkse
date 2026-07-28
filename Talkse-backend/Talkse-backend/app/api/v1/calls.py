from fastapi import APIRouter, UploadFile, HTTPException
import time, uuid
from app.session.store import new_session, get_session, save_session
from app.services.conversation_loop import prompt_for_field, handle_turn
from app.services import db
from app.services.poc import transcribe

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

@router.post("/")
def start_call():
    call_id = f"conv_web_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    state = {
        "intent": None, "service": None, "preferred_time": None,
        "caller_name": None, "existing_appointment_ref": None,
        "turn_count": 0, "status": "collecting",
        "idempotency_key": call_id, "booking_result": None,
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

    if result["is_faq"]:
        stream_gen = result["faq_stream"]
        sources = next(stream_gen)
        reply_text = " ".join(list(stream_gen))
        return {"reply_text": reply_text, "sources": sources, "state": state}

    return {"reply_text": result["reply_text"], "state": state, "terminal": result["terminal"]}

@router.post("/{call_id}/turn/audio")
async def turn_audio(call_id: str, file: UploadFile):
    """Browser-recorded audio blob path (equivalent of Tab1's audio_input)."""
    state = get_session(call_id)
    if not state:
        raise HTTPException(404, "call not found or expired")
    
    # We use a temporary file to save the uploaded audio for transcription.
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
