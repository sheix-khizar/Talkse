import time
import logging
from elevenlabs.client import ElevenLabs
from app.core.config import settings

logger = logging.getLogger("talkse")


class ElevenLabsTTS:
    name = "elevenlabs"

    def __init__(self):
        self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    def synthesize(self, text: str, out_path: str) -> float:
        start_time = time.perf_counter()
        audio = self._client.text_to_speech.convert(
            voice_id=settings.elevenlabs_voice_id,
            text=text,
            model_id=settings.elevenlabs_model_id,
        )
        with open(out_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        elapsed = time.perf_counter() - start_time
        logger.info(f"[TTS] ElevenLabs synthesis completed in {elapsed:.3f}s")
        return elapsed
