# Requirements

> **Status:** Current · **Updated:** 2026-11-09 · **Format:** [ADR 0001](../decisions/0001-requirements-and-architecture-format.md)

What the Monster House **shall** do, decomposed from the whole system down to the parts
that do it, with a check that every link holds.

## Where things are

| File | Holds |
|---|---|
| [spec-tree.md](spec-tree.md) | The subsystems, their ID prefixes and components, the N² interface chart (approved 2026-11-09) |
| [system.yaml](system.yaml) | System requirements, `SYS-NNN` |
| `eye.yaml`, `shw.yaml`, `ear.yaml`, `mth.yaml`, `voc.yaml`, `inf.yaml`, `thm.yaml` | Subsystem requirements, one file per subsystem, named after its prefix |
| `sim.yaml`, `dep.yaml`, `dev.yaml` | Enabling-system requirements (DEV has none for now) |
| [trace.md](trace.md) | **Generated, do not edit:** traceability matrix, coverage, diagrams |
| [../architecture/components.yaml](../architecture/components.yaml) | Every component that requirements are allocated to |
| [../interfaces/](../interfaces/) | One ICD per interface, `ICD-NNN-<slug>.md` |
| [../TBD.md](../TBD.md) | Every open value, cited as `TBD-NNN` |

## How to run the checker

From the repository root:

```bash
.venv/bin/python -m tools.reqs.check              # check, and regenerate trace.md
.venv/bin/python -m tools.reqs.check --no-write   # check only
.venv/bin/python -m tools.reqs.check --strict     # gaps and warnings fail too
.venv/bin/python -m tools.reqs.check --impact SYS-004   # what sits below SYS-004?
.venv/bin/python -m pytest tests/test_reqs_check.py      # the checker's own tests
```

Run it after every change to a requirement, a component or an ICD, and commit the
regenerated `trace.md` with the change. A test fails if `trace.md` is out of date.

The checker reports three levels:

| Level | Means | Fails the check? |
|---|---|---|
| **error** | Something is wrong: a broken link, a missing or misspelled field, a TBD-NNN that isn't in the register | Yes |
| **gap** | Something isn't done yet: a system requirement with no children, an ICD side with no interface requirement | Only with `--strict` |
| **warning** | The ICDs and `shared/topics.py` disagree about a topic name. The checker never changes either; a topic change is a message-format change, so ask the owner | Only with `--strict` |

## A requirement

```yaml
- id: EYE-004
  text: The eye renderer shall draw round pupils; it shall not draw slit pupils.
  type: constraint
  derives_from: [SYS-036]
  allocated_to: eye-renderer
  verify: inspection
  rationale: Friendly, never scary.
  source: CLAUDE.md "Tone"
  stage: 0
  status: proposed
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `PFX-NNN`. The prefix is the subsystem's from the spec tree (`SYS` for system requirements). **Permanent:** never renumbered, never reused, even after deletion |
| `text` | yes | One *shall* statement, worded so it can be checked. Write `TBD-NNN` for a value that isn't decided yet |
| `type` | yes | `functional` (what it does), `performance` (how fast, how often, how much, how loud), `interface` (how it meets another part or the outside world), `constraint` (a limit on how it may be built) |
| `derives_from` | subsystem requirements | The parent requirement(s) this one helps meet. System requirements have none |
| `allocated_to` | subsystem requirements | The one component that meets it, from `components.yaml`. It must belong to the same subsystem as the prefix, unless `allocation_note` says why not |
| `allocation_note` | no | Why a requirement is allocated outside its own subsystem |
| `icd` | interface requirements | The ICD that specifies the interface, e.g. `ICD-001` |
| `verify` | yes | How it will be shown to be met: `inspection` (look at it), `analysis` (calculate, including the budget check), `demonstration` (run it and watch), `test` (run it and measure) |
| `verified_by` | no | Where the evidence is, e.g. `tests/test_gaze.py::test_parallax`. Paths are checked to exist |
| `rationale` | no | Why this requirement exists |
| `source` | yes | Where it comes from: a document and section, or "owner" with a date |
| `stage` | yes | The first stage (0–5) in which it can be verified, in simulation for Stage 0 |
| `status` | yes | `proposed` (written, not yet reviewed by the owner), `approved`, or `deleted` (kept so its ID is never reused) |
| `notes` | no | Anything else |

## Rules

- **One requirement per statement.** Two "shall"s make two requirements.
- **No invented numbers.** A value that isn't in the docs or decided by the owner becomes a
  `TBD-NNN` row in [TBD.md](../TBD.md), cited in the text.
- **One owner per component.** Each component belongs to exactly one subsystem
  (`components.yaml`), and only that subsystem's requirements are allocated to it.
- **Cross-subsystem needs go through an ICD.** If Voice needs a USB port on the porch Pi
  (INF), Voice writes an interface requirement citing the ICD, and INF writes the
  matching one. The checker reports an ICD side with no interface requirement as a gap.
- **What the monster *shall* do is partly the owner's taste.** New requirements start as
  `proposed`; the owner approves them.

## What the checker checks

Errors:
- the YAML files read cleanly; IDs are unique and well formed
- every required field is present and spelled right; `type`, `verify`, `status` and
  `stage` have allowed values
- the prefix is a subsystem in the spec tree, and the requirement is in its prefix's file
- system requirements have no parent and no allocation; subsystem requirements have at
  least one existing parent, no loops, and an allocation to a component of their own
  subsystem (or an `allocation_note`)
- interface requirements name an ICD that exists
- `verified_by` paths exist
- components: allowed `kind`, a subsystem from the spec tree, named in the spec tree,
  `deployed_on` only on software and only onto parts
- ICDs: file name matches the ID, allowed status, every end is a component or a named
  outside entity, message `from`/`to` are ends, payload examples match their schema
- every `TBD-NNN` in the requirements, architecture and ICD folders is in the register,
  and none appears without its number

Gaps: system requirements with no children; ICD sides with no interface requirement.

Warnings: topics in an ICD but not in `shared/topics.py`, and the other way round.

## Writing an ICD

Each ICD is a Markdown page with one structured ```` ```yaml ```` block (the first one
with an `id:`):

```yaml
id: ICD-001
title: Eye commands and eye status
status: stub | skeleton | draft | approved
ends:
  - {component: monster-brain}
  - {component: eye-renderer}
  - {external: owner-phone}        # outside entities: house, owner-phone, visitors, neighbors
medium: MQTT through mosquitto, over Wi-Fi
messages:
  - name: look
    topic: monster/eyes/look       # MQTT; a varying level is written {side}. Or path: for HTTP
    from: monster-brain
    to: eye-renderer
    qos: 0
    retain: false
    rate: about 10 per second
    payload_schema: {...}          # JSON Schema subset, see tools/reqs/schema.py
    examples: [...]                # each one must match payload_schema
```
