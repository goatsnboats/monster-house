"""ICD-003 Clip commands and clip status: message payloads.

GENERATED from docs/interfaces/ICD-003-clips.md by `python -m tools.reqs.check`.
Don't edit it by hand: change the ICD, then run the checker (ADR 0003).

    payload = encode(name, message)   # bytes to send; ValueError if it breaks the ICD
    message = decode(name, payload)   # None (and logged) if the payload breaks the ICD
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shared.messages import codec

ICD = "ICD-003"


# player status (falcon-player, fake-fpp -> monster-brain): plain text
PlayerStatus = Literal['playing', 'idle']


# playlist playing (falcon-player, fake-fpp -> monster-brain): plain text
PlaylistPlaying = str


# The class (or classes) each JSON message becomes when received.
CLASSES: dict = {}  # every message in this ICD is plain text

# Each message's payload schema, exactly as written in the ICD.
SCHEMAS = {
    'player status': {'enum': ['playing', 'idle']},
    'playlist playing': {'type': 'string'},
}


def encode(name: str, message) -> bytes:
    """The payload to send for message `name`. Raises ValueError if it breaks the ICD."""
    return codec.encode(SCHEMAS[name], message)


def decode(name: str, payload: bytes):
    """The message received as `name`, or None (logged) if the payload breaks the ICD."""
    return codec.decode(SCHEMAS[name], CLASSES.get(name, ()), payload, f"{ICD} {name}")
