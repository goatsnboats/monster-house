"""Readiness report for a design review: which entry and exit criteria hold today.

    python -m tools.reqs.check --review srr     # prints it and writes docs/reviews/srr/readiness.md

The criteria are those in docs/reviews/README.md. Only what can be checked from the files
is checked here; the rest is listed as "judged at the review". SRR is the only review
with a report so far.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from tools.reqs.checks import GATES, Finding, events_for
from tools.reqs.load import SPEC_TREE, TBD_FILE, Model

CONOPS = "docs/conops.md"
STAGE0_ICDS = ["ICD-001", "ICD-002", "ICD-003", "ICD-004", "ICD-005", "ICD-015"]

Row = Tuple[str, str, str]  # (criterion, result: pass | fail | judged, detail)


def open_tbds(model: Model) -> List[dict]:
    """The open and deferred TBDs from the register's first table, with their columns."""
    text = (model.root / TBD_FILE).read_text()
    rows, header = [], None
    for line in text.splitlines():
        if not line.startswith("|"):
            if header and rows:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "ID":
            header = [c.lower() for c in cells]
            continue
        if header and re.match(r"^TBD-\d{3}$", cells[0]) and len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return [r for r in rows if r.get("status") in ("Open", "Deferred")]


def srr(model: Model, findings: List[Finding]) -> List[Row]:
    rows: List[Row] = []
    errors = [f for f in findings if f.level == "error"]
    sys_ids = sorted(r for r in model.reqs if r.startswith("SYS-") and model.reqs[r].get("status") != "deleted")
    live = {rid: r for rid, r in model.reqs.items() if r.get("status") != "deleted"}

    def add(name: str, ok: bool, detail: str, judged: bool = False) -> None:
        rows.append((name, "judged" if judged else ("pass" if ok else "fail"), detail))

    # Entry criteria
    spec = (model.root / SPEC_TREE).read_text() if (model.root / SPEC_TREE).exists() else ""
    add("E1 Spec tree approved", "**Status:** Approved" in spec, SPEC_TREE)
    unapproved = [r for r in sys_ids if live[r].get("status") != "approved"]
    add("E2 System requirements approved", not unapproved,
        f"{len(sys_ids) - len(unapproved)} of {len(sys_ids)} approved")
    childless = [f for f in findings if f.level == "gap" and "no children" in f.message]
    add("E3 Decomposed with rationale, checker clean", not errors and not childless,
        f"{len(errors)} checker errors, {len(childless)} system requirements without children")
    conops = model.root / CONOPS
    cited = set(re.findall(r"SYS-\d{3}", conops.read_text())) if conops.exists() else set()
    add("E4 Concept of operations written, steps mapped", conops.exists(),
        f"{len(cited & set(sys_ids))} of {len(sys_ids)} system requirements cited in {CONOPS}")
    unverified = [rid for rid in live if not events_for(model, rid)]
    add("E5 Verification plan covers every requirement", bool(model.events) and not unverified,
        f"{len(model.events)} events; {len(live) - len(unverified)} of {len(live)} requirements covered")
    risk_errors = [f for f in errors if "risks.yaml" in f.where]
    add("E6 Risk register with ratings and plans", bool(model.risks) and not risk_errors,
        f"{len(model.risks)} risks, {len(risk_errors)} errors")
    tbds = open_tbds(model)
    no_gate = [t["id"] for t in tbds if t.get("status") == "Open" and t.get("gate") not in GATES]
    add("E7 Every open TBD has a method and a gate", not no_gate,
        f"{len(tbds)} open or deferred" + (f"; no gate: {', '.join(no_gate)}" if no_gate else ""))
    drafts = [i for i in STAGE0_ICDS if model.icds.get(i, {}).get("status") in ("draft", "approved")]
    add("E8 Every ICD exists; Stage 0 ICDs drafted", len(drafts) == len(STAGE0_ICDS),
        f"{len(model.icds)} ICDs; Stage 0 drafted: {len(drafts)} of {len(STAGE0_ICDS)}")
    add("E9 Readiness report in the package", True, "this report")

    # Exit criteria that can be measured now
    proposed = [rid for rid, r in live.items() if r.get("status") == "proposed"]
    add("X1 No requirement still proposed", not proposed, f"{len(proposed)} proposed")
    add("X2 Concept of operations accepted", False, "the owner's call at the review", judged=True)
    add("X3 Proposed formats and topic differences decided", False,
        "ICD-004, ICD-005, ICD-015 and the shared/topics.py warnings: the owner's call", judged=True)
    due = [t["id"] for t in tbds if t.get("gate") == "SRR" and t.get("status") == "Open"]
    add("X4 TBDs due at SRR closed", not due, f"{len(due)} due at SRR still open" + (f": {', '.join(due)}" if due else ""))
    high = [rid for rid, r in model.risks.items()
            if r.get("status") == "open" and "high" in (r.get("likelihood"), r.get("impact"))]
    unplanned = [rid for rid in high if not (model.risks[rid].get("plan") and model.risks[rid].get("retire_by"))]
    add("X5 Every high risk has a plan and a gate", not unplanned, f"{len(high)} high risks, {len(unplanned)} without")
    add("X6 Review items closed or assigned", False, "recorded at the review", judged=True)
    add("X7 Baseline tagged srr", False, "done after the review", judged=True)
    return rows


def render(review: str, rows: List[Row], tbds: List[dict]) -> str:
    mark = {"pass": "✅ pass", "fail": "❌ not yet", "judged": "⏳ at the review"}
    lines = [f"# {review.upper()} readiness (generated, do not edit)", "",
             f"> Generated by `tools/reqs/check.py --review {review}`. Criteria: "
             "[docs/reviews/README.md](../README.md). E = entry criterion, X = exit criterion.", "",
             "| Criterion | Result | Detail |", "|---|---|---|"]
    lines += [f"| {name} | {mark[result]} | {detail} |" for name, result, detail in rows]
    lines += ["", "## TBD burndown by gate", "", "| Gate | Open TBDs due |", "|---|---|"]
    for gate in GATES:
        ids = [t["id"] for t in tbds if t.get("gate") == gate and t.get("status") == "Open"]
        lines.append(f"| {gate} | {len(ids)}: {', '.join(ids) if ids else '—'} |")
    deferred = [t["id"] for t in tbds if t.get("status") == "Deferred"]
    if deferred:
        lines.append(f"| Deferred | {len(deferred)}: {', '.join(deferred)} |")
    return "\n".join(lines) + "\n"
