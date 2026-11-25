"""Who is out there: radar slots turned into visitors (SHW-007, SHW-010, SHW-011).

The radar reports up to three slots, not people: a slot can jump to someone else. Each
tick the tracker matches the targets it sees to the visitors it knows (nearest first),
smooths each visitor's position, and works out whether they are coming toward the house
or going away from it, from how far they moved over about half a second (TBD-030, closed).

A visitor lost inside the door zone is held as "at the door" for the theme's door hold
(TBD-028), since the radar can't see the doorstep. They still count as here, so the
goodbye timer doesn't start while a kid is getting candy.

Positions are house meters on the ground (x, y); see shared/radar_frame.py.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from shared.radar_frame import RadarSite, house_to_radar, radar_to_house

SMOOTH_S = 0.15            # smoothing time constant: removes jitter, adds about this much lag
MATCH_M = 1.0              # a target this close to a visitor's last position is that visitor
DOOR_MATCH_M = 1.5         # ... and this close for a visitor held at the door
LOST_GRACE_S = 0.5         # a visitor missing this long (outside the door zone) has left
HEADING_WINDOW_S = 0.5     # coming vs going: position change over this long (TBD-030)
HEADING_MIN_M_S = 0.25     # slower than this along y is neither coming nor going


@dataclass
class Visitor:
    id: int
    x: float
    y: float
    first_seen: float
    last_seen: float
    heading: str | None = None           # "coming", "going", or None (standing still / not known)
    at_door_since: float | None = None
    marked: set = field(default_factory=set, repr=False)   # headings already announced
    _history: deque = field(default_factory=deque, repr=False)

    @property
    def at_door(self) -> bool:
        return self.at_door_since is not None

    def distance(self, x: float, y: float) -> float:
        return math.hypot(self.x - x, self.y - y)


@dataclass(frozen=True)
class Event:
    kind: str                # "arrived", "coming", "going", "at door", "left"
    visitor: Visitor


class Tracker:
    def __init__(self, site: RadarSite, door_hold_s: float) -> None:
        self.site = site
        self.door_hold_s = door_hold_s
        self.visitors: dict[int, Visitor] = {}
        self._next_id = 1
        self._last_tick: float | None = None

    def range_m(self, v: Visitor) -> float:
        """How far a visitor is from the radar, on the ground."""
        mx, my, _ = self.site.mount
        return math.hypot(v.x - mx, v.y - my)

    def in_door_zone(self, x: float, y: float) -> bool:
        zone = self.site.door_zone
        return zone is not None and zone.contains(*house_to_radar(x, y, self.site))

    def update(self, now: float, targets_mm: list[tuple[float, float]]) -> list[Event]:
        """Take the targets the radar sees now (radar mm) and return what changed."""
        dt = 0.0 if self._last_tick is None else max(0.0, now - self._last_tick)
        self._last_tick = now
        points = [radar_to_house(x, y, self.site)[:2] for x, y in targets_mm]
        events: list[Event] = []

        # Match nearest pairs first, each visitor and each target at most once.
        pairs = sorted((v.distance(*p), v.id, i) for v in self.visitors.values()
                       for i, p in enumerate(points))
        matched_v: set[int] = set()
        matched_p: set[int] = set()
        for dist, vid, i in pairs:
            if vid in matched_v or i in matched_p:
                continue
            v = self.visitors[vid]
            if dist <= (DOOR_MATCH_M if v.at_door else MATCH_M) or (v.at_door and self.in_door_zone(*points[i])):
                matched_v.add(vid)
                matched_p.add(i)
                self._seen(v, points[i], now, dt, events)

        for i, (x, y) in enumerate(points):
            if i not in matched_p:
                v = Visitor(self._next_id, x, y, first_seen=now, last_seen=now)
                v._history.append((now, x, y))
                self._next_id += 1
                self.visitors[v.id] = v
                events.append(Event("arrived", v))

        for vid in list(self.visitors):
            v = self.visitors[vid]
            if vid in matched_v or v.last_seen == now:
                continue
            if v.at_door:
                if now - v.at_door_since >= self.door_hold_s:
                    events.append(Event("left", self.visitors.pop(vid)))
            elif self.in_door_zone(v.x, v.y):
                v.at_door_since = now
                events.append(Event("at door", v))
            elif now - v.last_seen >= LOST_GRACE_S:
                events.append(Event("left", self.visitors.pop(vid)))
        return events

    def _seen(self, v: Visitor, point: tuple[float, float], now: float, dt: float,
              events: list[Event]) -> None:
        k = 1.0 - math.exp(-dt / SMOOTH_S) if dt > 0 else 1.0
        v.x += (point[0] - v.x) * k
        v.y += (point[1] - v.y) * k
        v.last_seen = now
        v.at_door_since = None
        v._history.append((now, v.x, v.y))
        while len(v._history) > 1 and now - v._history[1][0] >= HEADING_WINDOW_S:
            v._history.popleft()
        then, _, y0 = v._history[0]
        if now - then >= HEADING_WINDOW_S - 1e-6:
            speed = (v.y - y0) / (now - then)          # + is away from the house
            heading = "coming" if speed <= -HEADING_MIN_M_S else "going" if speed >= HEADING_MIN_M_S else None
            v.heading = heading
            if heading is not None and heading not in v.marked:    # announce each once
                v.marked.add(heading)
                events.append(Event(heading, v))
