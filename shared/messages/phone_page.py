"""ICD-004 Phone buttons and current mood: message payloads.

GENERATED from docs/interfaces/ICD-004-phone-page.md by `python -m tools.reqs.check`.
Don't edit it by hand: change the ICD, then run the checker (ADR 0003).

    payload = encode(name, message)   # bytes to send; ValueError if it breaks the ICD
    message = decode(name, payload)   # None (and logged) if the payload breaks the ICD
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shared.messages import codec

ICD = "ICD-004"


@dataclass
class State:
    """state (owner-phone -> phone-page)."""
    mood: Literal['asleep', 'waking', 'greeting', 'watching', 'goodbye']
    muted: bool
    theme: str
    themes: list[str]


@dataclass
class Button:
    """button (owner-phone -> phone-page)."""
    name: Literal['costume', 'burp', 'sing', 'mute', 'unmute', 'sleep', 'wake']


@dataclass
class ChooseTheme:
    """choose theme (owner-phone -> phone-page)."""
    name: str


@dataclass
class Mood:
    """mood (monster-brain -> phone-page)."""
    mood: Literal['asleep', 'waking', 'greeting', 'watching', 'goodbye']


# The class (or classes) each JSON message becomes when received.
CLASSES = {
    'state': (State,),
    'button': (Button,),
    'choose theme': (ChooseTheme,),
    'mood': (Mood,),
}

# Each message's payload schema, exactly as written in the ICD.
SCHEMAS = {
    'state': {'type': 'object',
              'required': ['mood', 'muted', 'theme', 'themes'],
              'additionalProperties': False,
              'properties': {'mood': {'enum': ['asleep',
                                               'waking',
                                               'greeting',
                                               'watching',
                                               'goodbye']},
                             'muted': {'type': 'boolean'},
                             'theme': {'type': 'string'},
                             'themes': {'type': 'array', 'items': {'type': 'string'}}}},
    'button': {'type': 'object',
               'required': ['name'],
               'additionalProperties': False,
               'properties': {'name': {'enum': ['costume',
                                                'burp',
                                                'sing',
                                                'mute',
                                                'unmute',
                                                'sleep',
                                                'wake']}}},
    'choose theme': {'type': 'object',
                     'required': ['name'],
                     'additionalProperties': False,
                     'properties': {'name': {'type': 'string'}}},
    'mood': {'type': 'object',
             'required': ['mood'],
             'additionalProperties': False,
             'properties': {'mood': {'enum': ['asleep',
                                              'waking',
                                              'greeting',
                                              'watching',
                                              'goodbye']}}},
}


def encode(name: str, message) -> bytes:
    """The payload to send for message `name`. Raises ValueError if it breaks the ICD."""
    return codec.encode(SCHEMAS[name], message)


def decode(name: str, payload: bytes):
    """The message received as `name`, or None (logged) if the payload breaks the ICD."""
    return codec.decode(SCHEMAS[name], CLASSES.get(name, ()), payload, f"{ICD} {name}")
