import os
import sys
import time
import wave
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv()

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
    """Streams TTS audio chunks from Deepgram, plays audio live through speakers,
    and returns (time_to_first_chunk, total_tts_time).
    Optionally saves the full audio to out_path.
    """
    start_time = time.perf_counter()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY missing in environment variables.")
        
    client = DeepgramClient(api_key=api_key)
    sample_rate = 24000
    
    # Request raw linear16 PCM audio stream
    audio_stream = client.speak.v1.audio.generate(
        text=reply_text,
        model="aura-asteria-en",
        encoding="linear16",
        sample_rate=sample_rate
    )
    
    first_chunk_time = None
    all_pcm_chunks = []
    
    # Initialize sounddevice RawOutputStream for live zero-latency audio playback
    stream = sd.RawOutputStream(samplerate=sample_rate, channels=1, dtype='int16')
    stream.start()
    
    try:
        for chunk in audio_stream:
            if not chunk:
                continue
                
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter() - start_time
                print(f"[Streaming TTS] Time to First Audio Chunk: {first_chunk_time:.3f}s [FAST] (Playback Started!)")
                
            stream.write(chunk)
            if out_path:
                all_pcm_chunks.append(chunk)
    finally:
        stream.stop()
        stream.close()
        
    total_tts_time = time.perf_counter() - start_time
    if first_chunk_time is None:
        first_chunk_time = total_tts_time
        
    print(f"[Streaming TTS] Total TTS synthesis & playback time: {total_tts_time:.3f}s")
    
    # Save audio file if out_path requested
    if out_path and all_pcm_chunks:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(all_pcm_chunks))
        print(f"[Streaming TTS] Saved audio to: '{out_path}'")
        
    return first_chunk_time, total_tts_time

if __name__ == "__main__":
    ttft, total = stream_and_play_tts("Hello! Welcome to Bloom Aesthetics & Wellness Medspa. How can I help you today?")
    print(f"TTFT: {ttft:.3f}s, Total: {total:.3f}s")
