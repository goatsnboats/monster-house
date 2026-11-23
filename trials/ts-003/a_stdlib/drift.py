"""Option A's drift test: schemas.json and the dataclasses must match the ICD."""

from __future__ import annotations

import json
import typing
from dataclasses import MISSING, fields

import messages
from shape import compare, enum, icd_shape

KINDS = {float: "number", int: "integer", str: "string"}


def code_shape(cls) -> dict:
    hints = typing.get_type_hints(cls)
    shape = {}
    for f in fields(cls):
        hint = hints[f.name]
        kind = enum(typing.get_args(hint)) if typing.get_origin(hint) is typing.Literal else KINDS[hint]
        # The minimum lives only in the ICD (checked at run time), so it is not compared.
        shape[f.name] = (kind, f.default is MISSING, None)
    return shape


def drift(icd: dict) -> list[str]:
    found = []
    for name, msg in icd.items():
        if messages.SCHEMAS.get(name) != msg["payload_schema"]:
            found.append(f"{name}: schemas.json is out of date with the ICD (run the checker)")
        want = icd_shape(msg["payload_schema"], with_minimum=False)
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
