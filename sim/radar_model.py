"""The fake radar's brains-free core: pretend kids in, ESPHome LD2450 messages out.

No window and no MQTT here, so it's easy to test. `sim/fake_radar.py` draws the kids
and sends what this produces.

What it copies from the real radar (ICD-002, from ESPHome's source):
- Up to 3 slots. A kid keeps their slot while the radar can see them; a newly seen kid
  takes the lowest free slot.
- A radar "frame" `frame_hz` times a second (10, as our ESPHome config will set).
- x and y in whole millimeters relative to the radar; speed in mm/s, in steps of 10,
  negative when moving toward the radar and positive when moving away.
- A value is sent only when it changes, and once more one frame after it stops
  changing (ESPHome's timeout filter).
- An empty slot sends "nan" for x, y and speed (once, when it empties).
- target_count on change, the same way.
- Kids outside the radar's view (behind it, beyond 6 m or 60 degrees) or in the blind
  spot by the door (site config door_zone_mm, TBD-029) aren't seen (SIM-003).
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

from shared import topics
from shared.messages import radar_targets as radar
from shared.radar_frame import RadarSite, house_to_radar, in_view

NAN = "nan"


@dataclass
class Kid:
    """A pretend visitor, standing at (x, y) on the ground in house meters."""
    x: float
    y: float
    name: str = ""


@dataclass
class _Value:
    """One ESPHome sensor: what it last sent, and whether a repeat is due."""
    sent: str | None = None
    repeat_due: bool = False

    def frame(self, new: str) -> str | None:
        """The payload to send this frame, or None."""
        if new != self.sent:
            self.sent, self.repeat_due = new, new != NAN
            return new
        if self.repeat_due:              # the timeout filter's one repeat
            self.repeat_due = False
            return new
        return None


@dataclass
class _Slot:
    kid: Kid | None = None
    history: deque = field(default_factory=deque)   # (time, distance_mm)


class RadarModel:
    def __init__(self, site: RadarSite, frame_hz: float = 10.0, jitter_mm: float = 0.0,
                 speed_window_s: float = 0.3, rng: random.Random | None = None) -> None:
        self.site = site
        self.frame_s = 1.0 / frame_hz
        self.jitter_mm = jitter_mm
        self.speed_window_s = speed_window_s
        self.rng = rng or random.Random()
        self.slots = [_Slot() for _ in range(topics.RADAR_MAX_TARGETS)]
        self.values = {topic: _Value() for topic in self._all_topics()}
        self.next_frame_at: float | None = None

    @staticmethod
    def _all_topics() -> list[str]:
        out = [topics.radar_target(n, f) for n in range(1, topics.RADAR_MAX_TARGETS + 1)
               for f in topics.RADAR_TARGET_FIELDS]
        return out + [topics.RADAR_TARGET_COUNT]

    # -- what the radar sees -------------------------------------------------------

    def sees(self, kid: Kid) -> bool:
        """True if the radar can see this kid (in view and not in the door blind spot)."""
        x_mm, y_mm = house_to_radar(kid.x, kid.y, self.site)
        if not in_view(x_mm, y_mm):
            return False
        zone = self.site.door_zone
        return not (zone and zone.contains(x_mm, y_mm))

    def slot_of(self, kid: Kid) -> int | None:
        """The slot (1-3) the radar has this kid in, or None if it can't see them."""
        for n, slot in enumerate(self.slots, start=1):
            if slot.kid is kid:
                return n
        return None

    def _assign_slots(self, kids: list[Kid]) -> None:
        seen = [k for k in kids if self.sees(k)]
        for slot in self.slots:
            if slot.kid is not None and not any(slot.kid is k for k in seen):
                slot.kid = None
                slot.history.clear()
        for kid in seen:
            if self.slot_of(kid) is None:
                free = next((s for s in self.slots if s.kid is None), None)
                if free is None:
                    break                   # the LD2450 tracks 3 at most
                free.kid = kid

    # -- one radar frame -----------------------------------------------------------

    def frame(self, now: float, kids: list[Kid]) -> list[tuple[str, bytes]]:
        """One radar frame: the (topic, payload) pairs to publish now."""
        self._assign_slots(kids)
        readings: dict[str, str] = {}
        count = 0
        for n, slot in enumerate(self.slots, start=1):
            if slot.kid is None:
                x = y = speed = NAN
            else:
                count += 1
                x_mm, y_mm = house_to_radar(slot.kid.x, slot.kid.y, self.site)
                if self.jitter_mm:
                    x_mm += self.rng.gauss(0, self.jitter_mm)
                    y_mm += self.rng.gauss(0, self.jitter_mm)
                x, y = str(round(x_mm)), str(round(y_mm))
                speed = str(self._speed(slot, now, math.hypot(x_mm, y_mm)))
            readings[topics.radar_target(n, "x")] = x
            readings[topics.radar_target(n, "y")] = y
            readings[topics.radar_target(n, "speed")] = speed
        readings[topics.RADAR_TARGET_COUNT] = str(count)

        out = []
        for topic, text in readings.items():
            send = self.values[topic].frame(text)
            if send is not None:
                kind = "target count" if topic == topics.RADAR_TARGET_COUNT else "target value"
                out.append((topic, radar.encode(kind, send)))
        return out

    def _speed(self, slot: _Slot, now: float, distance_mm: float) -> int:
        """Change in distance from the radar, mm/s in steps of 10 (+ away, - toward)."""
        slot.history.append((now, distance_mm))
        while len(slot.history) > 1 and now - slot.history[0][0] > self.speed_window_s:
            slot.history.popleft()
        (t0, d0), (t1, d1) = slot.history[0], slot.history[-1]
        if t1 - t0 <= 0:
            return 0
        return int(round((d1 - d0) / (t1 - t0) / 10.0)) * 10

    def resend_all(self) -> None:
        """Send every value again at the next frame (ESPHome does this on reconnecting)."""
        for value in self.values.values():
            value.sent = None

    def due(self, now: float) -> bool:
        """True when it's time for the next frame (call this every screen frame)."""
        if self.next_frame_at is None or now >= self.next_frame_at:
            self.next_frame_at = (now if self.next_frame_at is None else self.next_frame_at) + self.frame_s
            if self.next_frame_at < now:            # fell behind (window dragged?): catch up
                self.next_frame_at = now + self.frame_s
            return True
        return False
