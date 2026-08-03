import asyncio
import base64
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session
from app.services.tts.router import synthesize_for_plan_bytes
from app.services import db

router = APIRouter()
logger = logging.getLogger("talkse")


async def _emit(websocket: WebSocket, event_type: str, data: dict):
    """Sends a typed event matching the frontend's expected {type, data}
    shape (see frontend/src/hooks/useLiveCall.js handleSocketEvent and the
    README's WebSocket Events table)."""
    await websocket.send_json({"type": event_type, "data": data})


async def _synthesize_and_emit(websocket: WebSocket, call_id: str, text: str, state: dict = None):
    """Synthesizes reply_text to audio and sends it as a base64-encoded
    audio.chunk event. Runs synthesize_for_plan_bytes() in a thread since
    it's a blocking network call (Deepgram/ElevenLabs SDKs are sync) and
    this handler is async — without this, one slow TTS call would stall
    every other concurrent call on the same event loop. Audio bytes are
    kept entirely in memory (no disk round-trip) to avoid the latency of
    writing a .wav to disk and immediately reading it back."""
    try:
        plan = state.get("plan", "free") if state else "free"
        task = asyncio.to_thread(synthesize_for_plan_bytes, plan, text)
        audio_bytes, elapsed, provider_used = await asyncio.wait_for(task, timeout=8.0)

        try:
            # DB write — psycopg2 is synchronous, so this must also be
            # offloaded or it blocks the event loop for every reply.
            await asyncio.to_thread(
                db.log_tts_usage,
                call_id,
                state.get("tenant_id") if state else None,
                provider_used,
                len(text),
                elapsed,
            )
        except Exception as e:
            logger.warning(f"[TTS] Failed to log usage: {e}")

        await websocket.send_json({
            "type": "audio.chunk",
            "data": {"audio_base64": base64.b64encode(audio_bytes).decode("ascii")},
        })
    except Exception as e:
        logger.warning(f"[TTS Warning] Failed to synthesize/send audio for call {call_id}: {e}")


async def _start_transcriber() -> "StreamingTranscriber | None":
    """Builds and opens the streaming STT connection off the event loop.
    Returns None (and logs) on any failure instead of leaving a
    partially-initialized object around — callers must treat None as
    'STT unavailable for this call' and must NOT call .close() on it."""
    try:
        transcriber = await asyncio.to_thread(StreamingTranscriber, sample_rate=16000)
        await asyncio.to_thread(transcriber.start)
        transcriber.begin_turn()
        return transcriber
    except Exception as e:
        logger.warning(f"[Streaming STT Warning] Could not start live transcriber: {e}")
        return None


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

    # The WebSocket is the single source of truth for the spoken greeting.
    # (The REST POST /api/v1/calls endpoint must NOT set
    # initial_prompt_emitted=True — see calls.py patch — or this block
    # never runs and the caller never hears an opening line.)
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

    transcriber = await _start_transcriber()

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
                        logger.warning(f"[Streaming STT Feed Error] {err}")
                        transcript = None
                else:
                    # STT never came up for this call. Don't silently eat
                    # every frame forever — tell the frontend once so it
                    # can surface a real error instead of looking "stuck".
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

                import asyncio
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(handle_turn, transcript, state),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.error(f"[handle_turn] Timed out for call {call_id}; transferring to human.")
                    state["status"] = "transferred_to_human"
                    result = {
                        "reply_text": "I'm having trouble processing that — let me transfer you to a team member.",
                        "llm_time": 10.0, "routed": False, "is_faq": False, "faq_stream": None, "terminal": True
                    }
                except Exception as e:
                    logger.error(f"[Turn Error] handle_turn failed for call {call_id}: {e}")
                    result = {
                        "reply_text": "Sorry, I hit a snag processing that. Could you say that again?",
                        "terminal": False,
                    }
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

                if result.get("is_faq") and result.get("faq_stream"):
                    stream_gen = result["faq_stream"]
                    try:
                        sources = next(stream_gen)
                    except StopIteration:
                        sources = []

                    answer_parts = []
                    for sentence in stream_gen:
                        if sentence:
                            answer_parts.append(sentence)
                            await _emit(websocket, "transcript.final", {
                                "role": "ai",
                                "text": sentence,
                            })
                            await _synthesize_and_emit(websocket, call_id, sentence, state)

                    if state is not None:
                        state.setdefault("transcript", []).append({
                            "role": "ai",
                            "text": " ".join(answer_parts),
                            "sources": sources,
                        })
                else:
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

                if result.get("terminal"):
                    await _emit(websocket, "call.ended", {
                        "callId": call_id,
                        "outcome": state.get("status"),
                    })
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if transcriber:
            try:
                await asyncio.to_thread(transcriber.close)
            except Exception as e:
                logger.warning(f"[Streaming STT] Error closing transcriber for {call_id}: {e}")
        # Save call log if not already saved via /end endpoint
        state = get_session(call_id)
        if state and state.get("status") not in ("ended",):
            state["status"] = "ended"
            save_session(call_id, state)
            tenant_id = state.get("tenant_id")
            if tenant_id:
                try:
                    await asyncio.to_thread(
                        db.insert_call_log,
                        tenant_id=tenant_id,
                        call_id=call_id,
                        caller_name=state.get("caller_name"),
                        status=state["status"],
                        started_at=None,
                        transcript=state.get("transcript", []),
                        booking_result=state.get("booking_result"),
                    )
                except Exception as e:
                    logger.error(f"Failed to save call log for {call_id}: {e}")
