#!/usr/bin/env bash
# Run once on the VM (Ubuntu 22.04) after cloning the repo.
# Usage: bash deploy/setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="personal-assistant"
VENV="$REPO_DIR/venv"
PYTHON="$VENV/bin/python"

echo "=== Installing system dependencies ==="
sudo apt-get update -q
sudo apt-get install -y python3.11 python3.11-venv python3-pip git ffmpeg \
    pkg-config libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libswscale-dev libswresample-dev libavfilter-dev

echo "=== Setting up Python virtualenv ==="
python3.11 -m venv "$VENV"
"$PYTHON" -m pip install --upgrade pip -q
"$PYTHON" -m pip install -r "$REPO_DIR/requirements.txt"

echo "=== Checking .env ==="
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    echo ""
    echo "!!! .env created from .env.example. Edit it before starting the bot:"
    echo "    nano $REPO_DIR/.env"
    echo ""
fi

echo "=== Installing systemd service ==="
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Personal Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=${REPO_DIR}
Environment=PATH=${VENV}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${PYTHON} ${REPO_DIR}/bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit your .env:  nano $REPO_DIR/.env"
echo "  2. Start the bot:   sudo systemctl start $SERVICE_NAME"
echo "  3. Check logs:      sudo journalctl -u $SERVICE_NAME -f"
echo "  4. Or tail file:    tail -f $REPO_DIR/bot.log"
