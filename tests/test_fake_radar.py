"""The fake radar sends what ESPHome's LD2450 component sends (ICD-002, SIM-001 to SIM-003),
and the radar geometry shared with the brain (shared/radar_frame.py)."""

from __future__ import annotations

import pytest

from shared import topics
from shared.messages import radar_targets as radar
from shared.radar_frame import (RadarSite, SiteError, Zone, house_to_radar, in_view, load_radar_site,
                                radar_to_house)
from sim.fake_radar import Layout, kid_at, new_kid
from sim.radar_model import Kid, RadarModel

SITE = RadarSite(mount=(0.0, 0.0, 1.2), approach_range_m=5.0, head_height_m=1.0,
                 door_zone=Zone(-1800, 0, -500, 900))
X1, Y1, S1 = (topics.radar_target(1, f) for f in topics.RADAR_TARGET_FIELDS)
X2 = topics.radar_target(2, "x")
COUNT = topics.RADAR_TARGET_COUNT


def as_dict(messages):
    return {topic: payload.decode() for topic, payload in messages}


# -- geometry ------------------------------------------------------------------------

def test_radar_and_house_coordinates_round_trip():
    site = RadarSite(mount=(0.5, 0.2, 1.2), approach_range_m=5, head_height_m=1.0)
    x_mm, y_mm = house_to_radar(1.5, 3.2, site)
    assert (x_mm, y_mm) == pytest.approx((1000, 3000))
    assert radar_to_house(x_mm, y_mm, site) == pytest.approx((1.5, 3.2, 1.0))


@pytest.mark.parametrize("x, y, seen", [
    (0, 3000, True), (0, -100, False), (0, 6100, False),       # in front, behind, too far
    (2900, 1000, False),                                         # more than 60 degrees aside
    (2500, 4000, True), (3100, 5000, False),                     # x beyond 3 m
])
def test_what_the_ld2450_can_see(x, y, seen):
    assert in_view(x, y) is seen


def test_site_config_loads_the_door_zone():
    site = load_radar_site()
    assert site.door_zone is not None and site.head_height_m > 0


def test_a_broken_site_config_says_what_to_fix(tmp_path):
    bad = tmp_path / "site.yaml"
    bad.write_text("radar: {}\n")
    with pytest.raises(SiteError, match="ICD-015"):
        load_radar_site(bad)


# -- what gets sent ------------------------------------------------------------------

def test_first_frame_clears_every_slot_like_esphome_at_boot():
    sent = as_dict(RadarModel(SITE).frame(0.0, []))
    assert sent[COUNT] == "0"
    for n in range(1, 4):
        for f in topics.RADAR_TARGET_FIELDS:
            assert sent[topics.radar_target(n, f)] == "nan"


def test_a_kid_is_sent_in_whole_millimeters_relative_to_the_radar():
    model = RadarModel(SITE)
    sent = as_dict(model.frame(0.0, [Kid(1.2345, 3.0)]))
    assert sent[X1] == "1234" or sent[X1] == "1235"
    assert sent[Y1] == "3000"
    assert sent[COUNT] == "1"


def test_values_go_only_on_change_plus_one_repeat():
    model, kids = RadarModel(SITE), [Kid(0.0, 3.0)]
    model.frame(0.0, kids)
    again = as_dict(model.frame(0.1, kids))      # unchanged: the timeout filter's one repeat
    assert again[X1] == "0" and again[Y1] == "3000"
    assert model.frame(0.2, kids) == []          # then silence: an empty or still walk is quiet
    assert model.frame(0.3, kids) == []


def test_a_kid_walking_toward_the_radar_has_negative_speed():
    model, kid = RadarModel(SITE), Kid(0.0, 4.0)
    model.frame(0.0, [kid])
    kid.y = 3.9
    sent = as_dict(model.frame(0.1, [kid]))
    assert int(sent[S1]) == -1000                # 100 mm in 0.1 s, toward the radar
    assert int(sent[S1]) % 10 == 0
    kid.y = 4.1
    assert int(as_dict(model.frame(0.2, [kid]))[S1]) > 0     # walking away


def test_a_kid_who_leaves_becomes_nan_once():
    model, kids = RadarModel(SITE), [Kid(0.0, 3.0)]
    model.frame(0.0, kids)
    model.frame(0.1, kids)
    gone = as_dict(model.frame(0.2, []))
    assert gone[X1] == gone[Y1] == gone[S1] == "nan" and gone[COUNT] == "0"
    assert as_dict(model.frame(0.3, [])) == {COUNT: "0"}   # the count's one repeat; nan isn't repeated
    assert model.frame(0.4, []) == []


def test_the_door_blind_spot_hides_a_kid():
    model = RadarModel(SITE)
    at_door = Kid(-1.2, 0.5)                     # radar (-1200, 500): inside the door zone
    assert not model.sees(at_door)
    assert as_dict(model.frame(0.0, [at_door]))[COUNT] == "0"


def test_a_kid_behind_the_radar_or_out_of_range_is_not_seen():
    model = RadarModel(SITE)
    assert not model.sees(Kid(0.0, -0.3))
    assert not model.sees(Kid(0.0, 6.5))


def test_kids_keep_their_slots_and_new_ones_take_the_lowest_free():
    model = RadarModel(SITE)
    a, b, c = Kid(0.0, 2.0, "A"), Kid(1.0, 3.0, "B"), Kid(-0.5, 4.0, "C")
    model.frame(0.0, [a, b])
    assert (model.slot_of(a), model.slot_of(b)) == (1, 2)
    model.frame(0.1, [b])                        # A leaves: B stays in slot 2
    assert model.slot_of(b) == 2
    model.frame(0.2, [b, c])                     # C takes the free slot 1
    assert model.slot_of(c) == 1


def test_resend_all_sends_everything_again_after_a_reconnect():
    model, kids = RadarModel(SITE), [Kid(0.0, 3.0)]
    for t in (0.0, 0.1, 0.2):
        model.frame(t, kids)
    model.resend_all()
    assert len(model.frame(0.3, kids)) == 10     # 3 slots x 3 values + the count


def test_every_payload_meets_icd_002():
    model, kid = RadarModel(SITE, jitter_mm=30), Kid(0.3, 5.0)
    for i in range(30):
        kid.y -= 0.1
        for topic, payload in model.frame(i * 0.1, [kid]):
            kind = "target count" if topic == COUNT else "target value"
            assert radar.decode(kind, payload) is not None
            if kind == "target value" and payload != b"nan":
                int(payload)                     # a whole number, no decimals


def test_frames_come_about_ten_times_a_second():
    model = RadarModel(SITE, frame_hz=10)
    ticks = sum(model.due(i / 60) for i in range(600))     # 10 s of 60 fps screen frames
    assert 99 <= ticks <= 101


# -- the window's helpers ------------------------------------------------------------

def test_layout_maps_meters_to_pixels_and_back():
    layout = Layout.load()
    px = layout.to_px(1.0, 2.0)
    assert layout.to_m(*px) == pytest.approx((1.0, 2.0), abs=1 / layout.ppm)


def test_up_to_three_kids_can_be_added_and_picked_up():
    kids: list[Kid] = []
    for i in range(4):
        new_kid(kids, float(i), 3.0)
    assert [k.name for k in kids] == ["A", "B", "C"]
    assert kid_at(kids, 1.05, 3.0) is kids[1]
    assert kid_at(kids, 1.5, 3.5) is None
