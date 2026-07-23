import os
import time
import wave
import numpy as np
import sounddevice as sd
import webrtcvad

def record_turn(max_seconds: int = 15, silence_threshold_ms: int = 800, sample_rate: int = 16000) -> str:
    """Captures a single speech turn from default microphone using WebRTC VAD.
    
    Starts recording when speech is first detected, and stops after silence_threshold_ms of continuous
    silence or max_seconds hard cap.
    Returns path to the saved temporary WAV file.
    """
    vad = webrtcvad.Vad(mode=2)  # Aggressiveness mode 2 (balanced)
    frame_duration_ms = 30
    frame_samples = int(sample_rate * frame_duration_ms / 1000) # 480 samples @ 16kHz
    bytes_per_sample = 2 # 16-bit PCM
    frame_bytes = frame_samples * bytes_per_sample

    silence_frames_needed = int(silence_threshold_ms / frame_duration_ms)
    max_frames = int(max_seconds * 1000 / frame_duration_ms)

    audio_buffer = []
    consecutive_silence_count = 0
    speech_started = False

    print("\n[Mic Input] Listening... Speak into your microphone now.")

    def audio_callback(indata, frames, time_info, status):
        nonlocal speech_started, consecutive_silence_count
        if status:
            print(f"[Mic Warning] {status}", flush=True)

        # Ensure int16 mono audio bytes
        pcm_bytes = (indata[:, 0] * 32767).astype(np.int16).tobytes()

        # WebRTC VAD expects exact frame_bytes length
        if len(pcm_bytes) == frame_bytes:
            try:
                is_speech = vad.is_speech(pcm_bytes, sample_rate)
            except Exception:
                is_speech = True

            if is_speech:
                if not speech_started:
                    print("[Mic Input] Speech detected — recording turn...")
                    speech_started = True
                audio_buffer.append(pcm_bytes)
                consecutive_silence_count = 0
            else:
                if speech_started:
                    audio_buffer.append(pcm_bytes)
                    consecutive_silence_count += 1

    # Start InputStream
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32',
                         blocksize=frame_samples, callback=audio_callback):
        start_time = time.time()
        while True:
            time.sleep(0.03)
            # Stop if speech was started and silence threshold reached
            if speech_started and consecutive_silence_count >= silence_frames_needed:
                print(f"[Mic Input] Silence detected ({silence_threshold_ms}ms) — stopping record.")
                break

            # Hard timeout cap
            if time.time() - start_time >= max_seconds:
                print(f"[Mic Input] Max duration ({max_seconds}s) reached — stopping record.")
                break

    if not audio_buffer:
        print("[Mic Warning] No speech captured during window.")
        # Create 1-second silence fallback clip to avoid empty file crashes
        audio_buffer = [b'\x00' * frame_bytes] * 30

    os.makedirs("turns", exist_ok=True)
    out_file = os.path.join("turns", f"live_turn_{int(time.time()*1000)}.wav")

    with wave.open(out_file, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(bytes_per_sample)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(audio_buffer))

    print(f"[Mic Input] Turn recorded and saved to '{out_file}'.")
    return out_file

if __name__ == "__main__":
    path = record_turn(max_seconds=5)
    print("Recorded file:", path)
