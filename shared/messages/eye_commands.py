"""ICD-001 Eye commands and eye status: message payloads.

GENERATED from docs/interfaces/ICD-001-eye-commands.md by `python -m tools.reqs.check`.
Don't edit it by hand: change the ICD, then run the checker (ADR 0003).

    payload = encode(name, message)   # bytes to send; ValueError if it breaks the ICD
    message = decode(name, payload)   # None (and logged) if the payload breaks the ICD
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shared.messages import codec

ICD = "ICD-001"


@dataclass
class LookAt:
    """look (monster-brain -> eye-renderer, house-preview), one of 2 choices."""
    x: float
    y: float
    z: float


@dataclass
class LookIdle:
    """look (monster-brain -> eye-renderer, house-preview), one of 2 choices."""
    mode: Literal['idle']


@dataclass
class Expression:
    """expression (monster-brain -> eye-renderer, house-preview)."""
    name: Literal['neutral', 'happy', 'sparkle', 'surprised', 'sleepy', 'asleep']
    ms: int


@dataclass
class Blink:
    """blink (monster-brain -> eye-renderer, house-preview)."""
    ms: int


@dataclass
class Theme:
    """theme (monster-brain -> eye-renderer, house-preview)."""
    name: str


# status (eye-renderer -> monster-brain): plain text
Status = Literal['online', 'offline']


# The class (or classes) each JSON message becomes when received.
CLASSES = {
    'look': (LookAt, LookIdle),
    'expression': (Expression,),
    'blink': (Blink,),
    'theme': (Theme,),
}

# Each message's payload schema, exactly as written in the ICD.
SCHEMAS = {
    'look': {'oneOf': [{'title': 'LookAt',
                        'type': 'object',
                        'required': ['x', 'y', 'z'],
                        'additionalProperties': False,
                        'properties': {'x': {'type': 'number'},
                                       'y': {'type': 'number'},
                                       'z': {'type': 'number'}}},
                       {'title': 'LookIdle',
                        'type': 'object',
                        'required': ['mode'],
                        'additionalProperties': False,
                        'properties': {'mode': {'enum': ['idle']}}}]},
    'expression': {'type': 'object',
                   'required': ['name', 'ms'],
                   'additionalProperties': False,
                   'properties': {'name': {'enum': ['neutral',
                                                    'happy',
                                                    'sparkle',
                                                    'surprised',
                                                    'sleepy',
                                                    'asleep']},
                                  'ms': {'type': 'integer', 'minimum': 0}}},
    'blink': {'type': 'object',
              'required': ['ms'],
              'additionalProperties': False,
              'properties': {'ms': {'type': 'integer', 'minimum': 0}}},
    'theme': {'type': 'object',
              'required': ['name'],
              'additionalProperties': False,
              'properties': {'name': {'type': 'string'}}},
    'status': {'enum': ['online', 'offline']},
}


def encode(name: str, message) -> bytes:
    """The payload to send for message `name`. Raises ValueError if it breaks the ICD."""
    return codec.encode(SCHEMAS[name], message)


def decode(name: str, payload: bytes):
    """The message received as `name`, or None (logged) if the payload breaks the ICD."""
    return codec.decode(SCHEMAS[name], CLASSES.get(name, ()), payload, f"{ICD} {name}")
