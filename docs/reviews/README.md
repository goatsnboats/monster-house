# Design reviews: SRR, PDR and CDRs

> **Status:** Plan, agreed with the owner 2026-11-09 · **Updated:** 2026-11-09

The monster is reviewed at gates, alongside the prototyping rather than instead of it. The
prototype is the evidence: simulator measurements become the `basis` of performance
requirements, and tests named in `verified_by` show requirements being met.

## How the reviews work here

- **The owner is the review board** and makes every go/no-go call. Claude prepares the
  package and runs the checks.
- **A review is a package plus a session.** The package lives in `docs/reviews/<review>/`
  (for example `docs/reviews/srr/`). It holds what was reviewed, the readiness report, the
  decisions, and the review items.
- **Review items** (`RI-<review>-NN`, for example `RI-SRR-03`) are the findings: each has
  an owner, a due gate and a status. Closed items stay, as history.
- **Readiness is checked by the tools where possible.** `tools/reqs/check.py` will gain a
  `--review <name>` mode that prints the entry criteria below as pass, fail or accepted gap
  (to be built while preparing SRR).
- **After a review, its baseline is frozen** with a git tag (`srr`, `pdr`, `cdr-1`, ...).
  Later changes to frozen items need a short change note and the owner's OK.

## Schedule

| Review | Question | When | Gates |
|---|---|---|---|
| **SRR** System Requirements Review | Are we building the right thing, and are the requirements complete and checkable? | December 2026, during Stage 0 Steps 2-4 | Freezing the requirements baseline |
| **PDR** Preliminary Design Review | Will this design meet the requirements, backed by trades, budgets and prototype evidence? | Late January 2027, once Stage 0 Steps 2-6 run | The detailed design of every stage, starting with the eye pod |
| **CDR-1** Eyes | Is the eye pod ready to buy and build? | Stage 0 exit, late February 2027 | Stage 1 purchase (Pis, projectors) |
| **CDR-2** Ears | Is the radar ready? | Late April 2027 | Stage 2 purchase |
| **CDR-3** Voice | Are the porch Pi, FPP and sound ready? | Late May 2027 | Stage 3 purchase |
| **CDR-4** Mouth | Are the lips ready? | Late July 2027 | Stage 4 purchase |
| **CDR-5** Extras | Are fog and rumble ready? | Late August 2027 | Stage 5 purchase |

PDR comes a month before CDR-1 so that its findings can still change the eye pod before
anything is bought (owner chose this, 2026-11-09). One system PDR covers the whole design
at a preliminary level, Voice and Mouth included; each stage's detail is reviewed once, at
its CDR, which also reviews what changed since PDR. The stage months are architecture
§11's.

**Considered and not chosen** (owner, 2026-11-09): PDR held together with CDR-1, and a
PDR per stage before each CDR.

## SRR package, in this order (owner, 2026-11-09)

1. **Concept of operations** (`docs/conops.md`): a Halloween night from setup to teardown,
   what visitors see and hear, and what the owner does on the phone.
2. **Requirements review:** the owner reviews the 118 proposed subsystem requirements,
   with the ConOps to hand.
3. **Verification plan:** for each requirement, the stage and the test, demonstration,
   inspection or analysis that verifies it.
4. **Risk register:** the risks now scattered through `architecture.md`, with likelihood,
   impact and how each is retired.

## SRR — System Requirements Review

**Entry criteria**
1. The spec tree is approved. *(Done 2026-11-09.)*
2. All system requirements are approved. *(Done 2026-11-09.)*
3. Every subsystem requirement exists with a parent, an allocation, an
   `allocation_rationale`, and every system requirement has a `decomposition`; the checker
   reports 0 errors. *(Done 2026-11-09.)*
4. The concept of operations is written, and every step in it maps to system
   requirements.
5. The verification plan gives every requirement a stage and a planned verification event.
6. The risk register exists, with likelihood, impact and a retirement plan for each risk.
7. Every open TBD has a resolution method and a need-by gate (SRR, PDR or a CDR).
8. Every ICD on the N² chart exists; the Stage 0 ICDs are drafted in full. *(Done.)*
9. The readiness report (`check.py --review srr`) is in the package.

**Exit criteria**
1. No requirement is still `proposed`: each is approved, rewritten or deleted.
2. The ConOps is accepted; every ConOps step is covered by requirements, and every
   requirement traces to a ConOps step or a stated constraint.
3. The proposed formats (ICD-004, ICD-005, ICD-015) and the topic differences with
   `shared/topics.py` are decided by the owner.
4. Every TBD needed by SRR is closed; the rest are scheduled to a later gate.
5. Every high risk has a retirement plan and a gate by which it must be retired.
6. Every review item is closed or assigned to a later gate.
7. The requirements baseline is tagged `srr`.

## PDR — Preliminary Design Review (system, late January 2027)

**Entry criteria**
1. SRR's review items are closed or deferred with the owner's OK.
2. The Stage 0 prototype runs end to end on the desktop (eyes, brain, fake radar, fake
   FPP, house preview, phone page: Steps 2-6), and the rest of Stage 0 is on track.
3. The trade studies that PDR depends on are decided with ADRs: message schemas
   (TBD-003) and projector (TBD-012); the eye layout (TBD-004) is decided.
4. Every ICD is at least a draft; ICDs 001-005 and 015 are implemented in code and tested.
5. The budgets for Stage 1 hosts are complete: no TBDs, nothing over.
6. The latency model exists, and the timing requirements on paths P1, P2 and P4 have a
   `basis` from an estimate or a simulator measurement.
7. The Stage 0 requirements are verified in the simulator, with `verified_by` filled in.
8. The risk register is updated, with the Stage 1 risks' retirement tests planned.

**Exit criteria**
1. The design is shown to meet every system requirement at a preliminary level: each
   performance requirement has a `basis`, or an accepted plan to get one by its CDR.
2. No budget is over.
3. ICDs 001-005, 013 and 015 are approved.
4. `check.py --strict` passes, apart from a listed set of gaps the owner accepts.
5. The design baseline is tagged `pdr`.

## CDR-n — Critical Design Review, one per hardware stage

**Entry criteria (every CDR)**
1. The previous review's items are closed or deferred with the owner's OK.
2. Every requirement for stage *n* is approved and has a written verification procedure.
3. Every ICD used in stage *n* is approved (none left as a skeleton).
4. Every TBD needed by stage *n* is closed (the measurements and tests are done).
5. The stage *n* budgets are complete: no TBDs, nothing over.
6. Every stage *n* performance requirement has a `basis`.
7. A parts list with costs, compared with architecture §11's estimate for the stage.
8. Install, setup and teardown checklists for stage *n* are drafted.
9. The stage *n* risks are retired, or their mitigation is in place.
10. A "design delta since PDR" section: what changed in stage *n*'s design since PDR,
    and why (for Voice and Mouth, which are thinnest at PDR, this is most of the review).

**Exit criteria (every CDR)**
1. The owner gives go or no-go for the purchase and the build.
2. The stage *n* design is tagged `cdr-n` and frozen; later changes need a change note.
3. The verification procedures are ready to run once it's built.

**What each CDR focuses on**

| CDR | Subsystems | TBDs to close | ICDs to approve |
|---|---|---|---|
| CDR-1 Eyes | EYE, INF (eye Pis, power, network) | TBD-005, 006, 009, 012, 013, 014, 017, 025, 032 | ICD-008, 009, 011, 013, 014 |
| CDR-2 Ears | EAR, INF (porch mounting) | TBD-008, 016, 018, 029, 030 | ICD-002 (real radar), 010 |
| CDR-3 Voice | SHW (FPP, porch Pi), VOC, INF | TBD-010, 015, 022, 024, 026, 031, 036 | ICD-003 (real FPP), 007, 012 |
| CDR-4 Mouth | MTH | TBD-007, 027, 033, 035 | ICD-006 |
| CDR-5 Extras | VOC (rumble), fog (not yet in the tree) | Fog design | — |
