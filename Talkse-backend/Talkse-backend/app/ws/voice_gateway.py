import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session
from app.services.tts.router import synthesize_for_plan
from app.services import db

router = APIRouter()


async def _emit(websocket: WebSocket, event_type: str, data: dict):
    """Sends a typed event matching the frontend's expected {type, data}
    shape (see frontend/src/hooks/useLiveCall.js handleSocketEvent and the
    README's WebSocket Events table)."""
    await websocket.send_json({"type": event_type, "data": data})


async def _synthesize_and_emit(websocket: WebSocket, call_id: str, text: str, state: dict = None):
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
        plan = state.get("plan", "free") if state else "free"
        task = asyncio.to_thread(synthesize_for_plan, plan, text, out_path)
        elapsed, provider_used = await asyncio.wait_for(task, timeout=5.0)
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
            
        try:
            db.log_tts_usage(
                call_id, 
                state.get("tenant_id") if state else None, 
                provider_used, 
                len(text), 
                elapsed
            )
        except Exception as e:
            import logging
            logging.getLogger("talkse").warning(f"[TTS] Failed to log usage: {e}")

        await websocket.send_json({
            "type": "audio.chunk",
            "data": {"audio_base64": base64.b64encode(audio_bytes).decode("ascii")},
        })
    except Exception as e:
        import logging
        logger = logging.getLogger("talkse")
        logger.warning(f"[TTS Warning] Failed to synthesize/send audio for call {call_id}: {e}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)  # don't accumulate WAV files — see Sprint 4 for the STT temp-file equivalent


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
        "plan": state.get("plan", "free"),
    })

    if state.get("turn_count", 0) == 0 and state.get("status") == "collecting" and not state.get("initial_prompt_emitted"):
        state["initial_prompt_emitted"] = True
        save_session(call_id, state)
        from app.services.conversation_loop import next_missing_field, prompt_for_field
        missing = next_missing_field(state) or "intent"
        opening = prompt_for_field(missing)
        
        await _emit(websocket, "transcript.final", {
            "role": "ai",
            "text": opening,
        })
        await _emit(websocket, "state.changed", {
            "status": state.get("status"),
            "isAiSpeaking": True,
        })
        await _synthesize_and_emit(websocket, call_id, opening, state)
        await _emit(websocket, "state.changed", {
            "status": state.get("status"),
            "isAiSpeaking": False,
        })

    transcriber = None
    try:
        transcriber = StreamingTranscriber(sample_rate=16000)
        transcriber.start()
        transcriber.begin_turn()
    except Exception as e:
        import logging
        logging.getLogger("talkse").warning(f"[Streaming STT Warning] Could not start live transcriber: {e}")

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            data_bytes = msg.get("bytes")
            data_text = msg.get("text")

            if data_bytes:
                if transcriber:
                    try:
                        transcript = transcriber.feed(data_bytes)
                    except Exception as err:
                        import logging
                        logging.getLogger("talkse").warning(f"[Streaming STT Feed Error] {err}")
                        transcript = None
                else:
                    transcript = None
            elif data_text:
                try:
                    import json
                    parsed = json.loads(data_text)
                    transcript = parsed.get("text") or parsed.get("transcript")
                except Exception:
                    transcript = data_text
            else:
                transcript = None

            if transcript:
                await _emit(websocket, "transcript.final", {
                    "role": "customer",
                    "text": transcript,
                })

                if "transcript" not in state:
                    state["transcript"] = []
                state["transcript"].append({"role": "customer", "text": transcript})

                result = handle_turn(transcript, state)
                save_session(call_id, state)

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": True,
                    "nlu": {
                        "intent": {"label": state.get("intent"), "confidence": 95},
                        "service": state.get("service"),
                        "time": state.get("preferred_time"),
                        "callerName": state.get("caller_name")
                    }
                })

                reply_text = result.get("reply_text")
                if reply_text:
                    await _emit(websocket, "transcript.final", {
                        "role": "ai",
                        "text": reply_text,
                    })
                    await _synthesize_and_emit(websocket, call_id, reply_text, state)

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": False,
                    "nlu": {
                        "intent": {"label": state.get("intent"), "confidence": 95},
                        "service": state.get("service"),
                        "time": state.get("preferred_time"),
                        "callerName": state.get("caller_name")
                    }
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
        # Save call log if not already saved via /end endpoint
        state = get_session(call_id)
        if state and state.get("status") not in ("ended",):
            state["status"] = "ended"
            save_session(call_id, state)
            tenant_id = state.get("tenant_id")
            if tenant_id:
                try:
                    db.insert_call_log(
                        tenant_id=tenant_id,
                        call_id=call_id,
                        caller_name=state.get("caller_name"),
                        status=state["status"],
                        started_at=None,
                        transcript=state.get("transcript", []),
                        booking_result=state.get("booking_result")
                    )
                except Exception as e:
                    import logging
                    logging.getLogger("talkse").error(f"Failed to save call log for {call_id}: {e}")
