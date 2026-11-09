# TS-001 — How we document requirements, architecture and interfaces

> **Status:** Decided (owner, 2026-11-08, in session; scored evaluation not run, see §9) · **Date:** 2026-11-08 · **Decides:** the format and tooling for requirements, architecture and ICDs · **TBD:** [TBD-001](../TBD.md) (closed) · **ADR:** [0001](../decisions/0001-requirements-and-architecture-format.md) · **Affects:** every requirement and ICD written from now on; the message-format study (TBD-003); the Stage 0 plan

## 1. Question
In what form, and with what tooling, should we keep the system requirements, their
decomposition and allocation to hardware and software components, the architecture
(nodes, software, functions) and the interface control documents (ICDs)?

## 2. Context

**Owner direction (2026-11-08):**
- **System requirements** as traditional *shall* statements.
- **Subsystem requirements** decomposed from them and allocated to individual hardware
  and software components.
- **ICDs** for the interfaces between components.
- Every allocation recorded as a **parent/child link**.
- Each requirement has a **type**: functional, performance, interface or constraint.
  The owner added **constraint** on 2026-11-08, for limits on the design rather than
  behavior, e.g. GLES 3.0, budget, a livable bedroom, the "never scary" tone.
- TBDs are allowed in any document if each has an ID in the top-level register
  (`docs/TBD.md`), which links to the open trades and decisions (owner, 2026-11-08).
- A design folder like cairn's, describing the hardware nodes, the software running on
  them (with its functions), and the interfaces between them.
- Trade studies will change the allocation and the architecture over time.
- A standard such as **SysML** may help to document all of this formally.

**What must be captured, whichever option wins.** These fields are the information
model, and the options below are different ways of storing it:

| Item | Fields |
|---|---|
| Requirement | ID (`SYS-001`, `EYE-014`…), *shall* text, type (F / P / I / C), parent ID(s), allocated to (component), verification method (inspection / analysis / demonstration / test), rationale, source (architecture § or owner), stage needed by, status |
| Component | ID, kind (hardware node / software / external), runs on (for software; this changes by stage, e.g. the brain runs on the desktop in Stages 0–2 and the porch Pi from Stage 3), functions |
| Interface | ICD ID, the two ends, medium (Wi-Fi MQTT, DDP, HTTP, analog audio, power, mechanical), messages and payloads, timing, failure behavior |
| Trace | requirement → parent, requirement → component, interface requirement → ICD, requirement → test, trade study → the requirements it changes, `TBD-NNN` → the register |

**What depends on it:**
- Every requirement and ICD from now on.
- The message-format study. If the ICDs hold machine-readable payload definitions,
  `shared/` can be generated from them or tested against them.
- The renderer study, whose criteria should trace to the eye requirements.

**Deadline:** before the system requirements are written. Stage 0 Step 1's
infrastructure work doesn't need to wait.

**Cost to reverse:** lowest now, while nothing is written. It grows with each
requirement. Converting between plain-text formats can be scripted; converting out of a
modeling language takes more work.

## 3. Criteria

### Gates (must pass)
| ID | Gate | How checked |
|---|---|---|
| G1 | The source of truth is plain text in git and can be reviewed as a diff | Inspect the files it produces |
| G2 | A tool or script automatically flags broken parent/child links, orphaned or unallocated requirements, missing types, and `TBD-NNN` references missing from the register | Run it on a seeded broken example |
| G3 | No paid license | Documented licensing |
| G4 | Runs on the Ubuntu 24.04 desktop | Install it and run it |
| G5 | Claude Code can write and edit the source directly; no editing only through a graphical tool | Author a sample requirement, component and interface |

### Weighted criteria
The weights in this table are weight set **W1**. The owner asked for the options to be
scored under all three sets below, locked on 2026-11-08 before any evidence was
gathered.

| Set | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---|---|---|---|---|---|---|---|---|
| **W1 Proposed** | 20 | 20 | 10 | 10 | 15 | 5 | 10 | 10 |
| **W2 More formality** | 15 | 20 | 20 | 15 | 10 | 5 | 10 | 5 |
| **W3 Readability first** | 25 | 20 | 5 | 5 | 20 | 5 | 10 | 10 |

| ID | Criterion | W1 weight | How measured | 1 = | 3 = | 5 = |
|---|---|---|---|---|---|---|
| C1 | Readable by the owner without tools (GitHub web, phone) | 20 | View the sample on GitHub | Unreadable without the tool | Readable but cluttered by syntax | Reads like a normal document |
| C2 | Traceability reports: matrix, coverage, impact of a change | 20 | Generate them from the sample | Link checks only | Matrix or coverage, not both | Matrix, coverage and "what does changing X touch" |
| C3 | Formality and alignment with standards (SysML semantics, ReqIF export) | 10 | Documented features | Ad-hoc format | Borrows SysML terms; exportable with a script | Native SysML v2 or standard ReqIF |
| C4 | Architecture and interface diagrams generated from the source | 10 | Generate one from the sample | Drawn by hand | Generated with our own glue | Generated by the tool |
| C5 | Effort per change, e.g. adding a requirement and allocating it | 15 | Time and lines for one change on the sample | Several files and a tool run | One or two files | One small edit |
| C6 | Longevity: maintenance activity and bus factor | 5 | Release history and contributors, checked on the day | Stale or single-maintainer | Active, small team | Active, standard-backed or widely used |
| C7 | Fit with the code: ICD payloads can drive or check the `shared/` schemas | 10 | Prototype one ICD to a test | No route | Possible with a custom script | Natural, machine-readable payload definitions |
| C8 | Learning curve for the owner | 10 | Judgment, after the sample | New language and tool | New file conventions | Plain Markdown and YAML |

**Why these weights:** You read these documents more than anyone else, and the point of
the exercise is traceability, so C1 and C2 carry the most. C5 matters because trade
studies will keep changing allocations, and costly changes get skipped. C3 is
deliberately moderate: formality only helps if it's used. **Raise C3 if you value SysML
conformance for its own sake**, e.g. for practice or to keep the option of a SysML tool
later.

## 4. Options

### Screened out
| Option | Reason |
|---|---|
| Cameo / MagicDraw (SysML v1 GUI tools) | Fails G3: paid license. Also G1 and G5: binary or XMI model files, edited through a GUI |
| Eclipse Papyrus (SysML 1.6) | Fails G1 and G5: an XMI model edited through a GUI, which doesn't diff well |
| Capella (Arcadia method) | Fails G5, and G1 in practice: a GUI-first XML model. It also uses Arcadia rather than SysML |
| Doorstop | Dominated by StrictDoc: a similar one-file-per-item model, with fewer reports and no ReqIF *(judgment, to verify)* |
| sphinx-needs | Needs a Sphinx and reStructuredText documentation build, and overlaps StrictDoc's niche with more setup *(judgment; the owner can pull it back in)* |
| Spreadsheet / CSV | Weak for long text and ICDs; links can only be checked by a custom script, which is option A with worse ergonomics |
| Commercial requirements tools (DOORS, Jama) | Fails G3 |

### Shortlist

**A — Markdown + YAML, with a small checker of our own.** Requirements live in YAML files
(one per subsystem) using the fields in §2. Architecture pages and ICDs are Markdown,
with ICD payloads as YAML or JSON Schema blocks. A Python script of about 200 lines
checks the links and generates a traceability matrix and Mermaid diagrams. It uses SysML
*vocabulary* (block, port, allocate, satisfy, verify) but none of its tooling.

**B — StrictDoc.** An open-source, text-based requirements tool (`.sdoc` files) with
parent/child links, custom fields, traceability and coverage reports, an HTML export, and
ReqIF import and export. Architecture pages and ICDs stay Markdown, linked by ID.

**C — SysML v2 textual notation, end to end.** `.sysml` files for requirements
(`requirement def`, `satisfy`), structure (`part def`, `port def`, `interface def`) and
allocation (`allocate`). It's validated and visualized with open tooling (the SysML v2
pilot implementation, or the Syside editor), plus generated Markdown views for reading.

**D — Hybrid.** SysML v2 textual for the architecture (parts, ports, interfaces and the
deployment of software onto hardware), with requirements in A's YAML (or StrictDoc).
Requirements link to SysML elements by name.

**To verify during the evidence step** (not from memory): StrictDoc's current release and
ReqIF support; the status of the SysML v2 open tooling (pilot implementation releases,
Syside's license, whether a validator runs from the command line); and the status of the
OMG SysML v2 specification.

## 5. Evidence
*Not run.* The owner decided after framing (§9). The planned sample (three system
requirements, six subsystem requirements, two components, and an ICD for
`monster/eyes/look`) becomes the first content written in option A instead.

**Conversion cost, discussed 2026-11-08 (judgment):** with stable IDs, YAML ↔ StrictDoc
is under one scripted session. YAML requirements → SysML v2 is about one scripted
session. Markdown architecture → SysML v2 is one or two sessions by hand for a system
this size (about 15 components and 8 interfaces). The lasting cost of a format change is
the references to the files, not the files themselves, so stable IDs are what keep this
reversible.

## 6. Scores
*Not run.*

## 7. Sensitivity
*Not run.*

## 8. Recommendation
*Not made.* Before the owner's decision, the discussion covered:
- the four options;
- the concern that SysML v2 would be **too restrictive**: everything must fit its type
  system, one syntax error breaks validation, and staged deployment is fiddly to model;
- the **unverified state of the open SysML v2 tooling** (a command-line validator and
  readable views).

D was the owner's first lean.

## 9. Decision
**A: Markdown + YAML with our own checker, with a planned move to SysML v2 for the
architecture (option D) once SysML v2 tooling and viewing are established.**
Owner, 2026-11-08, in session.

**Owner's reasoning:** start with what is readable and cheap to change. Adopt SysML's
formality when the tools make it usable rather than restrictive.

**Weighted scoring was not run.** The owner chose on judgment after the framing and the
discussion of conversion cost. B (StrictDoc) and C (SysML v2 throughout) were set aside
on that basis, not on scores. The revisit is tracked as TBD-019.

**To keep the later move to SysML cheap**, A is written SysML-ready (see ADR 0001,
Consequences).

## Links
- Owner direction: session of 2026-11-08
- Skill: `.claude/skills/trade-study/SKILL.md`
