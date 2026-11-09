---
name: trade-study
description: Run a trade study for one Monster House decision - compare alternatives against owner-weighted criteria, with tagged evidence and a sensitivity check, then recommend. Use when a choice of tool, library, hardware or approach has two or more defensible options and changes what gets built (renderer, message formats, projector, requirements tooling). Output is a study in docs/trades/ and a Proposed ADR in docs/decisions/ - never production code.
---

# Trade study

**Output is a document, never production code.** Throwaway trial code is allowed,
but only under `trials/<study-slug>/`, and nothing outside that folder may import it.

## When to run one

Run one when a decision has **two or more defensible options** and the choice **changes
what gets built**, adds a dependency, costs money, or is costly to reverse.

Don't run one for naming, formatting, test layout, or anything where the project
already has a clear precedent. Make those calls yourself and mention them.

## Outputs

| File | From | Holds |
|---|---|---|
| `docs/trades/TS-NNN-<slug>.md` | `docs/templates/trade-study.md` | The evidence: question, criteria, options, scores, sensitivity, recommendation |
| `docs/decisions/NNNN-<slug>.md` | `docs/templates/adr.md` | The decision itself, in one page. It stays **Proposed** until the owner decides |

Number each in order, from the highest existing number in its folder. Studies and ADRs
are numbered separately.

## Method

There are two hard stops. At each one, update the study's status line, commit, and end
the turn.

1. **Frame the question.** Write one sentence for what's being decided. Then record what
   depends on it (requirements, other studies, stage-plan steps), the deadline, and the
   cost of reversing it later. Read `CLAUDE.md`, `docs/architecture.md`, `docs/TBD.md`
   and the code before framing. A study framed only from the request repeats work
   already done. Link the study from its row in `docs/TBD.md`, adding a row if there
   isn't one.
2. **Set the criteria.**
   - **Gates** are must-haves, checked pass/fail. An option that fails a gate is out,
     whatever its score.
   - **Weighted criteria** each get a 1–5 scale. Write down what a 1, a 3 and a 5 look
     like *before* scoring, so the scale can't drift toward a favorite.
   - Trace criteria to requirements where they exist (e.g. "SYS-012").
3. **List the options broadly, then narrow.** Start wide, including "do nothing /
   status quo" where it's meaningful. Screen out each option with a one-line reason
   (which gate it fails, or why it's dominated by another option). Shortlist at most four.
4. **🛑 Stop 1: the owner sets the weights.** Propose weights totalling 100, with a
   line of reasoning for each, and ask the owner to confirm or change them. **Score
   nothing before the weights are set.** Status: `Awaiting weights`.
5. **Gather evidence.** Every finding carries one tag:
   - **measured:** a trial or benchmark run in this study. Give the command, the
     machine and the numbers.
   - **documented:** a source. Give the link, the version, and the date it was checked.
     Check it now, not from memory.
   - **judgment:** your reasoning, stated as such.

   Prefer measured over documented, and documented over judgment. When a measurement
   isn't possible yet (e.g. no Pi), say so, and say what would measure it later.
6. **Score and check sensitivity.**
   - Score each option 1–5 on each criterion against the written scale, and cite the
     evidence row behind each score.
   - Weighted total = Σ(weight × score). The maximum is 500.
   - **Sensitivity:** for the runner-up, find the smallest change to a single weight
     that would let it tie the leader. If a change of 10 points or less flips the
     result, call it **close** and say what the owner's choice really hinges on.
   - Also note any gate that passed only narrowly.
7. **Recommend.** Give the recommended option, its main risks, what evidence would
   change the recommendation, and what reversing it would cost later.
8. **🛑 Stop 2: the owner decides.** Draft the ADR as **Proposed**, and set the study
   to `Recommended`. Commit and stop. Only the owner's decision makes the ADR
   **Accepted**. When it does, record who decided, the date and where (the chat
   session date, a commit or a PR). Then update the study's Decision section, any
   requirement allocations the decision changes, and its `docs/TBD.md` row: move it
   to Closed with a link to the ADR.
   - **Keep the TBD row's status in step with the study:** `Awaiting weights` at
     Stop 1, `Recommended` at Stop 2.

## Rules

- **Recommend; don't decide.** Choosing between options is always the owner's call.
- **The owner may decide at any point,** even before scoring. Record the decision and
  the owner's reasoning, mark the sections that weren't run as "Not run", and say
  plainly in §9 that no scores back the choice. Never fill in scores afterwards to
  justify it. Example: TS-001.
- **Find the couplings.** Say so explicitly when this decision constrains another
  (e.g. a non-Python renderer means the message schemas need a definition in a neutral
  language).
- **A rejected option, recorded with its reason, is worth as much as the winner.**
- **Never edit an Accepted ADR.** Write a new ADR that supersedes it.
- Plain Markdown with absolute dates. Mermaid diagrams are fine.

## Report back

Report where the study stopped (Stop 1 or Stop 2), the open question for the owner,
and the couplings it found.
