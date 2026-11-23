"""The eye's MQTT link (eyes/link.py): brain messages in, online/offline out (ICD-001)."""

from __future__ import annotations

import random
import socket
import threading
import time
from types import SimpleNamespace

import pytest

from eyes.expressions import EXPRESSIONS
from eyes.link import LISTENS_TO, EyeLink, apply
from eyes.state import EyeState
from shared import topics
from shared.messages import eye_commands as eyes
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, connect, new_client


def fresh_state() -> EyeState:
    return EyeState((1.0, 4.0, 0.0), rng=random.Random(1))


# ── apply(): each message does what ICD-001 says ─────────────────────────────────────

def test_look_at_a_point_stops_wandering():
    state = fresh_state()
    apply(state, "look", eyes.LookAt(x=3.0, y=1.0, z=2.0), False, print)
    assert not state.idle
    assert state.gaze_target != (0.0, 0.0)


def test_look_idle_wanders():
    state = fresh_state()
    apply(state, "look", eyes.LookAt(x=3.0, y=1.0, z=2.0), False, print)
    apply(state, "look", eyes.LookIdle(mode="idle"), False, print)
    assert state.idle


def test_expression_eases_in():
    state = fresh_state()
    apply(state, "expression", eyes.Expression(name="happy", ms=300), False, print)
    state.update(0.5)
    assert state.expression() == EXPRESSIONS["happy"]


def test_blink_closes_the_eye_halfway_through():
    state = fresh_state()
    apply(state, "blink", eyes.Blink(ms=200), False, print)
    frame = state.update(0.1)
    assert frame.expression.open == pytest.approx(0.0, abs=0.01)


def test_theme_calls_back():
    seen = []
    apply(fresh_state(), "theme", eyes.Theme(name="christmas"), False, seen.append)
    assert seen == ["christmas"]


def test_a_live_message_means_the_brain_is_here_but_a_retained_one_does_not():
    state = fresh_state()
    state.update(10.0)                                       # long silence: fallback mode
    apply(state, "theme", eyes.Theme(name="halloween"), True, lambda name: None)
    assert not state.brain_present                           # the broker's stored copy
    apply(state, "blink", eyes.Blink(ms=180), False, print)
    assert state.brain_present


# ── The network side, without a broker ──────────────────────────────────────────────

def fake_msg(topic: str, payload: bytes, retain: bool = False):
    return SimpleNamespace(topic=topic, payload=payload, retain=retain)


def test_good_messages_queue_and_bad_ones_are_dropped():
    link = EyeLink("left")
    link._on_message(None, None, fake_msg(topics.EYES_BLINK, b'{"ms": 180}'))
    link._on_message(None, None, fake_msg(topics.EYES_BLINK, b'{"ms": "fast"}'))         # breaks ICD-001
    link._on_message(None, None, fake_msg(topics.EYES_EXPRESSION, b"not json"))
    link._on_message(None, None, fake_msg(topics.STATE, b"asleep"))                     # not for the eyes
    link._on_message(None, None, fake_msg(topics.THEME, b'{"name": "halloween"}', retain=True))
    assert link.messages() == [("blink", eyes.Blink(ms=180), False),
                               ("theme", eyes.Theme(name="halloween"), True)]
    assert link.messages() == []


def test_listens_to_every_brain_to_eye_message():
    assert set(LISTENS_TO.values()) == set(eyes.SCHEMAS) - {"status"}


# ── With the real broker (skipped if none is running) ───────────────────────────────

def broker_is_running() -> bool:
    try:
        with socket.create_connection((DEFAULT_HOST, DEFAULT_PORT), timeout=0.5):
            return True
    except OSError:
        return False


needs_broker = pytest.mark.skipif(not broker_is_running(), reason="no MQTT broker on localhost:1883")


class StatusWatcher:
    """Another client watching an eye's status topic, like the brain will."""

    def __init__(self, side: str) -> None:
        self.seen: list[str] = []
        self.changed = threading.Condition()
        self.client = new_client("pytest-status")
        self.client.on_message = self._on_message
        connect(self.client)
        self.client.loop_start()
        self.client.subscribe(topics.eye_status(side), qos=1)

    def _on_message(self, _c, _u, msg) -> None:
        with self.changed:
            self.seen.append(eyes.decode("status", msg.payload))
            self.changed.notify_all()

    def wait_for(self, status: str, timeout: float = 5) -> bool:
        with self.changed:
            return self.changed.wait_for(lambda: self.seen and self.seen[-1] == status, timeout)

    def close(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()


def wait_for_messages(link: EyeLink, timeout: float = 5) -> list:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        got = [m for m in link.messages() if not m[2]]       # ignore retained ones (the theme)
        if got:
            return got
        time.sleep(0.02)
    return []


@pytest.mark.integration
@needs_broker
def test_online_then_commands_then_offline():
    watcher = StatusWatcher("right")
    link = EyeLink("right")
    try:
        link.start()
        assert watcher.wait_for("online"), watcher.seen
        talker = new_client("pytest-brain")
        connect(talker)
        talker.loop_start()
        talker.publish(topics.EYES_BLINK, eyes.encode("blink", eyes.Blink(ms=180)), qos=1).wait_for_publish(5)
        assert wait_for_messages(link) == [("blink", eyes.Blink(ms=180), False)]
        talker.disconnect()
        talker.loop_stop()
    finally:
        link.stop()
    assert watcher.wait_for("offline"), watcher.seen
    watcher.close()


@pytest.mark.integration
@needs_broker
def test_the_broker_says_offline_if_the_eye_vanishes():
    """MQTT last-will: the eye's connection just drops (a crash, the Pi unplugged)."""
    watcher = StatusWatcher("left")
    link = EyeLink("left")
    link.start()
    try:
        assert watcher.wait_for("online"), watcher.seen
        link.client.loop_stop()                  # stop paho, then cut the connection dead
        link.client.socket().close()
        assert watcher.wait_for("offline", timeout=10), watcher.seen
    finally:
        watcher.close()
