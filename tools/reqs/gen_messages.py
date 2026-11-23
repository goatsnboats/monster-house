"""Write the message classes in shared/messages/ from the ICDs (ADR 0003).

The ICDs are the only definition of each message payload. For every ICD with message
schemas, this writes one plain Python module (ICD-001-eye-commands.md ->
shared/messages/eye_commands.py) holding:

- a dataclass for each JSON-object message (a `oneOf` gets one class per choice, named
  by the choice's `title`), and a type alias for each plain-text one;
- CLASSES and SCHEMAS (the ICD's schemas, copied as they are);
- encode() and decode(), which check every payload against those schemas.

The checker runs this every time (`python -m tools.reqs.check`), the way it writes
trace.md, and a test fails if a module on disk differs from what this would write.
Nobody edits the generated modules by hand.

It understands the same JSON-Schema subset as shared/schema.py. A schema it can't turn
into Python raises GeneratorError, naming the ICD and message.
"""

from __future__ import annotations

import pprint
import re
from pathlib import Path

from shared.messages.codec import is_json
from tools.reqs.load import Model

OUT_DIR = Path("shared/messages")
HAND_WRITTEN = {"__init__.py", "codec.py"}
HEADER_MARK = "GENERATED from docs/interfaces/"
PY_TYPES = {"number": "float", "integer": "int", "string": "str", "boolean": "bool"}


class GeneratorError(ValueError):
    pass


def module_name(icd_file: str) -> str:
    """'ICD-001-eye-commands.md' -> 'eye_commands'."""
    return re.sub(r"^ICD-\d{3}-", "", icd_file.removesuffix(".md")).replace("-", "_")


def class_name(message: str) -> str:
    """'target count' -> 'TargetCount'."""
    return "".join(word.capitalize() for word in re.split(r"[\s_-]+", message))


def py_type(sub: dict, where: str) -> str:
    """The Python type for one property's schema."""
    if "enum" in sub:
        return "Literal[" + ", ".join(repr(v) for v in sub["enum"]) + "]"
    kind = sub.get("type")
    if kind == "array" and "items" in sub:
        return f"list[{py_type(sub['items'], where)}]"
    if kind in PY_TYPES:
        return PY_TYPES[kind]
    raise GeneratorError(f"{where}: no Python type for {sub} (extend tools/reqs/gen_messages.py)")


def dataclass_source(name: str, schema: dict, doc: str, where: str) -> list[str]:
    if schema.get("type") != "object":
        raise GeneratorError(f"{where}: a oneOf choice must be an object")
    required = schema.get("required", [])
    props = schema.get("properties", {})
    lines = ["@dataclass", f"class {name}:", f'    """{doc}"""']
    # Required fields first: a dataclass can't put a field without a default after one with.
    for key in sorted(props, key=lambda k: k not in required):
        if not key.isidentifier():
            raise GeneratorError(f"{where}: {key!r} can't be a Python field name")
        default = "" if key in required else " = None"
        lines.append(f"    {key}: {py_type(props[key], where)}{default}")
    if not props:
        lines.append("    pass")
    return lines


def _names(ends) -> str:
    """'a' or ['a', 'b'] -> 'a' or 'a, b'."""
    return ", ".join(ends) if isinstance(ends, list) else str(ends)


def render(icd: dict) -> str:
    """The generated module for one ICD."""
    icd_id, icd_file = icd["id"], icd["_file"]
    messages = [m for m in icd.get("messages") or [] if "payload_schema" in m]
    lines = [
        f'"""{icd_id} {icd["title"]}: message payloads.',
        "",
        f"{HEADER_MARK}{icd_file} by `python -m tools.reqs.check`.",
        "Don't edit it by hand: change the ICD, then run the checker (ADR 0003).",
        "",
        "    payload = encode(name, message)   # bytes to send; ValueError if it breaks the ICD",
        "    message = decode(name, payload)   # None (and logged) if the payload breaks the ICD",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Literal",
        "",
        "from shared.messages import codec",
        "",
        f'ICD = "{icd_id}"',
    ]
    classes: dict[str, list[str]] = {}
    seen: set[str] = set()
    for m in messages:
        name, schema = m["name"], m["payload_schema"]
        where = f"{icd_id} {name}"
        route = f"{_names(m.get('from'))} -> {_names(m.get('to'))}"
        if is_json(schema):
            choices = schema.get("oneOf", [schema])
            if len(choices) > 1 and not all(c.get("title") for c in choices):
                raise GeneratorError(f"{where}: give each oneOf choice a title (its class name)")
            names = [c.get("title") or class_name(name) for c in choices]
            for cls, choice in zip(names, choices):
                doc = f"{name} ({route})" + (f", one of {len(choices)} choices" if len(choices) > 1 else "") + "."
                lines += ["", ""] + dataclass_source(cls, choice, doc, where)
            classes[name] = names
        else:
            names = [class_name(name)]
            lines += ["", "", f"# {name} ({route}): plain text", f"{names[0]} = {py_type(schema, where)}"]
        for cls in names:
            if cls in seen or not cls.isidentifier():
                raise GeneratorError(f"{where}: class name {cls!r} is not usable or is used twice")
            seen.add(cls)

    lines += ["", "", "# The class (or classes) each JSON message becomes when received."]
    if classes:
        lines.append("CLASSES = {")
        lines += [f"    {name!r}: ({', '.join(names)}{',' if len(names) == 1 else ''})," for name, names in classes.items()]
        lines.append("}")
    else:
        lines.append("CLASSES: dict = {}  # every message in this ICD is plain text")
    lines += ["", "# Each message's payload schema, exactly as written in the ICD.", "SCHEMAS = {"]
    for m in messages:
        text = pprint.pformat(m["payload_schema"], sort_dicts=False, width=84)
        lines.append(f"    {m['name']!r}: " + text.replace("\n", "\n" + " " * (len(repr(m["name"])) + 6)) + ",")
    lines.append("}")
    lines += [
        "", "",
        "def encode(name: str, message) -> bytes:",
        '    """The payload to send for message `name`. Raises ValueError if it breaks the ICD."""',
        "    return codec.encode(SCHEMAS[name], message)",
        "", "",
        "def decode(name: str, payload: bytes):",
        '    """The message received as `name`, or None (logged) if the payload breaks the ICD."""',
        '    return codec.decode(SCHEMAS[name], CLASSES.get(name, ()), payload, f"{ICD} {name}")',
    ]
    return "\n".join(lines) + "\n"


def render_all(model: Model) -> dict[str, str]:
    """{file name: module text} for every ICD that has message schemas."""
    out = {}
    for icd in sorted(model.icds.values(), key=lambda i: i["id"]):
        if any("payload_schema" in m for m in icd.get("messages") or []):
            out[module_name(icd["_file"]) + ".py"] = render(icd)
    return out


def write_all(root: Path, model: Model) -> list[str]:
    """Rewrite the generated modules; remove generated ones whose ICD has gone. Returns the names."""
    folder = root / OUT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    modules = render_all(model)
    for old in folder.glob("*.py"):
        if old.name not in modules and old.name not in HAND_WRITTEN and HEADER_MARK in old.read_text():
            old.unlink()
    for name, text in modules.items():
        path = folder / name
        if not path.exists() or path.read_text() != text:
            path.write_text(text)
    return sorted(modules)
