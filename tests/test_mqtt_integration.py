"""End-to-end: a message published by one client arrives at another through Mosquitto.

Needs the development broker on localhost:1883 (deploy/mosquitto/run-dev.sh).
If nothing is listening there, these tests are skipped, not failed.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import pytest

from shared import topics
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, connect, new_client

REPO_ROOT = Path(__file__).resolve().parent.parent


def broker_is_running() -> bool:
    try:
        with socket.create_connection((DEFAULT_HOST, DEFAULT_PORT), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not broker_is_running(),
        reason=f"no MQTT broker on {DEFAULT_HOST}:{DEFAULT_PORT} (start deploy/mosquitto/run-dev.sh)",
    ),
]


def unique_test_topic() -> str:
    """A fresh topic under monster/debug/test, so parallel or stray messages can't interfere."""
    return f"{topics.DEBUG_TEST}/{uuid.uuid4().hex[:8]}"


def test_message_between_two_clients():
    topic = unique_test_topic()
    sent = {"test": "hello from pytest", "id": uuid.uuid4().hex}  # TBD-003: plain dict until schemas exist
    received: list[dict] = []
    subscribed = threading.Event()
    arrived = threading.Event()

    def on_subscribe(*_args):
        subscribed.set()

    def on_message(_client, _userdata, msg):
        received.append(json.loads(msg.payload))
        arrived.set()

    listener = new_client("pytest-sub")
    listener.on_subscribe = on_subscribe
    listener.on_message = on_message
    connect(listener)
    listener.loop_start()

    talker = new_client("pytest-pub")
    connect(talker)
    talker.loop_start()
    try:
        listener.subscribe(topic, qos=1)
        assert subscribed.wait(5), "subscription was not confirmed"

        talker.publish(topic, json.dumps(sent), qos=1).wait_for_publish(timeout=5)

        assert arrived.wait(5), "message did not arrive"
        assert received == [sent]
    finally:
        for client in (talker, listener):
            client.disconnect()
            client.loop_stop()


def test_message_between_two_programs():
    """The debug tool, run as two separate programs: `sub` receives what `pub` sends."""
    topic = unique_test_topic()
    payload = json.dumps({"test": "hello between programs", "id": uuid.uuid4().hex})  # TBD-003
    tool = [sys.executable, "-m", "shared.mqtt_tool"]

    sub = subprocess.Popen(
        [*tool, "sub", topic, "--count", "1", "--timeout", "10"],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        # Wait until the subscriber says it is subscribed, then publish.
        ready_line = sub.stderr.readline()
        assert ready_line.startswith("subscribed:"), ready_line

        pub = subprocess.run(
            [*tool, "pub", topic, payload],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        assert pub.returncode == 0, pub.stderr

        out, err = sub.communicate(timeout=10)
    finally:
        if sub.poll() is None:
            sub.kill()

    assert sub.returncode == 0, err
    assert out.strip() == f"{topic} {payload}"
