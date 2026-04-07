#!/bin/bash
git push origin main
ssh admin@192.168.86.32 "cd ~/assistant && git pull origin main && pip install -r requirements.txt --break-system-packages -q && sudo systemctl restart assistant"
echo "Deployed to Pi!"
