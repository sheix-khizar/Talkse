import audioop
import io
import wave


def mulaw_b64_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """8kHz mulaw -> 8kHz linear16 PCM."""
    return audioop.ulaw2lin(mulaw_bytes, 2)


def pcm16_to_mulaw(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """Linear16 PCM at any sample_rate -> 8kHz mulaw, resampling if needed."""
    if sample_rate != 8000:
        pcm_bytes, _ = audioop.ratecv(pcm_bytes, 2, 1, sample_rate, 8000, None)
    return audioop.lin2ulaw(pcm_bytes, 2)


def extract_pcm_from_wav_bytes(wav_bytes: bytes) -> tuple[bytes, int]:
    """Deepgram's synthesize_bytes() returns a WAV container by default.
    Unwraps it to (raw_pcm_bytes, sample_rate) so it can be fed to
    pcm16_to_mulaw(). Raises if the audio isn't a WAV container (e.g. mp3
    from ElevenLabs)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate()
