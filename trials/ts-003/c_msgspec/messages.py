"""ICD-001 messages, option C: msgspec Structs are the definition in code.

forbid_unknown_fields rejects keys the ICD doesn't list. msgspec checks values when it
decodes, not when a Struct is created. A drift test (drift.py) compares these structs
with the ICD.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

import msgspec
from msgspec import Meta, Struct

log = logging.getLogger(__name__)

ExpressionName = Literal["neutral", "happy", "sparkle", "surprised", "sleepy", "asleep"]
Status = Literal["online", "offline"]
Milliseconds = Annotated[int, Meta(ge=0)]


class Message(Struct, forbid_unknown_fields=True):
    pass


class LookAt(Message):
    """Look at this point (meters, house coordinates)."""
    x: float
    y: float
    z: float


class LookIdle(Message):
    """Wander and look around on your own."""
    mode: Literal["idle"]


class Expression(Message):
    name: ExpressionName
    ms: Milliseconds


class Blink(Message):
    ms: Milliseconds


class Theme(Message):
    name: str


# msgspec can't decode "LookAt or LookIdle" in one step without a tag field in the JSON
# (which would change the wire format), so look tries each class in turn.
CLASSES = {"look": (LookAt, LookIdle), "expression": (Expression,), "blink": (Blink,), "theme": (Theme,)}


def encode(name: str, msg) -> bytes:
    """The bytes to publish. Note: msgspec does not check values here."""
    if name == "status":
        return msgspec.convert(msg, Status).encode()
    return msgspec.json.encode(msg)


def decode(name: str, payload: bytes):
    """The message, or None (logged) if the payload breaks the ICD."""
    try:
        if name == "status":
            return msgspec.convert(payload.decode(), Status)
    except (msgspec.ValidationError, UnicodeDecodeError) as err:
        log.warning("dropped %s: %s", name, err)
        return None
    errors = []
    for cls in CLASSES[name]:
        try:
            return msgspec.json.decode(payload, type=cls)
        except (msgspec.ValidationError, msgspec.DecodeError) as err:
            errors.append(str(err))
    log.warning("dropped %s: %s", name, " / ".join(errors))
    return None
