"""Option D's drift test: messages.py must be exactly what the generator writes from the ICD."""

from __future__ import annotations

import json

import codec
import generate


def drift(icd: dict) -> list[str]:
    found = []
    if generate.OUT.read_text() != generate.source(icd):
        found.append("messages.py is out of date with the ICD (run generate.py)")
    for name, msg in icd.items():
        for example in msg["examples"]:
            raw = example.encode() if name == "status" else json.dumps(example).encode()
            if codec.decode(name, raw) is None:
                found.append(f"{name}: the ICD example {example} doesn't decode")
    return found
