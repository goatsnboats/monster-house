"""The brain's view of the radar (ICD-002): ESPHome's separate value messages, put back
together into up to three targets.

ESPHome sends x, y and speed for each slot as separate plain-text messages, and only
when they change. An empty slot reads "nan". So the brain keeps the last value of
each, and a slot counts as a target while both its x and y are numbers.

Slots aren't people: when someone leaves, the radar may give their slot to someone
else. Telling visitors apart, coming from going, and holding visitors lost at the door
come in Step 4 (SHW-010, SHW-011).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shared import topics
from shared.messages import radar_targets as radar

# topic -> (slot, field), built from shared/topics.py so no topic string is written here.
_VALUE_TOPICS = {topics.radar_target(n, f): (n, f)
                 for n in range(1, topics.RADAR_MAX_TARGETS + 1) for f in topics.RADAR_TARGET_FIELDS}

SUBSCRIPTIONS = [topics.RADAR_SENSOR_ALL, topics.RADAR_STATUS]


@dataclass(frozen=True)
class Target:
    """One radar slot with someone in it: radar millimeters (ICD-002)."""
    slot: int
    x_mm: float
    y_mm: float
    speed_mm_s: float | None


def _number(text: str) -> float | None:
    """A radar value as a number, or None for "nan" (empty slot) or anything unreadable."""
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


class RadarState:
    """The latest values from the radar. Feed it every message with `update`."""

    def __init__(self) -> None:
        self.online = False
        self.count: int | None = None
        self._values: dict[tuple[int, str], float | None] = {}

    def update(self, topic: str, payload: bytes) -> bool:
        """Take one radar message. Returns False if it isn't a radar message we use."""
        if topic == topics.RADAR_STATUS:
            status = radar.decode("status", payload)
            if status is None:
                return False
            self.online = status == "online"
            return True
        if topic == topics.RADAR_TARGET_COUNT:
            count = radar.decode("target count", payload)
            if count is None:
                return False
            self.count = None if count == "nan" else int(count)
            return True
        key = _VALUE_TOPICS.get(topic)
        if key is None:
            return False
        text = radar.decode("target value", payload)
        if text is None:
            return False
        self._values[key] = _number(text)
        return True

    def targets(self) -> list[Target]:
        """Every slot that has someone in it now. Empty while the radar is offline."""
        if not self.online:
            return []
        out = []
        for n in range(1, topics.RADAR_MAX_TARGETS + 1):
            x, y = self._values.get((n, "x")), self._values.get((n, "y"))
            if x is not None and y is not None:
                out.append(Target(n, x, y, self._values.get((n, "speed"))))
        return out
