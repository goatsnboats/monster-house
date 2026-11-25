"""Clip pools, the minimum gap and clip-finished (SHW-016, SHW-017, SHW-020, SHW-026,
SHW-018), and the fake FPP answering as ICD-003 says (SIM-004)."""

from __future__ import annotations

import random
import wave

import pytest

from brain.clips import FPP_ANSWER_S, ClipPool, Voice
from shared import topics
from shared.messages import clips as icd
from sim.fake_fpp import FakeFpp, clip_seconds

POOLS = {"greet": ["g1", "g2", "g3", "g4", "g5"], "comment": ["c1", "c2"], "door": []}


def test_a_pool_plays_every_clip_before_repeating():
    pool = ClipPool(POOLS["greet"], random.Random(3))
    for _ in range(20):
        assert sorted(pool.next() for _ in range(5)) == POOLS["greet"]


def test_a_new_round_never_starts_with_the_last_clip():
    pool = ClipPool(["a", "b"], random.Random(0))
    picks = [pool.next() for _ in range(200)]
    assert all(a != b for a, b in zip(picks, picks[1:]))


def test_an_empty_pool_gives_nothing():
    assert ClipPool([], random.Random()).next() is None
    assert not Voice(POOLS, 10).say("door", 0.0)
    assert not Voice(POOLS, 10).say("no such pool", 0.0)


def play(voice: Voice, now: float, length: float) -> float:
    """FPP plays the started clip for `length` s; returns when it ended."""
    voice.on_status("playing", now + 0.05)
    assert voice.busy(now + length - 0.01)
    voice.on_status("idle", now + length)
    return now + length


def test_minimum_gap_from_the_end_of_the_last_clip():
    v = Voice(POOLS, 10)
    assert v.say("comment", 0.0) and v.take_starts() == [v.pools["comment"]._last]
    assert not v.say("comment", 1.0)                       # still playing
    end = play(v, 0.0, 3.0)
    assert not v.busy(end)
    assert not v.say("comment", end + 9.9)                 # gap not over
    assert v.say("comment", end + 10.0)


def test_the_greeting_can_skip_the_gap():
    v = Voice(POOLS, 10)
    v.say("comment", 0.0)
    end = play(v, 0.0, 3.0)
    assert v.say("greet", end + 0.1, keep_gap=False)


def test_muted_says_nothing():
    v = Voice(POOLS, 10)
    v.muted = True
    assert not v.say("greet", 0.0, keep_gap=False) and v.take_starts() == []


def test_fpp_not_answering_lets_the_brain_carry_on():
    v = Voice(POOLS, 10)
    assert v.say("greet", 0.0)
    assert v.busy(FPP_ANSWER_S - 0.1)
    assert not v.busy(FPP_ANSWER_S)                         # counts as finished
    assert not v.fpp_responding
    v.on_status("idle", 30.0)
    assert v.fpp_responding


def test_a_stale_idle_does_not_end_a_clip():
    v = Voice(POOLS, 10)
    v.say("greet", 0.0)
    v.on_status("idle", 0.1)                                # before "playing"
    assert v.busy(0.2)


# ── Fake FPP ────────────────────────────────────────────────────────────────────

def test_fake_fpp_answers_playing_then_idle(tmp_path):
    fpp = FakeFpp(tmp_path, default_s=2.5)
    out = fpp.start("greet_01", 10.0)
    assert out == [(topics.FPP_STATUS, b"playing"), (topics.FPP_PLAYLIST_PLAYING, b"greet_01")]
    assert icd.decode("player status", out[0][1]) == "playing"
    assert fpp.tick(12.4) == []
    assert fpp.tick(12.5) == [(topics.FPP_STATUS, b"idle")]
    assert fpp.tick(13.0) == []


def test_fake_fpp_uses_the_recording_length(tmp_path):
    audio = tmp_path / "bye_01.wav"
    with wave.open(str(audio), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(8000)
        w.writeframes(b"\0\0" * 12000)                      # 1.5 s
    assert clip_seconds(audio, 3.0) == pytest.approx(1.5)
    assert clip_seconds(tmp_path / "missing.wav", 3.0) == 3.0


def test_brain_voice_and_fake_fpp_together(tmp_path):
    """The brain's start goes out on ICD-003's topic, the fake FPP answers, the voice is free."""
    v, fpp = Voice(POOLS, 10, random.Random(1)), FakeFpp(tmp_path, default_s=2.0)
    v.say("greet", 0.0)
    (name,) = v.take_starts()
    topic = topics.fpp_playlist_start(name)
    assert topics.fpp_playlist_from_start(topic) == name
    for t, p in fpp.start(name, 0.1):
        if t == topics.FPP_STATUS:
            v.on_status(icd.decode("player status", p), 0.1)
    assert v.busy(1.0)
    for t, p in fpp.tick(2.1):
        v.on_status(icd.decode("player status", p), 2.1)
    assert not v.busy(2.1)
