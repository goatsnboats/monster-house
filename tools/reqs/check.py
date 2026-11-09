"""Check the requirements baseline and regenerate docs/requirements/trace.md.

Run from the repository root:

    .venv/bin/python -m tools.reqs.check                 # check, then rewrite trace.md
    .venv/bin/python -m tools.reqs.check --no-write      # check only
    .venv/bin/python -m tools.reqs.check --strict        # gaps and warnings fail too
    .venv/bin/python -m tools.reqs.check --impact SYS-004   # what sits below SYS-004?

Exit status: 0 if there are no errors (or, with --strict, no findings at all), else 1.
What each check means: docs/requirements/README.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a plain script: make "tools" importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.reqs.checks import check_all, children_of  # noqa: E402
from tools.reqs.load import TRACE, Model, load  # noqa: E402
from tools.reqs.trace import render  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def impact(model: Model, rid: str) -> list[str]:
    """Everything below a requirement: its descendants, their components and ICDs."""
    out, todo = [], [rid]
    while todo:
        cur = todo.pop(0)
        for child in children_of(model, cur):
            r = model.reqs[child]
            extra = f" → {r.get('allocated_to')}" + (f", {r['icd']}" if r.get("icd") else "")
            out.append(f"{child} (child of {cur}){extra}")
            todo.append(child)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root (default: this repo)")
    ap.add_argument("--no-write", action="store_true", help="don't rewrite docs/requirements/trace.md")
    ap.add_argument("--strict", action="store_true", help="fail on gaps and warnings, not only errors")
    ap.add_argument("--impact", metavar="ID", help="list what sits below a requirement, then stop")
    args = ap.parse_args(argv)

    model = load(args.root)
    if args.impact:
        if args.impact not in model.reqs:
            print(f"{args.impact} is not a requirement")
            return 1
        print("\n".join(impact(model, args.impact)) or "(nothing below it yet)")
        return 0

    findings = check_all(model)
    for level in ("error", "warning", "gap"):
        for f in findings:
            if f.level == level:
                print(f)

    if not args.no_write:
        (args.root / TRACE).write_text(render(model, findings))

    n = {level: sum(f.level == level for f in findings) for level in ("error", "gap", "warning")}
    failed = n["error"] > 0 or (args.strict and (n["gap"] or n["warning"]))
    print(f"\n{len(model.reqs)} requirements, {len(model.comps)} components, {len(model.icds)} ICDs: "
          f"{'FAIL' if failed else 'OK'} ({n['error']} errors, {n['gap']} gaps, {n['warning']} warnings)"
          + ("" if args.no_write else f"; wrote {TRACE}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
