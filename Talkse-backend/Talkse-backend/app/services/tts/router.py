import logging
from app.services.tts.deepgram_tts import DeepgramTTS
from app.services.tts.elevenlabs_tts import ElevenLabsTTS

logger = logging.getLogger("talkse")

_deepgram = DeepgramTTS()
_elevenlabs = None  # lazy — avoid requiring ELEVENLABS_API_KEY on free-only deployments

VALID_PROVIDERS = ("deepgram", "elevenlabs")


def _get_elevenlabs():
    global _elevenlabs
    if _elevenlabs is None:
        _elevenlabs = ElevenLabsTTS()
    return _elevenlabs


def _chain_for_provider(provider: str) -> list:
    """deepgram is always the last fallback in the chain — it has no
    external-account setup requirement beyond DEEPGRAM_API_KEY, which is
    already mandatory to boot the app (see README)."""
    if provider == "elevenlabs":
        return [_get_elevenlabs(), _deepgram]
    return [_deepgram]


def default_provider_for_plan(plan: str) -> str:
    """Only used once, at call-creation time, to pick a sensible starting
    pipeline. After that, the call's own voice_pipeline (in its session
    state) is the source of truth, not the tenant's plan."""
    return "elevenlabs" if plan == "paid" else "deepgram"


def synthesize_for_provider_bytes(provider: str, text: str) -> tuple[bytes, float, str]:
    """Tries the given provider (falling back to deepgram if it fails),
    entirely in memory. Returns (audio_bytes, elapsed_seconds, provider_name_used).
    Raises RuntimeError only if every provider in the chain fails."""
    if provider not in VALID_PROVIDERS:
        provider = "deepgram"
    last_err = None
    for tts in _chain_for_provider(provider):
        try:
            audio_bytes, elapsed = tts.synthesize_bytes(text)
            return audio_bytes, elapsed, tts.name
        except Exception as e:
            logger.warning(
                f"[TTS] {tts.name} failed for provider={provider!r}: {e}. "
                f"Trying next provider in chain."
            )
            last_err = e
    raise RuntimeError(f"All TTS providers failed for provider={provider!r}") from last_err


def synthesize_for_provider(provider: str, text: str, out_path: str) -> tuple[float, str]:
    """File-based entry point — kept for callers that still want a .wav on disk."""
    if provider not in VALID_PROVIDERS:
        provider = "deepgram"
    last_err = None
    for tts in _chain_for_provider(provider):
        try:
            elapsed = tts.synthesize(text, out_path)
            return elapsed, tts.name
        except Exception as e:
            logger.warning(f"[TTS] {tts.name} failed for provider={provider!r}: {e}.")
            last_err = e
    raise RuntimeError(f"All TTS providers failed for provider={provider!r}") from last_err


# --- Back-compat wrappers (plan-keyed) -------------------------------------
# Kept so any other caller (tests, the REST /turn endpoint) that still
# passes "free"/"paid" keeps working without modification.

def synthesize_for_plan_bytes(plan: str, text: str) -> tuple[bytes, float, str]:
    return synthesize_for_provider_bytes(default_provider_for_plan(plan), text)


def synthesize_for_plan(plan: str, text: str, out_path: str) -> tuple[float, str]:
    return synthesize_for_provider(default_provider_for_plan(plan), text, out_path)
