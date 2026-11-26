"""The house preview's layout (sim/house_preview.yaml) and the math to put an eye
image onto a window seen at an angle in the photo.

A window in the photo is a four-cornered shape, not a rectangle (the camera sees it a
little from the side). The homography H maps the eye image's corners (0..1 square)
onto the window's four corners; the shader uses its inverse to find, for each photo
pixel, which eye pixel lands there. Plain Python: it's a 3x3 matrix, solved only when a
corner is dragged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LAYOUT_FILE = Path(__file__).resolve().parent / "house_preview.yaml"
SIDES = ("left", "right")

Point = tuple[float, float]
Matrix = list[list[float]]


class LayoutError(Exception):
    """The layout file is missing or wrong; the message says what to fix."""


@dataclass
class HouseLayout:
    photo: Path
    windows: dict[str, list[Point]]                # side -> TL, TR, BR, BL (photo px)
    lips: dict[str, list[Point]] = field(default_factory=dict)
    lip_color: str = "#c050ff"
    iris_colors: list[str] = field(default_factory=list)


def _points(raw, n: int | None = None) -> list[Point]:
    pts = [(float(x), float(y)) for x, y in raw]
    if n is not None and len(pts) != n:
        raise ValueError(f"expected {n} points, got {len(pts)}")
    return pts


def load_layout(path: Path = LAYOUT_FILE) -> HouseLayout:
    try:
        raw = yaml.safe_load(path.read_text())
        return HouseLayout(
            photo=REPO_ROOT / raw["photo"],
            windows={side: _points(raw["windows"][side], 4) for side in SIDES},
            lips={name: _points(pts) for name, pts in (raw.get("lips") or {}).items()},
            lip_color=str(raw.get("lip_color", "#c050ff")),
            iris_colors=[str(c) for c in raw.get("iris_colors", [])],
        )
    except FileNotFoundError:
        raise LayoutError(f"no house preview layout at {path}") from None
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as err:
        raise LayoutError(f"{path}: the layout is incomplete or wrong ({err!r})") from None


def save_layout(layout: HouseLayout, path: Path = LAYOUT_FILE) -> None:
    """Write the dragged positions back, keeping the file's comments (only the numbers change)."""
    lines = path.read_text().splitlines()
    fmt = lambda pts: "[" + ", ".join(f"[{round(x)}, {round(y)}]" for x, y in pts) + "]"   # noqa: E731
    values = {**{s: layout.windows[s] for s in SIDES}, **layout.lips}
    out = []
    for line in lines:
        key = line.strip().split(":", 1)[0]
        if line.startswith("  ") and key in values and ":" in line:
            indent = line[:len(line) - len(line.lstrip())]
            pad = " " * max(1, 7 - len(key))
            line = f"{indent}{key}:{pad}{fmt(values[key])}"
        out.append(line)
    path.write_text("\n".join(out) + "\n")


# ── Homography ──────────────────────────────────────────────────────────────────

def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("the four corners don't make a usable shape")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    return [m[i][n] / m[i][i] for i in range(n)]


def homography(src: list[Point], dst: list[Point]) -> Matrix:
    """The 3x3 matrix taking each of the four src points to the matching dst point."""
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = _solve(a, b) + [1.0]
    return [h[0:3], h[3:6], h[6:9]]


def apply(h: Matrix, p: Point) -> Point:
    x, y = p
    w = h[2][0] * x + h[2][1] * y + h[2][2]
    return ((h[0][0] * x + h[0][1] * y + h[0][2]) / w, (h[1][0] * x + h[1][1] * y + h[1][2]) / w)


def invert(h: Matrix) -> Matrix:
    (a, b, c), (d, e, f), (g, i, j) = h
    det = a * (e * j - f * i) - b * (d * j - f * g) + c * (d * i - e * g)
    if abs(det) < 1e-12:
        raise ValueError("the four corners don't make a usable shape")
    return [[(e * j - f * i) / det, (c * i - b * j) / det, (b * f - c * e) / det],
            [(f * g - d * j) / det, (a * j - c * g) / det, (c * d - a * f) / det],
            [(d * i - e * g) / det, (b * g - a * i) / det, (a * e - b * d) / det]]


UNIT_SQUARE: list[Point] = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def photo_to_eye(corners: list[Point]) -> Matrix:
    """Photo pixel -> eye image (0..1, top-left origin) for a window with these corners."""
    return invert(homography(UNIT_SQUARE, corners))
