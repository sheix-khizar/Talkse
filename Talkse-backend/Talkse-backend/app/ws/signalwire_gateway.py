import asyncio
import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn, prompt_for_field, next_missing_field
from app.services.tts.router import synthesize_for_provider_bytes
from app.services.telephony.audio_convert import (
    mulaw_b64_to_pcm16, pcm16_to_mulaw, extract_pcm_from_wav_bytes,
)
from app.session.store import get_session, save_session
from app.services import db

router = APIRouter()
logger = logging.getLogger("talkse")

SW_SAMPLE_RATE = 8000  # SignalWire's <Stream> default: mulaw @ 8kHz
CHUNK_SIZE = 640  # 640 bytes = 80ms of 8kHz mu-law audio


def _refresh_pipeline(call_sid: str, state: dict) -> str:
    """Re-reads only the voice_pipeline field from the session store so a
    mid-call pipeline switch (PUT /api/v1/calls/{call_id}/pipeline) takes
    effect on the next turn, without clobbering the rest of the in-memory
    state this handler has been accumulating."""
    latest = get_session(call_sid)
    if latest and "voice_pipeline" in latest:
        state["voice_pipeline"] = latest["voice_pipeline"]
    return state.get("voice_pipeline", "deepgram")


async def _send_audio(websocket: WebSocket, stream_id: str | None, text: str, provider: str):
    """Synthesizes text and streams it back to SignalWire as paced mulaw
    frames. If the chosen provider's audio can't be parsed as WAV (e.g. a
    future regression reintroduces raw mp3), falls back to Deepgram instead
    of the caller hearing dead silence."""
    try:
        audio_bytes, _, provider_used = await asyncio.to_thread(synthesize_for_provider_bytes, provider, text)
        try:
            pcm, native_rate = await asyncio.to_thread(extract_pcm_from_wav_bytes, audio_bytes)
        except Exception as conv_err:
            logger.warning(
                f"[SignalWire TTS] {provider_used} output wasn't valid WAV "
                f"({conv_err}); retrying with deepgram."
            )
            audio_bytes, _, provider_used = await asyncio.to_thread(synthesize_for_provider_bytes, "deepgram", text)
            pcm, native_rate = await asyncio.to_thread(extract_pcm_from_wav_bytes, audio_bytes)

        mulaw = pcm16_to_mulaw(pcm, native_rate)

        for i in range(0, len(mulaw), CHUNK_SIZE):
            chunk = mulaw[i : i + CHUNK_SIZE]
            payload_b64 = base64.b64encode(chunk).decode("ascii")
            msg = {
                "event": "media",
                "media": {"payload": payload_b64},
            }
            if stream_id:
                msg["stream_id"] = stream_id
                msg["streamSid"] = stream_id
            await websocket.send_json(msg)
            await asyncio.sleep(0.04)
    except Exception as e:
        logger.error(f"[SignalWire TTS] Failed to synthesize/send audio: {e}")


@router.websocket("/ws/signalwire/{call_sid}")
async def signalwire_ws(websocket: WebSocket, call_sid: str):
    await websocket.accept()
    state = get_session(call_sid)
    if not state:
        state = {
            "intent": None, "service": None, "preferred_time": None,
            "caller_name": None, "existing_appointment_ref": None,
            "turn_count": 0, "status": "collecting",
            "idempotency_key": call_sid, "booking_result": None,
            "tenant_id": db.DEFAULT_TENANT_ID,
            "plan": "free",
            "voice_pipeline": "deepgram",
            "initial_prompt_emitted": False,
        }
        save_session(call_sid, state)

    stream_id = None
    transcriber = None

    try:
        transcriber = await asyncio.to_thread(StreamingTranscriber, sample_rate=SW_SAMPLE_RATE)
        await asyncio.to_thread(transcriber.start)
        transcriber.begin_turn()
    except Exception as e:
        logger.warning(f"[SignalWire] Streaming STT unavailable: {e}")
        transcriber = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start" or isinstance(msg.get("start"), dict):
                start_obj = msg.get("start", {}) if isinstance(msg.get("start"), dict) else {}
                stream_id = start_obj.get("streamSid") or start_obj.get("stream_id") or msg.get("streamSid") or msg.get("stream_id")

            if not stream_id:
                stream_id = msg.get("streamSid") or msg.get("stream_id")

            if not state.get("initial_prompt_emitted"):
                state["initial_prompt_emitted"] = True
                save_session(call_sid, state)
                opening = prompt_for_field(next_missing_field(state) or "intent")
                state.setdefault("transcript", []).append({"role": "ai", "text": opening})
                provider = _refresh_pipeline(call_sid, state)
                asyncio.create_task(_send_audio(websocket, stream_id, opening, provider))

            if event == "media":
                if not transcriber:
                    continue
                media_payload = msg.get("media", {}).get("payload")
                if not media_payload:
                    continue

                try:
                    pcm = mulaw_b64_to_pcm16(base64.b64decode(media_payload))
                    transcript = transcriber.feed(pcm)
                except Exception as err:
                    logger.warning(f"[SignalWire] STT feed error for call {call_sid}: {err}")
                    transcript = None

                if transcript:
                    state.setdefault("transcript", []).append({"role": "customer", "text": transcript})

                    try:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(handle_turn, transcript, state), timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"[SignalWire] handle_turn timed out for call {call_sid}")
                        result = {
                            "reply_text": "Sorry, that's taking longer than expected — could you repeat that?",
                            "terminal": False,
                        }
                    except Exception as e:
                        logger.error(f"[SignalWire] handle_turn failed for call {call_sid}: {e}")
                        result = {
                            "reply_text": "Sorry, I hit a snag processing that. Could you say that again?",
                            "terminal": False,
                        }

                    save_session(call_sid, state)

                    if result.get("is_faq") and result.get("faq_stream"):
                        stream_gen = result["faq_stream"]
                        try:
                            next(stream_gen)  # sources header, unused over voice
                        except StopIteration:
                            pass
                        provider = _refresh_pipeline(call_sid, state)
                        for sentence in stream_gen:
                            if sentence:
                                asyncio.create_task(_send_audio(websocket, stream_id, sentence, provider))
                    elif result.get("reply_text"):
                        state.setdefault("transcript", []).append({"role": "ai", "text": result["reply_text"]})
                        provider = _refresh_pipeline(call_sid, state)
                        asyncio.create_task(_send_audio(websocket, stream_id, result["reply_text"], provider))

                    if result.get("terminal"):
                        break

            elif event == "stop":
                break

    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        logger.error(f"[SignalWire] handle_turn timed out for call {call_sid}")
    except Exception as e:
        logger.error(f"[SignalWire] Unexpected error in call {call_sid}: {e}", exc_info=True)
    finally:
        if transcriber:
            try:
                await asyncio.to_thread(transcriber.close)
            except Exception as e:
                logger.warning(f"[SignalWire] Error closing transcriber: {e}")

        state = get_session(call_sid)
        if state and state.get("status") != "ended":
            state["status"] = "ended"
            save_session(call_sid, state)
            tenant_id = state.get("tenant_id")
            if tenant_id:
                try:
                    await asyncio.to_thread(
                        db.insert_call_log,
                        tenant_id=tenant_id, call_id=call_sid,
                        caller_name=state.get("caller_name"), status=state["status"],
                        started_at=None, transcript=state.get("transcript", []),
                        booking_result=state.get("booking_result"),
                    )
                except Exception as e:
                    logger.error(f"[SignalWire] Failed to save call log: {e}")
