import io
import time
import logging
from elevenlabs.client import ElevenLabs
from app.core.config import settings

logger = logging.getLogger("talkse")


class ElevenLabsTTS:
    name = "elevenlabs"
    timeout_seconds = 3.5

    def __init__(self):
        self._client = ElevenLabs(api_key=settings.elevenlabs_api_key, timeout=self.timeout_seconds)

    def synthesize_bytes(self, text: str) -> tuple[bytes, float]:
        """Synthesizes speech and returns the raw audio bytes directly,
        with no disk round-trip. Returns (audio_bytes, elapsed_seconds)."""
        start_time = time.perf_counter()

        audio = self._client.text_to_speech.convert(
            voice_id=settings.elevenlabs_voice_id,
            text=text,
            model_id=settings.elevenlabs_model_id,
        )

        buffer = io.BytesIO()
        for chunk in audio:
            buffer.write(chunk)

        elapsed = time.perf_counter() - start_time
        logger.info(f"[TTS] ElevenLabs synthesis completed in {elapsed:.3f}s")
        return buffer.getvalue(), elapsed

    def synthesize(self, text: str, out_path: str) -> float:
        """Back-compat file-based entry point, used by anything (e.g. CLI
        tools, tests) that still wants a .wav on disk."""
        audio_bytes, elapsed = self.synthesize_bytes(text)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return elapsed
