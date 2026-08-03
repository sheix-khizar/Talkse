import time
import logging
from deepgram import DeepgramClient
from app.core.config import settings

logger = logging.getLogger("talkse")


class DeepgramTTS:
    name = "deepgram"
    timeout_seconds = 3.0

    def synthesize(self, text: str, out_path: str) -> float:
        start_time = time.perf_counter()
        client = DeepgramClient(api_key=settings.deepgram_api_key)

        audio_stream = client.speak.v1.audio.generate(
            text=text,
            model="aura-asteria-en"
        )

        with open(out_path, "wb") as f:
            for chunk in audio_stream:
                f.write(chunk)

        elapsed = time.perf_counter() - start_time
        logger.info(f"[TTS] Deepgram synthesis completed in {elapsed:.3f}s")
        return elapsed
