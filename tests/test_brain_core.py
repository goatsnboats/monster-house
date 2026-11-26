"""The whole brain on a pretend clock: pretend kids on the radar model (ICD-002), the fake
FPP answering its clips (ICD-003), and everything it sends to the eyes (ICD-001) and the
phone page (ICD-004). Covers Step 4's "done when" (a pretend visit from asleep to goodbye
and back to sleep) and the failure behavior (SHW-018)."""

from __future__ import annotations

import pytest

from shared import topics
from shared.messages import eye_commands as eyes
from sim.pretend_visit import ONE_KID, ONE_KID_S, Visit, walk
from sim.radar_model import Kid

def test_the_step_4_story_plays_through(tmp_path):
    """The results page's visit: up the path, to the door and out of sight, and away."""
    v = Visit(tmp_path)
    v.run(ONE_KID_S, ONE_KID)
    assert v.moods() == ["asleep", "waking", "greeting", "watching", "goodbye", "asleep"]
    goodbye = dict((m, t) for t, m in v.mood_changes())["goodbye"]
    assert goodbye > 24 + v.theme.timing.goodbye_after_s       # not while at the door (15-24 s)


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


def test_never_two_blinks_in_a_row(tmp_path):
    v = Visit(tmp_path)
    a, b = walk(-1.0, 5.5, 2.0, t0=1), walk(1.5, 5.5, 2.0, t0=1.4)
    v.run(90, lambda t: [a(t), b(t)])
    times = v.blinks()
    assert min(q - p for p, q in zip(times, times[1:])) >= 0.5 - 1e-9
