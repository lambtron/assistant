#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip sox

echo "Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages

echo "Downloading Piper voice model..."
mkdir -p ~/assistant/models
cd ~/assistant/models
if [ ! -f en_US-lessac-medium.onnx ]; then
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
fi

echo "Generating beep sound..."
sox -n ~/beep.wav synth 0.3 sine 800 vol 0.5

echo "Installing systemd service..."
sudo cp ~/assistant/scripts/assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable assistant

sudo systemctl start assistant
echo "Setup complete! Assistant is running."
