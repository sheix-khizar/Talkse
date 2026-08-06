"""
Live streaming STT via Deepgram's websocket API.

Maintains ONE persistent Deepgram connection for an entire multi-turn
conversation, instead of opening and tearing down a brand-new websocket on
every turn. Per-turn boundaries are signaled with a Finalize control message
(flushes the current utterance WITHOUT closing the socket), and a background
keep-alive thread pings the connection during the silent gaps between turns
(while the LLM/TTS stages are running) so Deepgram's idle timeout doesn't
drop the connection and force a reconnect on the next turn.

Usage for a whole conversation:
    transcriber = StreamingTranscriber()
    transcriber.start()                 # once, before the first turn
    try:
        for each turn:
            transcriber.begin_turn()
            ... send_frame(...) from the mic callback ...
            transcript, ttfr, turn_elapsed, finalize_overhead = transcriber.end_turn()
    finally:
        transcriber.close()              # once, after the last turn

IMPORTANT: send_frame() is non-blocking (enqueues to a Queue). A dedicated
background sender thread performs the actual websocket send_media() calls.
This prevents sounddevice's real-time audio callback thread from blocking on
network I/O.
"""
import os
import time
import queue
import threading
import logging
from deepgram import DeepgramClient

logger = logging.getLogger("talkse")

# Deepgram closes idle streaming connections after ~10-12s with no audio or
# keep-alive traffic. LLM + TTS turnaround between turns can easily exceed
# that, so we ping well under the timeout.
KEEP_ALIVE_INTERVAL_SECONDS = 5


class StreamingTranscriber:
    """Wraps a single Deepgram live-transcription connection that is reused
    across an entire multi-turn conversation. Frames are queued by the caller
    and sent to Deepgram from a dedicated background thread, so the audio
    capture callback never performs blocking network I/O."""

    def __init__(self, sample_rate: int = 16000):
        from app.core.config import settings
        api_key = settings.deepgram_api_key or os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY missing in settings or environment variables.")

        self.sample_rate = sample_rate
        self.client = DeepgramClient(api_key=api_key)
        self.connection = None
        self.conn = None
        self.socket_cm = None
        self._listen_thread = None

        self._final_transcript_parts: list[str] = []
        self._latest_interim: str = ""
        self._first_result_time: float | None = None
        self._turn_start_time: float | None = None

        self._send_queue: "queue.Queue[bytes | None]" = queue.Queue()
        self._sender_thread: threading.Thread | None = None
        self._send_error: Exception | None = None

        self._keep_alive_stop = threading.Event()
        self._keep_alive_thread: threading.Thread | None = None
        self._connection_open = False
        self.on_transcript_update = None  # optional callback: cb(full_text: str, is_final: bool)

    def _on_transcript(self, result, **kwargs):
        if self._first_result_time is None:
            self._first_result_time = time.perf_counter()

        try:
            channel = getattr(result, "channel", None)
            if not channel:
                return
            alt = channel.alternatives[0]
            text = getattr(alt, "transcript", "")

            is_final = getattr(result, "is_final", True)
            speech_final = getattr(result, "speech_final", False)
            if is_final:
                if text:
                    self._final_transcript_parts.append(text)
                    self._turn_complete = True
                self._latest_interim = ""
                if speech_final:
                    self._turn_complete = True
            else:
                if text:
                    self._latest_interim = text

            full_hypothesis = " ".join(self._final_transcript_parts + ([self._latest_interim] if self._latest_interim else [])).strip()
            if self.on_transcript_update and full_hypothesis:
                try:
                    self.on_transcript_update(full_hypothesis, is_final or speech_final)
                except Exception as cb_err:
                    logger.warning(f"[Streaming STT Callback Error] {cb_err}")
        except Exception as e:
            logger.warning(f"[Streaming STT Warning] Parse error: {e}")

    def _sender_loop(self):
        """Runs on a background thread for the lifetime of the connection
        (not restarted per turn). Pulls frames off the queue and sends them
        to Deepgram. Any network delay/blocking happens here, never on the
        audio callback thread."""
        while True:
            frame = self._send_queue.get()
            if frame is None:  # sentinel -> shut down
                self._send_queue.task_done()
                break
            try:
                if self.conn:
                    self.conn.send_media(frame)
            except Exception as e:
                self._send_error = e
                logger.error(f"[Streaming STT] Send error on background thread: {e}")
            self._send_queue.task_done()

    def _keep_alive_loop(self):
        """Runs for the lifetime of the connection. Pings Deepgram periodically
        so the socket survives silent gaps between turns (LLM + TTS
        turnaround), which would otherwise exceed Deepgram's idle timeout and
        drop the connection — forcing an expensive reconnect on the next turn."""
        while not self._keep_alive_stop.wait(KEEP_ALIVE_INTERVAL_SECONDS):
            try:
                if self.conn and self._connection_open:
                    self.conn.send_keep_alive()
            except Exception as e:
                logger.warning(f"[Streaming STT] Keep-alive send failed: {e}")

    def start(self):
        """Opens the Deepgram connection ONCE for the whole conversation.
        Do not call this per turn — use begin_turn()/end_turn() instead."""
        self.connection = self.client.listen.v1.connect(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=self.sample_rate,
            channels=1,
            interim_results=True,
            punctuate=True,
            endpointing=200,
        )
        self.socket_cm = self.connection
        self.conn = self.socket_cm.__enter__()
        self._connection_open = True

        self.conn.on("message", self._on_transcript)
        self.conn.on("Results", self._on_transcript)
        self._listen_thread = threading.Thread(target=self.conn.start_listening, daemon=True)
        self._listen_thread.start()

        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()

        self._keep_alive_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
        self._keep_alive_thread.start()

    def begin_turn(self):
        """Resets per-turn state. Call at the start of every turn. Does NOT
        touch the network connection — the same websocket carries every turn
        of the conversation."""
        self._final_transcript_parts = []
        self._latest_interim = ""
        self._first_result_time = None
        self._turn_start_time = time.perf_counter()
        self._turn_complete = False

    def send_frame(self, pcm_bytes: bytes):
        """Non-blocking: enqueues one frame of 16-bit mono PCM audio.
        Safe to call from a real-time audio callback — this never touches the network directly."""
        self._send_queue.put(pcm_bytes)

    def feed(self, pcm_bytes: bytes) -> str | None:
        """Enqueues audio and returns a transcript if a turn is complete (silence detected)."""
        self.send_frame(pcm_bytes)
        if getattr(self, "_turn_complete", False):
            transcript = " ".join(self._final_transcript_parts).strip()
            self.begin_turn()  # reset for next turn
            return transcript
        return None

    def get_current_hypothesis(self) -> tuple[str, bool]:
        """Returns (current_full_text, is_turn_complete)."""
        full_text = " ".join(self._final_transcript_parts + ([self._latest_interim] if self._latest_interim else [])).strip()
        is_complete = getattr(self, "_turn_complete", False)
        return full_text, is_complete

    def end_turn(self) -> tuple[str, float, float, float]:
        """
        Signals end-of-turn to Deepgram with a Finalize control message, which
        flushes the current utterance WITHOUT closing the connection — the
        same socket stays open and ready for the next turn immediately.

        Returns (final_transcript, time_to_first_result, turn_elapsed, finalize_overhead).

        turn_elapsed spans this turn's begin_turn() to end_turn() call (i.e.
        essentially this turn's recording duration) — it is NOT a proxy for
        connection overhead. finalize_overhead isolates the cost of the
        Finalize round-trip alone, measured only after recording stopped for
        this turn — THIS is the number that reflects real per-turn STT
        latency now that we don't reconnect every turn.
        """
        # Block until every frame queued for this turn has actually been sent
        # to the socket before we ask Deepgram to finalize.
        self._send_queue.join()

        ttfr = (self._first_result_time - self._turn_start_time) if (self._first_result_time and self._turn_start_time) else 0.0

        finalize_start = time.perf_counter()
        if self.conn:
            try:
                self.conn.send_finalize()
                time.sleep(0.2)  # brief grace period for the final transcript to arrive over the still-open socket
            except Exception as e:
                logger.warning(f"[Streaming STT Finalize Warning] {e}")
        finalize_overhead = time.perf_counter() - finalize_start

        turn_elapsed = time.perf_counter() - self._turn_start_time if self._turn_start_time else 0.0

        if self._send_error:
            err = self._send_error
            self._send_error = None
            raise RuntimeError(f"Streaming STT send failed: {err}")

        transcript = " ".join(self._final_transcript_parts).strip()
        if not transcript and self._latest_interim:
            transcript = self._latest_interim.strip()

        return transcript, ttfr, turn_elapsed, finalize_overhead

    def close(self):
        """Tears down the connection for real. Call ONCE, after the whole
        conversation is done (ideally in a finally block so it always runs,
        even if a turn raises partway through)."""
        self._keep_alive_stop.set()

        self._send_queue.put(None)  # sentinel -> stop the sender thread
        if self._sender_thread:
            self._sender_thread.join(timeout=5)

        if self.conn and self._connection_open:
            try:
                self.conn.send_close_stream()
                time.sleep(0.1)
                self.socket_cm.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"[Streaming STT Close Warning] {e}")
        self._connection_open = False
