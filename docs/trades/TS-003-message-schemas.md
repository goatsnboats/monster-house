# TS-003 — Message schemas in code: how payloads are defined and checked

> **Status:** Evaluating · **Date:** 2026-11-22 · **Decides:** how the Python components define, build and check MQTT payloads, and how that stays in step with the ICDs · **TBD:** TBD-003 · **ADR:** — · **Affects:** `shared/`, Stage 0 Steps 1-6, ICD-001 to ICD-004, ADR 0001

Status moves through `Framing` → `Awaiting weights` (Stop 1) → `Evaluating` →
`Recommended` (Stop 2) → `Decided (owner, YYYY-MM-DD, <where>)`.

## 1. Question

How should the Python code define the MQTT message payloads, build and check them, and
stay in step with the payload schemas already written in the ICDs?

## 2. Context

- **What is already settled.** The *wire format* is not part of this study. The ICDs
  (ADR 0001) already define every payload as a JSON Schema (a small subset) in their YAML
  blocks: JSON objects in UTF-8 for our own commands (ICD-001, ICD-003, ICD-004), plain
  text for eye status, and ESPHome's plain-text numbers for the radar (ICD-002). The
  checker validates each ICD's examples against its schema with the 100-line
  `tools/reqs/schema.py` (standard library only). CLAUDE.md asks before any change to a
  message format, so every option here must keep those bytes as they are.
- **What depends on it:** Stage 0 Step 1's "done when" (a test message through
  Mosquitto *using the shared schemas*); every component that sends or receives a
  message: eye renderer (Step 2), fake radar (Step 3), brain and fake FPP (Step 4), house
  preview (Step 5), phone page (Step 6); simulator parity (CLAUDE.md); EYE and SHW
  requirements on ignoring malformed messages (checked in VE-002 and VE-003).
- **Constraints and owner direction:**
  - Topic names and payload formats live in one place, `shared/` (CLAUDE.md).
  - Everything runs on Raspberry Pi OS 64-bit (Python 3.11, aarch64); the eye Pi has
    1 GB of memory, and its budget is still open (TBD-032).
  - Plain, readable code; the owner reads it but isn't a full-time developer (CLAUDE.md).
  - Ask before adding a heavy dependency (CLAUDE.md).
  - Every component is Python (ADR 0002), so no neutral cross-language definition is
    needed for now.
  - This is a choice in the design of the system, so it gets a formal study (owner,
    2026-11-11); the owner approved starting it on 2026-11-18.
- **Deadline:** before the eye renderer's MQTT listener (Step 2, last item) and the fake
  radar (Step 3), both December 2026. The drawing work in Step 2 does not wait for it.
- **Cost to reverse:** low today (no component sends or receives a payload yet). It grows
  with each component written against the choice; after Step 6 a change touches every
  component and its tests.

## 3. Criteria

### Gates (must pass)

| ID | Gate | How checked | Traces to |
|---|---|---|---|
| G1 | Keeps the ICD wire format exactly: same JSON keys and types, plain-text status and radar values | The ICD examples encode to the same bytes and decode back | CLAUDE.md (ask before changing a message format), ICD-001 to ICD-004 |
| G2 | Runs on Raspberry Pi OS 64-bit, Python 3.11, aarch64, installed with pip from pinned versions (pure Python, or wheels published for that platform) | Package index listing for the pinned version; install on the desktop | SYS-039, SYS-040 |
| G3 | A payload is defined in one place, or a test fails when the code and the ICD disagree | A deliberate mismatch makes `pytest` or the checker fail | CLAUDE.md (one place), ADR 0001 |
| G4 | A malformed message can be detected and dropped without crashing the receiver | Feed a bad payload; the receiver logs it and carries on | SYS-017, SYS-037 |

### Weighted criteria

| ID | Criterion | Weight | How measured | 1 = | 3 = | 5 = |
|---|---|---|---|---|---|---|
| C1 | **One source, no drift:** how many places change when a payload changes, and how surely a mismatch is caught | **35** | Count the edits for a sample change (add a field to `expression`); seed a mismatch and see what catches it | Two or more hand-kept copies; a mismatch shows up only at run time | Two copies, but a test fails on any mismatch | One source; everything else derives from it automatically |
| C2 | **Readable for the owner:** how plain the definitions and the sending/receiving code are | **20** | Write the ICD-001 messages in each option; judge against "plain over clever" (CLAUDE.md) | Needs a framework's concepts (validators, generated code nobody reads) to follow | Readable with one library idiom to learn | Plain Python a reader follows line by line |
| C3 | **Catches mistakes:** what is checked on receive (types, enums, ranges, unknown keys) and whether the editor flags a wrong field when sending | **10** | Seed bad payloads (wrong type, unknown enum, extra key, out of range); check the editor's type hints | Only "is it JSON" | Types and required keys | Everything in the ICD schema, plus typed fields in the editor |
| C4 | **Footprint on the Pi:** extra install size, memory and import time in each component | **15** | Measure on the desktop (no Pi yet: TBD-013); judge the Pi from that | Tens of MB of memory or > 0.5 s import | A few MB, < 0.2 s | Standard library or near zero |
| C5 | **Dependency risk:** new packages to pin, their maintenance and license, and how long they will last | **20** | Package index and project pages, checked during the study | Several new packages, or one with an uncertain future | One well-maintained package | No new dependency |

Weights total 100, **set by the owner on 2026-11-22** (Stop 1, chat session). The draft was
30 / 25 / 20 / 15 / 10. The owner said keeping dependencies few and having one source of
truth matter most, and chose 35 / 20 / 10 / 15 / 20 from three proposed sets: C1 and C5 rise,
and the points come mostly from C3 (gate G4 already makes sure a bad message can't crash a
receiver) and some from C2. Together C4 and C5, the two "keep it light" criteria, now
carry 35.

Considered and left out as a criterion: **speed.** The busiest message is about 10 per
second (ICD-001 `look`); any option handles that with room to spare (judgment).

## 4. Options

### Screened out

| Option | Reason |
|---|---|
| Plain dicts, each component checks what it reads | Fails G3: every component holds its own idea of the payload |
| Protocol Buffers, MessagePack, CBOR | Fail G1: change the wire format away from the JSON in the ICDs, and lose readable `mosquitto_sub` output |
| `TypedDict` hints only | Fails G4 on its own: no check at run time. Covered by option A's hand-written types plus a checker |
| `jsonschema` package, payloads stay dicts | Dominated by A: the same "ICD is the source" shape, plus a dependency the 100-line checker doesn't need yet (A can switch to it later if the schemas outgrow the subset) |
| attrs + cattrs, marshmallow | Dominated by B and C: the same "model in code" shape, but no built-in export to JSON Schema to compare with the ICDs |

### Shortlist

**A — ICD-first, standard library.** The ICD schemas stay the only definition. The
checker writes them into `shared/schemas.json` (generated, kept up to date like
`trace.md`), and receivers check each payload with the existing small checker, moved
into `shared/`. Small hand-written dataclasses give the code named fields; a test makes
every ICD example round-trip through its dataclass. No new dependency.

**B — pydantic v2 models.** One `pydantic` model per message in `shared/`, which builds
and checks payloads. A test compares each model's exported JSON Schema (or at least the
ICD examples) with the ICD, so the two copies can't drift silently. One new dependency
(`pydantic` and its compiled core).

**C — msgspec Structs.** The same shape as B with `msgspec`: small typed structs that
decode and check JSON in one step, and can export JSON Schema for the same drift test.
One new, smaller dependency.

**D — Generated from the ICDs.** A small generator (our own, about 150 lines, or
`datamodel-code-generator` as a development-only tool) turns each ICD schema into a
Python dataclass with its checks, written to `shared/` and kept up to date by the
checker. The ICD is the one source; nobody edits the generated file.

## 5. Evidence

*Under way (weights set 2026-11-22).*

Planned:
- **measured:** a trial in `trials/ts-003/` writing ICD-001's five messages in each
  option; the edits for one sample change; seeded mismatches and bad payloads; install
  size, memory and import time on the desktop.
- **documented:** aarch64 wheels for the pinned `pydantic`, `pydantic-core` and
  `msgspec` versions on PyPI; maintenance and license (checked on the day).
- **judgment:** readability, read side by side.

## 6. Scores

*Not run yet (evidence first).*

## 7. Sensitivity

*Not run yet.*

## 8. Recommendation

*Not yet.*

## 9. Decision

*Open.*

## Couplings

- **ADR 0001 (ICD format):** options A and D keep the ICD schema as the source, as ADR 0001
  intended. With B and C the code holds a second definition, so ADR 0001's "the ICD
  defines the payload" becomes "the ICD and the code must agree, checked by a test".
- **ICD-002 (radar):** ESPHome sends each value as a plain-text number on its own topic,
  not JSON. Every option needs a small per-topic parser there; the study's trial covers it.
- **TBD-030 (coming vs going):** if the brain works it out from position (no new topic),
  ICD-002 doesn't grow.
- **TBD-032 (Pi memory):** C4 feeds the eye Pi's memory budget.
- **TBD-015 (FPP topics):** the FPP payloads are FPP's, not ours; they get parsed, not defined.

## Links

- [TBD register](../TBD.md) (TBD-003)
- [ADR 0001](../decisions/0001-requirements-and-architecture-format.md), [ADR 0002](../decisions/0002-eye-renderer.md)
- [ICD-001](../interfaces/ICD-001-eye-commands.md), [ICD-002](../interfaces/ICD-002-radar-targets.md), [ICD-003](../interfaces/ICD-003-clips.md), [ICD-004](../interfaces/ICD-004-phone-page.md)
- `tools/reqs/schema.py`: the existing schema checker
