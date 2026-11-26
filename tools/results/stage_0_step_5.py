"""Make the figures for docs/results/stage-0-step-5/ from the real house preview.

    .venv/bin/python -m tools.results.stage_0_step_5              # on the GPU (EGL)
    .venv/bin/python -m tools.results.stage_0_step_5 --software   # without a GPU

Each figure is sim/house_preview.py's own drawing (the real eye renderer, warped onto
the photo), offscreen. The eyes look at a pretend kid 0.8 m right of center: on the
sidewalk (6 m out) for the comparisons, and on the walk (4 m) for the expressions.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from unittest import mock

import pygame

from eyes.config import load_theme, load_window
from sim.house_layout import SIDES, load_layout
import eyes.render
from sim.house_preview import DUSK, MODE_TEXT, MODES, render_png

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "results" / "stage-0-step-5"
HEIGHT = 1000
SIDEWALK = (0.8, 6.0, 1.0)           # house m
WALK = (0.8, 4.0, 1.0)
CROP = (250, 290, 320, 130)          # the two windows, at HEIGHT (x, y, w, h)
ZOOM = 2


def crop(path: Path) -> pygame.Surface:
    img = pygame.image.load(str(path)).subsurface(CROP).copy()
    return pygame.transform.smoothscale(img, (CROP[2] * ZOOM, CROP[3] * ZOOM))


def grid(tiles: list[tuple[str, pygame.Surface]], cols: int, path: Path) -> None:
    """Tiles with a caption under each, on a dark background."""
    font = pygame.font.Font(None, 30)
    w, h = tiles[0][1].get_size()
    rows = (len(tiles) + cols - 1) // cols
    out = pygame.Surface((cols * w + (cols + 1) * 12, rows * (h + 40) + 12))
    out.fill((24, 24, 26))
    for i, (label, img) in enumerate(tiles):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 40)
        out.blit(img, (x, y))
        out.blit(font.render(label, True, (235, 235, 230)), (x + 4, y + h + 8))
    pygame.image.save(out, str(path))


def old_layout(size, eye_size, shape):
    """The full-window rule before 2026-11-26 (iris sized to the whole sketch), for the
    before/after figure only."""
    if shape != "square":
        return ORIGINAL_LAYOUT(size, eye_size, shape)
    scale = min(size[0] / 300, size[1] / 400)
    return scale, (size[0] / (236 * scale), size[1] / (320 * scale)), True


ORIGINAL_LAYOUT = eyes.render.layout


def curve(x0: float, x1: float, y: float, dip: float, n: int = 7) -> list[tuple[float, float]]:
    """n points from x0 to x1 at height y, sagging by `dip` px in the middle (a smile)."""
    return [(x0 + (x1 - x0) * i / (n - 1), y + dip * math.sin(math.pi * i / (n - 1))) for i in range(n)]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--software", action="store_true")
    args = p.parse_args(argv)
    pygame.init()
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    tmp = OUT / "figures" / "_tmp.png"
    layout = load_layout()
    windows = {s: load_window(s) for s in SIDES}
    theme = load_theme("halloween")
    render = lambda path, **kw: render_png(path, layout, windows, theme, HEIGHT, software=args.software, **kw)  # noqa: E731

    render(OUT / "figures" / "01-house.png", expression="neutral", dusk=1, look=SIDEWALK)
    render(OUT / "figures" / "02-handles.png", handles=True)

    tiles = []
    for mode in MODES:
        render(tmp, mode=mode, expression="neutral", dusk=1, look=SIDEWALK)
        tiles.append((MODE_TEXT[mode], crop(tmp)))
    grid(tiles, 2, OUT / "figures" / "03-eye-modes.png")

    tiles = []
    for i, color in enumerate(layout.iris_colors):
        render(tmp, iris=i, expression="neutral", dusk=1, look=SIDEWALK)
        tiles.append((color + (" (theme)" if i == 0 else ""), crop(tmp)))
    grid(tiles, 2, OUT / "figures" / "04-iris-colors.png")

    tiles = []
    for name in ("neutral", "happy"):
        for where, point in (("sidewalk, 6 m", SIDEWALK), ("walk, 4 m", WALK)):
            render(tmp, expression=name, dusk=1, look=point)
            tiles.append((f"{name}, kid on the {where}", crop(tmp)))
    grid(tiles, 2, OUT / "figures" / "05-expressions.png")

    # Owner feedback, 2026-11-26 (gloss #26): bigger iris, panes, a less worried mouth.
    tiles = []
    with mock.patch("eyes.render.layout", old_layout):
        render(tmp, expression="neutral", dusk=1, look=SIDEWALK, panes=False)
    tiles.append(("before: iris sized to the whole sketch", crop(tmp)))
    render(tmp, expression="neutral", dusk=1, look=SIDEWALK, panes=False)
    tiles.append(("now: iris sized to the white (about 1.25x)", crop(tmp)))
    grid(tiles, 2, OUT / "figures" / "06-bigger-iris.png")

    tiles = []
    for on in (False, True):
        render(tmp, expression="neutral", dusk=1, look=SIDEWALK, panes=on)
        tiles.append(("window panes " + ("on" if on else "off"), crop(tmp)))
    for mode in ("oval", "matched"):
        render(tmp, mode=mode, expression="neutral", dusk=1, look=SIDEWALK)
        tiles.append((f"panes on, {MODE_TEXT[mode]}", crop(tmp)))
    grid(tiles, 2, OUT / "figures" / "07-panes.png")

    (ux0, uy), (ux1, _) = layout.lips["upper"][0], layout.lips["upper"][-1]
    (lx0, ly), (lx1, _) = layout.lips["lower"][0], layout.lips["lower"][-1]
    mouths = [("flat (as now)", layout.lips),
              ("lower lip curved into a smile", {"upper": layout.lips["upper"], "lower": curve(lx0, lx1, ly, 90)}),
              ("both lips curved", {"upper": curve(ux0, ux1, uy, 45), "lower": curve(lx0, lx1, ly, 110)})]
    small = []
    for label, lips in mouths:
        alt = copy.deepcopy(layout)
        alt.lips = lips
        render_png(tmp, alt, windows, theme, HEIGHT, expression="happy", dusk=1, look=SIDEWALK,
                   software=args.software)
        img = pygame.image.load(str(tmp)).subsurface((180, 250, 460, 380)).copy()
        small.append((label, img))
    grid(small, 3, OUT / "figures" / "08-mouth-shapes.png")
    tmp.unlink()

    left, right = windows["left"], windows["right"]
    results = {
        "window_corners_photo_px": layout.windows,
        "glass_m": {"left": left.window_m, "right": right.window_m},
        "glass_aspect_real": {s: round(w.window_m[0] / w.window_m[1], 3) for s, w in windows.items()},
        "glass_aspect_photo": {s: round((c[1][0] - c[0][0]) / (c[3][1] - c[0][1]), 3)
                               for s, c in layout.windows.items()},
        "modes": MODE_TEXT, "iris_colors": layout.iris_colors, "dusk_steps": DUSK,
        "renderer": "software (llvmpipe)" if args.software else "GPU (EGL)",
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps(results["glass_aspect_real"]), json.dumps(results["glass_aspect_photo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
