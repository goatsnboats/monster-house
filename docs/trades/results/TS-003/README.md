# TS-003 results report — message schemas in code

> **Status:** Final · **Date:** 2026-11-22 · **Study:** [TS-003](../../TS-003-message-schemas.md) · **Decision:** [ADR 0003](../../../decisions/0003-message-schemas.md) (Proposed) · **TBD:** TBD-003

This report backs up TS-003 with its evidence: ICD-001's five messages written four ways,
then round-tripped, attacked, changed and measured. Everything here can be regenerated
from [`trials/ts-003/`](../../../../trials/ts-003/README.md) (see [Reproduce](#reproduce)).

## Summary

**Option D (generated from the ICDs) scores 480 of 500; option A (ICD-first,
hand-written dataclasses) 465; C (msgspec) 325; B (pydantic) 285.**

| | Total | C1 One source (35) | C2 Readable (20) | C3 Catches mistakes (10) | C4 Footprint (15) | C5 Dependencies (20) |
|---|---|---|---|---|---|---|
| **D** Generated from the ICDs | **480** | 5 | 4 | 5 | 5 | 5 |
| **A** ICD-first, standard library | 465 | 4 | 5 | 5 | 5 | 5 |
| **C** msgspec 0.22.0 | 325 | 3 | 3 | 4 | 4 | 3 |
| **B** pydantic 2.14.4 | 285 | 3 | 3 | 5 | 2 | 2 |

**What decided it:**
1. **All four are equally safe on the wire.** Each kept the ICD's JSON exactly, dropped
   all 16 bad payloads without crashing, and caught all five seeded ICD changes.
2. **Where the definition lives separates them.** After an ICD change, D needed no code
   edit, A needed one line in four of five cases, and B and C needed one in every case.
3. **Dependencies and footprint rule out B.** pydantic brings five packages and adds
   14 MB of memory to each component. msgspec is light, but it sends bad messages
   unchecked and can't read look's "point or idle" without changing the JSON.
4. **D against A is close.** It comes down to one judged point on each side: whether
   keeping a 69-line generator is worth never hand-editing the code.

**Order of events.** The owner set the weights on 2026-11-22 (Stop 1); the evidence was
gathered and scored the same day.

## What was compared

| | Option | Defines each message in | Checks with |
|---|---|---|---|
| A | ICD-first, standard library | The ICD, plus a hand-written dataclass | The project's small schema checker, from the ICD |
| B | pydantic v2 | A pydantic model (`strict=True`, `extra="forbid"`) | pydantic |
| C | msgspec | A msgspec Struct (`forbid_unknown_fields`) | msgspec, on decode only |
| D | Generated from the ICDs | The ICD only; `generate.py` writes the dataclasses | The same small checker as A |

Every option has a **drift test**, the test that fails when its code and the ICD
disagree: A, B and C compare their fields with the ICD; D regenerates its file and
compares the text.

**Machine:** Intel Core Ultra 7 270K Plus, Ubuntu 26.04, Python 3.11.18 (x86_64). No Pi
yet (TBD-013).

## Gates

| Gate | A | B | C | D | Evidence |
|---|---|---|---|---|---|
| G1 Keeps the ICD's wire format | pass | pass | pass, narrowly | pass | All 7 ICD-001 examples round-trip to the same JSON. C can't decode the look `oneOf` in one step without a tag key in the JSON, so it tries each class in turn |
| G2 Runs on the Pi from pinned pip installs | pass | pass | pass | pass | Standard library (A, D); cp311 aarch64 wheels on PyPI for pydantic-core 2.50.5 and msgspec 0.22.0 |
| G3 One place, or a test fails on a mismatch | pass | pass | pass | pass | Every drift test caught all 5 seeded ICD changes |
| G4 A bad payload is dropped without crashing | pass | pass | pass | pass | 16 of 16 bad payloads dropped, no crash ([logs](logs/)) |

## Evidence by criterion

### C1 — One source, no drift

Five changes were made to a copy of ICD-001 that the code didn't have; then each
option's drift test was run.

| Seeded ICD change | A | B | C | D |
|---|---|---|---|---|
| Add a required key (`expression.ease`) | caught; 1 code line | caught; 1 code line | caught; 1 code line | caught; regenerate |
| Add an allowed value (`wink`) | caught; 1 code line | caught; 1 code line | caught; 1 code line | caught; regenerate |
| Change a limit (`blink.ms` minimum 0 → 20) | caught; **no code edit** (rules come from the ICD) | caught; 1 code line | caught; 1 code line | caught; regenerate |
| Rename a key (`theme.name` → `theme`) | caught; 1 code line | caught; 1 code line | caught; 1 code line | caught; regenerate |
| Remove a key (`look.z`) | caught; 1 code line | caught; 1 code line | caught; 1 code line | caught; regenerate |

The first change was then made for real in each option ([sample-change.diff](logs/sample-change.diff)).
A, B and C each need the ICD edit plus one line of code. D needs only the ICD edit, then
`generate.py`. The drift tests were clean afterwards in all four.

### C2 — Readable for the owner

Non-blank lines of code a reader meets:

| | Messages | Sending and receiving | Drift test | Other |
|---|---|---|---|---|
| A | `messages.py` 62 (classes, encode, decode) | (in `messages.py`) | 33 | Schema checker 62 (already in the repo) |
| B | `messages.py` 51 | (in `messages.py`) | 31 | — |
| C | `messages.py` 53 | (in `messages.py`) | 31 | — |
| D | generated `messages.py` 58 (classes and schemas) | `codec.py` 34 | 15 | `generate.py` 69; schema checker 62 |

A, B and C's drift tests share a 38-line field comparer. The traps a reader must know:
- **B:** without `strict=True`, pydantic turns `{"ms": "180"}` into 180. That was
  measured with the default settings.
- **C:** msgspec doesn't check values when sending, and look needs a try-each-class loop.
- **D:** the file is written by code, and its `oneOf` class names come from keys
  (`LookXYZ`, `LookMode`) unless the ICD gives each choice a `title`.

D's generator was written for ICD-001. It first failed on ICD-002 to ICD-004 (names with
spaces, messages with no JSON schema, booleans, lists). Six more lines made it generate
all four Stage 0 ICDs.

### C3 — Catches mistakes

| Bad payload received | A | B | C | D |
|---|---|---|---|---|
| Not JSON; empty; a JSON array | dropped | dropped | dropped | dropped |
| `"180"`, `true` or `180.5` for an integer | dropped | dropped | dropped | dropped |
| Below the minimum; extra key; missing key | dropped | dropped | dropped | dropped |
| Unknown expression, mode or status; both look shapes at once | dropped | dropped | dropped | dropped |
| A string for a number; a number for a string; status not UTF-8 | dropped | dropped | dropped | dropped |
| *Valid:* look with whole numbers | accepted | accepted | accepted | accepted |

| Bad message made in code and sent | A | B | C | D |
|---|---|---|---|---|
| `Blink(ms=-5)` | refused | refused | **sent** `{"ms":-5}` | refused |
| `Expression(name="angry", ms=300)` | refused | refused | **sent** | refused |
| `Blink(ms="180")` | refused | refused | **sent** `{"ms":"180"}` | refused |

### C4 — Footprint on the Pi

Median of 15 fresh processes on the desktop. Each process imports the option, then
decodes 1,000 look and 1,000 blink messages. "Extra memory" is measured over a process
that imports only `json`, `logging`, `dataclasses` and `typing` (17.9 MB, 6.6 ms).

| | Extra memory | Import time | Installed |
|---|---|---|---|
| A | 0.9 MB | 10.1 ms | nothing |
| B | **14.1 MB** | **47.3 ms** | 7.3 MB, 5 packages |
| C | 1.5 MB | 11.6 ms | 0.5 MB, 1 package |
| D | 0.3 MB | 8.5 ms | nothing |

A Pi 5 runs Python a few times slower than this desktop. B's import would probably take
0.15–0.25 s there (judgment, to be measured on a Pi: TBD-013).

### C5 — Dependency risk

PyPI, checked 2026-11-22:
- **pydantic 2.14.4** is MIT-licensed, with 21 releases in the past year. It needs
  pydantic-core 2.50.5 (compiled), annotated-types, typing-extensions and
  typing-inspection.
- **msgspec 0.22.0** is BSD-3-Clause, with no dependencies and 4 releases in the past
  year.
- **datamodel-code-generator 0.100.0** was considered as D's generator and left out. It
  needs pydantic, black, isort, jinja2 and more, and shipped 88 releases in the past
  year. D uses its own generator instead.

## Sensitivity

From [`score.py`](../../../../trials/ts-003/score.py) ([scores.json](scores.json)):
- **Weights:** A ties D only with a 15-point change to C1 (35 → 20) or to C2 (20 → 35),
  or by moving 7.5 points from C1 to C2. By the study's 10-point rule, that isn't close.
- **Scores:** lowering any one of D's C1, C2, C4 or C5 scores by a point ties or flips
  the result. The two judged scores that separate A and D are C1 (D 5, A 4) and C2
  (A 5, D 4).
- **B and C** trail by 155 or more, losing on C1, C4 and C5 together.

## Reproduce

See [`trials/ts-003/README.md`](../../../../trials/ts-003/README.md). In short, in a
separate virtual environment with pydantic 2.14.4, msgspec 0.22.0 and PyYAML 6.0.3, run
`python run_trials.py` from `trials/ts-003/`. It writes `results.json` and `logs/` here.
Then run `python score.py` to get the totals and sensitivity.

| File | Holds |
|---|---|
| [results.json](results.json) | Every measurement: machine, versions, probes, sample change, footprint, code size |
| [scores.json](scores.json) | Weights, scores, totals and sensitivity |
| [logs/probe-A.json](logs/probe-A.json) … [probe-D.json](logs/probe-D.json) | Each option's round trips, bad payloads, sends and seeded changes |
| [logs/sample-change.diff](logs/sample-change.diff) | The sample change, as edited by hand in each option |
