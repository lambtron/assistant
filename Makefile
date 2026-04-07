.PHONY: dev deploy setup-mac setup-pi

# Run locally on Mac (uses built-in mic/speaker)
dev:
	DEV_MODE=1 python3 assistant.py

# Push to GitHub and deploy to Pi
deploy:
	git push origin main
	ssh admin@192.168.86.32 "cd ~/assistant && git pull origin main && pip install -r requirements.txt --break-system-packages -q && sudo systemctl restart assistant"
	@echo "Deployed to Pi!"

# First-time Mac setup for local dev
setup-mac:
	brew install sox
	pip3 install -r requirements.txt
	mkdir -p models
	cd models && \
		[ -f en_US-lessac-medium.onnx ] || wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx && \
		[ -f en_US-lessac-medium.onnx.json ] || wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
	sox -n beep.wav synth 0.3 sine 800 vol 0.5
	@echo "Mac setup complete! Run 'make dev' to start."

# First-time Pi setup (run via SSH)
setup-pi:
	ssh admin@192.168.86.32 "cd ~/assistant && bash scripts/setup.sh"
