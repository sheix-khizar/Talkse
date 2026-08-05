import os
import io
import wave
import pytest
from unittest.mock import MagicMock
from app.services.tts.deepgram_tts import DeepgramTTS
from app.services.tts.elevenlabs_tts import ElevenLabsTTS


def test_elevenlabs_synthesize_bytes_returns_valid_wav():
    """Guards against the output_format regressing back to mp3 — that bug
    made ElevenLabs silently produce no audio on real calls."""
    fake_client = MagicMock()
    fake_client.text_to_speech.convert.return_value = [b"\x00\x01" * 100]

    provider = ElevenLabsTTS.__new__(ElevenLabsTTS)  # skip __init__ (no real API key needed)
    provider._client = fake_client

    wav_bytes, elapsed = provider.synthesize_bytes("hello")

    # Must be parseable as WAV, or the SignalWire telephony path will
    # throw and the caller hears silence.
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnframes() > 0
        assert wf.getframerate() == 16000


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TTS_TESTS") != "1",
    reason="RUN_LIVE_TTS_TESTS=1 not set"
)
def test_deepgram_tts_integration():
    """Live API test for DeepgramTTS."""
    if not os.getenv("DEEPGRAM_API_KEY"):
        pytest.skip("DEEPGRAM_API_KEY not set")
    
    provider = DeepgramTTS()
    out_path = "test_deepgram.wav"
    
    try:
        elapsed = provider.synthesize("Hello from deepgram integration test.", out_path)
        assert elapsed > 0
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TTS_TESTS") != "1",
    reason="RUN_LIVE_TTS_TESTS=1 not set"
)
def test_elevenlabs_tts_integration():
    """Live API test for ElevenLabsTTS."""
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("ELEVENLABS_API_KEY not set")

    provider = ElevenLabsTTS()
    out_path = "test_elevenlabs.wav"

    try:
        elapsed = provider.synthesize("Hello from elevenlabs integration test.", out_path)
        assert elapsed > 0
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
