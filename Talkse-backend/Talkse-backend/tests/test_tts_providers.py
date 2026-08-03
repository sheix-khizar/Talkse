import os
import pytest
from app.services.tts.deepgram_tts import DeepgramTTS
from app.services.tts.elevenlabs_tts import ElevenLabsTTS

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TTS_TESTS") != "1",
    reason="RUN_LIVE_TTS_TESTS=1 not set"
)
def test_deepgram_tts_integration():
    """Live API test for DeepgramTTS."""
    # Assuming DEEPGRAM_API_KEY is available in env.
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
