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
| [trace.md](trace.md) | **Generated, do not edit:** traceability matrix, coverage, budgets, diagrams |
| [pages/](pages/README.md) | **Generated, do not edit:** the requirements as readable pages, one per subsystem, a heading per requirement (for reading on a phone and commenting with gloss) |
| [timing-budgets.md](timing-budgets.md) | The end-to-end information paths, hop by hop |
| [verification-plan.md](verification-plan.md), [verification.yaml](verification.yaml) | How each requirement will be verified: events by stage, each covering requirements of its own method |
| [risk-register.md](risk-register.md), [risks.yaml](risks.yaml) | What could go wrong, rated, with the gate and the event that retires each risk |
| [../architecture/components.yaml](../architecture/components.yaml) | Every component that requirements are allocated to, with its budget figures |
| `../architecture/nodes/`, `../architecture/software/` | One page per computer or controller, and per software item |
| [../interfaces/](../interfaces/) | One ICD per interface, `ICD-NNN-<slug>.md` |
| [../TBD.md](../TBD.md) | Every open value, cited as `TBD-NNN` |

## How to run the checker

From the repository root:

```bash
.venv/bin/python -m tools.reqs.check              # check, and regenerate trace.md
.venv/bin/python -m tools.reqs.check --no-write   # check only
.venv/bin/python -m tools.reqs.check --strict     # gaps and warnings fail too
.venv/bin/python -m tools.reqs.check --impact SYS-004   # what sits below SYS-004?
.venv/bin/python -m tools.reqs.check --review srr       # SRR readiness: docs/reviews/srr/readiness.md
.venv/bin/python -m pytest tests/test_reqs_check.py      # the checker's own tests
```

Run it after every change to a requirement, a component or an ICD, and commit the
regenerated `trace.md` with the change. A test fails if `trace.md` is out of date.

The checker reports three levels:

| Level | Means | Fails the check? |
|---|---|---|
| **error** | Something is wrong: a broken link, a missing or misspelled field, a TBD-NNN that isn't in the register | Yes |
| **gap** | Something isn't done yet: a system requirement with no children, an ICD side with no interface requirement, a budget still waiting for a TBD-NNN, a performance requirement without a quantitative `basis` | Only with `--strict` |
| **warning** | The ICDs and `shared/topics.py` disagree about a topic name. The checker never changes either; a topic change is a message-format change, so ask the owner | Only with `--strict` |

## A requirement

```yaml
- id: EYE-004
  text: The eye renderer shall draw round pupils; it shall not draw slit pupils.
  type: constraint
  derives_from: [SYS-036]
  allocated_to: eye-renderer
  allocation_rationale: Pupil and lid shapes are drawn by the renderer.
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
| `allocated_to` | subsystem requirements | The component that meets it, from `components.yaml`, or a list of identical twins that each meet it (`[eye-pi-left, eye-pi-right]`). It must belong to the same subsystem as the prefix, unless `allocation_note` says why not; for an interface requirement it must be one of the ICD's ends |
| `allocation_rationale` | subsystem requirements | One line: why this component meets it (for example "a decision, and all decisions live in the brain"). Required |
| `allocation_note` | no | Why a requirement is allocated outside its own subsystem |
| `decomposition` | system requirements | One line: how it splits into its children, and why that way. Required |
| `basis` | performance requirements | The quantitative backing for how a performance requirement is decomposed or allocated: `{method: model, estimate or measurement, ref: <where the numbers are>}`. Until present it is a gap |
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
- **Every link says why.** Each system requirement has a `decomposition` line and each
  subsystem requirement an `allocation_rationale` line.
- **Performance allocations rest on numbers.** Every performance requirement, at either
  level, eventually gets a `basis`: a quantitative model (for example the budget check or
  the timing budgets), an estimate (with its source) or a measurement (owner,
  2026-11-09).
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
- system requirements have no parent and no allocation, and have a `decomposition`;
  subsystem requirements have at least one existing parent, no loops, an
  `allocation_rationale`, and an allocation to a component of their own subsystem (or an
  `allocation_note`)
- a `basis`, where given, names a method and a reference that exists
- interface requirements name an ICD that exists, and are allocated to one of its ends
- `verified_by` paths exist
- components: allowed `kind`, a subsystem from the spec tree, named in the spec tree,
  `deployed_on` only on software and only onto parts, a page for every software item
  and every computer or controller
- budgets: amounts are numbers or TBD-NNN, and no host is over budget at any stage
- ICDs: file name matches the ID, allowed status, every end is a component or a named
  outside entity, message `from`/`to` are ends, payload examples match their schema
- every `TBD-NNN` in the requirements, architecture and ICD folders is in the register,
  and none appears without its number

Gaps: system requirements with no children; ICD sides with no interface requirement;
budgets waiting for a TBD-NNN; performance requirements without a `basis`; requirements
with no verification event of their own method.

The risk register is checked too: its fields, that every high risk has a plan and a
gate, and that the events, TBDs and requirements it names exist.

The verification plan is checked too: each event's fields, that what it covers exists,
and that its method matches each covered requirement's `verify`.

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
files:                             # for file interfaces (theme folder, site config)
  - name: settings
    path: themes/{name}/settings.yaml
    payload_schema: {...}
    examples: [...]
```

## Budgets

`components.yaml` can say what a host **provides** (`{memory_mb: 1024, usb_ports: 4}`)
and what a component **needs** (`{memory_mb: 153}`). Software draws from the computer
it is `deployed_on`; a part draws from its `supplied_by`; a host's own needs (its
operating system) come from itself. `tools/reqs/budget.py` adds them up for every stage
and host. Over budget is an error; a TBD-NNN anywhere leaves that budget waiting (a
gap). Requirements that set these limits use `verify: analysis` and
`verified_by: [tools/reqs/budget.py]`. The results are in [trace.md](trace.md#budgets).
