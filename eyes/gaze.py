"""Gaze math: from a look point on the house to where this eye's iris sits (EYE-003).

The brain sends one point in house coordinates (ICD-001, ICD-015): meters, x to the
right as seen from the street, y from the house toward the street, z up. Each eye works
out its own direction from its own window, so the two pupils angle slightly toward each
other for a close kid and look parallel for someone far away (architecture §2).

The result is an iris offset in "sketch units": the 300 x 400 space of
docs/reference/eye-sketch.html, x to the right and y down, as seen from the street.
"""

from __future__ import annotations

import math

# How far the iris may travel from the center, in sketch units (from the sketch).
MAX_X = 46.0
MAX_Y = 88.0

# The turn (in degrees) that moves the iris all the way to the edge. Beyond it the
# iris stays at the edge. A taste setting: bigger = calmer eyes.
FULL_TURN_DEG = 60.0


def iris_offset(window: tuple[float, float, float], point: tuple[float, float, float]) -> tuple[float, float]:
    """Iris offset (x, y) in sketch units for an eye in `window` looking at `point`.

    Both are (x, y, z) in house coordinates. Like a real eyeball, the iris moves by
    the sine of the turn, so it slows down as it nears the edge.
    """
    dx = point[0] - window[0]
    dy = point[1] - window[1]
    dz = point[2] - window[2]
    if dy <= 0:
        dy = 1e-3            # a point beside or behind the wall: look as far round as possible
    yaw = math.atan2(dx, dy)                       # + = to the right, as seen from the street
    pitch = math.atan2(dz, math.hypot(dx, dy))     # + = up
    full = math.sin(math.radians(FULL_TURN_DEG))
    x = _clamp(math.sin(yaw) / full) * MAX_X
    y = -_clamp(math.sin(pitch) / full) * MAX_Y    # sketch y points down
    return x, y


def _clamp(v: float) -> float:
    return max(-1.0, min(1.0, v))
