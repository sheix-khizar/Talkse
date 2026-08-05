import base64
import io
import wave
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.telephony.audio_convert import (
    mulaw_b64_to_pcm16,
    pcm16_to_mulaw,
    extract_pcm_from_wav_bytes,
)
from app.services import db

client = TestClient(app)


def test_audio_conversion_mulaw_pcm_roundtrip():
    # 100 samples of zero PCM (16-bit linear PCM = 200 bytes)
    original_pcm = b"\x00\x00" * 100
    mulaw = pcm16_to_mulaw(original_pcm, sample_rate=8000)
    assert len(mulaw) == 100

    recovered_pcm = mulaw_b64_to_pcm16(mulaw)
    assert len(recovered_pcm) == 200


def test_extract_pcm_from_wav_bytes():
    # Generate a dummy 8kHz 16-bit mono WAV buffer
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 50)

    wav_data = buf.getvalue()
    pcm, rate = extract_pcm_from_wav_bytes(wav_data)
    assert rate == 8000
    assert len(pcm) == 100


def test_signalwire_voice_webhook():
    response = client.post(
        "/api/v1/signalwire/voice",
        data={
            "CallSid": "test_call_sid_123",
            "From": "+15550001111",
            "To": "+14155551234",
        },
    )
    assert response.status_code == 200
    assert "xml" in response.headers["content-type"]
    assert "<Response>" in response.text
    assert "<Connect>" in response.text
    assert "<Stream url=" in response.text
