"""The generated message modules in shared/messages/ (ADR 0003)."""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

import pytest

from shared.messages import codec
from shared.messages import eye_commands as eyes
from tools.reqs import gen_messages
from tools.reqs.load import load

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL = load(REPO_ROOT)


def icd_examples():
    """(module, message name, example) for every example of every generated message."""
    for icd in MODEL.icds.values():
        module = gen_messages.module_name(icd["_file"])
        for m in icd.get("messages") or []:
            if "payload_schema" in m:
                for example in m.get("examples") or []:
                    yield pytest.param(module, m["name"], example, id=f"{icd['id']} {m['name']} {example}")


def test_generated_modules_are_up_to_date():
    """The modules on disk are exactly what the ICDs make: run tools.reqs.check if this fails."""
    folder = REPO_ROOT / gen_messages.OUT_DIR
    expected = gen_messages.render_all(MODEL)
    for name, text in expected.items():
        assert (folder / name).read_text() == text, f"{name} is stale: run .venv/bin/python -m tools.reqs.check"
    on_disk = {p.name for p in folder.glob("*.py")} - gen_messages.HAND_WRITTEN
    assert on_disk == set(expected), "a generated module has no ICD any more: run tools.reqs.check"


@pytest.mark.parametrize("module, name, example", list(icd_examples()))
def test_every_icd_example_round_trips(module, name, example):
    mod = importlib.import_module(f"shared.messages.{module}")
    schema = mod.SCHEMAS[name]
    raw = json.dumps(example).encode() if codec.is_json(schema) else str(example).encode()
    message = mod.decode(name, raw)
    assert message is not None
    sent = mod.encode(name, message)
    back = json.loads(sent) if codec.is_json(schema) else sent.decode()
    assert json.dumps(back, sort_keys=True) == json.dumps(example, sort_keys=True)  # same JSON types too


def test_messages_become_their_classes():
    assert eyes.decode("look", b'{"x": 1.2, "y": 3.5, "z": 1.0}') == eyes.LookAt(x=1.2, y=3.5, z=1.0)
    assert eyes.decode("look", b'{"mode": "idle"}') == eyes.LookIdle(mode="idle")
    assert eyes.decode("blink", b'{"ms": 180}') == eyes.Blink(ms=180)
    assert eyes.decode("status", b"online") == "online"


def test_sending():
    assert eyes.encode("blink", eyes.Blink(ms=180)) == b'{"ms": 180}'
    assert eyes.encode("expression", eyes.Expression(name="happy", ms=300)) == b'{"name": "happy", "ms": 300}'
    assert eyes.encode("status", "offline") == b"offline"


@pytest.mark.parametrize("name, payload", [
    ("blink", b'{"ms": 18'),                                 # not JSON
    ("blink", b""),                                          # empty
    ("blink", b"[180]"),                                     # not an object
    ("blink", b'{"ms": "180"}'),                             # string for an integer
    ("blink", b'{"ms": true}'),                              # true for an integer
    ("blink", b'{"ms": -5}'),                                # below the minimum
    ("blink", b'{"ms": 180, "speed": 2}'),                   # a key the ICD doesn't have
    ("expression", b'{"name": "angry", "ms": 300}'),         # not one of the expressions
    ("expression", b'{"name": "happy"}'),                    # missing key
    ("look", b'{"x": 1, "y": 2, "z": 3, "mode": "idle"}'),   # both look shapes at once
    ("status", b"sleeping"),                                 # not a status
    ("status", b"\xff\xfe"),                                 # not UTF-8
])
def test_bad_payloads_are_dropped_and_logged(name, payload, caplog):
    with caplog.at_level(logging.WARNING):
        assert eyes.decode(name, payload) is None
    assert f"dropped ICD-001 {name}" in caplog.text


@pytest.mark.parametrize("name, message", [
    ("blink", eyes.Blink(ms=-5)),
    ("blink", eyes.Blink(ms="180")),
    ("expression", eyes.Expression(name="angry", ms=300)),
    ("status", "sleeping"),
])
def test_sending_a_bad_message_is_refused(name, message):
    with pytest.raises(ValueError):
        eyes.encode(name, message)


# --- The generator itself, on made-up ICDs ------------------------------------------------

def fake_icd(messages: list[dict]) -> dict:
    return {"id": "ICD-099", "title": "Test", "_file": "ICD-099-test.md", "messages": messages}


def load_module(text: str):
    namespace: dict = {}
    exec(compile(text, "generated", "exec"), namespace)
    return namespace


def test_optional_keys_are_left_out_when_none():
    schema = {"type": "object", "required": ["a"], "additionalProperties": False,
              "properties": {"a": {"type": "integer"}, "b": {"type": "string"}}}
    mod = load_module(gen_messages.render(fake_icd([{"name": "thing", "from": "x", "to": "y",
                                                     "payload_schema": schema}])))
    Thing = mod["Thing"]
    assert mod["encode"]("thing", Thing(a=1)) == b'{"a": 1}'
    assert mod["encode"]("thing", Thing(a=1, b="hi")) == b'{"a": 1, "b": "hi"}'
    assert mod["decode"]("thing", b'{"a": 1}') == Thing(a=1)


@pytest.mark.parametrize("schema, complaint", [
    ({"oneOf": [{"type": "object", "properties": {}}, {"type": "object", "properties": {}}]}, "title"),
    ({"type": "object", "properties": {"inner": {"type": "object"}}}, "no Python type"),
    ({"type": "object", "properties": {"not ok": {"type": "string"}}}, "field name"),
])
def test_generator_refuses_what_it_cannot_write(schema, complaint):
    with pytest.raises(gen_messages.GeneratorError, match=complaint):
        gen_messages.render(fake_icd([{"name": "thing", "from": "x", "to": "y", "payload_schema": schema}]))


def test_changing_the_icd_changes_the_module():
    """Drift can't hide: the ICD with a new key renders differently from what's on disk."""
    icd = json.loads(json.dumps(MODEL.icds["ICD-001"]))
    blink = next(m for m in icd["messages"] if m["name"] == "blink")
    blink["payload_schema"]["properties"]["soft"] = {"type": "boolean"}
    text = gen_messages.render(icd)
    assert "    soft: bool = None" in text
    assert text != (REPO_ROOT / "shared/messages/eye_commands.py").read_text()
