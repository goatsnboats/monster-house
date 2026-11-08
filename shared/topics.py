"""MQTT topic names for the whole Monster House system.

This is the ONE place topic strings are written down (see CLAUDE.md,
"Architecture rules"). Every other module imports names from here.

Source: docs/architecture.md §2 (eye messages) and §3c (topic map).

Topic NAMES only. What goes inside each message (payload formats and how they
are checked) is still open: TBD-003.

Wildcards, for reading the subscribe patterns below:
  +  matches exactly one level   (monster/eyes/+/status)
  #  matches everything below    (monster/#)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Monster brain -> eye pods   (architecture §2, "Messages it listens to")
# ---------------------------------------------------------------------------
EYES_LOOK = "monster/eyes/look"              # look at a point, or wander ("idle")
EYES_EXPRESSION = "monster/eyes/expression"  # ease into a named expression
EYES_BLINK = "monster/eyes/blink"            # blink now (both eyes together)

# Brain -> eye pods: which theme's art to load. Published retained.
THEME = "monster/theme"

# ---------------------------------------------------------------------------
# Eye pods -> monster brain: online/offline, using MQTT last-will
# ---------------------------------------------------------------------------
EYE_SIDES = ("left", "right")  # as seen from the street


def eye_status(side: str) -> str:
    """Status topic for one eye pod: eye_status("left") -> monster/eyes/left/status."""
    if side not in EYE_SIDES:
        raise ValueError(f"eye side must be one of {EYE_SIDES}, not {side!r}")
    return f"monster/eyes/{side}/status"


EYES_LEFT_STATUS = eye_status("left")
EYES_RIGHT_STATUS = eye_status("right")
EYES_STATUS_ALL = "monster/eyes/+/status"    # subscribe pattern: both eyes


# ---------------------------------------------------------------------------
# Monster brain -> phone page, debugging: current mood. Published retained.
# ---------------------------------------------------------------------------
STATE = "monster/state"

# ---------------------------------------------------------------------------
# Radar (ESPHome on an ESP32 + HLK-LD2450) -> monster brain   (architecture §4)
#
# ESPHome publishes each sensor on its own topic:
#     <node name>/sensor/<sensor id>/state
# and its own online/offline last-will on <node name>/status.
# The sensor ids are set by our ESPHome YAML (Stage 2, in esphome/), which
# must use the names produced here. The fake radar (Stage 0 Step 3) uses them too.
# ---------------------------------------------------------------------------
RADAR_NODE = "monster-radar"
RADAR_STATUS = f"{RADAR_NODE}/status"
RADAR_SENSOR_ALL = f"{RADAR_NODE}/sensor/+/state"   # subscribe pattern: every radar value
RADAR_TARGET_COUNT = f"{RADAR_NODE}/sensor/target_count/state"

RADAR_MAX_TARGETS = 3                  # the LD2450 tracks up to 3 people
RADAR_TARGET_FIELDS = ("x", "y", "speed")


def radar_target(target: int, field: str) -> str:
    """Topic for one value of one tracked person.

    radar_target(1, "x") -> monster-radar/sensor/target_1_x/state
    """
    if not 1 <= target <= RADAR_MAX_TARGETS:
        raise ValueError(f"radar target must be 1..{RADAR_MAX_TARGETS}, not {target!r}")
    if field not in RADAR_TARGET_FIELDS:
        raise ValueError(f"radar field must be one of {RADAR_TARGET_FIELDS}, not {field!r}")
    return f"{RADAR_NODE}/sensor/target_{target}_{field}/state"


# ---------------------------------------------------------------------------
# Falcon Player (FPP) <-> monster brain   (architecture §3a)
# Best-known topics; check them against the FPP version we install: TBD-015.
# ---------------------------------------------------------------------------
FPP_PREFIX = "falcon/player/FPP"       # "FPP" is the player's host name in FPP's settings
FPP_ALL = f"{FPP_PREFIX}/#"            # subscribe pattern: everything FPP publishes


def fpp_playlist_start(playlist: str) -> str:
    """Command topic that starts one FPP playlist (one voice clip), by name.

    fpp_playlist_start("greet_01") -> falcon/player/FPP/set/playlist/greet_01/start
    """
    if not playlist or any(ch in playlist for ch in "/+#"):
        raise ValueError(f"not a usable playlist name: {playlist!r}")
    return f"{FPP_PREFIX}/set/playlist/{playlist}/start"


# ---------------------------------------------------------------------------
# Development helpers (not in the architecture's topic map)
# ---------------------------------------------------------------------------
MONSTER_ALL = "monster/#"              # subscribe pattern: everything under monster/
DEBUG_TEST = "monster/debug/test"      # for tests and the debug tool; nothing acts on it


# Short names for the command-line debug tool (python -m shared.mqtt_tool).
# Topics with a parameter (an eye side, a radar target, a playlist) are listed
# for one example value; pass the full topic on the command line for others.
ALIASES: dict[str, str] = {
    "look": EYES_LOOK,
    "expression": EYES_EXPRESSION,
    "blink": EYES_BLINK,
    "theme": THEME,
    "state": STATE,
    "left-status": EYES_LEFT_STATUS,
    "right-status": EYES_RIGHT_STATUS,
    "eye-status": EYES_STATUS_ALL,
    "radar": RADAR_SENSOR_ALL,
    "radar-status": RADAR_STATUS,
    "fpp": FPP_ALL,
    "monster": MONSTER_ALL,
    "test": DEBUG_TEST,
}


def is_pattern(topic: str) -> bool:
    """True if the topic contains a wildcard (fine to subscribe to, not to publish on)."""
    return "+" in topic or "#" in topic
