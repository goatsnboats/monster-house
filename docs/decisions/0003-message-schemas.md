# 0003 — Message schemas: generate the code from the ICDs

> **Status:** Accepted (owner, 2026-11-22, in session) · **Date:** 2026-11-22 · **Deciders:** owner · **Supersedes:** — · **Trade study:** [TS-003](../trades/TS-003-message-schemas.md)

## Context
Every component is Python (ADR 0002) and talks over MQTT. The ICDs already define each
message as a small JSON Schema with examples (ADR 0001), and the checker validates the
examples with a 100-line, standard-library schema checker (`tools/reqs/schema.py`).
CLAUDE.md asks for topic names and payload formats in one place, plain code, few heavy
dependencies, and code that runs on a 1 GB Raspberry Pi 5.

A trial wrote ICD-001's messages four ways: the ICD with hand-written dataclasses (A),
pydantic (B), msgspec (C), and dataclasses generated from the ICD (D). All four kept the
ICD's JSON exactly, dropped 16 kinds of bad payload without crashing, and caught five
seeded ICD changes in a drift test. They differed in where the definition lives:
- **D** needed no code edit for any of the changes. A needed one for four of the five,
  and B and C for all five.
- **Footprint:** pydantic added 14 MB of memory and five packages. msgspec sent bad
  messages unchecked and couldn't read look's "point or idle" without changing the JSON.
- **Score:** with the owner's weights, D scored 480 of 500, A 465, C 325 and B 285.

## Decision
We will keep the ICDs as the only definition of our message payloads, and **generate
the Python message classes from them** with a small generator of our own, using the
standard library. The generator (about 70 lines) writes plain dataclasses and the
schemas into `shared/`, and the checker runs it, as it already writes `trace.md`.
Senders and receivers check every payload against the ICD schema with the existing
schema checker, moved from `tools/reqs/` into `shared/`. A receiver drops and logs a bad
payload; a sender refuses one.

## Consequences
- **Easier:**
  - An ICD change needs no hand edit to the code; running the checker brings `shared/`
    up to date.
  - No new dependency on any Pi. The message code adds about 0.3 MB of memory to each component.
  - Stage 0 Step 1's "done when" (a message through Mosquitto using the shared schemas)
    and the eye renderer's MQTT listener can proceed.
- **Harder:**
  - The generator is ours to keep. Each new JSON-schema keyword an ICD uses must be added
    to both the schema checker and the generator.
  - The generated file is committed and never edited by hand. A test fails if it
    differs from what the generator writes.
- **Must stay true:**
  - The ICD schema subset (`schema.py`'s keyword list) is now code the components run;
    widening it is a code change with tests.
  - A `oneOf` choice should carry a `title` in its ICD (for example `LookAt`,
    `LookIdle`) so its class reads well. That changes the ICD's text, not anything sent
    over MQTT.
- **Requirement allocations:** none change. The checks serve EYE-015 (the eye ignores
  malformed messages), and through it SYS-017 (the rest keeps running) and SYS-037 (no
  error on the eye screens).

## Alternatives considered
- **A — ICD first, hand-written dataclasses:** the same design without the generator,
  and a close second (465). Each ICD change needs a one-line code edit that a drift test
  insists on. It is the fallback if generated code proves hard to follow, and D can
  become A just by deleting the generator.
- **B — pydantic:** five new packages, 14 MB more memory per component, a second copy
  of each definition, and lax type conversion unless every model is made strict.
- **C — msgspec:** light, but a second copy of each definition. It sends bad messages
  unchecked and can't decode look's "point or idle" without adding a tag to the JSON.

## Links
- [TS-003](../trades/TS-003-message-schemas.md) and its [results report](../trades/results/TS-003/README.md)
- [TBD register](../TBD.md) (TBD-003)
- [ADR 0001](0001-requirements-and-architecture-format.md), [ADR 0002](0002-eye-renderer.md)
- Owner's decision: 2026-11-22, in the Claude Code session, after the Stop 2 recommendation ("D sounds good")

<!-- Status values: Proposed → Accepted (owner, YYYY-MM-DD, <where>) → Superseded by NNNN.
     An Accepted ADR is never edited; a new ADR supersedes it. -->
