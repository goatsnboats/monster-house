"""The eye's MQTT link (ICD-001): the brain's messages in, this eye's online/offline out.

paho-mqtt runs its network loop in its own thread. Each message is decoded and checked
there with the shared message classes (shared/messages, ADR 0003); good ones wait in a
queue, and the drawing loop applies them once per frame with `apply()`. So the eye's
state is only ever touched by the drawing thread.

Fail friendly (SYS-017, EYE-015): if the broker isn't there, the eye keeps drawing and
looks after itself, and paho keeps trying to reconnect. A bad message is logged and
dropped. The broker announces "offline" for us (MQTT last-will) if the eye vanishes.
"""

from __future__ import annotations

import logging
import queue

from eyes.state import EyeState
from shared import topics
from shared.messages import eye_commands as eyes
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, new_client

log = logging.getLogger(__name__)

# What the eye listens to, and which ICD-001 message each topic carries.
LISTENS_TO = {
    topics.EYES_LOOK: "look",
    topics.EYES_EXPRESSION: "expression",
    topics.EYES_BLINK: "blink",
    topics.THEME: "theme",
}
STATUS_QOS = 1      # ICD-001: status is QoS 1, retained
RECONNECT_S = (1, 10)


class EyeLink:
    def __init__(self, side: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host, self.port = host, port
        self.status_topic = topics.eye_status(side)
        self.inbox: queue.Queue = queue.Queue()
        self.connected = False
        self.client = new_client(f"eye-{side}")
        # If this eye disappears without saying goodbye, the broker says it for us.
        self.client.will_set(self.status_topic, eyes.encode("status", "offline"), qos=STATUS_QOS, retain=True)
        self.client.reconnect_delay_set(*RECONNECT_S)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        """Connect in the background; keeps retrying if the broker isn't up yet."""
        self.client.connect_async(self.host, self.port)
        self.client.loop_start()

    def stop(self) -> None:
        """Say goodbye ("offline") and disconnect."""
        if self.connected:
            info = self.client.publish(self.status_topic, eyes.encode("status", "offline"),
                                       qos=STATUS_QOS, retain=True)
            info.wait_for_publish(timeout=2)
        self.connected = False                 # a goodbye, not a lost broker
        self.client.disconnect()
        self.client.loop_stop()

    def messages(self) -> list[tuple[str, object, bool]]:
        """Everything received since the last call: (message name, message, retained)."""
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    # ── paho callbacks (network thread) ───────────────────────────────────────────

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            log.warning("broker refused the connection: %s", reason_code)
            return
        self.connected = True
        log.info("connected to %s:%d", self.host, self.port)
        client.subscribe([(topic, 1) for topic in LISTENS_TO])
        client.publish(self.status_topic, eyes.encode("status", "online"), qos=STATUS_QOS, retain=True)

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties) -> None:
        if self.connected:
            log.warning("lost the broker (%s); looking after myself until it's back", reason_code)
        self.connected = False

    def _on_message(self, _client, _userdata, msg) -> None:
        name = LISTENS_TO.get(msg.topic)
        if name is None:
            return
        message = eyes.decode(name, msg.payload)      # None, and logged, if it breaks ICD-001
        if message is not None:
            self.inbox.put((name, message, bool(msg.retain)))


def apply(state: EyeState, name: str, message, retained: bool, on_theme) -> None:
    """Act on one brain message (drawing thread). `on_theme(name)` switches the theme."""
    if name == "look":
        if isinstance(message, eyes.LookAt):
            state.look_at((message.x, message.y, message.z))
        else:
            state.look_idle()
    elif name == "expression":
        state.set_expression(message.name, message.ms)
    elif name == "blink":
        state.blink(message.ms)
    elif name == "theme":
        on_theme(message.name)
    # A retained message (the theme, kept by the broker) doesn't mean the brain is here now.
    if not retained:
        state.heard_from_brain()
