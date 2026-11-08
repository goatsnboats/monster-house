#!/usr/bin/env bash
# Run the Monster House development broker in this terminal (Ctrl+C to stop).
# Uses mosquitto-dev.conf from this folder: localhost:1883, no password.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$HERE/mosquitto-dev.conf"
MOSQUITTO="${MOSQUITTO_BIN:-mosquitto}"   # override to use a different binary
PORT=1883

if ! command -v "$MOSQUITTO" >/dev/null 2>&1 && [ ! -x "$MOSQUITTO" ]; then
    echo "Mosquitto is not installed. Install it with:"
    echo "    sudo apt install mosquitto mosquitto-clients"
    exit 1
fi

if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q .; then
    echo "Something is already listening on port $PORT."
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        echo "It's the system Mosquitto service that apt installed. Stop it with:"
        echo "    sudo systemctl disable --now mosquitto"
        echo "(or just use it: its default settings are also localhost:$PORT, no password)."
    fi
    exit 1
fi

echo "Starting Mosquitto with $CONF  (Ctrl+C to stop)"
exec "$MOSQUITTO" -c "$CONF"
