"""TS-001 option A trial: check requirement links and write trace reports.

Usage:
    python check.py ROOT --tbd TBD.md            # check only; exit 1 on any problem
    python check.py ROOT --tbd TBD.md --report OUT   # also write OUT/trace.md
    python check.py ROOT --impact SYS-001         # what does changing SYS-001 touch?

ROOT holds requirements/*.yaml, architecture/components.yaml and interfaces/ICD-*.md.
Trial code only (trials/ts-001); not imported by anything.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

TYPES = {"functional", "performance", "interface", "constraint"}
VERIFY = {"inspection", "analysis", "demonstration", "test"}
TBD_REF = re.compile(r"TBD-\d{3}")


def load(root: Path) -> tuple[dict, dict, dict]:
    reqs: dict[str, dict] = {}
    for f in sorted((root / "requirements").glob("*.yaml")):
        for r in yaml.safe_load(f.read_text()) or []:
            r["_file"] = f.name
            reqs[r["id"]] = r
    comps = {c["id"]: c for c in yaml.safe_load((root / "architecture/components.yaml").read_text())}
    icds = {}
    for f in sorted((root / "interfaces").glob("ICD-*.md")):
        block = re.search(r"```yaml\n(.*?)```", f.read_text(), re.S)
        icd = yaml.safe_load(block.group(1)) if block else {"id": f.stem}
        icd["_text"] = f.read_text()
        icds[icd["id"]] = icd
    return reqs, comps, icds


def check(root: Path, reqs: dict, comps: dict, icds: dict, tbd_file: Path | None) -> list[str]:
    errors = []
    for rid, r in reqs.items():
        where = f"{r['_file']}: {rid}"
        if r.get("type") not in TYPES:
            errors.append(f"{where}: type must be one of {sorted(TYPES)}")
        if r.get("verify") not in VERIFY:
            errors.append(f"{where}: verify must be one of {sorted(VERIFY)}")
        is_system = rid.startswith("SYS-")
        parents = r.get("derives_from", [])
        if not is_system and not parents:
            errors.append(f"{where}: subsystem requirement has no derives_from (orphan)")
        for p in parents:
            if p not in reqs:
                errors.append(f"{where}: parent {p} does not exist")
        if not is_system:
            comp = r.get("allocated_to")
            if not comp:
                errors.append(f"{where}: not allocated to a component")
            elif comp not in comps:
                errors.append(f"{where}: allocated to unknown component {comp}")
        if r.get("type") == "interface":
            if r.get("icd") not in icds:
                errors.append(f"{where}: interface requirement needs an existing icd (got {r.get('icd')})")
    for sid in (i for i in reqs if i.startswith("SYS-")):
        if not any(sid in r.get("derives_from", []) for r in reqs.values()):
            errors.append(f"{sid}: system requirement has no children (not decomposed)")
    for iid, icd in icds.items():
        for end in icd.get("ends", {}).values():
            if end.split(".")[0] not in comps:
                errors.append(f"{iid}: end {end} is not a known component")
        for msg in icd.get("messages", []):
            for ex in msg.get("examples", []):
                if not matches(ex, msg.get("payload_schema", {})):
                    errors.append(f"{iid}: example {ex} does not match {msg['topic']} schema")
    if tbd_file:
        known = set(TBD_REF.findall(tbd_file.read_text()))
        for f in root.rglob("*"):
            if f.suffix in {".yaml", ".md"}:
                for ref in set(TBD_REF.findall(f.read_text())) - known:
                    errors.append(f"{f.relative_to(root)}: {ref} is not in the TBD register")
    return errors


def matches(value, schema: dict) -> bool:
    """A tiny JSON-Schema subset (oneOf, type, required, properties, enum), enough for the trial."""
    if "oneOf" in schema:
        return sum(matches(value, s) for s in schema["oneOf"]) == 1
    if "enum" in schema and value not in schema["enum"]:
        return False
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict) or any(k not in value for k in schema.get("required", [])):
            return False
        return all(matches(value[k], s) for k, s in schema.get("properties", {}).items() if k in value)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def impact(rid: str, reqs: dict, icds: dict) -> list[str]:
    """Everything below a requirement: its descendants, their components and ICDs."""
    out, todo = [], [rid]
    while todo:
        cur = todo.pop()
        for child, r in reqs.items():
            if cur in r.get("derives_from", []):
                extra = f" → {r.get('allocated_to')}" + (f", {r['icd']}" if r.get("icd") else "")
                out.append(f"{child} (child of {cur}){extra}")
                todo.append(child)
    return out


def report(reqs: dict, comps: dict, icds: dict) -> str:
    lines = ["# Traceability (generated — do not edit)", "",
             "| Requirement | Type | Parents | Allocated to | ICD | Verify |", "|---|---|---|---|---|---|"]
    for rid, r in reqs.items():
        lines.append(f"| {rid} | {r['type']} | {', '.join(r.get('derives_from', [])) or '—'} | "
                     f"{r.get('allocated_to', '—')} | {r.get('icd', '—')} | {r['verify']} |")
    lines += ["", "## Allocation", "", "```mermaid", "flowchart LR"]
    for rid, r in reqs.items():
        for p in r.get("derives_from", []):
            lines.append(f"  {p.replace('-', '_')}[{p}] --> {rid.replace('-', '_')}[{rid}]")
        if r.get("allocated_to"):
            lines.append(f"  {rid.replace('-', '_')} -.-> {r['allocated_to'].replace('-', '_')}([{r['allocated_to']}])")
    lines += ["```", "", "## Interfaces", "", "```mermaid", "flowchart LR"]
    for iid, icd in icds.items():
        a, b = (e.split(".")[0] for e in icd["ends"].values())
        lines.append(f"  {a.replace('-', '_')}([{a}]) -- \"{iid}\" --> {b.replace('-', '_')}([{b}])")
    lines += ["```", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--tbd", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--impact")
    a = ap.parse_args()
    reqs, comps, icds = load(a.root)
    if a.impact:
        print("\n".join(impact(a.impact, reqs, icds)) or "(nothing below it)")
        return 0
    errors = check(a.root, reqs, comps, icds, a.tbd)
    for e in errors:
        print("ERROR", e)
    if a.report:
        a.report.mkdir(parents=True, exist_ok=True)
        (a.report / "trace.md").write_text(report(reqs, comps, icds))
    print(f"{len(reqs)} requirements, {len(comps)} components, {len(icds)} ICDs: "
          f"{'FAIL, ' + str(len(errors)) + ' problems' if errors else 'OK'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
