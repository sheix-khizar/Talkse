import io
import time
import logging
from deepgram import DeepgramClient
from app.core.config import settings

logger = logging.getLogger("talkse")


class DeepgramTTS:
    name = "deepgram"
    timeout_seconds = 3.0

    def __init__(self):
        # Reuse one client instance instead of constructing a new one on
        # every synthesize() call.
        self._client = DeepgramClient(api_key=settings.deepgram_api_key)

    def synthesize_bytes(self, text: str) -> tuple[bytes, float]:
        """Synthesizes speech and returns the raw audio bytes directly,
        with no disk round-trip. Returns (audio_bytes, elapsed_seconds)."""
        start_time = time.perf_counter()

        audio_stream = self._client.speak.v1.audio.generate(
            text=text,
            model="aura-asteria-en"
        )

        buffer = io.BytesIO()
        for chunk in audio_stream:
            buffer.write(chunk)

        elapsed = time.perf_counter() - start_time
        logger.info(f"[TTS] Deepgram synthesis completed in {elapsed:.3f}s")
        return buffer.getvalue(), elapsed

    def synthesize(self, text: str, out_path: str) -> float:
        """Back-compat file-based entry point, used by anything (e.g. CLI
        tools, tests) that still wants a .wav on disk."""
        audio_bytes, elapsed = self.synthesize_bytes(text)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return elapsed
