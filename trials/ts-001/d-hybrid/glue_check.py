"""TS-001 option D trial: cross-check YAML requirements against the SysML architecture.

Runs option A's checks on the requirements, but takes components and ICD IDs from the
short names (<'...'>) in architecture.sysml instead of components.yaml.
Usage: python glue_check.py ROOT --tbd TBD.md
"""
import re, sys, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "a"))
import check  # option A's checker (trial code, same folder tree)

ap = argparse.ArgumentParser(); ap.add_argument("root", type=Path); ap.add_argument("--tbd", type=Path)
a = ap.parse_args()
sysml = (a.root / "architecture.sysml").read_text()
parts = set(re.findall(r"part\s+<'([^']+)'>", sysml))
sysml_icds = set(re.findall(r"interface def\s+<'([^']+)'>", sysml))
reqs = {}
for f in sorted((a.root / "requirements").glob("*.yaml")):
    for r in check.yaml.safe_load(f.read_text()):
        r["_file"] = f.name; reqs[r["id"]] = r
comps = {p: {"id": p} for p in parts}
icd_docs = {p.stem: {"id": p.stem, "ends": {}} for p in (a.root / "interfaces").glob("ICD-*.md")}
errors = check.check(a.root, reqs, comps, icd_docs, a.tbd)
for i in sorted(sysml_icds ^ set(icd_docs)):
    errors.append(f"{i}: must exist both as a SysML interface def and as interfaces/{i}.md")
for e in errors: print("ERROR", e)
print(f"{len(reqs)} requirements, {len(parts)} SysML parts, {len(sysml_icds)} SysML interfaces: {'FAIL' if errors else 'OK'}")
sys.exit(1 if errors else 0)
