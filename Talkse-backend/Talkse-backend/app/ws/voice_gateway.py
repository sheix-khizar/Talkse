import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session
from app.services.poc import synthesize

router = APIRouter()


async def _emit(websocket: WebSocket, event_type: str, data: dict):
    """Sends a typed event matching the frontend's expected {type, data}
    shape (see frontend/src/hooks/useLiveCall.js handleSocketEvent and the
    README's WebSocket Events table)."""
    await websocket.send_json({"type": event_type, "data": data})


async def _synthesize_and_emit(websocket: WebSocket, call_id: str, text: str):
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
        await asyncio.to_thread(synthesize, text, out_path)
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
        await websocket.send_json({
            "type": "audio.chunk",
            "data": {"audio_base64": base64.b64encode(audio_bytes).decode("ascii")},
        })
    except Exception as e:
        print(f"[TTS Warning] Failed to synthesize/send audio for call {call_id}: {e}")
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
    })

    transcriber = StreamingTranscriber(sample_rate=16000)
    transcriber.start()
    transcriber.begin_turn()
    try:
        while True:
            data = await websocket.receive_bytes()
            transcript = transcriber.feed(data)
            if transcript:
                await _emit(websocket, "transcript.final", {
                    "role": "customer",
                    "text": transcript,
                })

                result = handle_turn(transcript, state)
                save_session(call_id, state)

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": True,
                })

                if result.get("reply_text"):
                    await _emit(websocket, "transcript.final", {
                        "role": "ai",
                        "text": result["reply_text"],
                    })
                    await _synthesize_and_emit(websocket, call_id, result["reply_text"])

                await _emit(websocket, "state.changed", {
                    "status": state.get("status"),
                    "isAiSpeaking": False,
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
