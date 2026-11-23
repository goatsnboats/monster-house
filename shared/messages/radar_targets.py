"""ICD-002 Radar targets: message payloads.

GENERATED from docs/interfaces/ICD-002-radar-targets.md by `python -m tools.reqs.check`.
Don't edit it by hand: change the ICD, then run the checker (ADR 0003).

    payload = encode(name, message)   # bytes to send; ValueError if it breaks the ICD
    message = decode(name, payload)   # None (and logged) if the payload breaks the ICD
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shared.messages import codec

ICD = "ICD-002"


# target value (radar-firmware, fake-radar -> monster-brain): plain text
TargetValue = str


# target count (radar-firmware, fake-radar -> monster-brain): plain text
TargetCount = Literal['0', '1', '2', '3', 'nan']


# status (radar-firmware, fake-radar -> monster-brain): plain text
Status = Literal['online', 'offline']


# The class (or classes) each JSON message becomes when received.
CLASSES: dict = {}  # every message in this ICD is plain text

# Each message's payload schema, exactly as written in the ICD.
SCHEMAS = {
    'target value': {'type': 'string'},
    'target count': {'type': 'string', 'enum': ['0', '1', '2', '3', 'nan']},
    'status': {'enum': ['online', 'offline']},
}


def encode(name: str, message) -> bytes:
    """The payload to send for message `name`. Raises ValueError if it breaks the ICD."""
    return codec.encode(SCHEMAS[name], message)


def decode(name: str, payload: bytes):
    """The message received as `name`, or None (logged) if the payload breaks the ICD."""
    return codec.decode(SCHEMAS[name], CLASSES.get(name, ()), payload, f"{ICD} {name}")
