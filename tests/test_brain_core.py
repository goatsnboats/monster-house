"""The whole brain on a pretend clock: pretend kids on the radar model (ICD-002), the fake
FPP answering its clips (ICD-003), and everything it sends to the eyes (ICD-001) and the
phone page (ICD-004). Covers Step 4's "done when" (a pretend visit from asleep to goodbye
and back to sleep) and the failure behavior (SHW-018)."""

from __future__ import annotations

import random

import pytest

from brain.core import Brain
from brain.settings import load_theme_settings
from shared import topics
from shared.messages import eye_commands as eyes
from shared.messages import phone_page
from shared.radar_frame import load_radar_site
from sim.fake_fpp import FakeFpp
from sim.radar_model import Kid, RadarModel

STEP = 0.1


class Visit:
    """Runs the brain, the radar model and the fake FPP together, 10 ticks a second."""

    def __init__(self, tmp_path, fpp: bool = True, seed: int = 4) -> None:
        self.site = load_radar_site()
        self.theme = load_theme_settings("halloween")
        self.brain = Brain(self.site, self.theme, random.Random(seed), any_time=True)
        self.radar = RadarModel(self.site)
        self.fpp = FakeFpp(tmp_path, default_s=2.5) if fpp else None
        self.t = 0.0
        self.sent: list[tuple[float, str, bytes]] = [(0.0, o.topic, o.payload) for o in self.brain.start(0.0)]
        self.radar_status(b"online")

    def radar_status(self, status: bytes) -> None:
        self.brain.on_message(topics.RADAR_STATUS, status, self.t)

    def run(self, seconds: float, kids=lambda t: []) -> None:
        end = self.t + seconds
        while self.t < end - 1e-9:
            self.t = round(self.t + STEP, 6)
            for topic, payload in self.radar.frame(self.t, kids(self.t)):
                self.brain.on_message(topic, payload, self.t)
            if self.fpp:
                for topic, payload in self.fpp.tick(self.t):
                    self.brain.on_message(topic, payload, self.t)
            for o in self.brain.tick(self.t):
                self.sent.append((self.t, o.topic, o.payload))
                name = topics.fpp_playlist_from_start(o.topic)
                if name and self.fpp:
                    for topic, payload in self.fpp.start(name, self.t):
                        self.brain.on_message(topic, payload, self.t)

    # What the brain sent, decoded.
    def moods(self) -> list[str]:
        return [phone_page.decode("mood", p).mood for _, t, p in self.sent if t == topics.STATE]

    def expressions(self, since: float = 0.0) -> list[str]:
        return [eyes.decode("expression", p).name for s, t, p in self.sent if t == topics.EYES_EXPRESSION and s >= since]

    def looks(self, since: float = 0.0) -> list[tuple[float, object]]:
        return [(s, eyes.decode("look", p)) for s, t, p in self.sent if t == topics.EYES_LOOK and s >= since]

    def blinks(self, since: float = 0.0) -> list[float]:
        return [s for s, t, _ in self.sent if t == topics.EYES_BLINK and s >= since]

    def clips(self) -> list[str]:
        return [n for _, t, _ in self.sent if (n := topics.fpp_playlist_from_start(t))]


def walk(x: float, y0: float, y1: float, t0: float, speed: float = 1.0):
    """A kid walking straight from y0 to y1 (house m) at `speed` m/s, starting at t0."""
    def at(t: float) -> Kid:
        d = max(0.0, t - t0) * speed
        return Kid(x, y0 - d if y1 < y0 else y0 + d) if d < abs(y1 - y0) else Kid(x, y1)
    return at


def test_a_pretend_visit_from_asleep_to_goodbye_and_back_to_sleep(tmp_path):
    v = Visit(tmp_path)
    v.run(2)
    assert v.moods() == ["asleep"] and v.expressions() == ["asleep"]
    coming = walk(1.5, 5.5, 1.5, t0=2)
    v.run(10, lambda t: [coming(t)])                          # walks up, stops near the porch
    assert v.moods() == ["asleep", "waking", "greeting", "watching"]
    assert v.clips()[:2] == ["yawn_01", v.clips()[1]] and v.clips()[1].startswith("greet_")
    assert "happy" in v.expressions()
    locked = [lk for _, lk in v.looks(since=6) if isinstance(lk, eyes.LookAt)]
    assert len(locked) > 50                                    # ~10 a second while tracking
    assert locked[-1].x == pytest.approx(1.5, abs=0.1) and locked[-1].z == 1.0

    going = walk(1.5, 1.5, 6.5, t0=v.t)
    v.run(8, lambda t: [going(t)])                            # walks away, out of range
    v.run(30)
    assert "bye_01" in v.clips() or "bye_02" in v.clips()
    assert v.moods() == ["asleep", "waking", "greeting", "watching", "goodbye", "asleep"]
    assert v.expressions()[-1] == "asleep"


def test_eyes_switch_between_kids_and_blink_on_each_switch(tmp_path):
    v = Visit(tmp_path)
    a, b = walk(-1.0, 5.5, 2.0, t0=0), walk(1.5, 5.5, 2.0, t0=0.3)
    v.run(40, lambda t: [a(t), b(t)])
    xs = [round(lk.x) for s, lk in v.looks(since=15) if isinstance(lk, eyes.LookAt)]
    switches = sum(1 for p, q in zip(xs, xs[1:]) if p != q)
    assert switches >= 4                                       # 25 s, holds of 3-6 s
    blinks = v.blinks(since=15)
    assert len(blinks) >= switches


def test_a_kid_at_the_door_holds_the_visit_and_the_eyes_look_at_the_door(tmp_path):
    v = Visit(tmp_path)
    to_door = walk(-1.1, 5.0, 0.4, t0=0)                       # ends inside the door zone
    v.run(12, lambda t: [to_door(t)])
    assert v.moods()[-1] == "watching"
    v.run(v.theme.timing.door_hold_s - 4, lambda t: [Kid(-1.1, 0.4)])
    assert v.moods()[-1] == "watching"                          # not gone: at the door
    last = [lk for _, lk in v.looks() if isinstance(lk, eyes.LookAt)][-1]
    assert (last.x, last.y, last.z) == v.site.door_point
    v.run(10, lambda t: [Kid(-1.1, 0.4)])
    assert "goodbye" in v.moods()                               # door hold over


def test_a_new_kid_coming_gets_a_surprised_glance(tmp_path):
    v = Visit(tmp_path)
    a = walk(-1.0, 5.5, 2.0, t0=0)
    v.run(12, lambda t: [a(t)])
    t0 = v.t
    b = walk(2.0, 5.5, 2.0, t0=t0)
    v.run(3, lambda t: [a(t), b(t)])
    assert v.expressions(since=t0)[:2] == ["surprised", "happy"]


def test_radar_offline_means_ambient_eyes_and_no_voice(tmp_path):
    v = Visit(tmp_path)
    a = walk(1.0, 5.5, 2.0, t0=0)
    v.run(12, lambda t: [a(t)])
    clips = len(v.clips())
    v.radar_status(b"offline")
    t0 = v.t
    v.run(30)
    assert v.moods()[-1] == "asleep"
    assert v.expressions(since=t0)[-1] == "neutral"            # eyes open and wandering
    assert isinstance(v.looks(since=t0)[-1][1], eyes.LookIdle)
    assert len(v.blinks(since=t0)) >= 5
    assert len(v.clips()) == clips                             # never talks


def test_an_eye_dropping_out_changes_nothing_and_one_coming_back_catches_up(tmp_path):
    v = Visit(tmp_path)
    a = walk(1.0, 5.5, 2.0, t0=0)
    hello = v.brain.on_message(topics.EYES_LEFT_STATUS, b"online", 0.0)
    assert eyes.decode("expression", hello[0].payload).name == "asleep"   # told to match
    v.run(12, lambda t: [a(t)])
    assert v.brain.on_message(topics.EYES_LEFT_STATUS, b"offline", v.t) == []
    v.run(5, lambda t: [a(t)])
    assert v.moods()[-1] == "watching"
    back = v.brain.on_message(topics.EYES_LEFT_STATUS, b"online", v.t)
    assert [o.topic for o in back] == [topics.EYES_EXPRESSION, topics.EYES_LOOK]
    assert eyes.decode("expression", back[0].payload).name == "happy"


def test_a_visit_still_plays_through_without_fpp(tmp_path):
    v = Visit(tmp_path, fpp=False)
    a = walk(1.0, 5.5, 2.0, t0=0)
    v.run(15, lambda t: [a(t)])
    assert v.moods() == ["asleep", "waking", "greeting", "watching"]
    assert not v.brain.voice.fpp_responding


def test_theme_is_published_first_and_retained(tmp_path):
    v = Visit(tmp_path)
    first = v.brain.start(0.0)[0]
    assert first.topic == topics.THEME and first.retain
    assert eyes.decode("theme", first.payload) == eyes.Theme("halloween")
