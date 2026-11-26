"""The brain reads the radar (ICD-002) and, for now, looks at the closest visitor
(Stage 0 Step 3 placeholder gaze). Fed with the fake radar's own output, so the two
can't drift apart (SIM-002)."""

from __future__ import annotations

import pytest

from brain import gaze
from brain.radar import RadarState
from shared import topics
from shared.radar_frame import RadarSite
from sim.radar_model import Kid, RadarModel

SITE = RadarSite(mount=(0.0, 0.0, 1.2), approach_range_m=5.0, head_height_m=1.0)


def fed(model: RadarModel, frames: list[list[Kid]], state: RadarState | None = None) -> RadarState:
    state = state or RadarState()
    state.update(topics.RADAR_STATUS, b"online")
    for i, kids in enumerate(frames):
        for topic, payload in model.frame(i * 0.1, kids):
            assert state.update(topic, payload)
    return state


def test_radar_messages_become_targets():
    state = fed(RadarModel(SITE), [[Kid(1.0, 3.0), Kid(-0.5, 2.0)]])
    found = {(t.slot, t.x_mm, t.y_mm) for t in state.targets()}
    assert found == {(1, 1000.0, 3000.0), (2, -500.0, 2000.0)}
    assert state.count == 2


def test_a_nan_slot_is_nobody():
    model = RadarModel(SITE)
    state = fed(model, [[Kid(0.0, 3.0)], []])
    assert state.targets() == []


def test_no_targets_while_the_radar_is_offline():
    state = fed(RadarModel(SITE), [[Kid(0.0, 3.0)]])
    state.update(topics.RADAR_STATUS, b"offline")
    assert state.targets() == []


def test_bad_or_foreign_messages_are_ignored():
    state = RadarState()
    assert not state.update(topics.RADAR_TARGET_COUNT, b"7")         # breaks ICD-002
    assert not state.update(topics.EYES_BLINK, b'{"ms": 100}')       # not a radar topic
    assert state.update(topics.radar_target(1, "x"), b"oops")         # a string, but no number
    assert state.targets() == []


def test_placeholder_gaze_looks_at_the_closest_visitor():
    state = fed(RadarModel(SITE), [[Kid(2.0, 4.0), Kid(-1.0, 2.0)]])
    assert gaze.look_point(state.targets(), SITE) == pytest.approx((-1.0, 2.0, 1.0))
    assert gaze.look_point([], SITE) is None
