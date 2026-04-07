import os
import subprocess
import sys
import numpy as np

DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"
DEVICE = "default" if DEV_MODE else "plughw:3,0"
THRESHOLD = 0.9

print(f"[BOOT] Starting assistant (DEV_MODE={DEV_MODE}, DEVICE={DEVICE})", flush=True)

if not DEV_MODE:
    print("[BOOT] Loading wake word model...", flush=True)
    from openwakeword.model import Model
    wake_model = Model()
    print(f"[BOOT] Wake models loaded: {list(wake_model.models.keys())}", flush=True)

from groq import Groq
from anthropic import Anthropic

groq_client = Groq()
claude_client = Anthropic()

print("[BOOT] API clients initialized", flush=True)


def play_beep():
    print("[BEEP] Playing beep...", flush=True)
    if DEV_MODE:
        result = subprocess.run(["afplay", "beep.wav"], capture_output=True)
    else:
        result = subprocess.run(["aplay", "-D", DEVICE, "/home/admin/beep.wav"], capture_output=True)
    print(f"[BEEP] Exit code: {result.returncode}, stderr: {result.stderr.decode()}", flush=True)


def record_speech(max_duration=10, silence_threshold=500, silence_duration=1.5):
    """Record speech with silence detection to stop early."""
    print("[RECORD] Recording (will stop on silence)...", flush=True)

    # Start recording process
    if DEV_MODE:
        cmd = ["rec", "-r", "16000", "-c", "1", "-b", "16", "-t", "raw", "-"]
    else:
        cmd = ["arecord", "-D", DEVICE, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    # Read audio in chunks and detect silence
    chunk_size = 1600  # 0.1 seconds at 16kHz
    chunks = []
    silent_chunks = 0
    silence_chunks_needed = int(silence_duration / 0.1)
    max_chunks = max_duration * 10

    try:
        for i in range(max_chunks):
            data = proc.stdout.read(chunk_size * 2)  # 2 bytes per sample
            if not data:
                break

            chunks.append(data)

            # Check if this chunk is silent
            audio = np.frombuffer(data, dtype=np.int16)
            if np.abs(audio).mean() < silence_threshold:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed and i > 10:  # At least 1s of audio
                    print(f"[RECORD] Silence detected after {i * 0.1:.1f}s", flush=True)
                    break
            else:
                silent_chunks = 0
    finally:
        proc.terminate()
        proc.wait()

    # Save to file
    audio_data = b''.join(chunks)
    subprocess.run(
        ["sox", "-r", "16000", "-e", "signed", "-b", "16", "-c", "1", "-t", "raw", "-", "/tmp/speech.wav"],
        input=audio_data,
        capture_output=True
    )

    print(f"[RECORD] Done ({len(chunks) * 0.1:.1f}s recorded)", flush=True)
    return "/tmp/speech.wav"


def transcribe(path):
    print("[TRANSCRIBE] Sending to Groq...", flush=True)
    with open(path, "rb") as f:
        result = groq_client.audio.transcriptions.create(
            model="distil-whisper-large-v3-en", file=f
        )
    print(f"[TRANSCRIBE] Result: {result.text}", flush=True)
    return result.text


def ask_claude(text):
    print("[CLAUDE] Asking Claude...", flush=True)
    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system="You are a helpful voice assistant. Keep responses short and conversational — 1-2 sentences max.",
        messages=[{"role": "user", "content": text}],
    )
    reply = response.content[0].text
    print(f"[CLAUDE] Reply: {reply}", flush=True)
    return reply


def speak(text):
    print("[SPEAK] Speaking...", flush=True)
    if DEV_MODE:
        proc = subprocess.Popen(
            f'echo "{text}" | piper --model models/en_US-lessac-medium.onnx --output_raw | play -r 22050 -e signed -b 16 -c 1 -t raw -',
            shell=True,
        )
    else:
        proc = subprocess.Popen(
            f'echo "{text}" | piper --model ~/assistant/models/en_US-lessac-medium.onnx --output_raw | aplay -D {DEVICE} -f S16_LE -r 22050',
            shell=True,
        )
    proc.wait()
    print("[SPEAK] Done", flush=True)


def listen_wake_word():
    proc = subprocess.Popen(
        [
            "arecord", "-D", DEVICE, "-f", "S16_LE",
            "-r", "16000", "-c", "1", "-t", "raw",
        ],
        stdout=subprocess.PIPE,
    )
    return proc


def handle_interaction():
    play_beep()
    path = record_speech()
    text = transcribe(path)
    print(f"[YOU] {text}", flush=True)
    reply = ask_claude(text)
    print(f"[ASSISTANT] {reply}", flush=True)
    speak(reply)


def run_dev():
    print("Assistant ready! [DEV] Press Enter to speak, Ctrl+C to quit.", flush=True)
    try:
        while True:
            input("Press Enter to speak...")
            handle_interaction()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


def run_prod():
    print("Assistant ready! [PROD] Say 'Hey Jarvis' to start.", flush=True)

    proc = listen_wake_word()

    try:
        while True:
            data = proc.stdout.read(2 * 1280)
            if not data:
                print("[WARN] No audio data received", flush=True)
                break
            audio = np.frombuffer(data, dtype=np.int16)
            prediction = wake_model.predict(audio)
            for key, value in prediction.items():
                if value > THRESHOLD:
                    proc.terminate()
                    proc.wait()
                    print(f"[WAKE] Detected: {key} ({value:.2f})", flush=True)
                    handle_interaction()
                    proc = listen_wake_word()
                    break
    except KeyboardInterrupt:
        proc.terminate()
        print("\nStopped.", flush=True)


def main():
    if DEV_MODE:
        run_dev()
    else:
        run_prod()


if __name__ == "__main__":
    main()