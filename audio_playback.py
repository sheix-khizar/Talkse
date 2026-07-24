import os
import sys
import time
import wave
import queue
import threading
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv()

_deepgram_client = None

def get_deepgram_client():
    global _deepgram_client
    if _deepgram_client is None:
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY missing in environment variables.")
        _deepgram_client = DeepgramClient(api_key=api_key)
    return _deepgram_client

def play_audio_file(path: str):
    """Plays a completed WAV audio file via sounddevice, blocking until done."""
    if not os.path.exists(path):
        print(f"[Audio Error] File '{path}' not found.")
        return
        
    try:
        with wave.open(path, "rb") as wf:
            samplerate = wf.getframerate()
            nchannels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            
            audio_data = np.frombuffer(frames, dtype=np.int16)
            if nchannels > 1:
                audio_data = audio_data.reshape(-1, nchannels)
                
            sd.play(audio_data, samplerate)
            sd.wait()
    except Exception as e:
        print(f"[Audio Playback Warning] Failed to play '{path}': {e}")

def stream_and_play_tts(reply_text: str, out_path: str = None) -> tuple[float, float]:
    start_time = time.perf_counter()
    client = get_deepgram_client()
    sample_rate = 24000

    audio_stream = client.speak.v1.audio.generate(
        text=reply_text, model="aura-asteria-en",
        encoding="linear16", sample_rate=sample_rate
    )

    chunk_queue = queue.Queue(maxsize=50)
    first_chunk_time = None
    all_pcm_chunks = []
    playback_done = threading.Event()

    def playback_worker():
        stream = sd.RawOutputStream(samplerate=sample_rate, channels=1, dtype='int16')
        stream.start()
        try:
            buffer = b""
            while True:
                chunk = chunk_queue.get()
                if chunk is None:  # sentinel = stream finished
                    if len(buffer) >= 2:
                        write_len = len(buffer) - (len(buffer) % 2)
                        stream.write(buffer[:write_len])
                    break
                
                buffer += chunk
                if len(buffer) >= 2:
                    write_len = len(buffer) - (len(buffer) % 2)
                    stream.write(buffer[:write_len])
                    buffer = buffer[write_len:]
        finally:
            stream.stop()
            stream.close()
            playback_done.set()

    worker = threading.Thread(target=playback_worker, daemon=True)
    worker.start()

    try:
        for chunk in audio_stream:
            if not chunk:
                continue
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter() - start_time
                print(f"[Streaming TTS] Time to First Audio Chunk: {first_chunk_time:.3f}s")
            chunk_queue.put(chunk)     # network thread just enqueues, never blocks on audio device
            if out_path:
                all_pcm_chunks.append(chunk)
    finally:
        chunk_queue.put(None)  # signal playback thread to finish
        playback_done.wait()

    total_tts_time = time.perf_counter() - start_time
    if first_chunk_time is None:
        first_chunk_time = total_tts_time
    print(f"[Streaming TTS] Total time: {total_tts_time:.3f}s")

    if out_path and all_pcm_chunks:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(all_pcm_chunks))

    return first_chunk_time, total_tts_time

def stream_and_play_tts_safe(text: str, out_path: str = None, max_retries: int = 2) -> tuple[float, float]:
    for attempt in range(max_retries + 1):
        try:
            return stream_and_play_tts(text, out_path)
        except Exception as e:
            print(f"[TTS Streaming Warning] Attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                time.sleep(1.5)
            else:
                print("[TTS Streaming Error] Giving up after retries.")
                return 0.0, 0.0

if __name__ == "__main__":
    ttft, total = stream_and_play_tts("Hello! Welcome to Bloom Aesthetics & Wellness Medspa. How can I help you today?")
    print(f"TTFT: {ttft:.3f}s, Total: {total:.3f}s")
