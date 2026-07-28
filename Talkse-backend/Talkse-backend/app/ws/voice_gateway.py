from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.streaming_stt import StreamingTranscriber
from app.services.conversation_loop import handle_turn
from app.session.store import get_session, save_session

router = APIRouter()

@router.websocket("/ws/calls/{call_id}")
async def voice_ws(websocket: WebSocket, call_id: str):
    await websocket.accept()
    state = get_session(call_id)
    if not state:
        await websocket.close(code=4404)
        return

    transcriber = StreamingTranscriber(sample_rate=16000)
    transcriber.start()
    transcriber.begin_turn()
    try:
        while True:
            data = await websocket.receive_bytes()   # raw PCM chunk from browser
            transcript = transcriber.feed(data)
            if transcript:
                result = handle_turn(transcript, state)
                save_session(call_id, state)
                await websocket.send_json({
                    "transcript": transcript,
                    "reply_text": result.get("reply_text"),
                    "terminal": result["terminal"],
                })
                if result["terminal"]:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        transcriber.close()
