"""A tiny JSON-Schema checker, enough for the payload examples in our ICDs.

Supported keywords: type, required, properties, additionalProperties (false only),
items, enum, const, minimum, maximum, oneOf. That covers every ICD payload so far.
If an ICD needs more, add it here (or move to the `jsonschema` package; ask first,
it's a new dependency). Unknown keywords are reported, never silently ignored.
"""

from __future__ import annotations

SUPPORTED = {
    "type", "required", "properties", "additionalProperties", "items", "enum", "const",
    "minimum", "maximum", "oneOf", "description", "title", "examples",
}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def problems(value, schema: dict, path: str = "payload") -> list[str]:
    """Every way `value` breaks `schema`; an empty list means it matches."""
    if not isinstance(schema, dict):
        return [f"{path}: schema must be a mapping"]
    unknown = set(schema) - SUPPORTED
    if unknown:
        return [f"{path}: schema keyword(s) not supported by tools/reqs/schema.py: {sorted(unknown)}"]

    if "oneOf" in schema:
        matching = [s for s in schema["oneOf"] if not problems(value, s, path)]
        if len(matching) != 1:
            return [f"{path}: matches {len(matching)} of the oneOf choices (must match exactly 1)"]

    found: list[str] = []
    if "const" in schema and value != schema["const"]:
        found.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path}: {value!r} is not one of {schema['enum']}")

    kind = schema.get("type")
    if kind is not None:
        kinds = kind if isinstance(kind, list) else [kind]
        if not any(_TYPES[k](value) for k in kinds if k in _TYPES):
            return found + [f"{path}: expected {kind}, got {type(value).__name__}"]

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            found.append(f"{path}: {value} is below the minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            found.append(f"{path}: {value} is above the maximum {schema['maximum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                found.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                found += problems(value[key], sub, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    found.append(f"{path}: unexpected key {key!r}")

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            found += problems(item, schema["items"], f"{path}[{i}]")
    return found
