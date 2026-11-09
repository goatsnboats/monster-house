"""Resource budgets: add up what components need against what their host provides.

In docs/architecture/components.yaml:

    a host says what it has:       provides: {memory_mb: 1024, usb_ports: 4}
    a program says what it uses:   needs: {memory_mb: 153}
                                   (taken from whatever it is deployed_on at that stage)
    a part says what it uses,      needs: {usb_ports: 1}
    and from which host:           supplied_by: porch-pi

A host's own needs (for example the operating system's memory) count against its own
provides. An amount is a number, or a TBD-NNN while it isn't known yet.

For every stage 0-5, every host and every resource it provides, the needs present at
that stage are added up. The result is deterministic: the same files always give the
same answer. Over budget is an error. Any TBD makes that budget incomplete, which is a
gap. Requirements that set these limits name this file in verified_by.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tools.reqs.load import Model

STAGES = range(6)
TBD = re.compile(r"^TBD-\d{3}$")


@dataclass
class Budget:
    host: str
    resource: str
    first_stage: int
    last_stage: int
    have: object
    consumers: list[tuple[str, object]] = field(default_factory=list)  # (component, amount)

    @property
    def tbds(self) -> list[str]:
        amounts = [a for _, a in self.consumers] + [self.have]
        return sorted({a for a in amounts if isinstance(a, str)})

    @property
    def need(self) -> float | None:
        if self.tbds:
            return None
        return sum(a for _, a in self.consumers)

    @property
    def status(self) -> str:
        if self.tbds:
            return "incomplete"
        return "over" if self.need > self.have else "ok"

    @property
    def stages(self) -> str:
        return str(self.first_stage) if self.first_stage == self.last_stage else f"{self.first_stage}–{self.last_stage}"


def host_at(comp: dict, stage: int) -> list[str]:
    """Where a program runs at a stage: the latest deployed_on entry at or before it."""
    deployed = comp.get("deployed_on") or {}
    earlier = [s for s in deployed if isinstance(s, int) and s <= stage]
    if not earlier:
        return []
    hosts = deployed[max(earlier)]
    return hosts if isinstance(hosts, list) else [hosts]


def _present(model: Model, cid: str, host_id: str, stage: int) -> bool:
    c = model.comps[cid]
    if cid == host_id:
        return True
    if c.get("kind") == "software":
        return host_id in host_at(c, stage)
    return c.get("supplied_by") == host_id and c.get("stage", 0) <= stage


def evaluate(model: Model) -> list[Budget]:
    budgets: list[Budget] = []
    for host_id, host in sorted(model.comps.items()):
        for resource, have in sorted((host.get("provides") or {}).items()):
            last = None
            for stage in STAGES:
                if host.get("stage", 0) > stage:
                    continue
                consumers = [(cid, (c.get("needs") or {})[resource])
                             for cid, c in sorted(model.comps.items())
                             if resource in (c.get("needs") or {}) and _present(model, cid, host_id, stage)]
                if not consumers:
                    last = None
                    continue
                if last is not None and last.consumers == consumers and last.last_stage == stage - 1:
                    last.last_stage = stage          # same as the stage before: extend the row
                    continue
                last = Budget(host_id, resource, stage, stage, have, consumers)
                budgets.append(last)
    return budgets


def findings(model: Model) -> list[tuple[str, str, str]]:
    """(level, where, message) for the checker."""
    out = []
    for cid, c in sorted(model.comps.items()):
        where = f"components.yaml: {cid}"
        supplier = c.get("supplied_by")
        if supplier and not (model.comps.get(supplier, {}).get("provides")):
            out.append(("error", where, f"supplied_by {supplier!r} is not a component with provides"))
        for key in ("needs", "provides"):
            for resource, amount in (c.get(key) or {}).items():
                ok = (isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount >= 0) \
                    or (isinstance(amount, str) and TBD.match(amount))
                if not ok:
                    out.append(("error", where, f"{key}.{resource} must be a number or a TBD-NNN, not {amount!r}"))
        if c.get("needs") and c.get("kind") == "part" and not supplier and not c.get("provides"):
            out.append(("error", where, "a part with needs must say where they come from (supplied_by)"))

    for b in evaluate(model):
        label = f"budget {b.host}"
        who = ", ".join(f"{cid} {amount}" for cid, amount in b.consumers)
        if b.status == "over":
            out.append(("error", label, f"{b.resource}, stage {b.stages}: needs {b.need} but has {b.have} ({who})"))
        elif b.status == "incomplete":
            out.append(("gap", label, f"{b.resource}, stage {b.stages}: waiting for {', '.join(b.tbds)}"))
    return out
