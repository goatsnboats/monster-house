"""Stage 0 Step 3's "done when", end to end through Mosquitto: a pretend kid moved on the
fake radar makes both eyes follow, using the placeholder gaze.

    fake radar model --ICD-002--> python -m brain --ICD-001 look--> both eyes' gaze

The eyes here are their state objects (eyes/state.py) fed by the real look messages,
without windows; the drawing itself is covered by the eye's own tests.

Uses the real radar and eye topics, so it briefly disturbs anything else listening on
the development broker. It removes the radar's retained messages afterwards.
Skipped if no broker is running.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from eyes.config import load_window
from eyes.state import EyeState
from shared import topics
from shared.messages import eye_commands as eyes
from shared.mqtt_client import connect, new_client
from shared.radar_frame import load_radar_site
from sim.radar_model import Kid, RadarModel
from tests.test_mqtt_integration import broker_is_running

REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(not broker_is_running(), reason="no MQTT broker on localhost:1883")]


def test_dragging_a_kid_makes_both_eyes_follow():
    site = load_radar_site()
    left, right = (EyeState(load_window(side).position_m) for side in ("left", "right"))
    looks: list = []
    got_look = threading.Condition()

    def on_message(_c, _u, msg):
        message = eyes.decode("look", msg.payload)
        with got_look:
            looks.append(message)
            got_look.notify_all()

    def wait_for(predicate, timeout=5.0):
        with got_look:
            return got_look.wait_for(lambda: any(predicate(m) for m in looks), timeout)

    eye_side = new_client("pytest-eyes")
    eye_side.on_message = on_message
    connect(eye_side)
    eye_side.subscribe(topics.EYES_LOOK)
    eye_side.loop_start()

    radar_side = new_client("pytest-radar")
    connect(radar_side)
    radar_side.loop_start()

    brain = subprocess.Popen([sys.executable, "-m", "brain", "--seconds", "15"], cwd=REPO_ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    model, kid = RadarModel(site), Kid(-1.1, 5.0)
    t = 0.0

    def radar_frames(n: int, kids) -> None:
        nonlocal t
        for _ in range(n):
            for topic, payload in model.frame(t, kids):
                radar_side.publish(topic, payload, qos=0, retain=True)
            t += 0.1
            time.sleep(0.1)

    try:
        time.sleep(1.0)                                   # let the brain connect
        radar_side.publish(topics.RADAR_STATUS, b"online", retain=True)

        # A kid on the sidewalk, to the left as seen from the street.
        radar_frames(5, [kid])
        assert wait_for(lambda m: isinstance(m, eyes.LookAt) and m.x == pytest.approx(-1.1, abs=0.01)), \
            "the brain never looked at the kid"
        for eye in (left, right):
            eye.look_at(_last_look(looks))
        left_before, right_before = left.gaze_target, right.gaze_target
        assert left_before[0] != pytest.approx(right_before[0])   # each eye has its own angle

        # Drag the kid across to the right: both eyes' irises move right.
        kid.x = 2.0
        radar_frames(5, [kid])
        assert wait_for(lambda m: isinstance(m, eyes.LookAt) and m.x == pytest.approx(2.0, abs=0.01))
        for eye in (left, right):
            eye.look_at(_last_look(looks))
        assert left.gaze_target[0] > left_before[0]
        assert right.gaze_target[0] > right_before[0]

        # The kid leaves: the eyes are told to wander.
        radar_frames(3, [])
        assert wait_for(lambda m: isinstance(m, eyes.LookIdle))
    finally:
        brain.kill()
        brain.wait(5)
        for topic in [*model.values, topics.RADAR_STATUS]:     # remove what we left retained
            radar_side.publish(topic, b"", qos=0, retain=True)
        time.sleep(0.2)
        for client in (radar_side, eye_side):
            client.disconnect()
            client.loop_stop()


def _last_look(looks) -> tuple[float, float, float]:
    last = [m for m in looks if isinstance(m, eyes.LookAt)][-1]
    return (last.x, last.y, last.z)
