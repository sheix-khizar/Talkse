from unittest.mock import MagicMock
import pytest
from app.services.tts import router as tts_router


def test_free_plan_uses_deepgram_only(monkeypatch):
    fake_deepgram = MagicMock()
    fake_deepgram.name = "deepgram"
    fake_deepgram.synthesize.return_value = 0.5
    monkeypatch.setattr(tts_router, "_deepgram", fake_deepgram)

    elapsed, provider = tts_router.synthesize_for_plan("free", "hi", "/tmp/x.wav")

    assert provider == "deepgram"
    fake_deepgram.synthesize.assert_called_once()


def test_paid_plan_falls_back_to_deepgram_on_elevenlabs_failure(monkeypatch):
    fake_eleven = MagicMock()
    fake_eleven.name = "elevenlabs"
    fake_eleven.synthesize.side_effect = RuntimeError("rate limited")

    fake_deepgram = MagicMock()
    fake_deepgram.name = "deepgram"
    fake_deepgram.synthesize.return_value = 0.4

    monkeypatch.setattr(tts_router, "_get_elevenlabs", lambda: fake_eleven)
    monkeypatch.setattr(tts_router, "_deepgram", fake_deepgram)

    elapsed, provider = tts_router.synthesize_for_plan("paid", "hi", "/tmp/x.wav")

    assert provider == "deepgram"
    fake_eleven.synthesize.assert_called_once()
    fake_deepgram.synthesize.assert_called_once()


def test_all_providers_failing_raises(monkeypatch):
    fake_deepgram = MagicMock()
    fake_deepgram.name = "deepgram"
    fake_deepgram.synthesize.side_effect = RuntimeError("down")
    monkeypatch.setattr(tts_router, "_deepgram", fake_deepgram)

    with pytest.raises(RuntimeError):
        tts_router.synthesize_for_plan("free", "hi", "/tmp/x.wav")
