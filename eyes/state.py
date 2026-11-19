"""Everything an eye knows from moment to moment, with no drawing in it.

The renderer calls `update(dt)` once per frame and draws the `Frame` it gets back. The
commands (`set_expression`, `blink`, `look_at`, `look_idle`) come from the brain's
messages (ICD-001) or, during development, from the keyboard and mouse.

Kept free of OpenGL and MQTT so the behavior can be tested with a fake clock.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from eyes.expressions import EXPRESSIONS, Expression
from eyes.gaze import iris_offset

# Pupil glide: an ease-out that covers 20% of the remaining way per 60 fps frame, as in
# the sketch (EYE-004).
GLIDE_RATE = -math.log(1 - 0.2) * 60
# Micro-saccades: small jumps so the pupil never looks frozen (EYE-004).
MICRO_SIZE = 1.5                 # sketch units
MICRO_EVERY_S = (0.4, 1.5)
MICRO_RATE = 30.0                # how fast a micro-jump happens
# Wandering, when told to idle or when the brain goes quiet (EYE-006, EYE-007).
WANDER_RANGE = (40.0, 60.0)      # sketch units, x and y (from the sketch)
WANDER_EVERY_S = (1.2, 3.0)
MOUSE_HOLD_S = 2.5               # after the mouse moves, wait this long before wandering again
NO_BLINK_BELOW_OPEN = 0.2        # no blinking while the eye is (nearly) shut


@dataclass(frozen=True)
class Frame:
    """What to draw this frame."""
    expression: Expression       # with the blink already applied to `open`
    gaze: tuple[float, float]    # iris offset, sketch units, as seen from the street


class EyeState:
    def __init__(self, window_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
                 blink_every_s: tuple[float, float] = (2.5, 6.0), blink_ms: int = 200,
                 fallback_after_s: float = 5.0, rng: random.Random | None = None) -> None:
        """
        window_position: this eye's window center in house coordinates (site config).
        blink_every_s, blink_ms: the theme's blink timing, for the fallback timer.
        fallback_after_s: how long without a brain message before the eye looks after
            itself (TBD-023: the owner hasn't set it; 5 s until then).
        """
        self.window = window_position
        self.blink_every_s = blink_every_s
        self.blink_ms = blink_ms
        self.fallback_after_s = fallback_after_s
        self.rng = rng or random.Random()
        self.now = 0.0

        # Expression: eases from `_from` to `_to` over `_ms`, starting at `_start`.
        self._from = self._to = EXPRESSIONS["neutral"]
        self._start = 0.0
        self._ms = 0
        # Gaze, in sketch units.
        self.gaze = (0.0, 0.0)
        self.gaze_target = (0.0, 0.0)
        self.idle = True                     # wandering on its own until given a point
        self._last_mouse = -1e9
        self._next_wander = 0.0
        self._micro = (0.0, 0.0)
        self._micro_target = (0.0, 0.0)
        self._next_micro = 0.0
        # Blinks.
        self._blink_start = -1.0
        self._blink_ms = blink_ms
        self._next_own_blink = self._own_blink_gap()
        # When the brain was last heard from (never, so far).
        self._last_brain = -1e9

    # ── Commands ──────────────────────────────────────────────────────────────────

    def set_expression(self, name: str, ms: int = 300) -> bool:
        """Ease into a named expression over ms milliseconds. False if the name is unknown."""
        if name not in EXPRESSIONS:
            return False
        self._from = self.expression()
        self._to = EXPRESSIONS[name]
        self._start = self.now
        self._ms = max(0, ms)
        return True

    def blink(self, ms: int | None = None) -> None:
        """Close and open the lids over ms milliseconds (default: the theme's)."""
        if self._blink_start < 0:
            self._blink_start = self.now
            self._blink_ms = max(1, ms if ms is not None else self.blink_ms)

    def look_at(self, point: tuple[float, float, float]) -> None:
        """Look at a point in house coordinates."""
        self.idle = False
        self.gaze_target = iris_offset(self.window, point)

    def look_idle(self) -> None:
        """Wander and look around on its own (EYE-007)."""
        self.idle = True

    def aim_sketch(self, x: float, y: float) -> None:
        """Development: aim at a point in sketch space (300 x 400), e.g. the mouse."""
        clamp = lambda v: max(-1.0, min(1.0, v))  # noqa: E731
        self.gaze_target = (clamp((x - 150) / 170) * 46, clamp((y - 200) / 220) * 88)
        self._last_mouse = self.now

    def heard_from_brain(self) -> None:
        """Call on every message from the brain; keeps the fallback timer from starting."""
        self._last_brain = self.now

    # ── Queries ───────────────────────────────────────────────────────────────────

    @property
    def brain_present(self) -> bool:
        return self.now - self._last_brain < self.fallback_after_s

    def expression(self) -> Expression:
        """The current expression, part-way through any easing."""
        if self._ms == 0:
            return self._to
        t = min(1.0, (self.now - self._start) * 1000 / self._ms)
        return self._from.blend(self._to, t * t * (3 - 2 * t))   # smoothstep: ease in and out

    # ── Each frame ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> Frame:
        """Advance the clock by dt seconds and return what to draw."""
        self.now += dt
        expr = self.expression()

        # Wander when idle or when the brain has gone quiet (unless the mouse is in charge).
        wandering = self.idle or not self.brain_present
        if wandering and self.now - self._last_mouse > MOUSE_HOLD_S and self.now >= self._next_wander:
            self.gaze_target = (self.rng.uniform(-1, 1) * WANDER_RANGE[0], self.rng.uniform(-1, 1) * WANDER_RANGE[1])
            self._next_wander = self.now + self.rng.uniform(*WANDER_EVERY_S)

        # Glide toward the target (ease-out), plus micro-saccades.
        k = 1 - math.exp(-GLIDE_RATE * dt)
        self.gaze = tuple(g + (t - g) * k for g, t in zip(self.gaze, self.gaze_target))
        if self.now >= self._next_micro:
            self._micro_target = (self.rng.uniform(-1, 1) * MICRO_SIZE, self.rng.uniform(-1, 1) * MICRO_SIZE)
            self._next_micro = self.now + self.rng.uniform(*MICRO_EVERY_S)
        m = 1 - math.exp(-MICRO_RATE * dt)
        self._micro = tuple(c + (t - c) * m for c, t in zip(self._micro, self._micro_target))

        # The brain owns blinks; the eye blinks on its own only when the brain is quiet.
        if not self.brain_present and self.now >= self._next_own_blink:
            if self._to.open > NO_BLINK_BELOW_OPEN:
                self.blink()
            self._next_own_blink = self.now + self._own_blink_gap()
        factor = 1.0
        if self._blink_start >= 0:
            t = (self.now - self._blink_start) * 1000 / self._blink_ms
            if t >= 1:
                self._blink_start = -1.0
            else:
                factor = abs(1 - 2 * t)          # shut at the halfway point, as in the sketch

        shown = Expression(expr.open * factor, expr.low, expr.curve, expr.pupil, expr.spark)
        return Frame(shown, (self.gaze[0] + self._micro[0], self.gaze[1] + self._micro[1]))

    def _own_blink_gap(self) -> float:
        return self.rng.uniform(*self.blink_every_s)
