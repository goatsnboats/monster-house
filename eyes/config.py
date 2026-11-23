"""Reading the eye's settings: its window from the site config (ICD-015, EYE-013, EYE-017)
and its colors and blink timing from the theme (ICD-005, EYE-014, EYE-016).

A broken or missing theme must never stop the eye (SYS-017): `load_theme` falls back to
the sketch's colors and timing and says why in the log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_CONFIG = REPO_ROOT / "config" / "site.yaml"
THEMES_DIR = REPO_ROOT / "themes"
SIDES = ("left", "right")
# How the eye fills its window (eyes.<side>.eye_shape, ICD-015). square: the white fills
# the whole window and the window frame is the eye's edge (owner's default, 2026-11-23);
# oval: the sketch's oval; stretch: an oval shaped like the window.
SHAPES = ("square", "oval", "stretch")
DEFAULT_SHAPE = "square"


@dataclass(frozen=True)
class Window:
    """One eye's window settings (ICD-015, eyes.<side>)."""
    position_m: tuple[float, float, float]   # window center, house coordinates
    window_m: tuple[float, float]            # usable glass, width x height, meters
    rotate_deg: int                          # 0, or 90 with the projector on its side
    mirror: bool                             # rear projection: flip left-right
    eye_center: tuple[float, float]          # where the eye sits in the window (0-1)
    eye_size: float                          # fraction of the window the eye fills
    brightness: float                        # 0-1, to match the two eyes
    eye_shape: str = DEFAULT_SHAPE           # square, oval or stretch (SHAPES)


@dataclass(frozen=True)
class Theme:
    """What the eye takes from a theme (ICD-005)."""
    name: str
    iris_color: tuple[float, float, float]
    sclera_color: tuple[float, float, float]
    blink_every_s: tuple[float, float]
    blink_ms: int


# The sketch's values (docs/reference/eye-sketch.html), used when a theme can't be read.
DEFAULT_THEME = Theme("default", (0.478, 0.333, 0.878), (0.965, 0.949, 0.902), (2.5, 6.0), 200)


class ConfigError(Exception):
    """The site config is missing or wrong; the message says what to fix."""


def load_window(side: str, path: Path = SITE_CONFIG) -> Window:
    if side not in SIDES:
        raise ConfigError(f"eye side must be one of {SIDES}, not {side!r}")
    try:
        site = yaml.safe_load(path.read_text())
        e = site["eyes"][side]
        p, w = e["position_m"], e["window_m"]
        window = Window(
            position_m=(float(p["x"]), float(p["y"]), float(p["z"])),
            window_m=(float(w["w"]), float(w["h"])),
            rotate_deg=int(e["rotate_deg"]),
            mirror=bool(e["mirror"]),
            eye_center=(float(e["eye_center"][0]), float(e["eye_center"][1])),
            eye_size=float(e["eye_size"]),
            brightness=float(e["brightness"]),
            eye_shape=str(e.get("eye_shape", DEFAULT_SHAPE)),
        )
    except FileNotFoundError:
        raise ConfigError(f"no site config at {path}") from None
    except (KeyError, IndexError, TypeError, ValueError, yaml.YAMLError) as err:
        raise ConfigError(f"{path}: eyes.{side} is incomplete or wrong ({err!r}); see ICD-015") from None
    if window.rotate_deg not in (0, 90):
        raise ConfigError(f"{path}: eyes.{side}.rotate_deg must be 0 or 90")
    if window.eye_shape not in SHAPES:
        raise ConfigError(f"{path}: eyes.{side}.eye_shape must be one of {SHAPES}, not {window.eye_shape!r}")
    if min(window.window_m) <= 0:
        raise ConfigError(f"{path}: eyes.{side}.window_m must be bigger than zero")
    return window


def hex_color(text: str) -> tuple[float, float, float]:
    """'#7a55e0' -> (0.478, 0.333, 0.878)."""
    text = text.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"not a #rrggbb color: {text!r}")
    return tuple(int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))


def load_theme(name: str, themes_dir: Path = THEMES_DIR) -> Theme:
    """The theme's eye colors and blink timing, or the defaults if it can't be read."""
    path = themes_dir / name / "settings.yaml"
    try:
        settings = yaml.safe_load(path.read_text())
        eyes, timing = settings["eyes"], settings["timing"]
        low, high = timing["blink_every_s"]
        return Theme(name, hex_color(eyes["iris_color"]), hex_color(eyes["sclera_color"]),
                     (float(low), float(high)), int(timing["blink_ms"]))
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as err:
        log.warning("theme %r unreadable (%s); keeping the default eye", name, err)
        return DEFAULT_THEME
