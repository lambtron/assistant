import os
import subprocess
import sys
import numpy as np

DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"
DEVICE = "default" if DEV_MODE else "plughw:3,0"
THRESHOLD = 0.7

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


def record_speech(duration=5):
    print(f"[RECORD] Recording {duration}s...", flush=True)
    if DEV_MODE:
        subprocess.run(
            ["rec", "-r", "16000", "-c", "1", "-b", "16", "/tmp/speech.wav", "trim", "0", str(duration)],
            capture_output=True,
        )
    else:
        subprocess.run(
            [
                "arecord", "-D", DEVICE, "-f", "S16_LE",
                "-r", "16000", "-c", "1", "-d", str(duration),
                "/tmp/speech.wav",
            ],
            capture_output=True,
        )
    print("[RECORD] Done", flush=True)
    return "/tmp/speech.wav"


def transcribe(path):
    print("[TRANSCRIBE] Sending to Groq...", flush=True)
    with open(path, "rb") as f:
        result = groq_client.audio.transcriptions.create(
            model="whisper-large-v3", file=f
        )
    print(f"[TRANSCRIBE] Result: {result.text}", flush=True)
    return result.text


def ask_claude(text):
    print("[CLAUDE] Asking Claude...", flush=True)
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
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