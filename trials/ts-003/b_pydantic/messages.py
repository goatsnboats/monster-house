"""ICD-001 messages, option B: pydantic v2 models are the definition in code.

strict=True stops pydantic turning "300" into 300 (its default is to convert);
extra="forbid" rejects keys the ICD doesn't list. A drift test (drift.py) compares
these models with the ICD.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

log = logging.getLogger(__name__)

ExpressionName = Literal["neutral", "happy", "sparkle", "surprised", "sleepy", "asleep"]
Status = Literal["online", "offline"]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


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
    ms: int = Field(ge=0)


class Blink(Message):
    ms: int = Field(ge=0)


class Theme(Message):
    name: str


CLASSES = {"look": (LookAt, LookIdle), "expression": (Expression,), "blink": (Blink,), "theme": (Theme,)}
READERS = {
    "look": TypeAdapter(LookAt | LookIdle),
    "expression": TypeAdapter(Expression),
    "blink": TypeAdapter(Blink),
    "theme": TypeAdapter(Theme),
    "status": TypeAdapter(Status),
}


def encode(name: str, msg) -> bytes:
    """The bytes to publish. Models check their values when they are created."""
    if name == "status":
        return READERS["status"].validate_python(msg).encode()
    return msg.model_dump_json().encode()


def decode(name: str, payload: bytes):
    """The message, or None (logged) if the payload breaks the ICD."""
    try:
        if name == "status":
            return READERS[name].validate_python(payload.decode())
        return READERS[name].validate_json(payload)
    except (ValidationError, UnicodeDecodeError) as err:
        log.warning("dropped %s: %s", name, str(err).replace("\n", " "))
        return None
