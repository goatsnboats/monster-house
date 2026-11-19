"""Tests for the eye renderer (eyes/): expressions, blinks, fallback, gaze, config, drawing.

The logic tests use a fake clock (update(dt)) and a seeded random generator. The drawing
tests use Mesa's CPU renderer, so they need no GPU; they are skipped if no OpenGL is
available at all.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest
import yaml

from eyes.config import ConfigError, DEFAULT_THEME, hex_color, load_theme, load_window
from eyes.expressions import EXPRESSIONS, Expression
from eyes.gaze import MAX_X, MAX_Y, iris_offset
from eyes.state import EyeState, Frame

REPO_ROOT = Path(__file__).resolve().parent.parent
LEFT_WINDOW = (-1.6, -0.5, 5.0)     # config/site.yaml
RIGHT_WINDOW = (1.6, -0.5, 5.0)


def run(state: EyeState, seconds: float, dt: float = 1 / 60, brain: bool = False) -> list[Frame]:
    frames = []
    for _ in range(round(seconds / dt)):
        if brain:
            state.heard_from_brain()
        frames.append(state.update(dt))
    return frames


# ── Expressions (EYE-002) ───────────────────────────────────────────────────────

def test_expression_table_matches_the_architecture():
    text = (REPO_ROOT / "docs/architecture.md").read_text()
    rows = re.findall(r"^\| `(\w+)` \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", text, re.M)
    table = {name: Expression(*map(float, values)) for name, *values in rows}
    assert table == EXPRESSIONS


def test_expression_eases_over_the_commanded_time():
    s = EyeState()
    assert s.set_expression("happy", ms=400)
    run(s, 0.2, dt=0.01, brain=True)
    half = s.expression()
    assert EXPRESSIONS["neutral"].open > half.open > EXPRESSIONS["happy"].open
    assert half.low == pytest.approx(EXPRESSIONS["happy"].low / 2, abs=0.01)   # smoothstep is 0.5 at the middle
    run(s, 0.21, dt=0.01, brain=True)
    assert s.expression() == EXPRESSIONS["happy"]


def test_zero_duration_is_instant_and_unknown_names_are_ignored():
    s = EyeState()
    s.set_expression("surprised", ms=0)
    assert s.expression() == EXPRESSIONS["surprised"]
    assert not s.set_expression("slit-pupil-angry")
    assert s.expression() == EXPRESSIONS["surprised"]


def test_a_new_expression_starts_from_where_the_eye_is_now():
    s = EyeState()
    s.set_expression("asleep", ms=1000)
    run(s, 0.5, brain=True)
    midway = s.expression()
    s.set_expression("neutral", ms=1000)
    assert s.expression() == midway        # no jump


# ── Blinks (EYE-005, EYE-006) ───────────────────────────────────────────────────

def test_commanded_blink_shuts_halfway_and_reopens():
    s = EyeState()
    s.heard_from_brain()
    s.blink(ms=200)
    opens = [f.expression.open for f in run(s, 0.3, dt=0.01, brain=True)]
    assert min(opens) < 0.1
    assert opens[-1] == pytest.approx(1.0)


def test_no_own_blinks_while_the_brain_is_talking():
    s = EyeState(rng=random.Random(1))
    opens = [f.expression.open for f in run(s, 20, brain=True)]
    assert min(opens) == pytest.approx(1.0)


def test_eye_blinks_and_wanders_on_its_own_when_the_brain_is_quiet():
    s = EyeState(blink_every_s=(1.0, 2.0), fallback_after_s=5.0, rng=random.Random(2))
    s.look_at((0.0, 3.0, 1.0))
    run(s, 1.0, brain=True)
    frames = run(s, 10)                     # the brain goes quiet
    assert not s.brain_present
    assert min(f.expression.open for f in frames) < 0.2
    assert len({round(f.gaze[0]) for f in frames}) > 5


def test_asleep_eye_does_not_blink():
    s = EyeState(blink_every_s=(0.5, 1.0), rng=random.Random(3))
    s.set_expression("asleep", ms=0)
    assert max(f.expression.open for f in run(s, 5)) == 0.0


# ── Gaze (EYE-003, EYE-004, EYE-007) ────────────────────────────────────────────

def test_looking_straight_out_centers_the_iris():
    assert iris_offset(LEFT_WINDOW, (-1.6, 10.0, 5.0)) == pytest.approx((0.0, 0.0), abs=1e-9)


def test_iris_moves_toward_the_point():
    x, y = iris_offset(LEFT_WINDOW, (2.0, 3.0, 1.0))     # to the right and below
    assert x > 0 and y > 0                               # sketch y points down
    x, y = iris_offset(LEFT_WINDOW, (-5.0, 3.0, 8.0))    # to the left and above
    assert x < 0 and y < 0


def test_iris_stays_inside_its_travel():
    for point in [(50, 0.1, -20), (-50, 0.1, 30), (0, -3, 0)]:
        x, y = iris_offset(RIGHT_WINDOW, point)
        assert abs(x) <= MAX_X and abs(y) <= MAX_Y


def test_eyes_converge_on_a_close_kid_and_go_parallel_far_away():
    kid = (0.0, 2.5, 1.0)
    left, right = iris_offset(LEFT_WINDOW, kid)[0], iris_offset(RIGHT_WINDOW, kid)[0]
    assert left > 0 > right                  # both turn in toward the middle
    far = (0.0, 200.0, 1.0)
    assert abs(iris_offset(LEFT_WINDOW, far)[0] - iris_offset(RIGHT_WINDOW, far)[0]) < 1.0


def test_pupil_glides_to_a_look_point_with_small_movements_left():
    s = EyeState(LEFT_WINDOW, rng=random.Random(4))
    target = (2.0, 3.0, 1.0)
    s.look_at(target)
    frames = run(s, 1.0, brain=True)
    goal = iris_offset(LEFT_WINDOW, target)
    assert abs(frames[5].gaze[0] - goal[0]) > 5                 # glides, not a jump
    end = frames[-1].gaze
    assert abs(end[0] - goal[0]) < 3 and abs(end[1] - goal[1]) < 3
    assert len({f.gaze for f in frames[-20:]}) > 1             # never frozen


def test_idle_wanders_even_with_the_brain_present():
    s = EyeState(rng=random.Random(5))
    s.look_idle()
    frames = run(s, 8, brain=True)
    assert len({round(f.gaze[0]) for f in frames}) > 5


# ── Config (EYE-013, EYE-016, EYE-017, ICD-005, ICD-015) ────────────────────────

def _icd_schema(icd_id: str) -> dict:
    from tools.reqs.load import load
    return load(REPO_ROOT).icds[icd_id]["files"][0]["payload_schema"]


def test_site_config_matches_icd_015():
    from tools.reqs.schema import problems
    site = yaml.safe_load((REPO_ROOT / "config/site.yaml").read_text())
    assert problems(site, _icd_schema("ICD-015")) == []


def test_halloween_theme_matches_icd_005():
    from tools.reqs.schema import problems
    settings = yaml.safe_load((REPO_ROOT / "themes/halloween/settings.yaml").read_text())
    assert problems(settings, _icd_schema("ICD-005")) == []


def test_window_settings_load_for_both_eyes():
    left, right = load_window("left"), load_window("right")
    assert left.window_m == (0.686, 1.219) and left.rotate_deg == 90
    assert right.window_m == (0.914, 1.219) and right.mirror


def test_bad_site_config_says_what_is_wrong(tmp_path):
    path = tmp_path / "site.yaml"
    path.write_text("eyes: {left: {position_m: {x: 1}}}\n")
    with pytest.raises(ConfigError, match="eyes.left"):
        load_window("left", path)
    with pytest.raises(ConfigError, match="no site config"):
        load_window("left", tmp_path / "missing.yaml")


def test_theme_colors_load_and_a_broken_theme_falls_back(tmp_path):
    theme = load_theme("halloween")
    assert theme.iris_color == hex_color("#7a55e0") and theme.blink_ms == 200
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "settings.yaml").write_text("eyes: [not, a, mapping]\n")
    assert load_theme("broken", tmp_path) == DEFAULT_THEME
    assert load_theme("missing", tmp_path) == DEFAULT_THEME


# ── Drawing (EYE-001, EYE-010, EYE-013), on the CPU renderer ────────────────────

@pytest.fixture(scope="module")
def gl():
    from eyes.render import offscreen
    try:
        ctx, _ = offscreen((8, 8), software=True)
    except Exception as err:   # no OpenGL at all on this machine
        pytest.skip(f"no OpenGL: {err}")
    return ctx


def _draw(gl, window, projector, frame, long_side=200):
    from eyes.render import EyeRenderer, output_size
    size = output_size(window, long_side, projector)
    fbo = gl.simple_framebuffer(size)
    r = EyeRenderer(gl, size, window, DEFAULT_THEME, projector, fbo)
    r.draw(frame)
    return size, r.read_rgba()


def _pixel(size, data, x, y):
    i = (y * size[0] + x) * 4
    return tuple(data[i:i + 3])


NEUTRAL = Frame(EXPRESSIONS["neutral"], (0.0, 0.0))


def test_output_is_shaped_like_the_window():
    from eyes.render import output_size
    left = load_window("left")
    assert output_size(left, 400, projector=False) == (225, 400)     # tall, as seen from the street
    assert output_size(left, 400, projector=True) == (400, 225)      # projector on its side
    assert output_size(load_window("right"), 400, projector=True) == (300, 400)


def test_eye_draws_pupil_in_the_middle_and_black_around(gl):
    size, data = _draw(gl, load_window("right"), False, NEUTRAL)
    assert _pixel(size, data, 0, 0) == (11, 11, 18)                   # background, #0b0b12
    assert _pixel(size, data, size[0] // 2, size[1] // 2) == (20, 15, 36)   # pupil, #140f24


def test_projector_view_is_the_street_view_mirrored(gl):
    right = load_window("right")                                      # rotate 0, mirror on
    looking = Frame(EXPRESSIONS["happy"], (30.0, 10.0))
    size, street = _draw(gl, right, False, looking)
    _, projector = _draw(gl, right, True, looking)
    w = size[0]
    for y in range(0, size[1], 7):
        for x in range(0, w, 7):
            assert _pixel(size, street, x, y) == _pixel(size, projector, w - 1 - x, y)


def test_closed_eye_shows_no_white(gl):
    size, data = _draw(gl, load_window("right"), False, Frame(EXPRESSIONS["asleep"], (0.0, 0.0)))
    sclera = tuple(round(c * 255) for c in DEFAULT_THEME.sclera_color)
    assert all(_pixel(size, data, x, y) != sclera for y in range(0, size[1], 3) for x in range(0, size[0], 3))


def test_eye_shapes_fill_more_of_the_tall_window(gl):
    """oval < stretch < window: how much of the left window is lit (not background)."""
    from eyes.render import layout
    assert layout((225, 400), 0.9, "oval")[1] == (1.0, 1.0)
    left = load_window("left")
    lit = {}
    for shape in ("oval", "stretch", "window"):
        from eyes.render import EyeRenderer, output_size
        size = output_size(left, 200, False)
        fbo = gl.simple_framebuffer(size)
        r = EyeRenderer(gl, size, left, DEFAULT_THEME, False, fbo, shape)
        r.draw(NEUTRAL)
        data = r.read_rgba()
        lit[shape] = sum(1 for i in range(0, len(data), 4) if tuple(data[i:i + 3]) != (11, 11, 18))
    assert lit["oval"] < lit["stretch"] < lit["window"]
    with pytest.raises(ValueError):
        layout((10, 10), 0.9, "square")
