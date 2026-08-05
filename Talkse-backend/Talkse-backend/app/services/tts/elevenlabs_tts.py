import io
import time
import wave
import logging
from elevenlabs.client import ElevenLabs
from app.core.config import settings

logger = logging.getLogger("talkse")

ELEVENLABS_SAMPLE_RATE = 16000  # must match the output_format requested below


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wraps raw 16-bit PCM in a WAV container so downstream code
    (extract_pcm_from_wav_bytes, and the browser's `type: 'audio/wav'`
    blob) can treat Deepgram and ElevenLabs output identically."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class ElevenLabsTTS:
    name = "elevenlabs"
    timeout_seconds = 3.5

    def __init__(self):
        self._client = ElevenLabs(api_key=settings.elevenlabs_api_key, timeout=self.timeout_seconds)

    def synthesize_bytes(self, text: str) -> tuple[bytes, float]:
        """Synthesizes speech as raw PCM (NOT the SDK's default MP3) and
        wraps it in a WAV container, so this is a drop-in match for what
        DeepgramTTS.synthesize_bytes() already returns. Returns
        (wav_bytes, elapsed_seconds).

        IMPORTANT: `output_format` must stay a `pcm_*` value, never the
        default mp3 one — the SignalWire telephony path
        (extract_pcm_from_wav_bytes) cannot parse mp3 and will silently
        drop audio for the turn if this regresses. Verify the exact
        `pcm_16000` identifier against the installed `elevenlabs` package
        version's docs if this starts raising.
        """
        start_time = time.perf_counter()

        audio = self._client.text_to_speech.convert(
            voice_id=settings.elevenlabs_voice_id,
            text=text,
            model_id=settings.elevenlabs_model_id,
            output_format=f"pcm_{ELEVENLABS_SAMPLE_RATE}",
        )

        pcm_buffer = io.BytesIO()
        for chunk in audio:
            pcm_buffer.write(chunk)

        wav_bytes = _pcm_to_wav_bytes(pcm_buffer.getvalue(), sample_rate=ELEVENLABS_SAMPLE_RATE)

        elapsed = time.perf_counter() - start_time
        logger.info(f"[TTS] ElevenLabs synthesis completed in {elapsed:.3f}s")
        return wav_bytes, elapsed

    def synthesize(self, text: str, out_path: str) -> float:
        """Back-compat file-based entry point, used by anything (e.g. CLI
        tools, tests) that still wants a .wav on disk."""
        audio_bytes, elapsed = self.synthesize_bytes(text)
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        return elapsed
