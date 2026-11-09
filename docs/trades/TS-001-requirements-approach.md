# TS-001 — How we document requirements, architecture and interfaces

> **Status:** Decided (owner, 2026-11-08, in session; scored afterwards at the owner's request, see §5–§9; C and D partly provisional †) · **Date:** 2026-11-08 · **Decides:** the format and tooling for requirements, architecture and ICDs · **TBD:** [TBD-001](../TBD.md) (closed) · **ADR:** [0001](../decisions/0001-requirements-and-architecture-format.md) · **Affects:** every requirement and ICD written from now on; the message-format study (TBD-003); the Stage 0 plan

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

**A′ — Doorstop.** Added at the evidence step: checking showed Doorstop is maintained
(3.2, 2026-07) and stores YAML items, so it is A's requirements half with a ready-made
tool, not a dominated StrictDoc. Architecture and ICDs stay as in A.

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

The owner asked for the scored evaluation on 2026-11-08, after deciding (§9). The weights
were locked in commit `5b9a112` before any evidence was gathered. The same sample
(3 system and 7 subsystem requirements, 5 components, ICD-001) was written in every
option under [`trials/ts-001/`](../../trials/ts-001/README.md). Machine: the owner's
Ubuntu 24.04 desktop, Java 21, Python 3.12 (in a uv virtual environment).

**Not yet run: the SysML v2 validator for C and D.** The OMG pilot jar was run once,
successfully, on a toy model (E12). The auto-mode safety check then blocked further runs
of this downloaded jar, pending the owner's permission. The C and D scores that depend on
it are marked † and are provisional.

**Seeded-error test (gate G2).** Six kinds of error were planted one at a time:
(1) a parent that doesn't exist, (2) a subsystem requirement with no parent, (3) a bad
type, (4) a subsystem requirement not allocated to a component, (5) an interface
requirement with no ICD, and (6) a `TBD-NNN` that isn't in the register.

| # | Option | Criterion | Finding | Kind | Source |
|---|---|---|---|---|---|
| E1 | A | G2 | The checker (`a/check.py`, 150 lines) caught **6/6** seeded errors, with exit code 1 on any problem | measured | `trials/ts-001/a/check.py` |
| E2 | A | C2, C4 | Generates a matrix (requirement → parents, component, ICD, verification method) plus Mermaid allocation and interface diagrams as Markdown that GitHub renders; `--impact SYS-001` lists its 5 descendants with their components and ICDs | measured | `check.py --report`, `--impact` |
| E3 | A, A′, B, D | C7 | The ICD's YAML block holds a JSON-Schema payload plus examples; the checker validates the examples against the schema. The same block could drive `shared/` code or tests | measured | `a/interfaces/ICD-001.md` |
| E4 | A′ (Doorstop 3.2) | G2 | With `--error-all` it caught **2/6**: a missing parent and a requirement with no parent. Custom fields (type, allocation, ICD) and TBD references aren't checked without a plugin we'd write. It also flags any text edit as "unreviewed changes", which isn't a TBD check. `doorstop publish` produces a parent/child matrix page, with no coverage or impact report | measured | `doorstop --error-all` |
| E5 | A′ | G1, C5 | **Doorstop rewrites item files when it validates, and stages them in git itself** (it stamps a hash on each link and a `reviewed` field; one run changed all 10 items), so routine checks change files in git. One file per requirement (10 files, 139 lines for the sample, against A's 66); adding a requirement needs `doorstop add` and then an edit | measured | trial run |
| E6 | A→A′ | conversion | A's YAML was converted to Doorstop items by a 20-line script, written and run in minutes. This supports the §9 conversion-cost estimates | measured | `a2-doorstop/a_to_doorstop.py` |
| E7 | B (StrictDoc 0.30.4) | G2 | Caught **2/6**: a missing parent and a bad type (choice fields are enforced). It missed a requirement with no parent, an unallocated requirement, an interface requirement with no ICD, and an unknown TBD. Required-field checks could catch more if system and subsystem requirements were split into separate grammar elements (not tested) | measured | `strictdoc export`, one error at a time |
| E8 | B | C1, C5 | 132 lines for the sample, including a 36-line grammar header. A blank line inside a requirement is a syntax error, which bit once during the trial. GitHub shows `.sdoc` as plain text, so the readable form is StrictDoc's HTML, which needs a local server or a hosted site | measured | trial run |
| E9 | B | C2, C3 | The HTML export includes document, table, trace and deep-trace views (17 MB of output, in 1.1 s). ReqIF export works (a 43 KB `.reqif`) | measured | `strictdoc export --formats reqif-sdoc` |
| E10 | B | C6 | 212 releases; the latest is 0.30.4 (2026-10-22); pushed 2026-11-06; Apache-2.0 | documented | PyPI, GitHub API (checked 2026-11-08) |
| E11 | C, D | C6, G3 | SysML v2.0 is a formal OMG standard (adopted mid-2025, published 2025-09, editorially revised 2026-03 for ISO). Free pilot implementation (EPL-2.0) with monthly releases; the latest is 2026-09.1 (2026-10-28) | documented | [OMG](https://www.omg.org/spec/SysML), [GitHub releases](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/releases) |
| E12 | C, D | G2, G4 | The pilot's `SysMLInteractive` runs from the command line on Java 21 and validated a toy model. Gotchas: it loops forever at end of input (it needs `%exit`; one run wrote a 12 GB log), a blank line ends an input chunk, and the library path has to be absolute. `trials/ts-001/sysml_check.sh` wraps it safely | measured | trial run |
| E13 | C, D | G3 | Syside's command-line and Python validation is **paid only** (Solo and Business plans). The free Syside Editor validates only inside VS Code, and its open-source predecessor is deprecated | documented | [Syside pricing](https://sensmetry.com/syside-pricing/), [license change](https://sensmetry.com/syside-editor-rebirth-sysml-v2-0-50x-speed-up-license-change-free-as-before/) |
| E14 | C | C1, C5 | 116 lines (70 for requirements). Each requirement is a 5-line block, but its parent links sit in separate `#derivation` connections and its allocation in a separate `satisfy` line, so adding one requirement means editing 3 places. Staged deployment (the brain moves from the desktop to the porch Pi in Stage 3) can't be stated simply; in the sample it's a comment | measured / judgment | `c-sysml/monster.sysml` |
| E15 | C | G2 | Name resolution catches a missing parent or component. Nothing in SysML flags an unallocated requirement, a missing `kind`, or a TBD. That needs our own query over the pilot's JSON output † | judgment † | pilot features |
| E16 | C, D | C4 | The pilot's `%viz` renders standard views via its bundled PlantUML. Graphviz isn't installed here; not yet run † | documented † | pilot help |
| E17 | D | G2 | The glue check (`d-hybrid/glue_check.py`, which reuses A's checker) resolves `allocated_to` and ICD IDs against SysML short names (`part <'monster-brain'> brain`). It caught 6/6 plus a misspelled component and an ICD missing on either side. SysML validity of `architecture.sysml` itself not yet run † | measured † | trial run |
| E18 | D | C1, C5, C8 | The architecture is 32 lines of SysML; the requirements stay A's 66 lines of YAML. An allocation change is one YAML field; a new component is one SysML line plus a validator run | measured | `d-hybrid/` |

## 6. Scores

All gates pass for every option, but **narrowly for A′ and B on G2** (each catches only
2/6 on its own, and would need a script like A's) **and provisionally for C and D** (the
validator run on the full sample is pending).

| Criterion | W1 | W2 | W3 | A | A′ Doorstop | B StrictDoc | C SysML v2 | D Hybrid |
|---|---|---|---|---|---|---|---|---|
| C1 Readable without tools | 20 | 15 | 25 | 4 (E2) | 3 (E5) | 3 (E8) | 2 (E14) | 3 (E18) |
| C2 Trace reports | 20 | 20 | 20 | 4 (E2) | 3 (E4) | 4 (E9) | 2 (E15) | 4 (E2, E17) |
| C3 Formality | 10 | 20 | 5 | 3 (E6) | 3 | 4 (E9) | 5 (E11) | 4 (E11) |
| C4 Generated diagrams | 10 | 15 | 5 | 3 (E2) | 2 | 2 (E9) | 4 † (E16) | 4 † (E16) |
| C5 Effort per change | 15 | 10 | 20 | 5 (E2) | 3 (E5) | 4 (E8) | 3 (E14) | 4 (E18) |
| C6 Longevity | 5 | 5 | 5 | 3 (own code) | 3 (E4) | 4 (E10) | 4 (E11) | 4 (E11) |
| C7 Drives the code | 10 | 10 | 10 | 4 (E3) | 4 (E3) | 4 (E3) | 3 (judgment) | 4 (E3) |
| C8 Learning curve | 10 | 5 | 10 | 5 | 4 | 3 | 1 | 2 |
| **Total, W1 Proposed** | | | | **400** | 310 | 350 | 275 | 360 |
| **Total, W2 More formality** | | | | **375** | 300 | 350 | 315 | **375** |
| **Total, W3 Readability first** | | | | **415** | 315 | 355 | 255 | 355 |

Computed by `trials/ts-001/score.py`. The maximum is 500.

## 7. Sensitivity

- **W1:** A leads D by 40. D would need about 40 more weight on C3, C4 or C6 to tie.
  That's not close.
- **W2: A and D tie at 375.** Under formality-heavy weights, the choice really is a
  matter of taste: whether formal architecture diagrams and SysML conformance are worth
  learning SysML (C8) and losing some readability (C1).
- **W3:** A leads B and D by 60. Not close.
- **The † items cut both ways.** If the pilot validates the full sample and `%viz`
  produces usable diagrams, C and D keep their C4 = 4. If the sample won't validate
  without fighting the tool, D's G5 is in doubt and its C4 drops, which widens A's lead.
- **B is never the leader.** Its strengths (trace views, ReqIF) are offset by a G2 that
  catches only 2/6 on its own and by `.sdoc` reading poorly on GitHub.

## 8. Recommendation

**A, as already decided, with D as the planned destination.** This matches ADR 0001,
and the evidence now supports it rather than only judgment:
- A wins outright under W1 and W3 and ties under W2.
- Its checker was cheap to write (150 lines) and caught every seeded error class, which
  none of the tools did on its own.

**What would change this:**
- the pilot validating the full sample cleanly *and* the owner weighting formality as in
  W2, which makes D an equal choice now rather than later;
- A's checker growing past a few hundred lines, at which point StrictDoc's ready-made
  reports start to pay for its format.

**Risks:**
- We maintain the checker ourselves.
- The SysML-ready conventions in ADR 0001 only help if they're kept.

**Cost to reverse:** low. A→Doorstop took a 20-line script (E6), and the D glue reuses
A's checker unchanged (E17).

## 9. Decision
**A: Markdown + YAML with our own checker, with a planned move to SysML v2 for the
architecture (option D) once SysML v2 tooling and viewing are established.**
Owner, 2026-11-08, in session.

**Owner's reasoning:** start with what is readable and cheap to change. Adopt SysML's
formality when the tools make it usable rather than restrictive.

**Order of events, for the record:** the owner decided after the framing and the
discussion of conversion cost. At the owner's request, the scored evaluation (§5–§8) was
run **afterwards**, with the weights locked before any evidence was gathered. It supports
the decision: A leads under two weight sets and ties D under the third. The revisit is
tracked as TBD-019.

**To keep the later move to SysML cheap**, A is written SysML-ready (see ADR 0001,
Consequences). The trial's SysML short-name convention (`part <'monster-brain'> …`) is
the intended bridge from the YAML component IDs.

## Links
- **Results report, with screenshots:** [results/TS-001](results/TS-001/README.md)
- Trials and scoring script: [`trials/ts-001/`](../../trials/ts-001/README.md)
- Owner direction: session of 2026-11-08
- Skill: `.claude/skills/trade-study/SKILL.md`
