"""Option D: encode and decode the generated message classes (hand-written, never changes per message)."""

from __future__ import annotations

import json
import logging
from dataclasses import MISSING, asdict, fields

from messages import CLASSES, SCHEMAS  # generated
from schema import problems  # the small checker, moved into shared/

log = logging.getLogger(__name__)


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
        required = {f.name for f in fields(cls) if f.default is MISSING}
        if required <= set(value) <= {f.name for f in fields(cls)}:
            return cls(**value)
    log.warning("dropped %s: no class has the keys %s (run generate.py)", name, sorted(value))
    return None
