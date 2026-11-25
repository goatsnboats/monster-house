"""Where the radar is, and how its readings map onto the house (ICD-002, ICD-015).

The radar reports each person in millimeters relative to itself (ICD-002): `x` across
its view, `y` straight out from it. The house uses meters (ICD-015): origin on the
ground below the radar, x to the right as seen from the street, y from the house toward
the street, z up. The radar faces the street, so its `y` is the house's `y`.

Which way the radar's `x` points as seen from the street isn't documented; we assume it
grows to the right, like the house's x, and check it at the Stage 2 install (TBD-039).
If it turns out the other way, change X_SIGN here: the brain and the fake radar both
use these functions, so they stay in step.

The radar is assumed to look straight out (no yaw; see TBD-037), and its own small
downward tilt is ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_CONFIG = REPO_ROOT / "config" / "site.yaml"

X_SIGN = 1          # +1: radar x grows to the right as seen from the street (TBD-039)

# What the LD2450 can see (architecture §4; Hi-Link's datasheet): about 6 m out and
# 60 degrees either side of straight ahead, and x within +-3 m (ICD-002).
MAX_RANGE_MM = 6000
MAX_ANGLE_DEG = 60
MAX_X_MM = 3000


@dataclass(frozen=True)
class Zone:
    """A rectangle in radar millimeters (ICD-015 radar.door_zone_mm)."""
    x1: float
    y1: float
    x2: float
    y2: float

    def contains(self, x_mm: float, y_mm: float) -> bool:
        return (min(self.x1, self.x2) <= x_mm <= max(self.x1, self.x2)
                and min(self.y1, self.y2) <= y_mm <= max(self.y1, self.y2))


@dataclass(frozen=True)
class RadarSite:
    """The radar's part of the site config (ICD-015)."""
    mount: tuple[float, float, float]     # house coordinates, meters
    approach_range_m: float
    head_height_m: float
    door_zone: Zone | None = None         # where the radar loses visitors (TBD-029)
    door_point: tuple[float, float, float] | None = None   # where to look at the door (house m)


class SiteError(Exception):
    """The site config is missing or wrong; the message says what to fix."""


def load_radar_site(path: Path = SITE_CONFIG) -> RadarSite:
    try:
        site = yaml.safe_load(path.read_text())
        radar = site["radar"]
        m = radar["mount"]
        zone = radar.get("door_zone_mm")
        door = site.get("door_point")
        return RadarSite(
            mount=(float(m["x"]), float(m["y"]), float(m["z"])),
            approach_range_m=float(radar["approach_range_m"]),
            head_height_m=float(site["head_height_m"]),
            door_zone=Zone(*(float(zone[k]) for k in ("x1", "y1", "x2", "y2"))) if zone else None,
            door_point=tuple(float(door[k]) for k in ("x", "y", "z")) if door else None,
        )
    except FileNotFoundError:
        raise SiteError(f"no site config at {path}") from None
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as err:
        raise SiteError(f"{path}: the radar settings are incomplete or wrong ({err!r}); see ICD-015") from None


def radar_to_house(x_mm: float, y_mm: float, site: RadarSite) -> tuple[float, float, float]:
    """A radar reading -> the visitor's head, in house meters (head at head_height_m)."""
    mx, my, _ = site.mount
    return (mx + X_SIGN * x_mm / 1000.0, my + y_mm / 1000.0, site.head_height_m)


def house_to_radar(x_m: float, y_m: float, site: RadarSite) -> tuple[float, float]:
    """A spot on the ground in house meters -> where the radar would place it, in mm."""
    mx, my, _ = site.mount
    return (X_SIGN * (x_m - mx) * 1000.0, (y_m - my) * 1000.0)


def in_view(x_mm: float, y_mm: float) -> bool:
    """True if the LD2450 can see this spot: in front, within range, angle and x limits."""
    if y_mm <= 0 or abs(x_mm) > MAX_X_MM:
        return False
    if math.hypot(x_mm, y_mm) > MAX_RANGE_MM:
        return False
    return abs(math.degrees(math.atan2(x_mm, y_mm))) <= MAX_ANGLE_DEG
