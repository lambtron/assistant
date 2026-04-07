import os
import subprocess
import numpy as np
from openwakeword.model import Model
from groq import Groq
from anthropic import Anthropic

wake_model = Model()
groq_client = Groq()
claude_client = Anthropic()

DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"
DEVICE = "default" if DEV_MODE else "plughw:3,0"
THRESHOLD = 0.7


def play_beep():
    if DEV_MODE:
        subprocess.run(["afplay", "beep.wav"], capture_output=True)
    else:
        subprocess.run(["aplay", "-D", DEVICE, "/home/admin/beep.wav"], capture_output=True)


def record_speech(duration=5):
    print("Listening...")
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
    return "/tmp/speech.wav"


def transcribe(path):
    with open(path, "rb") as f:
        result = groq_client.audio.transcriptions.create(
            model="whisper-large-v3", file=f
        )
    return result.text


def ask_claude(text):
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system="You are a helpful voice assistant. Keep responses short and conversational — 1-2 sentences max.",
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text


def speak(text):
    if DEV_MODE:
        proc = subprocess.Popen(
            f'echo "{text}" | piper --model piper-models/en_US-lessac-medium.onnx --output_raw | play -r 22050 -e signed -b 16 -c 1 -t raw -',
            shell=True,
        )
    else:
        proc = subprocess.Popen(
            f'echo "{text}" | piper --model ~/piper-models/en_US-lessac-medium.onnx --output_raw | aplay -D {DEVICE} -f S16_LE -r 22050',
            shell=True,
        )
    proc.wait()


def listen_wake_word():
    if DEV_MODE:
        proc = subprocess.Popen(
            ["rec", "-r", "16000", "-c", "1", "-b", "16", "-t", "raw", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            [
                "arecord", "-D", DEVICE, "-f", "S16_LE",
                "-r", "16000", "-c", "1", "-t", "raw",
            ],
            stdout=subprocess.PIPE,
        )
    return proc


def main():
    mode = "DEV" if DEV_MODE else "PROD"
    print(f"Assistant ready! [{mode}] Say 'Hey Jarvis' to start.")

    proc = listen_wake_word()

    try:
        while True:
            data = proc.stdout.read(2 * 1280)
            if not data:
                break
            audio = np.frombuffer(data, dtype=np.int16)
            prediction = wake_model.predict(audio)
            for key, value in prediction.items():
                if value > THRESHOLD:
                    proc.terminate()
                    proc.wait()
                    print("Wake word detected!")
                    play_beep()
                    path = record_speech()
                    text = transcribe(path)
                    print(f"You: {text}")
                    reply = ask_claude(text)
                    print(f"Assistant: {reply}")
                    speak(reply)
                    proc = listen_wake_word()
                    break
    except KeyboardInterrupt:
        proc.terminate()
        print("\nStopped.")


if __name__ == "__main__":
    main()
