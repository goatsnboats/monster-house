"""Gaze in Step 4: following visitors (SHW-007, SHW-010, SHW-011), the focus choice
(SHW-008, SHW-013) and the look point (SHW-006, SHW-012)."""

from __future__ import annotations

import random
import statistics

import pytest

from brain.focus import Focus
from brain.gaze import visitor_point
from brain.visitors import HEADING_WINDOW_S, LOST_GRACE_S, SMOOTH_S, Tracker
from shared.radar_frame import RadarSite, Zone

DOOR = Zone(-1800, 0, -500, 900)
SITE = RadarSite(mount=(0.0, 0.0, 1.2), approach_range_m=5.0, head_height_m=1.0,
                 door_zone=DOOR, door_point=(-1.15, 0.45, 1.0))
STEP = 0.1
HOLD = 15.0


def run(tracker: Tracker, t0: float, seconds: float, targets) -> tuple[float, list]:
    """Feed `targets(t)` (a list of radar-mm points) every 0.1 s; return the end time and events."""
    events, t = [], t0
    while t < t0 + seconds - 1e-9:
        t = round(t + STEP, 6)
        events += tracker.update(t, targets(t))
    return t, events


def kinds(events):
    return [(e.kind, e.visitor.id) for e in events]


# ── Tracking ────────────────────────────────────────────────────────────────────

def test_smoothing_takes_out_jitter():
    tr = Tracker(SITE, HOLD)
    noisy = lambda t: [(0 + (120 if round(t * 10) % 2 else -120), 3000)]   # noqa: E731
    xs = []
    t = 0.0
    for _ in range(40):
        t = round(t + STEP, 6)
        tr.update(t, noisy(t))
        xs.append(tr.visitors[1].x)
    assert statistics.pstdev(xs[10:]) < 0.12 / 2              # less than half the raw jitter


def test_smoothing_follows_a_step_quickly():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(0, 3000)])
    run(tr, 1, 3 * SMOOTH_S + 0.05, lambda t: [(500, 3000)])
    assert tr.visitors[1].x == pytest.approx(0.5, abs=0.05)   # caught up in about 0.5 s


def test_visitors_keep_their_identity_when_radar_slots_swap():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(-1000, 3000), (1000, 3000)])
    left = next(v.id for v in tr.visitors.values() if v.x < 0)
    run(tr, 1, 1, lambda t: [(1000, 3000), (-1000, 3000)])     # same people, other slots
    assert len(tr.visitors) == 2
    assert next(v.id for v in tr.visitors.values() if v.x < 0) == left


@pytest.mark.parametrize("speed, expected", [(-1000, "coming"), (1000, "going"), (0, None)])
def test_coming_or_going_from_half_a_second_of_movement(speed, expected):
    tr = Tracker(SITE, HOLD)
    _, events = run(tr, 0, 1.5, lambda t: [(0, 4000 + speed * t)])
    v = tr.visitors[1]
    assert v.heading == expected
    marks = [e for e in events if e.kind in ("coming", "going")]
    assert [e.kind for e in marks] == ([expected] if expected else [])
    if marks:                                  # decided after about half a second
        tr2 = Tracker(SITE, HOLD)
        t, _ = run(tr2, 0, HEADING_WINDOW_S - STEP, lambda t: [(0, 4000 + speed * t)])
        assert tr2.visitors[1].heading is None
        run(tr2, t, 0.4, lambda t: [(0, 4000 + speed * t)])
        assert tr2.visitors[1].heading == expected


def test_someone_lost_away_from_the_door_has_left():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(1000, 3000)])
    t, events = run(tr, 1, LOST_GRACE_S + 0.1, lambda t: [])
    assert kinds(events) == [("left", 1)] and not tr.visitors


def test_someone_lost_at_the_door_is_held_then_let_go():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(-1100, 500)])                  # standing in the door zone
    t, events = run(tr, 1, HOLD - 0.5, lambda t: [])
    assert kinds(events) == [("at door", 1)] and tr.visitors[1].at_door
    t, events = run(tr, t, 1.0, lambda t: [])
    assert kinds(events) == [("left", 1)]


def test_someone_back_from_the_door_is_the_same_visitor():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(-1100, 500)])
    t, _ = run(tr, 1, 8, lambda t: [])
    t, events = run(tr, t, 0.5, lambda t: [(-700, 800)])     # reappears nearby
    assert [k for k, _ in kinds(events) if k == "arrived"] == []
    assert not tr.visitors[1].at_door


# ── Focus ───────────────────────────────────────────────────────────────────────

class Scene:
    """A tracker and a focus, run together; records every switch."""

    def __init__(self) -> None:
        self.tr = Tracker(SITE, HOLD)
        self.focus = Focus((3, 6), random.Random(2))
        self.t = 0.0
        self.switches: list[float] = []
        self.who: int | None = None

    def run(self, seconds: float, targets) -> None:
        end = self.t + seconds
        while self.t < end - 1e-9:
            self.t = round(self.t + STEP, 6)
            v, switched = self.focus.choose(self.t, self.tr, self.tr.update(self.t, targets(self.t)))
            self.who = v.id if v else None
            if switched:
                self.switches.append(self.t)


def test_a_new_arrival_wins_and_counts_as_a_switch():
    s = Scene()
    s.run(2, lambda t: [(0, 2000)])
    assert s.who == 1 and s.switches == []                    # first lock-on: not a switch
    s.run(0.1, lambda t: [(0, 2000), (2000, 4000)])
    assert s.who == 2 and len(s.switches) == 1


def test_focus_holds_3_to_6_s_then_switches_between_kids():
    s = Scene()
    s.run(60, lambda t: [(-800, 2000), (800, 2000)])           # two kids standing
    gaps = [b - a for a, b in zip(s.switches, s.switches[1:])]
    assert len(s.switches) >= 9
    assert all(3 - 1e-6 <= g <= 6 + STEP + 1e-6 for g in gaps)


def test_one_visitor_never_counts_as_a_switch():
    s = Scene()
    s.run(30, lambda t: [(0, 2000)])
    assert s.who == 1 and s.switches == []


def test_switching_prefers_coming_then_closest():
    s = Scene()
    near, far_coming = (500, 1500), lambda t: (-1500, 5000 - 600 * t)
    s.run(0.1, lambda t: [near])
    s.run(0.1, lambda t: [near, far_coming(t)])               # arrives: wins at once
    s.run(0.1, lambda t: [near, far_coming(t), (1500, 2500)])  # another arrival
    assert s.who == 3
    s.run(6.1, lambda t: [near, far_coming(t), (1500, 2500)])  # hold ends: coming kid next
    assert s.who == 2


def test_a_kid_going_away_is_watched_until_they_leave():
    s = Scene()
    s.run(1, lambda t: [(-800, 2000), (800, 2000)])
    s.run(4, lambda t: [(-800, 2000), (800, 2000 + 1000 * (t - 1))])   # kid 2 walks off
    assert s.who == 2
    assert s.tr.visitors[2].heading == "going"
    s.run(8, lambda t: [(-800, 2000), (800, min(5900, 2000 + 1000 * (t - 1)))])
    assert s.who == 2                                          # held past the 3-6 s hold
    s.run(1, lambda t: [(-800, 2000)])                         # gone: back to kid 1
    assert s.who == 1


# ── Look point ──────────────────────────────────────────────────────────────────

def test_look_point_is_the_head_or_the_door():
    tr = Tracker(SITE, HOLD)
    run(tr, 0, 1, lambda t: [(-1100, 500)])
    v = tr.visitors[1]
    assert visitor_point(v, SITE) == pytest.approx((v.x, v.y, 1.0))
    run(tr, 1, 1, lambda t: [])
    assert visitor_point(v, SITE) == SITE.door_point
