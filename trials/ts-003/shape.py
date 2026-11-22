"""The "shape" of a payload, for drift checks: which fields, their types, and limits.

A shape is a dict {field: (kind, required, minimum)}, where kind is "number",
"integer", "string" or a tuple of allowed values (an enum). Options A, B and C each
turn their classes into shapes and compare them with the ICD's; equal shapes mean the
code and the ICD agree. A message with oneOf has a list of shapes; a plain-text enum
(the eye status) has a tuple of values.
"""

from __future__ import annotations


def enum(values) -> tuple:
    """Allowed values, in a fixed order (their order in the ICD doesn't matter)."""
    return tuple(sorted(values))


def icd_shape(schema: dict, with_minimum: bool = True):
    if "oneOf" in schema:
        return [icd_shape(s, with_minimum) for s in schema["oneOf"]]
    if "enum" in schema and schema.get("type") != "object":
        return enum(schema["enum"])
    required = set(schema.get("required", []))
    shape = {}
    for key, sub in schema.get("properties", {}).items():
        kind = enum(sub["enum"]) if "enum" in sub else sub["type"]
        minimum = sub.get("minimum") if with_minimum else None
        shape[key] = (kind, key in required, minimum)
    return shape


def compare(name: str, icd, code) -> list[str]:
    """Human-readable differences between the ICD's shape and the code's."""
    if icd == code:
        return []
    if isinstance(icd, dict) and isinstance(code, dict):
        found = []
        for key in sorted(set(icd) | set(code)):
            if key not in code:
                found.append(f"{name}: the ICD has {key!r}, the code doesn't")
            elif key not in icd:
                found.append(f"{name}: the code has {key!r}, the ICD doesn't")
            elif icd[key] != code[key]:
                found.append(f"{name}.{key}: ICD says {icd[key]}, code says {code[key]}")
        return found
    return [f"{name}: ICD says {icd}, code says {code}"]
