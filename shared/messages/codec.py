"""Turn messages into payload bytes and back, checking each against its ICD schema.

The generated modules next to this file (eye_commands.py, ...) call these two functions
with the right schema; components call the modules' own encode() and decode().

- A payload whose schema is an object (or a choice of objects) is JSON in UTF-8.
  Anything else (the eye status, the radar's numbers) is plain text.
- decode() never raises: a payload that breaks the ICD is logged and dropped (None),
  so a bad message can't crash a component ("fail friendly", EYE-015).
- encode() raises ValueError for a message that breaks the ICD: that's a bug in our
  own code, and tests should catch it before it reaches the house.
"""

from __future__ import annotations

import json
import logging
from dataclasses import MISSING, asdict, fields, is_dataclass

from shared.schema import problems

log = logging.getLogger(__name__)


def is_json(schema: dict) -> bool:
    """True if this payload travels as a JSON object, False if as plain text."""
    return schema.get("type") == "object" or "oneOf" in schema


def encode(schema: dict, value) -> bytes:
    """The bytes to send for `value`. Raises ValueError if `value` breaks the schema."""
    data = value
    if is_dataclass(value):
        # An optional key left at None is simply not sent.
        optional = {f.name for f in fields(value) if f.default is None}
        data = {k: v for k, v in asdict(value).items() if not (v is None and k in optional)}
    found = problems(data, schema)
    if found:
        raise ValueError("; ".join(found))
    text = json.dumps(data) if is_json(schema) else str(data)
    return text.encode("utf-8")


def decode(schema: dict, classes: tuple, payload: bytes, label: str):
    """The message in `payload`, or None (logged) if it breaks the schema.

    JSON objects become the matching class from `classes`; plain text stays a string.
    `label` names the message in the log, e.g. "ICD-001 blink".
    """
    try:
        text = payload.decode("utf-8")
        data = json.loads(text) if is_json(schema) else text
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        log.warning("dropped %s: not readable (%s)", label, err)
        return None
    found = problems(data, schema)
    if found:
        log.warning("dropped %s: %s", label, "; ".join(found))
        return None
    if not is_json(schema):
        return data
    for cls in classes:
        names = {f.name for f in fields(cls)}
        required = {f.name for f in fields(cls) if f.default is MISSING}
        if required <= set(data) <= names:
            return cls(**data)
    # Can't happen while the generated classes match the schema (a test checks that).
    log.warning("dropped %s: no message class has the keys %s", label, sorted(data))
    return None
