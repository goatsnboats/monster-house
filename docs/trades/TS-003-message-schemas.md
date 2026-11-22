# TS-003 — Message schemas in code: how payloads are defined and checked

> **Status:** Recommended · **Date:** 2026-11-22 · **Decides:** how the Python components define, build and check MQTT payloads, and how that stays in step with the ICDs · **TBD:** TBD-003 · **ADR:** [0003](../decisions/0003-message-schemas.md) (Proposed) · **Affects:** `shared/`, Stage 0 Steps 1-6, ICD-001 to ICD-004, ADR 0001

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
  preview (Step 5), phone page (Step 6); simulator parity (CLAUDE.md); EYE-015 on
  ignoring malformed messages (checked in VE-002 and VE-003).
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

**D — Generated from the ICDs.** A small generator of our own turns each ICD schema into
Python dataclasses, written to `shared/` and kept up to date by the checker; receivers
check payloads with the same small checker as A. The ICD is the one source; nobody edits
the generated file. (`datamodel-code-generator` was considered as the generator and left
out: see E10.)

## 5. Evidence

Gathered 2026-11-22 with the trial in [`trials/ts-003/`](../../trials/ts-003/README.md):
ICD-001's five messages written in each option, a drift test for each, and a probe that
round-trips, attacks and changes them. The full report, with logs, is
[results/TS-003](results/TS-003/README.md). Desktop: Intel Core Ultra 7 270K Plus,
Ubuntu 26.04, Python 3.11.18; pydantic 2.14.4 (pydantic-core 2.50.5), msgspec 0.22.0.

| # | Tag | Finding |
|---|---|---|
| E1 | measured | **G1, all four pass.** Every ICD-001 example (7) decodes and encodes back to the same JSON keys, values and types. A and D write `{"ms": 180}`, B and C `{"ms":180}`: the same JSON, spacing aside. |
| E2 | measured | **G4, all four pass; receiving is equally strict.** All 16 bad payloads (not JSON, wrong type, `true` or `180.5` for an integer, below the minimum, extra key, unknown name, missing key, both look shapes at once, bad status, not UTF-8) are dropped and logged by every option, with no crash. A valid look with whole numbers is accepted by all. |
| E3 | measured | **Sending a bad message:** A, B and D refuse `Blink(ms=-5)`, `Expression(name="angry")` and `Blink(ms="180")`. **C sends all three** (`{"ms":-5}`): msgspec checks only when it decodes. |
| E4 | measured | pydantic's default (lax) mode turns `{"ms": "180"}` into 180. B needs `strict=True` on every model to match the ICD; the trial sets it once in a base class. |
| E5 | measured | msgspec can't decode "LookAt or LookIdle" (look's `oneOf`) in one step: it refuses an untagged union of two structs, and a tag adds a `"type"` key to the JSON, which would break G1. C tries each class in turn instead. |
| E6 | measured | **G3, all four pass.** Five seeded ICD changes the code didn't have (add a required key, add an allowed value, change a limit, rename a key, remove a key): every option's drift test caught all five. Code edits then needed: **A** 4 of 5 (the limit change needs none: A checks limits against the ICD itself); **B** 5 of 5; **C** 5 of 5; **D** none (rerun the generator). |
| E7 | measured | **Sample change** (add a required `ease` to `expression`), done for real; the drift test is clean afterwards in all four. Edited by hand: **A** the ICD + 1 line, then the checker rewrites `schemas.json`; **B** the ICD + 1 line; **C** the ICD + 1 line; **D** the ICD only, then `generate.py` rewrites `messages.py`. Diff: [sample-change.diff](results/TS-003/logs/sample-change.diff). |
| E8 | measured | **Footprint on the desktop** (median of 15 fresh processes; import, then 2,000 decodes): extra memory over a plain-Python baseline **A 0.9 MB, B 14.1 MB, C 1.5 MB, D 0.3 MB**; import **A 10.1 ms, B 47.3 ms, C 11.6 ms, D 8.5 ms** (baseline 6.6 ms). Installed: B 7.3 MB in 5 packages, C 0.5 MB, A and D nothing. |
| E9 | documented | PyPI, checked 2026-11-22. **pydantic** 2.14.4, MIT, pure Python, needs pydantic-core 2.50.5 (MIT, compiled; cp311 manylinux aarch64 wheel published), annotated-types, typing-extensions and typing-inspection; 21 pydantic releases in the past year. **msgspec** 0.22.0, BSD-3-Clause, cp311 manylinux aarch64 wheel, no dependencies; 4 releases in the past year (github.com/msgspec/msgspec). G2: both pass. |
| E10 | documented | **datamodel-code-generator** 0.100.0 (PyPI, 2026-11-22) needs pydantic, black, isort, jinja2, inflect, genson and argcomplete, and shipped 88 releases in the past year. Too heavy and too fast-moving for C5, so D uses a small generator of our own. |
| E11 | measured | **D's generator covers all four Stage 0 ICDs.** Written for ICD-001, it failed on ICD-002 to ICD-004 (names with spaces, messages with no JSON schema, booleans, lists); 6 more lines fixed all of it. It is 69 lines. A `oneOf` choice gets its class name from its keys (`LookXYZ`, `LookMode`) unless the ICD gives it a `title`. |
| E12 | measured | **Code to read** (non-blank lines): A `messages.py` 62 + drift test 33; B 51 + 31; C 53 + 31; D `codec.py` 34 + drift test 15 + `generate.py` 69, plus the generated `messages.py` (58). A and D share the existing schema checker (62, moved from `tools/reqs/` to `shared/`); A, B and C's drift tests share a 38-line shape comparer. |
| E13 | judgment | **Readability**, read side by side. A is plain dataclasses, `json` and the checker the project already has. D's generated file reads like A's (plain dataclasses and the schemas as a Python dict), but it is code written by code: you change the ICD, run the generator, and never edit the file. B and C read well once you know their idioms (`BaseModel`, `ConfigDict`, `Field(ge=0)`, `TypeAdapter`; `Struct`, `Meta`, `Annotated`), and each has a trap a reader must know (E4, E5). |
| E14 | judgment | **On the Pi:** a Pi 5 runs Python a few times slower than this desktop, so B's import would be roughly 0.15 to 0.25 s and its memory about the same 14 MB in each Python component. Measurable once a Pi arrives (TBD-013). |

## 6. Scores

Scored against the scales in §3, written before any evidence was gathered.

| Criterion (weight) | A ICD-first | B pydantic | C msgspec | D Generated |
|---|---|---|---|---|
| C1 One source, no drift (35) | **4**: two copies of the field names, one of the rules; a test catches every mismatch (E6, E7) | **3**: two copies; a test catches every mismatch (E6) | **3**: as B (E6) | **5**: the ICD is the only copy; regenerating fixes every seeded change (E6, E7) |
| C2 Readable for the owner (20) | **5**: plain Python (E12, E13) | **3**: one library's idioms, and strict mode to remember (E4, E13) | **3**: one library's idioms, and the look workaround (E5, E13) | **4**: plain generated code, but code written by code (E11, E13) |
| C3 Catches mistakes (10) | **5**: everything in the ICD, on receive and on send (E2, E3) | **5**: the same, with `strict=True` (E2, E3, E4) | **4**: receive only; bad messages go out (E2, E3) | **5**: as A (E2, E3) |
| C4 Footprint on the Pi (15) | **5**: standard library, +0.9 MB (E8) | **2**: +14 MB, 47 ms import, 7.3 MB installed (E8, E14) | **4**: +1.5 MB, 0.5 MB installed (E8) | **5**: standard library, +0.3 MB (E8) |
| C5 Dependency risk (20) | **5**: none (E9) | **2**: five packages, though one well-run project (E9) | **3**: one well-maintained package (E9) | **5**: none; the generator is ours (E10, E11) |
| **Weighted total (of 500)** | **465** | **285** | **325** | **480** |

## 7. Sensitivity

From [`score.py`](../../trials/ts-003/score.py) ([scores.json](results/TS-003/scores.json)).

- **D leads A by 15; B and C trail by 155 or more.** No reasonable weights bring B or C
  back: they lose on C1, C4 and C5 together, three of your four heaviest criteria.
- **On the weights, D against A is not close.** A ties D only if C1 drops from 35 to 20,
  or C2 rises from 20 to 35 (a 15-point change to one weight). Moving 7.5 points from C1
  to C2 also ties.
- **On the scores, D against A is close.** A and D differ on only two criteria, both
  judged: C1 (D 5, A 4) and C2 (A 5, D 4). Lowering any one of D's scores by a point
  ties or flips the result. For example, if you find generated code harder to follow
  (D's C2 at 3), A wins 465 to 460.
- **What it really hinges on:** would you rather keep a 69-line generator so that an ICD
  change needs no code edit at all (D), or edit one line by hand per change, with a test
  that fails until you do (A)?
- **Narrow gates:** C passes G1 only by trying each look class in turn (E5). B passes G4
  as strictly as the others only with `strict=True` (E4).

## 8. Recommendation

**Option D: generate the message classes from the ICDs**, with the standard library and
no new dependency.

- **Why:** it is the only option where the ICD is truly the one source (your heaviest
  criterion). It adds no dependency and the least memory, and it checks everything the
  ICD says on both send and receive.
- **A and D are close, and both are good choices.** They are the same design (the ICD
  defines each message, and the small checker enforces it); D adds a generator for the
  classes. Choose A if you would rather read hand-written classes than keep a generator.
- **Main risks:**
  - The generator is our code. Each new JSON-schema keyword an ICD uses must be added to
    both the checker and the generator (E11 needed 6 lines for ICD-002 to ICD-004).
  - Class names for a `oneOf` (`LookXYZ`) read badly unless the ICD gives each choice a
    `title`. That adds a line to ICD-001 but doesn't change any message on the wire.
  - The generated file must be committed and never edited by hand. The checker would run
    the generator, as it already writes `trace.md`, and the drift test would fail if anyone
    edits the file.
- **What would change it:**
  - Generated code proving hard for you to follow: A instead.
  - ICDs needing JSON-schema features well beyond today's subset: reconsider the
    `jsonschema` package, a new dependency, for checking.
  - A component written in another language: the ICDs' JSON Schema already serves it.
- **Cost to reverse:** low. Going from D to A means deleting the generator and keeping its
  last output as hand-written code. Going to B or C later means rewriting `shared/` and
  every component's sending and receiving, and that cost grows with each Stage 0 step.

## 9. Decision

*Open: the owner decides (Stop 2). Proposed: [ADR 0003](../decisions/0003-message-schemas.md).*

## Couplings

- **ADR 0001 (ICD format):** options A and D keep the ICD schema as the source, as ADR 0001
  intended. With either, the schema subset the checker understands (`tools/reqs/schema.py`)
  becomes code the components run, so it moves into `shared/`. With B and C the code holds a second definition, so ADR 0001's "the ICD
  defines the payload" becomes "the ICD and the code must agree, checked by a test".
- **ICD-002 (radar):** ESPHome sends each value as a plain-text number on its own topic,
  not JSON. The ICD types these as strings, so every option hands the brain text that it
  turns into numbers itself; that parsing is the same in all four and wasn't trialled.
- **TBD-030 (coming vs going):** if the brain works it out from position (no new topic),
  ICD-002 doesn't grow.
- **TBD-032 (Pi memory):** C4 feeds the eye Pi's memory budget.
- **TBD-015 (FPP topics):** the FPP payloads are FPP's, not ours; they get parsed, not defined.

## Links

- [TBD register](../TBD.md) (TBD-003)
- [ADR 0001](../decisions/0001-requirements-and-architecture-format.md), [ADR 0002](../decisions/0002-eye-renderer.md)
- [ICD-001](../interfaces/ICD-001-eye-commands.md), [ICD-002](../interfaces/ICD-002-radar-targets.md), [ICD-003](../interfaces/ICD-003-clips.md), [ICD-004](../interfaces/ICD-004-phone-page.md)
- `tools/reqs/schema.py`: the existing schema checker
- [Results report](results/TS-003/README.md) and the trial, [`trials/ts-003/`](../../trials/ts-003/README.md)
