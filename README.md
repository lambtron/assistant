# Assistant

A voice-activated desk assistant powered by Claude, running on a Raspberry Pi.
Say "Hey Jarvis" and ask anything — it listens, thinks, and speaks back.

**Wake word** → **Listen** → **Transcribe** → **Think** → **Speak**

## Stack

| Layer         | Technology             | Runs on    |
| ------------- | ---------------------- | ---------- |
| Wake word     | OpenWakeWord           | Local (Pi) |
| Transcription | Groq Whisper API       | Cloud      |
| Intelligence  | Claude API (Anthropic) | Cloud      |
| TTS           | Piper                  | Local (Pi) |

## Hardware

| Item                                | Notes                                        | Cost |
| ----------------------------------- | -------------------------------------------- | ---- |
| Raspberry Pi 4 Model B (2GB+ RAM)   | Any Pi 4 works; 2GB is sufficient            | ~$35 |
| ReSpeaker XVF3800 with Case         | USB-C mic array with built-in speaker output | ~$50 |
| Mono Enclosed Speaker 4R 5W (Seeed) | Connects to ReSpeaker's 3.5mm jack           | ~$6  |
| USB-C to USB-A cable                | **Must be a data cable**, not power-only     | —    |
| microSD card (16GB+)                | For Raspberry Pi OS                          | —    |
| USB-C power supply for Pi           | 5V 3A recommended                            | —    |

## API Keys

You'll need free accounts and API keys from:

- [Groq](https://console.groq.com) — for Whisper speech-to-text
- [Anthropic](https://console.anthropic.com) — for Claude

## Build Guide

### 1. Flash the Pi

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your
   computer
2. Insert the microSD card into your computer
3. Open the Imager and select:
   - **Device**: Raspberry Pi 4
   - **OS**: Raspberry Pi OS (other) → **Raspberry Pi OS Lite (64-bit)**
   - **Storage**: Your microSD card
4. Click the **settings/gear icon** before writing and configure:
   - **Hostname**: `raspberrypi`
   - **Username and password**: Choose something memorable
   - **Wi-Fi**: Enter your home network SSID and password (use 2.4GHz if your
     router has separate bands)
   - **SSH**: Enable with password authentication
5. Flash the card

### 2. Boot and Connect

1. Insert the microSD card into the Pi (slot on the underside)
2. Plug in power via USB-C — wait about 60 seconds for first boot
3. From your computer, find the Pi on your network:
   ```bash
   ping raspberrypi.local
   # or scan your network
   arp -a | grep raspberry
   ```
4. SSH in:
   ```bash
   ssh yourusername@raspberrypi.local
   ```

### 3. Connect the Hardware

1. Plug the ReSpeaker XVF3800 into the Pi via USB-C to USB-A cable — use a
   **blue USB 3.0 port**
2. Plug the mono speaker into the ReSpeaker's 3.5mm audio jack
3. Verify the ReSpeaker is detected:
   ```bash
   lsusb
   # Should show: Seeed Technology Co., Ltd. reSpeaker XVF3800 4-Mic Array

   arecord -l
   # Should list the ReSpeaker as a capture device

   aplay -l
   # Should list the ReSpeaker as a playback device
   ```
4. Test recording and playback:
   ```bash
   # Record 5 seconds
   arecord -D plughw:3,0 -f S16_LE -r 16000 -d 5 test.wav
   # Play it back (you should hear yourself)
   aplay -D plughw:3,0 test.wav
   ```

> **Note**: If the ReSpeaker doesn't show up in `lsusb`, try a different USB
> cable. Some USB-C cables are power-only and don't carry data.

### 4. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip sox
pip install openwakeword groq anthropic numpy piper-tts --break-system-packages
```

### 5. Download the Piper Voice Model

```bash
mkdir -p ~/piper-models
cd ~/piper-models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### 6. Generate the Beep Sound

```bash
sox -n ~/beep.wav synth 0.3 sine 800 vol 0.5
```

Test it:

```bash
aplay -D plughw:3,0 ~/beep.wav
```

### 7. Adjust Speaker Volume

```bash
alsamixer
# Press F6, select reSpeaker XVF3800, raise volume with arrow keys
# Press Escape to exit
sudo alsactl store
```

### 8. Clone and Configure

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/assistant.git
```

Create your environment file:

```bash
cat << EOF > ~/.assistant.env
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
EOF
```

### 9. Test It

```bash
cd ~/assistant
source ~/.assistant.env
export GROQ_API_KEY ANTHROPIC_API_KEY
python3 assistant.py
```

Say "Hey Jarvis", wait for the beep, then ask a question. You should hear Claude
respond through the speaker.

### 10. Run on Boot

Install the systemd service so it starts automatically:

```bash
sudo cp ~/assistant/scripts/assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable assistant
sudo systemctl start assistant
```

Now the assistant starts whenever the Pi is powered on. Check status with:

```bash
sudo systemctl status assistant
journalctl -u assistant -f   # live logs
```

## Local Development (Mac)

You can run the assistant locally on your Mac for faster iteration.

### One-time setup:

```bash
make setup-mac
```

This installs sox, Python dependencies, downloads the Piper voice model, and
generates the beep sound.

### Run locally:

```bash
make dev
```

This uses your Mac's built-in mic and speaker instead of the ReSpeaker.

### Deploy to Pi:

```bash
make deploy
```

This pushes to GitHub and SSHs into the Pi to pull the latest code and restart
the service.

## Troubleshooting

**ReSpeaker not detected**: Try a different USB-C to USB-A cable. Many cables
are power-only. The ReSpeaker LED will light up even with a power-only cable, so
don't rely on that.

**Can't SSH into Pi**: Make sure your computer and Pi are on the same Wi-Fi
network. Try `arp -a` to find the Pi's IP address. If it doesn't appear,
re-flash the SD card and double-check the Wi-Fi credentials.

**Audio too quiet**: Run `alsamixer`, select the ReSpeaker (F6), and raise the
volume. Save with `sudo alsactl store`.

**Wake word too sensitive**: Adjust the `THRESHOLD` value in `assistant.py` —
raise it toward `0.8` or `0.9` to reduce false triggers.

**GPU warnings in console**: Ignore any `onnxruntime` GPU/CUDA warnings — the Pi
has no GPU, so it falls back to CPU automatically.

**SD card shows wrong size**: If your microSD shows a tiny size (e.g. 42MB) on
your computer, it likely has a leftover Linux partition. Use Disk Utility (Mac)
or Raspberry Pi Imager's Erase option to reformat it.

## Shutting Down

Always shut down the Pi cleanly to avoid SD card corruption:

```bash
sudo shutdown now
```

Wait for the green LED to stop blinking before unplugging power.
