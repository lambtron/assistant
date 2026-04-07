.PHONY: dev deploy setup-mac setup-pi setup

PI_USER = admin
PI_HOST = 192.168.86.32

# Run locally on Mac (uses built-in mic/speaker, press Enter to speak)
dev:
	DEV_MODE=1 python3 assistant.py

# Push to GitHub and deploy to Pi
deploy:
	git push origin main
	ssh $(PI_USER)@$(PI_HOST) "cd ~/assistant && git pull origin main && pip install -r requirements.txt --break-system-packages -q && sudo systemctl restart assistant"
	@echo "Deployed to Pi!"

# First-time Mac setup for local dev
setup-mac:
	brew install sox
	pip3 install groq anthropic numpy piper-tts
	mkdir -p models
	cd models && \
		[ -f en_US-lessac-medium.onnx ] || wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
		[ -f en_US-lessac-medium.onnx.json ] || wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
	sox -n beep.wav synth 0.3 sine 800 vol 0.5
	ssh-copy-id $(PI_USER)@$(PI_HOST)
	@echo "Mac setup complete! Run 'make dev' to start locally, 'make deploy' to deploy."

# Run setup directly on the Pi
setup:
	bash scripts/setup.sh

# Run setup on Pi via SSH from Mac
setup-pi:
	ssh $(PI_USER)@$(PI_HOST) "cd ~/assistant && bash scripts/setup.sh"