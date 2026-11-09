"""The checks. Each returns a list of Findings; check_all() runs them all.

Three levels:
  error    something is wrong (a broken link, a bad field). The checker fails.
  gap      something is not done yet (a system requirement with no children, an
           ICD end with no interface requirement). Expected while the baseline is
           being built; fails only with --strict.
  warning  a mismatch the checker may not fix itself (ICD topics vs
           shared/topics.py). Fails only with --strict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tools.reqs import schema, shared_topics
from tools.reqs import budget
from tools.reqs.load import ARCH_DIR, COMPONENTS, ICD_DIR, REQ_DIR, SPEC_TREE, TOPICS_FILE, Model

TYPES = {"functional", "performance", "interface", "constraint"}
VERIFY = {"inspection", "analysis", "demonstration", "test"}
STATUSES = {"proposed", "approved", "deleted"}
STAGES = range(0, 6)
REQ_FIELDS_REQUIRED = ["id", "text", "type", "verify", "source", "stage", "status"]
REQ_FIELDS_KNOWN = set(REQ_FIELDS_REQUIRED) | {
    "derives_from", "allocated_to", "allocation_note", "icd", "verified_by", "rationale", "notes", "_file",
}
COMP_KINDS = {"part", "software"}
COMP_FIELDS_KNOWN = {
    "id", "kind", "subsystem", "name", "stage", "location", "functions", "ports", "deployed_on", "notes",
    "needs", "provides", "supplied_by",
}
ICD_STATUSES = {"stub", "skeleton", "draft", "approved"}

REQ_ID = re.compile(r"^([A-Z]{3})-(\d{3})$")
ICD_ID = re.compile(r"^ICD-\d{3}$")
COMP_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TBD_REF = re.compile(r"TBD-\d{3}")
# "TBD" on its own: not "TBD-019", the file name "TBD.md" or the phrase "TBD register".
BARE_TBD = re.compile(r"\bTBD\b(?![-.]\w| register)")

# Files whose TBD references are checked (TBD.md itself is the register).
TBD_CHECKED_DIRS = [REQ_DIR, ARCH_DIR, ICD_DIR]


@dataclass(frozen=True)
class Finding:
    level: str   # "error" | "gap" | "warning"
    where: str   # file or ID
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.where}: {self.message}"


def check_all(model: Model) -> list[Finding]:
    findings = [Finding("error", where, msg) for where, msg in model.load_errors]
    findings += check_requirements(model)
    findings += check_components(model)
    findings += check_icds(model)
    findings += check_tbds(model)
    findings += check_coverage(model)
    findings += check_topics(model)
    findings += [Finding(level, where, msg) for level, where, msg in budget.findings(model)]
    return findings


# ── Requirements ────────────────────────────────────────────────────────────────

def expected_file(prefix: str) -> str:
    """system.yaml for SYS, otherwise the prefix in lower case: EYE -> eye.yaml."""
    return "system.yaml" if prefix == "SYS" else f"{prefix.lower()}.yaml"


def check_requirements(model: Model) -> list[Finding]:
    out = []
    for rid, r in model.reqs.items():
        def err(msg: str) -> None:
            out.append(Finding("error", f"{r['_file']}: {rid}", msg))

        match = REQ_ID.match(rid)
        if not match:
            err("ID must look like ABC-123 (three capitals, dash, three digits)")
            continue
        prefix = match.group(1)
        for name in REQ_FIELDS_REQUIRED:
            if r.get(name) in (None, ""):
                err(f"missing field {name!r}")
        for name in sorted(set(r) - REQ_FIELDS_KNOWN):
            err(f"unknown field {name!r} (see docs/requirements/README.md)")
        if "type" in r and r["type"] not in TYPES:
            err(f"type must be one of {sorted(TYPES)}, not {r['type']!r}")
        if "verify" in r and r["verify"] not in VERIFY:
            err(f"verify must be one of {sorted(VERIFY)}, not {r['verify']!r}")
        if "status" in r and r["status"] not in STATUSES:
            err(f"status must be one of {sorted(STATUSES)}, not {r['status']!r}")
        if "stage" in r and r["stage"] not in STAGES:
            err(f"stage must be a whole number 0-5, not {r['stage']!r}")

        # Prefix and file
        if prefix not in model.prefixes:
            err(f"prefix {prefix} is not a subsystem in the spec tree")
        elif r["_file"] != expected_file(prefix):
            err(f"belongs in {expected_file(prefix)}, not {r['_file']}")

        # Parents and allocation
        parents = r.get("derives_from") or []
        if not isinstance(parents, list):
            err("derives_from must be a list, e.g. [SYS-001]")
            parents = []
        if prefix == "SYS":
            if parents:
                err("a system requirement has no parent (remove derives_from)")
            if r.get("allocated_to"):
                err("system requirements are allocated through their children (remove allocated_to)")
        else:
            if not parents:
                err("no derives_from: every subsystem requirement needs a parent (orphan)")
            for p in parents:
                if p == rid:
                    err("derives from itself")
                elif p not in model.reqs:
                    err(f"parent {p} does not exist")
            out += _check_allocation(model, rid, r, prefix)

        # Interfaces
        if r.get("type") == "interface":
            icd = r.get("icd")
            if not icd:
                err("interface requirement has no icd")
            elif icd not in model.icds:
                err(f"icd {icd} does not exist in {ICD_DIR}/")
            else:
                ends = set(icd_end_names(model.icds[icd]))
                for comp in allocations(r):
                    if comp not in ends:
                        err(f"allocated to {comp}, which is not one of {icd}'s ends")
        elif r.get("icd") and r["icd"] not in model.icds:
            err(f"icd {r['icd']} does not exist in {ICD_DIR}/")

        # Verification links: anything that looks like a path must exist.
        for ref in r.get("verified_by") or []:
            path = str(ref).split("::")[0].split(" ")[0]
            if "/" in path and not (model.root / path).exists():
                err(f"verified_by {ref!r}: {path} does not exist")

    out += _check_cycles(model)
    return out


def allocations(r: dict) -> list[str]:
    """allocated_to as a list. It is one component, or a list of identical twins
    (e.g. [eye-pi-left, eye-pi-right]) that each meet the requirement."""
    value = r.get("allocated_to")
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _check_allocation(model: Model, rid: str, r: dict, prefix: str) -> list[Finding]:
    where = f"{r['_file']}: {rid}"
    if not allocations(r):
        return [Finding("error", where, "not allocated to a component (allocated_to)")]
    out = []
    for comp_id in allocations(r):
        comp = model.comps.get(comp_id)
        if comp is None:
            out.append(Finding("error", where, f"allocated to {comp_id}, which is not in {COMPONENTS}"))
        elif comp.get("subsystem") != prefix and not r.get("allocation_note"):
            out.append(Finding("error", where,
                               f"allocated to {comp_id}, which belongs to {comp.get('subsystem')}, not {prefix}; "
                               "allocate within the subsystem or explain why in allocation_note"))
    return out


def _check_cycles(model: Model) -> list[Finding]:
    out = []
    for start in model.reqs:
        seen, todo = set(), list(model.reqs[start].get("derives_from") or [])
        while todo:
            cur = todo.pop()
            if cur == start:
                out.append(Finding("error", start, "is its own ancestor (derives_from loop)"))
                break
            if cur in seen or cur not in model.reqs:
                continue
            seen.add(cur)
            todo += model.reqs[cur].get("derives_from") or []
    return out


# ── Components ──────────────────────────────────────────────────────────────────

def check_components(model: Model) -> list[Finding]:
    out = []
    mentioned = set(re.findall(r"`([a-z0-9-]+)`", model.spec_tree_text))
    for cid, c in model.comps.items():
        def err(msg: str) -> None:
            out.append(Finding("error", f"{COMPONENTS}: {cid}", msg))

        if not COMP_ID.match(cid):
            err("ID must be lower-case words joined by dashes")
        for name in ["kind", "subsystem", "name", "stage"]:
            if c.get(name) in (None, ""):
                err(f"missing field {name!r}")
        for name in sorted(set(c) - COMP_FIELDS_KNOWN):
            err(f"unknown field {name!r}")
        if c.get("kind") not in COMP_KINDS:
            err(f"kind must be one of {sorted(COMP_KINDS)}, not {c.get('kind')!r}")
        if c.get("subsystem") not in model.prefixes or c.get("subsystem") == "SYS":
            err(f"subsystem {c.get('subsystem')!r} is not a subsystem in the spec tree")
        if c.get("stage") not in STAGES:
            err(f"stage must be a whole number 0-5, not {c.get('stage')!r}")
        if cid not in mentioned:
            err(f"not named in {SPEC_TREE} (add it to its subsystem's table)")

        page = component_page(model, cid)
        if page is not None and not (model.root / page).exists():
            err(f"needs a page: {page}")

        deployed = c.get("deployed_on")
        if c.get("kind") == "part" and deployed:
            err("a part isn't deployed on anything (deployed_on is for software)")
        if c.get("kind") == "software" and deployed:
            if not isinstance(deployed, dict):
                err("deployed_on must map a stage to a part, e.g. {0: desktop, 3: porch-pi}")
                continue
            for stage, hosts in deployed.items():
                if stage not in STAGES:
                    err(f"deployed_on stage {stage!r} must be 0-5")
                for host in hosts if isinstance(hosts, list) else [hosts]:
                    if model.comps.get(host, {}).get("kind") != "part":
                        err(f"deployed_on {host!r} (stage {stage}) is not a part in {COMPONENTS}")
    return out


def hosts(model: Model) -> set[str]:
    """Parts that some software runs on: the hardware nodes."""
    found = set()
    for c in model.comps.values():
        for stage_hosts in (c.get("deployed_on") or {}).values():
            found.update(stage_hosts if isinstance(stage_hosts, list) else [stage_hosts])
    return found


def component_page(model: Model, cid: str) -> str | None:
    """The page a component must have: every software item and every hardware node."""
    c = model.comps[cid]
    if c.get("kind") == "software":
        return f"{ARCH_DIR}/software/{cid}.md"
    if cid in hosts(model):
        return f"{ARCH_DIR}/nodes/{cid}.md"
    return None


# ── ICDs ────────────────────────────────────────────────────────────────────────

def icd_end_names(icd: dict) -> list[str]:
    """The component IDs and external names at an ICD's ends."""
    names = []
    for end in icd.get("ends") or []:
        if isinstance(end, dict):
            names.append(end.get("component") or end.get("external"))
    return names


def icd_sides(model: Model, icd: dict) -> dict[str, set[str]]:
    """The sides of an ICD that each need an interface requirement.

    A side is a subsystem at the ICD's ends: {"SHW": {"monster-brain"}, "EYE": {...}}.
    If every end is a component of the same subsystem (an internal ICD such as
    brain <-> FPP), each component is its own side. External ends (the owner's phone,
    the house) and subsystems marked "requirements: none" in the spec tree have no
    requirements of their own and are left out.
    """
    names = icd_end_names(icd)
    comps = [n for n in names if n in model.comps]
    by_subsystem: dict[str, set[str]] = {}
    for c in comps:
        by_subsystem.setdefault(model.comps[c]["subsystem"], set()).add(c)
    if len(by_subsystem) == 1 and len(comps) == len(names):
        return {c: {c} for c in comps}
    # Subsystems the spec tree marks "requirements: none" (DEV) can't hold one.
    return {s: cs for s, cs in by_subsystem.items() if model.prefixes.get(s, {}).get("requirements") != "none"}


def check_icds(model: Model) -> list[Finding]:
    out = []
    for iid, icd in model.icds.items():
        where = f"{icd['_file']}"

        def err(msg: str) -> None:
            out.append(Finding("error", where, msg))

        if not ICD_ID.match(iid):
            err(f"id {iid!r} must look like ICD-001")
        if not icd["_file"].startswith(f"{iid}-"):
            err(f"file name must start with {iid}-")
        if icd.get("status") not in ICD_STATUSES:
            err(f"status must be one of {sorted(ICD_STATUSES)}, not {icd.get('status')!r}")
        if not icd.get("title"):
            err("missing title")
        ends = icd.get("ends") or []
        if len(ends) < 2:
            err("needs at least two ends")
        for end in ends:
            if not isinstance(end, dict) or not (end.get("component") or end.get("external")):
                err(f"end {end!r} must be {{component: <id>}} or {{external: <name>}}")
            elif end.get("component") and end["component"] not in model.comps:
                err(f"end {end['component']} is not in {COMPONENTS}")
            elif end.get("external") and end["external"] not in model.externals:
                err(f"external end {end['external']} is not in the spec tree's externals")
        names = set(icd_end_names(icd))
        for i, msg in enumerate((icd.get("messages") or []) + (icd.get("files") or [])):
            label = msg.get("name") or msg.get("topic") or msg.get("path") or f"item {i + 1}"
            for side in ("from", "to"):
                for name in _as_list(msg.get(side)):
                    if name not in names:
                        err(f"{label}: {side} {name!r} is not one of this ICD's ends")
            payload_schema = msg.get("payload_schema")
            examples = msg.get("examples") or []
            if payload_schema is not None and not examples:
                err(f"{label}: has a payload_schema but no examples")
            for ex in examples:
                for problem in schema.problems(ex, payload_schema or {}):
                    err(f"{label}: example {ex!r} doesn't match its schema: {problem}")
    return out


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ── TBD references ──────────────────────────────────────────────────────────────

def check_tbds(model: Model) -> list[Finding]:
    out = []
    for folder in TBD_CHECKED_DIRS:
        for path in sorted((model.root / folder).rglob("*")):
            if path.suffix not in {".md", ".yaml"} or not path.is_file():
                continue
            rel = str(path.relative_to(model.root))
            for n, line in enumerate(path.read_text().splitlines(), 1):
                for ref in TBD_REF.findall(line):
                    if ref not in model.tbds:
                        out.append(Finding("error", f"{rel}:{n}", f"{ref} is not in the TBD register (docs/TBD.md)"))
                if BARE_TBD.search(line):
                    out.append(Finding("error", f"{rel}:{n}", "bare 'TBD': cite a TBD-NNN from docs/TBD.md"))
    return out


# ── Coverage (gaps) ─────────────────────────────────────────────────────────────

def children_of(model: Model, rid: str) -> list[str]:
    return sorted(c for c, r in model.reqs.items() if rid in (r.get("derives_from") or []))


def check_coverage(model: Model) -> list[Finding]:
    out = []
    live = {rid: r for rid, r in model.reqs.items() if r.get("status") != "deleted"}
    for rid in sorted(live):
        if rid.startswith("SYS-") and not children_of(model, rid):
            out.append(Finding("gap", rid, "system requirement has no children yet (not decomposed)"))
    for iid, icd in sorted(model.icds.items()):
        for side, comps in icd_sides(model, icd).items():
            if not any(r.get("icd") == iid and set(allocations(r)) & comps and r.get("type") == "interface"
                       for r in live.values()):
                out.append(Finding("gap", iid, f"no interface requirement on the {side} side"))
    return out


# ── Topics vs shared/topics.py (warnings) ───────────────────────────────────────

def icd_topics(model: Model) -> dict[str, str]:
    """{topic template: ICD id} for every MQTT message in every ICD."""
    found = {}
    for iid, icd in sorted(model.icds.items()):
        for msg in icd.get("messages") or []:
            if msg.get("topic"):
                found.setdefault(msg["topic"], iid)
    return found


def check_topics(model: Model) -> list[Finding]:
    path = model.root / TOPICS_FILE
    if not path.exists():
        return [Finding("warning", TOPICS_FILE, "not found; topics not compared")]
    shared = shared_topics.topics_in_shared(path)
    return [Finding("warning", where, msg) for where, msg in shared_topics.compare(icd_topics(model), shared)]

