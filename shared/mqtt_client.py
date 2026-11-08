"""Small helpers for connecting to the Monster House MQTT broker (paho-mqtt 2.x)."""

from __future__ import annotations

import uuid

import paho.mqtt.client as mqtt

# The Stage 0 development broker (deploy/mosquitto/mosquitto-dev.conf).
# Components will take the broker address from their YAML config later.
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1883


def new_client(name: str) -> mqtt.Client:
    """Create an MQTT client with a readable, unique client id like 'mqtt-tool-1a2b3c'.

    The id must be unique: the broker disconnects an older client if a new one
    connects with the same id.
    """
    client_id = f"{name}-{uuid.uuid4().hex[:6]}"
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)


class BrokerUnreachable(Exception):
    """Raised when nothing answers at the broker's host and port."""


def connect(client: mqtt.Client, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Connect, turning low-level socket errors into one friendly message."""
    try:
        client.connect(host, port)
    except OSError as err:
        raise BrokerUnreachable(
            f"Can't reach the MQTT broker at {host}:{port} ({err.strerror or err}). "
            "Is it running? Start it with deploy/mosquitto/run-dev.sh"
        ) from err
