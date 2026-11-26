"""The phone page (ICD-004; SHW-019, SHW-020, SHW-021, SHW-023, SHW-030, SHW-031): the web
server, the buttons in the brain, and a press reaching the eyes within half a second."""

from __future__ import annotations

import datetime as dt
import json
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from brain import phone
from brain.core import BUTTONS, COSTUME_S
from brain.moods import Mood
from shared import topics
from shared.messages import eye_commands as eyes
from shared.messages import phone_page as icd
from sim.pretend_visit import Visit, walk

REPO_ROOT = Path(__file__).resolve().parent.parent
NOON = dt.datetime(2027, 10, 31, 12, 0)        # outside the show hours


# ── The web server ──────────────────────────────────────────────────────────────

@pytest.fixture
def page():
    inbox: queue.Queue = queue.Queue()
    p = phone.PhonePage(inbox, port=0)
    p.set_state({"mood": "watching", "muted": False, "theme": "halloween", "themes": ["halloween"]})
    p.start()
    yield p, inbox, f"http://127.0.0.1:{p.port}"
    p.stop()


def request(url: str, body: dict | bytes | None = None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def test_the_page_has_every_button(page):
    _, _, url = page
    status, body = request(url + "/")
    assert status == 200
    for name in BUTTONS:
        assert f'data-name="{name}"' in body.decode()


def test_state_follows_icd_004(page):
    _, _, url = page
    status, body = request(url + "/api/state")
    assert status == 200
    assert icd.decode("state", body) == icd.State("watching", False, "halloween", ["halloween"])


def test_a_button_goes_to_the_brains_inbox(page):
    _, inbox, url = page
    for name in BUTTONS:
        assert request(url + "/api/button", {"name": name})[0] == 204
        assert inbox.get_nowait() == ("button", name)


@pytest.mark.parametrize("path, body", [
    ("/api/button", {"name": "explode"}),
    ("/api/button", b"not json"),
    ("/api/theme", {"name": "no-such-theme"}),
    ("/api/button", b"x" * 5000),
])
def test_bad_requests_are_refused_and_nothing_happens(page, path, body):
    _, inbox, url = page
    assert request(url + path, body)[0] == 400
    assert inbox.empty()


def test_a_known_theme_is_accepted(page):
    _, inbox, url = page
    assert request(url + "/api/theme", {"name": "halloween"})[0] == 204
    assert inbox.get_nowait() == ("theme", "halloween")


def test_only_this_computer_can_reach_it():
    assert phone.HOST == "127.0.0.1"


# ── The buttons in the brain ────────────────────────────────────────────────────

def expressions(outs):
    return [eyes.decode("expression", o.payload).name for o in outs if o.topic == topics.EYES_EXPRESSION]


def clips(outs):
    return [n for o in outs if (n := topics.fpp_playlist_from_start(o.topic))]


def test_mute_stops_the_voice_but_not_the_eyes(tmp_path):
    v = Visit(tmp_path)
    v.brain.press("mute", v.t)
    v.run(15, lambda t: [walk(1.0, 5.5, 2.0, t0=0)(t)])
    assert v.moods()[-1] == "watching" and v.clips() == []
    assert v.brain.state()["muted"]
    v.brain.press("unmute", v.t)
    assert not v.brain.state()["muted"]


def test_sleep_now_holds_it_asleep_even_with_a_kid_coming(tmp_path):
    v = Visit(tmp_path)
    v.run(12, lambda t: [walk(1.0, 5.5, 2.0, t0=0)(t)])
    v.brain.press("sleep", v.t)
    assert v.brain.moods.mood is Mood.ASLEEP
    v.run(10, lambda t: [walk(-1.0, 5.5, 2.0, t0=12)(t)])
    assert v.brain.moods.mood is Mood.ASLEEP


def test_wake_now_works_outside_show_hours_until_sleep_now(tmp_path):
    v = Visit(tmp_path)
    v.brain.any_time = False
    out = []
    for i in range(30):                                # noon: stays asleep
        out += v.brain.tick(i * 0.1, NOON)
    assert v.brain.moods.mood is Mood.ASLEEP
    v.brain.press("wake", 3.0)
    assert v.brain.moods.mood is Mood.WAKING
    for i in range(31, 200):                           # still noon: carries on through its moods
        v.brain.tick(i * 0.1, NOON)
    assert v.brain.moods.mood is not Mood.WAKING
    v.brain.press("sleep", 20.0)
    assert v.brain.moods.mood is Mood.ASLEEP and v.brain.hold == "sleep"


def test_great_costume_sparkles_then_goes_back(tmp_path):
    v = Visit(tmp_path)
    v.run(12, lambda t: [walk(1.0, 5.5, 2.0, t0=0)(t)])
    out = v.brain.press("costume", v.t)
    assert expressions(out) == ["sparkle"]
    assert clips(out)[0].startswith("costume_")
    t0 = v.t
    v.run(3.5, lambda t: [walk(1.0, 5.5, 2.0, t0=0)(t)])
    assert v.expressions(since=t0 + 0.1)[-1] == "happy"


def test_the_owners_clips_skip_the_gap_and_cut_in(tmp_path):
    v = Visit(tmp_path)
    v.brain.voice.say("comment", 0.0)                  # a clip playing
    v.brain.voice.take_starts()
    out = v.brain.press("burp", 0.5)
    assert clips(out) == ["burp_01"]


def test_muted_buttons_say_nothing(tmp_path):
    v = Visit(tmp_path)
    v.brain.press("mute", 0.0)
    assert clips(v.brain.press("burp", 0.1)) == []


def test_sing_with_no_songs_does_nothing(tmp_path):
    v = Visit(tmp_path)
    assert v.brain.press("sing", 0.0) == []           # the Halloween sing pool is empty


def test_choosing_a_theme_tells_the_eyes(tmp_path):
    v = Visit(tmp_path)
    (out,) = v.brain.set_theme("halloween")
    assert out.topic == topics.THEME and out.retain
    assert v.brain.set_theme("no-such-theme") == []


# ── Within half a second, end to end (SYS-023, SHW-023) ─────────────────────────

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.integration
def test_a_press_on_the_phone_reaches_the_eyes_within_half_a_second():
    from tests.test_mqtt_integration import broker_is_running
    if not broker_is_running():
        pytest.skip("no MQTT broker on localhost:1883")
    from shared.mqtt_client import connect, new_client

    port = _free_port()
    brain = subprocess.Popen([sys.executable, "-m", "brain", "--any-time", "--phone-port", str(port),
                              "--seconds", "20"], cwd=REPO_ROOT, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    seen = threading.Event()
    got: list[float] = []

    def on_message(_c, _u, msg):
        m = eyes.decode("expression", msg.payload)
        if m is not None and m.name == "sparkle":
            got.append(time.perf_counter())
            seen.set()

    eye = new_client("pytest-phone-eye")
    eye.on_message = on_message
    connect(eye)
    eye.subscribe(topics.EYES_EXPRESSION, qos=1)
    eye.loop_start()
    try:
        url = f"http://127.0.0.1:{port}"
        for _ in range(50):                            # wait for the page
            try:
                request(url + "/api/state")
                break
            except OSError:
                time.sleep(0.1)
        time.sleep(0.5)
        times = []
        for _ in range(3):                             # spaced past the 3 s sparkle, so each one shows
            seen.clear()
            start = time.perf_counter()
            assert request(url + "/api/button", {"name": "costume"})[0] == 204
            assert seen.wait(2.0), "the eyes never heard the press"
            times.append(got[-1] - start)
            time.sleep(COSTUME_S + 0.3)
        assert max(times) < 0.5, times
    finally:
        brain.terminate()
        brain.wait(5)
        eye.disconnect()
        eye.loop_stop()
