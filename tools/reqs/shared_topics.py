"""Compare the MQTT topics named in the ICDs with shared/topics.py.

shared/topics.py is the code's one list of topic names (CLAUDE.md); the ICDs are the
documents. They must agree. This module only reports differences; it never changes
either side (a topic change is a message-format change: ask the owner first).

In an ICD, a part of a topic that varies is written in braces:
    monster/eyes/{side}/status
    monster-radar/sensor/target_{n}_{field}/state
    falcon/player/FPP/set/playlist/{name}/start
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path


def topics_in_shared(topics_file: Path) -> dict[str, str]:
    """Every publishable topic shared/topics.py can produce: {how it's named: topic}.

    Includes the plain constants (EYES_LOOK, ...) and the topics its helper
    functions build. Subscribe patterns (with + or #) and prefixes are left out:
    they aren't topics a message is sent on.
    """
    spec = importlib.util.spec_from_file_location("_shared_topics_for_check", topics_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    found = {}
    for name, value in vars(mod).items():
        if (name.isupper() and isinstance(value, str) and "/" in value
                and not name.endswith("_PREFIX") and not mod.is_pattern(value)):
            found[name] = value

    # Helper functions that build topics from a parameter.
    if hasattr(mod, "radar_target"):
        for n in range(1, mod.RADAR_MAX_TARGETS + 1):
            for f in mod.RADAR_TARGET_FIELDS:
                found[f"radar_target({n}, {f!r})"] = mod.radar_target(n, f)
    if hasattr(mod, "fpp_playlist_start"):
        found["fpp_playlist_start(<name>)"] = mod.fpp_playlist_start("{name}")
    return found


def _as_regex(template: str) -> re.Pattern:
    """Turn a topic template into a pattern where each {name} matches one topic level."""
    parts = re.split(r"(\{[^}/]+\})", template)
    return re.compile("".join("[^/]+" if p.startswith("{") else re.escape(p) for p in parts))


def compare(icd_topics: dict[str, str], shared: dict[str, str]) -> list[tuple[str, str]]:
    """Mismatches as (where, message).

    icd_topics: {topic template: ICD id}. shared: from topics_in_shared().
    """
    mismatches = []
    for template, icd in sorted(icd_topics.items()):
        pattern = _as_regex(template)
        if not any(pattern.fullmatch(t) or t == template for t in shared.values()):
            mismatches.append((icd, f"topic {template} is in the ICD but not in shared/topics.py"))
    patterns = [_as_regex(t) for t in icd_topics]
    for name, topic in sorted(shared.items()):
        if not any(p.fullmatch(topic) for p in patterns) and topic not in icd_topics:
            mismatches.append(("shared/topics.py", f"{name} = {topic} is in no ICD"))
    return mismatches
