#!/bin/bash
set -e

APP_DIR="/home/admin/assistant"

cd "$APP_DIR"
git pull origin main
pip install -r requirements.txt --break-system-packages -q
sudo systemctl restart assistant

echo "Deploy complete!"
