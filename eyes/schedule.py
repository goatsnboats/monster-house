"""A random-looking schedule that both eyes work out on their own from the clock.

While the eyes wander, or blink on their fallback timer, they get no messages telling
them when or where (EYE-006, EYE-007). If each eye rolled its own dice they'd drift
apart: one looking left while the other looks right. Instead, both eyes take their
"dice" from the time of day. Two eyes that agree on the time agree on every wander
point and every blink, with no messages at all. On the Pis that means their clocks
must be in sync, which NTP does to within a few milliseconds.

How it works: time is cut into equal windows. Each window has one event, at a random
moment early in the window, and the randomness comes from the window's number. With
windows of (lo + hi) / 2 and the event somewhere in the first (hi - lo) / 2 of each,
the gap between two events is always between lo and hi seconds.
"""

from __future__ import annotations

import math
import random


class ClockSchedule:
    def __init__(self, name: str, every_s: tuple[float, float]) -> None:
        lo, hi = every_s
        if not 0 < lo <= hi:
            raise ValueError(f"every_s must be 0 < lo <= hi, not {every_s!r}")
        self.name = name                       # different schedules, different dice
        self.window = (lo + hi) / 2
        self.spread = (hi - lo) / 2

    def _rng(self, n: int) -> random.Random:
        return random.Random(f"{self.name}:{n}")    # a string seed: the same in every process

    def event_time(self, n: int) -> float:
        return n * self.window + self._rng(n).random() * self.spread

    def last_event(self, t: float) -> int:
        """The number of the latest event at or before clock time t (seconds)."""
        n = math.floor(t / self.window)
        return n if self.event_time(n) <= t else n - 1

    def values(self, n: int, count: int) -> list[float]:
        """`count` random numbers from -1 to 1 belonging to event n."""
        rng = self._rng(n)
        rng.random()                           # the first number is the event's time
        return [rng.uniform(-1, 1) for _ in range(count)]
