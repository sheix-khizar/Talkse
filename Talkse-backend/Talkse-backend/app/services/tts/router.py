import logging
from app.services.tts.deepgram_tts import DeepgramTTS
from app.services.tts.elevenlabs_tts import ElevenLabsTTS

logger = logging.getLogger("talkse")

_deepgram = DeepgramTTS()
_elevenlabs = None  # lazy — avoid requiring ELEVENLABS_API_KEY on free-only deployments


def _get_elevenlabs():
    global _elevenlabs
    if _elevenlabs is None:
        _elevenlabs = ElevenLabsTTS()
    return _elevenlabs


def _chain_for_plan(plan: str) -> list:
    if plan == "paid":
        return [_get_elevenlabs(), _deepgram]
    return [_deepgram]


def synthesize_for_plan(plan: str, text: str, out_path: str) -> tuple[float, str]:
    """File-based entry point — kept for any caller that still wants a .wav
    on disk (tests, CLI tools). The live WebSocket path uses
    synthesize_for_plan_bytes() below instead, which skips disk entirely."""
    last_err = None
    for provider in _chain_for_plan(plan):
        try:
            elapsed = provider.synthesize(text, out_path)
            return elapsed, provider.name
        except Exception as e:
            logger.warning(
                f"[TTS] {provider.name} failed for plan={plan!r}: {e}. "
                f"Trying next provider in chain."
            )
            last_err = e
    raise RuntimeError(f"All TTS providers failed for plan={plan!r}") from last_err


def synthesize_for_plan_bytes(plan: str, text: str) -> tuple[bytes, float, str]:
    """Tries each provider in the plan's chain in order, entirely in memory.
    Returns (audio_bytes, elapsed_seconds, provider_name_used).
    Raises RuntimeError only if every provider in the chain fails."""
    last_err = None
    for provider in _chain_for_plan(plan):
        try:
            audio_bytes, elapsed = provider.synthesize_bytes(text)
            return audio_bytes, elapsed, provider.name
        except Exception as e:
            logger.warning(
                f"[TTS] {provider.name} failed for plan={plan!r}: {e}. "
                f"Trying next provider in chain."
            )
            last_err = e
    raise RuntimeError(f"All TTS providers failed for plan={plan!r}") from last_err
