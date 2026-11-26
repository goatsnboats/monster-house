"""The mood state machine (SHW-001 to SHW-005, SHW-015, SHW-018, SHW-019, SHW-022),
played with a pretend clock and a pretend voice."""

from __future__ import annotations

import datetime as dt
import random

import pytest

from brain.moods import (DROOP_AFTER_S, LOOK_AROUND_S, NO_CLIP_HOLD_S, Action, Mood,
                         MoodMachine, Senses)
from brain.settings import ThemeSettings, Timing, load_theme_settings

TIMING = Timing()     # the owner's starting values (2026-11-24)
STEP = 0.1
HERE = Senses(present=True, approaching=True)
NOBODY = Senses()


class FakeVoice:
    """Clips last `length` seconds; keeps a log of what was said."""

    def __init__(self, length: float = 3.0, muted: bool = False) -> None:
        self.length = length
        self.muted = muted
        self.said: list[tuple[float, str, bool]] = []
        self._until = -1.0

    def say(self, pool, now, keep_gap=True):
        if self.muted or self.busy(now):
            return False
        self.said.append((round(now, 2), pool, keep_gap))
        self._until = now + self.length
        return True

    def busy(self, now):
        return now < self._until

    def pools(self):
        return [p for _, p, _ in self.said]


class Clock:
    """Runs a machine forward, collecting every action with its time."""

    def __init__(self, voice: FakeVoice | None = None) -> None:
        self.voice = voice or FakeVoice()
        self.m = MoodMachine(TIMING, self.voice, random.Random(1))
        self.now = 0.0
        self.log: list[tuple[float, Action]] = [(0.0, a) for a in self.m.start(0.0)]

    def run(self, seconds: float, senses: Senses) -> None:
        end = self.now + seconds
        while self.now < end - 1e-9:
            self.now = round(self.now + STEP, 6)
            self.log += [(self.now, a) for a in self.m.tick(self.now, senses)]

    def moods(self) -> list[str]:
        return [a.value for _, a in self.log if a.kind == "mood"]

    def kinds(self, kind: str) -> list[tuple[float, str | int]]:
        return [(t, a.value) for t, a in self.log if a.kind == kind]


def test_a_whole_visit_runs_asleep_to_asleep():
    c = Clock()
    c.run(1, NOBODY)
    assert c.m.mood is Mood.ASLEEP and c.m.look == "idle"
    c.run(0.1, HERE)
    assert c.m.mood is Mood.WAKING
    c.run(10, HERE)                                  # wake clip (3 s), greeting (3 s)
    assert c.m.mood is Mood.WATCHING and c.m.look == "focus"
    c.run(TIMING.goodbye_after_s + 0.2, NOBODY)
    assert c.m.mood is Mood.GOODBYE and c.m.look == "hold"
    c.run(TIMING.sleep_after_s + 0.2, NOBODY)
    assert c.m.mood is Mood.ASLEEP
    assert c.moods() == ["asleep", "waking", "greeting", "watching", "goodbye", "asleep"]
    assert c.voice.pools()[:3] == ["wake", "greet", "comment"] or c.voice.pools()[:2] == ["wake", "greet"]
    assert "bye" in c.voice.pools()


def test_waking_waits_for_the_wake_clip_and_locks_on():
    c = Clock(FakeVoice(length=4.0))
    c.run(0.1, HERE)
    assert c.m.look == "idle"                         # looking around first
    c.run(LOOK_AROUND_S, HERE)
    assert c.m.look == "focus"                        # locked on
    assert c.m.mood is Mood.WAKING                    # the 4 s yawn is still playing
    c.run(3.0, HERE)
    assert c.m.mood is Mood.GREETING
    assert c.voice.said[1][1:] == ("greet", False)    # the greeting isn't held back by the gap


def test_waking_without_a_clip_moves_on_after_a_short_hold():
    c = Clock(FakeVoice(muted=True))
    c.run(NO_CLIP_HOLD_S, HERE)
    assert c.m.mood is Mood.WAKING
    c.run(0.2, HERE)
    assert c.m.mood is Mood.GREETING


def test_visitor_who_leaves_while_waking_lets_it_sleep():
    c = Clock(FakeVoice(length=30))                   # a very long yawn
    c.run(0.1, HERE)
    c.run(TIMING.goodbye_after_s + 0.2, NOBODY)
    assert c.moods() == ["asleep", "waking", "asleep"]


def test_someone_standing_still_does_not_wake_it():
    c = Clock()
    c.run(5, Senses(present=True, approaching=False))
    assert c.m.mood is Mood.ASLEEP


def test_someone_new_during_goodbye_is_greeted_without_a_yawn():
    c = Clock()
    c.run(10, HERE)
    c.run(TIMING.goodbye_after_s + 0.2, NOBODY)
    assert c.m.mood is Mood.GOODBYE
    c.run(0.1, Senses(present=True))
    assert c.moods()[-2:] == ["goodbye", "greeting"]
    assert c.voice.pools().count("wake") == 1


def test_goodbye_looks_where_they_left_then_droops():
    c = Clock(FakeVoice(length=1.0))
    c.run(10, HERE)
    c.run(TIMING.goodbye_after_s + 0.1, NOBODY)
    start = [t for t, v in c.kinds("mood") if v == "goodbye"][0]
    c.run(DROOP_AFTER_S + 0.2, NOBODY)
    sleepy = [t for t, v in c.kinds("expression") if v == "sleepy" and t > start]
    assert sleepy and sleepy[0] - start >= DROOP_AFTER_S - 1e-9


def test_comments_come_every_10_to_20_s_while_watching():
    c = Clock(FakeVoice(length=2.0))
    c.run(120, HERE)
    times = [t for t, p, _ in c.voice.said if p == "comment"]
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert len(times) >= 5
    assert all(TIMING.comment_every_s[0] - 0.11 <= g <= TIMING.comment_every_s[1] + 0.11 for g in gaps)


def test_blinks_while_awake_at_the_theme_interval_and_none_asleep():
    c = Clock()
    c.run(40, NOBODY)
    assert c.kinds("blink") == []                      # asleep: no blinks
    c.run(60, HERE)
    times = [t for t, _ in c.kinds("blink")]
    gaps = [b - a for a, b in zip(times[1:], times[2:])]
    assert len(times) > 10
    assert all(TIMING.blink_every_s[0] - 0.11 <= g <= TIMING.blink_every_s[1] + 0.11 for g in gaps)
    assert {v for _, v in c.kinds("blink")} == {TIMING.blink_ms}


def test_asleep_snores_with_a_flutter():
    c = Clock()
    c.run(TIMING.snore_every_s * 2 + 2, NOBODY)
    assert c.voice.pools() == ["snore", "snore"]
    assert [v for _, v in c.kinds("expression")] == ["asleep", "sleepy", "asleep", "sleepy", "asleep"]


def test_radar_offline_means_ambient_eyes_and_no_visits():
    c = Clock()
    c.run(10, HERE)
    assert c.m.mood is Mood.WATCHING
    c.run(0.1, Senses(present=False, radar_online=False))
    assert c.m.mood is Mood.ASLEEP and c.m.ambient and c.m.awake and c.m.look == "idle"
    assert c.kinds("expression")[-1][1] == "neutral"   # eyes open, wandering
    said = len(c.voice.said)
    c.run(40, Senses(approaching=True, radar_online=False))
    assert c.m.mood is Mood.ASLEEP                       # never wakes for a visit
    assert len(c.voice.said) == said                     # and never talks
    assert len(c.kinds("blink")) > 5                     # but keeps blinking
    c.run(0.1, NOBODY)                                   # radar back
    assert not c.m.ambient and c.kinds("expression")[-1][1] == "asleep"


def test_outside_show_hours_it_stays_asleep_and_quiet():
    c = Clock()
    c.run(70, Senses(present=True, approaching=True, show_time=False))
    assert c.m.mood is Mood.ASLEEP
    assert c.voice.said == []


def test_mood_is_announced_once_per_change():
    c = Clock()
    c.run(10, HERE)
    assert c.moods() == ["asleep", "waking", "greeting", "watching"]


def test_show_hours_including_past_midnight():
    evening = ThemeSettings("t", show_hours=(dt.time(17, 30), dt.time(21, 30)))
    assert evening.in_show_hours(dt.datetime(2027, 10, 31, 18, 0))
    assert not evening.in_show_hours(dt.datetime(2027, 10, 31, 21, 30))
    late = ThemeSettings("t", show_hours=(dt.time(22, 0), dt.time(1, 0)))
    assert late.in_show_hours(dt.datetime(2027, 10, 31, 23, 0))
    assert late.in_show_hours(dt.datetime(2027, 11, 1, 0, 30))
    assert not late.in_show_hours(dt.datetime(2027, 11, 1, 12, 0))


def test_the_halloween_theme_loads_with_the_owners_values():
    s = load_theme_settings("halloween")
    assert s.timing == Timing()
    assert s.clips["greet"][0] == "greet_01"
    assert s.show_hours == (dt.time(17, 30), dt.time(21, 30))
