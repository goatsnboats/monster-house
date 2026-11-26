"""House preview (SIM-005, SIM-006): the warp onto the photo's windows, the layout file,
the eye modes, and a real offscreen render."""

from __future__ import annotations

import shutil

import pygame
import pytest

from eyes.config import load_theme, load_window
from eyes.link import EyeLink
from shared import topics
from sim.house_layout import (LAYOUT_FILE, SIDES, UNIT_SQUARE, apply, homography, invert, load_layout,
                              photo_to_eye, save_layout)
from sim.house_preview import eye_window, render_png

TILTED = [(602, 650), (690, 656), (688, 817), (600, 812)]


def test_the_warp_puts_the_eye_corners_on_the_window_corners():
    h = homography(UNIT_SQUARE, TILTED)
    for src, dst in zip(UNIT_SQUARE, TILTED):
        assert apply(h, src) == pytest.approx(dst)
    back = photo_to_eye(TILTED)
    for src, dst in zip(UNIT_SQUARE, TILTED):
        assert apply(back, dst) == pytest.approx(src, abs=1e-9)
    assert apply(invert(h), apply(h, (0.3, 0.7))) == pytest.approx((0.3, 0.7))


def test_corners_in_a_line_are_refused():
    with pytest.raises(ValueError):
        photo_to_eye([(0, 0), (1, 1), (2, 2), (3, 3)])


def test_layout_saves_dragged_points_and_keeps_the_comments(tmp_path):
    path = tmp_path / "layout.yaml"
    shutil.copy(LAYOUT_FILE, path)
    layout = load_layout(path)
    layout.windows["left"][0] = (600.4, 649.6)
    layout.lips["upper"][1] = (800, 930)
    save_layout(layout, path)
    again = load_layout(path)
    assert again.windows["left"][0] == (600, 650)
    assert again.lips["upper"][1] == (800, 930)
    assert again.windows["right"] == layout.windows["right"]
    assert path.read_text().count("#") == LAYOUT_FILE.read_text().count("#")


def test_matched_eyes_are_the_same_size_in_meters():
    left, right = load_window("left"), load_window("right")
    small = left if left.window_m[0] < right.window_m[0] else right
    unit = lambda w: min(w.window_m[0] / 300, w.window_m[1] / 400)   # noqa: E731
    sizes = [eye_window(w, "matched", small)[0].eye_size * unit(w) for w in (left, right)]
    assert sizes[0] == pytest.approx(sizes[1])
    assert eye_window(right, "matched", small)[1] == "oval"
    assert eye_window(right, "window", small) == (right, "square")


def test_the_preview_listens_but_never_says_it_is_an_eye():
    link = EyeLink(None, client_name="house-preview-test")
    assert link.status_topic is None
    assert topics.eye_status("left") != link.status_topic


def _green_pixels(img: pygame.Surface, box) -> int:
    x0, y0, x1, y1 = box
    n = 0
    for x in range(x0, x1, 2):
        for y in range(y0, y1, 2):
            r, g, b, *_ = img.get_at((x, y))
            n += g > r + 60 and g > b + 60
    return n


def test_the_eyes_cover_the_green_windows_in_a_real_render(tmp_path):
    """Drawn offscreen in software: the photo's lit green windows are replaced by eyes."""
    layout = load_layout()
    out = tmp_path / "preview.png"
    render_png(out, layout, {s: load_window(s) for s in SIDES}, load_theme("halloween"), 500,
               software=True, settle_s=0.2)
    img = pygame.image.load(str(out))
    photo = pygame.transform.smoothscale(pygame.image.load(str(layout.photo)), img.get_size())
    for side in SIDES:
        xs = [p[0] for p in layout.windows[side]]
        ys = [p[1] for p in layout.windows[side]]
        box = (int(min(xs) * 500 / 2040) + 3, int(min(ys) * 500 / 2040) + 3,
               int(max(xs) * 500 / 2040) - 3, int(max(ys) * 500 / 2040) - 3)
        assert _green_pixels(photo, box) > 20           # lit green in the photo
        assert _green_pixels(img, box) == 0             # an eye now
