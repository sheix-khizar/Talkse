from typing import Protocol


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, out_path: str) -> float:
        """Writes synthesized audio to out_path. Returns elapsed seconds.
        Must raise on failure — callers (router.py) rely on exceptions to
        trigger fallback to the next provider in the chain, not on a
        sentinel return value."""
        ...
