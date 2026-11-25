"""Where the eyes should look (architecture §3b, "Turning radar data into a gaze").

PLACEHOLDER (Stage 0 Step 3): look at the target closest to the radar, at head height,
with no smoothing and no focus rules. Step 4 adds the filter and the focus choice
(new arrival wins, hold 3-6 s, closest breaks ties; SHW-007 to SHW-009).

The brain sends one point in house coordinates; each eye works out its own angle from
its own window (ICD-001, EYE-003).
"""

from __future__ import annotations

import math

from brain.radar import Target
from shared.radar_frame import RadarSite, radar_to_house


def closest(targets: list[Target]) -> Target | None:
    """The target nearest the radar, or None if there's nobody."""
    return min(targets, key=lambda t: math.hypot(t.x_mm, t.y_mm), default=None)


def look_point(targets: list[Target], site: RadarSite) -> tuple[float, float, float] | None:
    """The point to look at (house meters), or None to wander (nobody there)."""
    target = closest(targets)
    if target is None:
        return None
    return radar_to_house(target.x_mm, target.y_mm, site)


def visitor_point(visitor, site: RadarSite) -> tuple[float, float, float]:
    """Where to look for one tracked visitor (brain/visitors.py), in house meters: their
    head (site head height, SHW-006), or the door point while they're held at the door
    (SHW-012). Without a door point in the site config, their last seen spot."""
    if visitor.at_door and site.door_point is not None:
        return site.door_point
    return (visitor.x, visitor.y, site.head_height_m)
