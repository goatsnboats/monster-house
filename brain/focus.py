"""Which visitor the eyes look at (SHW-008, SHW-012, SHW-013).

- A new arrival wins at once.
- A visitor who turns to go becomes the focus until they leave (to wave them off).
- Otherwise hold one visitor for a random 3-6 s (theme focus_hold_s), then switch to
  someone else, preferring visitors coming toward the house over those standing still,
  and those over visitors going; the closest breaks ties.

`choose` says whether the eyes switched from one visitor to another, so the brain can
blink on the switch (owner, 2026-11-24).
"""

from __future__ import annotations

import random

from brain.visitors import Event, Tracker, Visitor

_RANK = {"coming": 0, None: 1, "going": 2}


class Focus:
    def __init__(self, hold_s: tuple[float, float], rng: random.Random | None = None) -> None:
        self.hold_s = hold_s
        self.rng = rng or random.Random()
        self.current: int | None = None
        self._until = 0.0
        self._seeing_off = False       # holding a visitor who is going, until they leave

    def choose(self, now: float, tracker: Tracker, events: list[Event]) -> tuple[Visitor | None, bool]:
        """The focus visitor now (or None), and True if the eyes switched visitors."""
        visitors = tracker.visitors
        before = self.current if self.current in visitors else None
        if before is None:
            self._seeing_off = False

        arrivals = [e.visitor for e in events if e.kind == "arrived" and e.visitor.id in visitors]
        going = [e.visitor for e in events if e.kind == "going" and e.visitor.id in visitors]
        if arrivals:
            self._set(arrivals[-1], now, seeing_off=False)
        elif going:
            self._set(going[-1], now, seeing_off=True)
        elif before is None or (now >= self._until and not self._seeing_off):
            others = [v for v in visitors.values() if v.id != before]
            if others:
                best = min(others, key=lambda v: (_RANK.get(v.heading, 1), tracker.range_m(v)))
                self._set(best, now, seeing_off=False)
            elif before is None:
                self.current = None
            else:
                self._until = now + self.rng.uniform(*self.hold_s)   # only one: keep looking

        after = self.current if self.current in visitors else None
        return (visitors.get(after) if after else None,
                before is not None and after is not None and after != before)

    def _set(self, v: Visitor, now: float, seeing_off: bool) -> None:
        self.current = v.id
        self._seeing_off = seeing_off
        self._until = now + self.rng.uniform(*self.hold_s)

    def glance(self, v: Visitor, now: float) -> None:
        """Look at this visitor now and hold them (a kid just seen coming, SHW-014)."""
        self._set(v, now, seeing_off=False)
