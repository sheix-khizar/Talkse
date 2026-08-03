"""
Standalone mic/VAD diagnostic. Run this directly (not through conversation_loop.py)
to see exactly what's happening to your audio frame-by-frame while you talk:
- real input amplitude (RMS)
- webrtcvad's is_speech decision at multiple aggressiveness modes

Run it, talk normally for the whole 8 seconds (including natural pauses between
words/sentences like you would in a real turn), then read the printed summary.

Usage:
    python debug_vad.py
"""
import time
import numpy as np
import sounddevice as sd
import webrtcvad

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
DURATION_SECONDS = 8

vads = {mode: webrtcvad.Vad(mode) for mode in (0, 1, 2, 3)}

frame_log = []  # (frame_index, rms, {mode: is_speech})


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Mic Warning] {status}", flush=True)

    samples_float = indata[:, 0]
    rms = float(np.sqrt(np.mean(samples_float.astype(np.float64) ** 2)))

    pcm_bytes = (samples_float * 32767).astype(np.int16).tobytes()

    if len(pcm_bytes) != FRAME_SAMPLES * 2:
        frame_log.append((len(frame_log), rms, None))  # malformed frame, flag it
        return

    decisions = {}
    for mode, vad in vads.items():
        try:
            decisions[mode] = vad.is_speech(pcm_bytes, SAMPLE_RATE)
        except Exception as e:
            decisions[mode] = f"ERROR: {e}"

    frame_log.append((len(frame_log), rms, decisions))


def main():
    print(f"Listing input devices (default marked with '>'):")
    print(sd.query_devices())
    default_in = sd.default.device[0]
    print(f"\nUsing default input device index: {default_in}")
    print(f"\nRecording for {DURATION_SECONDS}s at {SAMPLE_RATE}Hz. Talk normally, including pauses.")
    print("Starting in 1 second...")
    time.sleep(1)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                         blocksize=FRAME_SAMPLES, callback=audio_callback):
        time.sleep(DURATION_SECONDS)

    print(f"\nCaptured {len(frame_log)} frames.\n")

    malformed = [f for f in frame_log if f[2] is None]
    if malformed:
        print(f"WARNING: {len(malformed)} frames were malformed (wrong byte length) — "
              f"this alone can break VAD/streaming reliably. Check your audio device's "
              f"reported sample rate/channels match SAMPLE_RATE=16000, channels=1.\n")

    valid = [f for f in frame_log if f[2] is not None]
    if not valid:
        print("No valid frames captured — check your microphone/device selection above.")
        return

    rms_values = [f[1] for f in valid]
    print(f"RMS amplitude — min: {min(rms_values):.5f}  max: {max(rms_values):.5f}  avg: {sum(rms_values)/len(rms_values):.5f}")
    print("(For reference: near-silence is usually well under 0.01. A normal speaking "
          "voice close to a laptop mic is often in the 0.02-0.2+ range, but this varies "
          "a lot by device/gain — compare min vs max above rather than trusting fixed numbers.)\n")

    for mode in (0, 1, 2, 3):
        speech_frames = sum(1 for f in valid if f[2].get(mode) is True)
        pct = 100 * speech_frames / len(valid)
        print(f"VAD mode {mode}: {speech_frames}/{len(valid)} frames flagged as speech ({pct:.1f}%)")

    print("\nPer-frame detail (frame_index, rms, mode0, mode1, mode2, mode3):")
    for idx, rms, decisions in valid:
        row = " ".join(f"m{m}={str(decisions[m])[0]}" for m in (0, 1, 2, 3))
        print(f"  {idx:4d}  rms={rms:.5f}  {row}")


if __name__ == "__main__":
    main()
