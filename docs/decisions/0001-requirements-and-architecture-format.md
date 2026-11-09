# 0001 — Requirements, architecture and ICDs in Markdown and YAML, SysML-ready

> **Status:** Accepted (owner, 2026-11-08, in session) · **Date:** 2026-11-08 · **Deciders:** owner · **Supersedes:** — · **Trade study:** [TS-001](../trades/TS-001-requirements-approach.md)

## Context
The owner wants traditional systems-engineering documentation:
- system *shall* requirements, decomposed into subsystem requirements allocated to
  hardware and software components;
- parent/child links;
- a type on every requirement (functional, performance, interface, constraint);
- ICDs for every interface;
- architecture pages for the hardware nodes and the software running on them.

Trade studies will keep changing the allocations. SysML v2 offers formal architecture
modeling, but its open tooling is young: a command-line validator and readable views are
unverified. Its type system and its all-or-nothing validation risk being too restrictive
for a project this size.

## Decision
We will keep requirements in YAML files, and the architecture and ICDs as Markdown
pages with structured YAML blocks. A small Python checker in the repo will validate every
link and generate a traceability matrix and Mermaid diagrams. When SysML v2 tooling and
viewing are established, we will revisit moving the architecture (not the requirements)
to SysML v2 text notation (TS-001 option D). That revisit is tracked as TBD-019.

## Consequences
- **Easier:** reviewing on GitHub or a phone; one small edit per change; no external
  tool to install or outlive.
- **Harder:** we maintain the checker ourselves. There is no standard formal semantics
  and no ReqIF export without a script.
- **Must stay true, so that the move to SysML stays cheap:**
  - **IDs are stable and never reused.** This covers requirements (`SYS-`, `BRN-`,
    `EYE-`, …), components and ICDs. Code, tests, studies and the TBD register refer to
    them by ID.
  - **Field names follow SysML concepts:** component kinds `part` (hardware node) and
    `software`; `ports`; interface `ends`; requirement links `derives_from` (parent),
    `allocated_to` (satisfied by a component), `verified_by`; and software
    `deployed_on` per stage.
  - **Structured data lives in YAML,** not only in prose: component lists, ports,
    interface ends, deployment by stage. That keeps a SysML generator scriptable.
- **The checker must flag:** broken or missing parents, unallocated child requirements,
  missing types, interface requirements without an ICD, and `TBD-NNN` references
  missing from [TBD.md](../TBD.md).

## Alternatives considered
- **StrictDoc:** real traceability tooling, but `.sdoc` doesn't read well on GitHub, and
  it doesn't model the architecture.
- **SysML v2 throughout:** the most formal, but the hardest to read, verbose to change,
  and its tools are unproven here.
- **Hybrid (SysML v2 architecture + YAML requirements):** the owner's first lean, and
  still the intended destination. Deferred until the tooling is established.
- **GUI SysML tools** (Cameo, Papyrus, Capella): fail the plain-text, free and
  editable-by-Claude must-haves.

## Links
- Trade study: [TS-001](../trades/TS-001-requirements-approach.md)
- Owner decision: session of 2026-11-08 ("start with A and look to move to SysML once
  tooling and viewing etc is established")
- Revisit: TBD-019 in [TBD.md](../TBD.md)
