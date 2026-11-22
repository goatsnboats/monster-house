"""Option C's drift test: the msgspec structs must match the ICD."""

from __future__ import annotations

import json
import typing

import msgspec.inspect as mi

import messages
from shape import compare, enum, icd_shape

KINDS = {mi.FloatType: "number", mi.IntType: "integer", mi.StrType: "string"}


def code_shape(cls) -> dict:
    shape = {}
    for f in mi.type_info(cls).fields:
        t = f.type
        kind = enum(t.values) if isinstance(t, mi.LiteralType) else KINDS[type(t)]
        minimum = getattr(t, "ge", None)
        shape[f.name] = (kind, f.required, minimum)
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
