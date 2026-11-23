"""Run inside one option's folder; prints that option's results as JSON.

    cd a_stdlib && PYTHONPATH=..:. python ../probe.py

G1: every ICD example decodes and encodes back to the same JSON (same keys, same types).
G4 / C3: bad payloads are dropped, not crashing, and not accepted.
C3: a bad message is refused when it is created or sent.
G3 / C1: seeded changes to the ICD that the code doesn't have are caught.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging

import icd
import drift
import messages

logging.disable(logging.CRITICAL)
api = importlib.import_module("codec") if importlib.util.find_spec("codec") else messages
ICD = icd.messages()

BAD = [
    ("blink", "not JSON", b'{"ms": 18'),
    ("blink", "empty payload", b""),
    ("blink", "JSON array, not an object", b"[180]"),
    ("blink", "string for an integer", b'{"ms": "180"}'),
    ("blink", "true for an integer", b'{"ms": true}'),
    ("blink", "fraction for an integer", b'{"ms": 180.5}'),
    ("blink", "below the minimum", b'{"ms": -5}'),
    ("blink", "extra key", b'{"ms": 180, "speed": 2}'),
    ("expression", "unknown expression name", b'{"name": "angry", "ms": 300}'),
    ("expression", "missing key", b'{"name": "happy"}'),
    ("look", "string for a number", b'{"x": "1.2", "y": 3.5, "z": 1.0}'),
    ("look", "both look shapes at once", b'{"x": 1, "y": 2, "z": 3, "mode": "idle"}'),
    ("look", "unknown mode", b'{"mode": "dance"}'),
    ("theme", "number for a string", b'{"name": 5}'),
    ("status", "unknown status", b"sleeping"),
    ("status", "not UTF-8", b"\xff\xfe"),
]
GOOD = [("look", "whole-number coordinates (valid: integers are numbers)", b'{"x": 1, "y": 2, "z": 3}')]


def same_json(a, b) -> bool:
    """Same keys, values and JSON types (1 and 1.0 count as different)."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def g1() -> list[dict]:
    rows = []
    for name, m in ICD.items():
        for example in m["examples"]:
            raw = example.encode() if name == "status" else json.dumps(example).encode()
            msg = api.decode(name, raw)
            out = api.encode(name, msg) if msg is not None else None
            back = None if out is None else (out.decode() if name == "status" else json.loads(out))
            rows.append({"message": name, "example": example, "sent": None if out is None else out.decode(),
                         "ok": back is not None and same_json(back, example)})
    return rows


def bad_payloads() -> list[dict]:
    rows = []
    for name, label, raw in BAD + GOOD:
        try:
            result = api.decode(name, raw)
            outcome = "dropped" if result is None else f"accepted as {result!r}"
        except Exception as err:  # a crash: what G4 must never see
            outcome = f"CRASH {type(err).__name__}: {err}"
        rows.append({"message": name, "case": label, "should": "accept" if (name, label, raw) in GOOD else "drop",
                     "outcome": outcome})
    return rows


def send_side() -> list[dict]:
    """Make a bad message in code and try to send it."""
    rows = []
    for label, make in [("Blink(ms=-5)", lambda: messages.Blink(ms=-5)),
                        ("Expression(name='angry', ms=300)", lambda: messages.Expression(name="angry", ms=300)),
                        ("Blink(ms='180')", lambda: messages.Blink(ms="180"))]:
        name = "blink" if label.startswith("Blink") else "expression"
        try:
            sent = api.encode(name, make())
            rows.append({"case": label, "outcome": f"SENT {sent.decode()}"})
        except Exception as err:
            rows.append({"case": label, "outcome": f"refused ({type(err).__name__})"})
    return rows


def _add_ease(m):
    e = m["expression"]
    e["payload_schema"]["properties"]["ease"] = {"enum": ["linear", "smooth"]}
    e["payload_schema"]["required"].append("ease")
    e["examples"] = [{"name": "happy", "ms": 300, "ease": "smooth"}]


def _add_wink(m):
    m["expression"]["payload_schema"]["properties"]["name"]["enum"].append("wink")


def _blink_min(m):
    m["blink"]["payload_schema"]["properties"]["ms"]["minimum"] = 20


def _rename_theme(m):
    s = m["theme"]["payload_schema"]
    s["properties"] = {"theme": s["properties"].pop("name")}
    s["required"] = ["theme"]
    m["theme"]["examples"] = [{"theme": "halloween"}]


def _drop_z(m):
    s = m["look"]["payload_schema"]["oneOf"][0]
    del s["properties"]["z"]
    s["required"].remove("z")
    m["look"]["examples"][0] = {"x": 1.2, "y": 3.5}


SEEDS = [
    ("add a required key (expression.ease)", _add_ease),
    ("add an allowed value (expression name 'wink')", _add_wink),
    ("change a limit (blink ms minimum 0 -> 20)", _blink_min),
    ("rename a key (theme name -> theme)", _rename_theme),
    ("remove a key (look z)", _drop_z),
]


def regenerated(changed: dict):
    """Pretend the checker or generator has run on the changed ICD (options A and D only)."""
    schemas = {n: m["payload_schema"] for n, m in changed.items()}
    if api is not messages:  # option D: rebuild messages.py in memory
        import generate
        ns: dict = {}
        exec(generate.source(changed), ns)
        api.CLASSES, api.SCHEMAS = ns["CLASSES"], ns["SCHEMAS"]
        return lambda: [p for p in drift.drift(changed) if "out of date" not in p]
    if hasattr(messages, "SCHEMAS"):  # option A: schemas.json rewritten by the checker
        messages.SCHEMAS = schemas
        return lambda: drift.drift(changed)
    return None


def seeds() -> list[dict]:
    rows = []
    for label, edit in SEEDS:
        changed = icd.changed(ICD, edit)
        saved = {k: getattr(m, k, None) for m in (messages, api) for k in ("SCHEMAS", "CLASSES")}
        before = drift.drift(changed)
        check_after = regenerated(changed)
        after = check_after() if check_after else None
        for m in (messages, api):  # undo the pretend regeneration
            for k in ("SCHEMAS", "CLASSES"):
                if saved.get(k) is not None and hasattr(m, k):
                    setattr(m, k, saved[k])
        if not before:
            verdict = "MISSED"
        elif after is None:
            verdict = "caught by the drift test; code edit needed"
        elif after:
            verdict = "caught; after regenerating, the drift test still asks for a code edit"
        else:
            verdict = "caught; regenerating fixes it, no code edit"
        rows.append({"seed": label, "verdict": verdict, "first_problem": before[0] if before else None,
                     "after_regenerating": after})
    return rows


if __name__ == "__main__":
    print(json.dumps({"g1": g1(), "bad": bad_payloads(), "send": send_side(), "seeds": seeds()}, indent=1))
