"""
Test scaffolding for the Talkse backend.

Why this file exists:
`conversation_loop.py` unconditionally imports `audio_playback`, which
unconditionally imports `sounddevice`, which requires the system PortAudio
library to even *import* (not just to record). That means today, you cannot
import the core conversation logic on any machine/container without a working
audio stack installed — even though the business logic itself never touches
audio hardware directly.

This is exactly the kind of coupling worth fixing during the FastAPI
migration (the server will never play audio locally), but until it's fixed,
we stub the hardware-coupled modules here so tests (and later, the FastAPI
process) can import the logic cleanly.
"""
import sys
import types
import os

# Ensure repo root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _install_stub(name: str, **attrs):
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


# --- Stub sounddevice / webrtcvad so audio_playback.py / mic_input.py import cleanly ---
class _FakeStream:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def start(self): pass
    def stop(self): pass
    def close(self): pass

_install_stub(
    "sounddevice",
    InputStream=_FakeStream,
    OutputStream=_FakeStream,
    play=lambda *a, **k: None,
    stop=lambda *a, **k: None,
    wait=lambda *a, **k: None,
    query_devices=lambda *a, **k: [],
)

_install_stub(
    "webrtcvad",
    Vad=lambda *a, **k: types.SimpleNamespace(is_speech=lambda *a, **k: False),
)

import pytest


@pytest.fixture(autouse=True)
def _no_real_env(monkeypatch):
    """
    Belt-and-suspenders: even if a real .env is present on the machine running
    tests, make sure unit tests never accidentally hit a real API because a
    key happened to be set. Tests that need "a key present" set their own
    fake value explicitly.
    """
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "DEEPGRAM_API_KEY"):
        monkeypatch.setenv(var, "test-key-not-real")
