"""Option B's drift test: the pydantic models must match the ICD."""

from __future__ import annotations

import json
import typing

import annotated_types

import messages
from shape import compare, enum, icd_shape

KINDS = {float: "number", int: "integer", str: "string"}


def code_shape(model) -> dict:
    shape = {}
    for key, info in model.model_fields.items():
        hint = info.annotation
        kind = enum(typing.get_args(hint)) if typing.get_origin(hint) is typing.Literal else KINDS[hint]
        minimum = next((m.ge for m in info.metadata if isinstance(m, annotated_types.Ge)), None)
        shape[key] = (kind, info.is_required(), minimum)
    return shape


def drift(icd: dict) -> list[str]:
    found = []
    for name, msg in icd.items():
        want = icd_shape(msg["payload_schema"])
        if name == "status":
            have = enum(typing.get_args(messages.Status))
        else:
            have = [code_shape(c) for c in messages.CLASSES[name]]
            have = have if isinstance(want, list) else have[0]
        found += compare(name, want, have)
        for example in msg["examples"]:
            raw = example.encode() if name == "status" else json.dumps(example).encode()
            if messages.decode(name, raw) is None:
                found.append(f"{name}: the ICD example {example} doesn't decode")
    return found
