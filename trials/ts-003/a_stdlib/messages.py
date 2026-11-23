"""ICD-001 messages, option A: the ICD is the definition, standard library only.

The schemas come from the ICDs (schemas.json, written by the checker the way it writes
trace.md). The dataclasses below only give the code named, typed fields; a drift test
(drift.py) fails if they and the ICD disagree.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Literal

from schema import problems  # the small checker, moved into shared/

log = logging.getLogger(__name__)
SCHEMAS = json.loads((Path(__file__).parent / "schemas.json").read_text())

ExpressionName = Literal["neutral", "happy", "sparkle", "surprised", "sleepy", "asleep"]
Status = Literal["online", "offline"]


@dataclass
class LookAt:
    """Look at this point (meters, house coordinates)."""
    x: float
    y: float
    z: float


@dataclass
class LookIdle:
    """Wander and look around on your own."""
    mode: Literal["idle"]


@dataclass
class Expression:
    name: ExpressionName
    ms: int


@dataclass
class Blink:
    ms: int


@dataclass
class Theme:
    name: str


# Which classes each message can be (look is one of two).
CLASSES = {"look": (LookAt, LookIdle), "expression": (Expression,), "blink": (Blink,), "theme": (Theme,)}


def encode(name: str, msg) -> bytes:
    """The bytes to publish. Raises ValueError if the message breaks the ICD (our bug)."""
    value = msg if name == "status" else asdict(msg)
    found = problems(value, SCHEMAS[name])
    if found:
        raise ValueError("; ".join(found))
    return value.encode() if name == "status" else json.dumps(value).encode()


def decode(name: str, payload: bytes):
    """The message, or None (logged) if the payload breaks the ICD."""
    try:
        value = payload.decode() if name == "status" else json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        log.warning("dropped %s: not readable (%s)", name, err)
        return None
    found = problems(value, SCHEMAS[name])
    if found:
        log.warning("dropped %s: %s", name, "; ".join(found))
        return None
    if name == "status":
        return value
    for cls in CLASSES[name]:
        if set(value) == {f.name for f in fields(cls)}:
            return cls(**value)
    log.warning("dropped %s: no class has the keys %s (run the drift test)", name, sorted(value))
    return None
