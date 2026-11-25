"""The brain's part of a theme: timings, clip pools and show hours (ICD-005, SHW-027).

None of these numbers are written in code; they come from themes/<name>/settings.yaml.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
THEMES_DIR = REPO_ROOT / "themes"
DEFAULT_THEME = "halloween"


class ThemeError(Exception):
    """The theme's settings are missing or wrong; the message says what to fix."""


def _span(value) -> tuple[float, float]:
    """A [low, high] range from the theme, low first."""
    low, high = (float(v) for v in value)
    return (min(low, high), max(low, high))


@dataclass(frozen=True)
class Timing:
    """theme.timing (ICD-005). Seconds unless the name says otherwise."""
    goodbye_after_s: float = 5
    sleep_after_s: float = 20
    comment_every_s: tuple[float, float] = (10, 20)
    min_gap_s: float = 10
    snore_every_s: float = 30
    blink_every_s: tuple[float, float] = (2.5, 6.0)
    blink_ms: int = 200
    focus_hold_s: tuple[float, float] = (3, 6)
    door_hold_s: float = 15


@dataclass(frozen=True)
class ThemeSettings:
    name: str
    timing: Timing = field(default_factory=Timing)
    clips: dict[str, list[str]] = field(default_factory=dict)
    show_hours: tuple[dt.time, dt.time] | None = None    # None: always show time

    def in_show_hours(self, when: dt.datetime) -> bool:
        """True during show hours (SHW-019, TBD-024). Handles hours that pass midnight."""
        if self.show_hours is None:
            return True
        start, end = self.show_hours
        now = when.time()
        return start <= now < end if start <= end else (now >= start or now < end)


def _clock(text: str) -> dt.time:
    hours, minutes = (int(v) for v in str(text).split(":"))
    return dt.time(hours, minutes)


def load_theme_settings(name: str = DEFAULT_THEME, themes_dir: Path = THEMES_DIR) -> ThemeSettings:
    path = themes_dir / name / "settings.yaml"
    try:
        raw = yaml.safe_load(path.read_text())
        t = raw["timing"]
        timing = Timing(
            goodbye_after_s=float(t["goodbye_after_s"]),
            sleep_after_s=float(t["sleep_after_s"]),
            comment_every_s=_span(t["comment_every_s"]),
            min_gap_s=float(t["min_gap_s"]),
            snore_every_s=float(t["snore_every_s"]),
            blink_every_s=_span(t["blink_every_s"]),
            blink_ms=int(t["blink_ms"]),
            focus_hold_s=_span(t["focus_hold_s"]),
            door_hold_s=float(t["door_hold_s"]),
        )
        clips = {pool: [str(c) for c in (names or [])] for pool, names in raw["clips"].items()}
        hours = raw.get("show_hours")
        show_hours = (_clock(hours[0]), _clock(hours[1])) if hours else None
        return ThemeSettings(name=str(raw["theme"]), timing=timing, clips=clips, show_hours=show_hours)
    except FileNotFoundError:
        raise ThemeError(f"no theme settings at {path}") from None
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as err:
        raise ThemeError(f"{path}: the theme settings are incomplete or wrong ({err!r}); see ICD-005") from None
